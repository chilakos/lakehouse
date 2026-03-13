"""Example Bronze-Silver trades pipeline DAG.

Demonstrates Airflow 3.x patterns with SparkSubmitOperator for a
medallion architecture pipeline: Bronze ingestion -> Quality check -> Silver transform.

Uses OpenLineage for automatic lineage capture via Airflow provider configuration.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from airflow.sdk import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

logger = logging.getLogger(__name__)


def _on_failure_callback(context):
    """Placeholder failure callback for alerting.

    In production, this would send alerts to PagerDuty, Slack, or email.
    """
    dag_id = context.get("dag", {}).dag_id if hasattr(context.get("dag", {}), "dag_id") else "unknown"
    task_id = context.get("task_instance", {}).task_id if hasattr(context.get("task_instance", {}), "task_id") else "unknown"
    logger.error(
        "Task failed: dag_id=%s, task_id=%s, execution_date=%s",
        dag_id,
        task_id,
        context.get("execution_date", "unknown"),
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

# OpenLineage Spark configuration passed to all SparkSubmitOperators
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

# Merge all Spark configs
_spark_conf = {**_spark_iceberg_conf, **_spark_openlineage_conf}

# Spark packages (Iceberg runtime + OpenLineage agent)
_spark_packages = (
    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1,"
    "io.openlineage:openlineage-spark_2.12:1.25.0"
)


with DAG(
    dag_id="example_bronze_silver_trades",
    schedule="0 6 * * *",
    start_date=None,
    catchup=False,
    default_args=default_args,
    tags=["bronze", "silver", "trades", "example"],
    doc_md="""
    ## Bronze-Silver Trades Pipeline

    Ingests raw trade data into Bronze layer, runs quality checks,
    then transforms to Silver entity-centric format.

    **Lineage:** Tracked via OpenLineage -> Marquez
    """,
) as dag:

    ingest = SparkSubmitOperator(
        task_id="ingest_bronze_trades",
        application="/opt/airflow/etl_src/pipelines/bronze_trades.py",
        name="bronze-trades-ingest",
        conf=_spark_conf,
        packages=_spark_packages,
        verbose=False,
    )

    quality_check = SparkSubmitOperator(
        task_id="quality_check_trades",
        application="/opt/airflow/etl_src/pipelines/quality_trades.py",
        name="trades-quality-check",
        conf=_spark_conf,
        packages=_spark_packages,
        verbose=False,
    )

    transform = SparkSubmitOperator(
        task_id="transform_silver_trades",
        application="/opt/airflow/etl_src/pipelines/silver_trades.py",
        name="silver-trades-transform",
        conf=_spark_conf,
        packages=_spark_packages,
        verbose=False,
    )

    # Dependency: ingest -> quality_check -> transform
    ingest >> quality_check >> transform
