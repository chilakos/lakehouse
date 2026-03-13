"""Production Bronze-Silver positions pipeline DAG.

Ingests raw position data into Bronze layer, runs quality checks at each
boundary, then transforms to Silver entity-centric format. Follows the
hybrid DAG pattern: source-specific Bronze-to-Silver.

Lineage: Tracked via OpenLineage -> Marquez.
Schedule: Daily at 06:30 UTC (offset from trades).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from airflow.sdk import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

logger = logging.getLogger(__name__)


def _on_failure_callback(context):
    """Failure callback for alerting (PagerDuty/Slack in production)."""
    dag_id = context.get("dag", {}).dag_id if hasattr(context.get("dag", {}), "dag_id") else "unknown"
    task_id = context.get("task_instance", {}).task_id if hasattr(context.get("task_instance", {}), "task_id") else "unknown"
    logger.error(
        "Task failed: dag_id=%s, task_id=%s, execution_date=%s",
        dag_id, task_id, context.get("execution_date", "unknown"),
    )


# Locked decision: retries=3, exponential backoff
default_args = {
    "owner": "data-engineering",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "on_failure_callback": _on_failure_callback,
}

# OpenLineage Spark configuration
_spark_openlineage_conf = {
    "spark.extraListeners": "io.openlineage.spark.agent.OpenLineageSparkListener",
    "spark.openlineage.transport.type": "http",
    "spark.openlineage.transport.url": "{{ var.value.get('marquez_url', 'http://marquez:5000') }}",
    "spark.openlineage.transport.endpoint": "api/v1/lineage",
    "spark.openlineage.namespace": "lakehouse",
}

# Base Spark configuration for Iceberg REST catalog
_spark_iceberg_conf = {
    "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    "spark.sql.catalog.lakehouse": "org.apache.iceberg.spark.SparkCatalog",
    "spark.sql.catalog.lakehouse.type": "rest",
    "spark.sql.catalog.lakehouse.uri": "{{ var.value.get('nessie_iceberg_uri', 'http://nessie:19120/iceberg') }}",
    "spark.sql.catalog.lakehouse.warehouse": "lakehouse",
    "spark.sql.catalog.lakehouse.io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
    "spark.sql.defaultCatalog": "lakehouse",
}

_spark_conf = {**_spark_iceberg_conf, **_spark_openlineage_conf}
_spark_packages = (
    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1,"
    "io.openlineage:openlineage-spark_2.12:1.25.0"
)


with DAG(
    dag_id="bronze_silver_positions",
    schedule="30 6 * * *",
    start_date=None,
    catchup=False,
    default_args=default_args,
    tags=["bronze", "silver", "positions"],
    doc_md="""
    ## Bronze-Silver Positions Pipeline

    Ingests raw position data into Bronze layer with metadata columns,
    runs quality checks, transforms to Silver entity-centric format.

    **Schedule:** Daily at 06:30 UTC
    **Lineage:** Tracked via OpenLineage -> Marquez
    **Quality:** Soda Core gates at Bronze and Silver boundaries
    """,
) as dag:

    ingest_positions_bronze = SparkSubmitOperator(
        task_id="ingest_positions_bronze",
        application="/opt/airflow/etl_src/pipelines/bronze/positions_ingest.py",
        name="bronze-positions-ingest",
        conf=_spark_conf,
        packages=_spark_packages,
        verbose=False,
    )

    quality_check_bronze_positions = SparkSubmitOperator(
        task_id="quality_check_bronze_positions",
        application="/opt/airflow/etl_src/quality/scanner.py",
        application_args=["--checks", "/opt/airflow/etl_src/quality/checks/bronze_positions.yml"],
        name="bronze-positions-quality",
        conf=_spark_conf,
        packages=_spark_packages,
        verbose=False,
    )

    transform_positions_silver = SparkSubmitOperator(
        task_id="transform_positions_silver",
        application="/opt/airflow/etl_src/pipelines/silver/positions_clean.py",
        name="silver-positions-transform",
        conf=_spark_conf,
        packages=_spark_packages,
        verbose=False,
    )

    quality_check_silver_positions = SparkSubmitOperator(
        task_id="quality_check_silver_positions",
        application="/opt/airflow/etl_src/quality/scanner.py",
        application_args=["--checks", "/opt/airflow/etl_src/quality/checks/silver_positions.yml"],
        name="silver-positions-quality",
        conf=_spark_conf,
        packages=_spark_packages,
        verbose=False,
    )

    # Dependency chain: ingest -> quality -> transform -> quality
    ingest_positions_bronze >> quality_check_bronze_positions >> transform_positions_silver >> quality_check_silver_positions
