"""Iceberg table maintenance DAG.

Runs weekly maintenance operations on all Iceberg tables:
compaction, snapshot expiration, orphan file cleanup, and manifest rewriting.
Uses maintenance.py functions via SparkSubmitOperator.

Schedule: Weekly Sunday at 02:00 UTC.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from airflow.sdk import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

logger = logging.getLogger(__name__)


def _on_failure_callback(context):
    """Failure callback for alerting."""
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

# Spark configuration (Iceberg only -- no OpenLineage for maintenance)
_spark_iceberg_conf = {
    "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    "spark.sql.catalog.lakehouse": "org.apache.iceberg.spark.SparkCatalog",
    "spark.sql.catalog.lakehouse.type": "rest",
    "spark.sql.catalog.lakehouse.uri": "{{ var.value.get('nessie_iceberg_uri', 'http://nessie:19120/iceberg') }}",
    "spark.sql.catalog.lakehouse.warehouse": "lakehouse",
    "spark.sql.catalog.lakehouse.io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
    "spark.sql.defaultCatalog": "lakehouse",
}

_spark_packages = "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1"

# Tables to maintain (namespace.table_name)
_TABLES = [
    ("bronze", "trades"),
    ("bronze", "positions"),
    ("silver", "trades"),
    ("silver", "positions"),
    ("gold", "trading_metrics"),
]


with DAG(
    dag_id="iceberg_maintenance",
    schedule="0 2 * * 0",
    start_date=None,
    catchup=False,
    default_args=default_args,
    tags=["maintenance", "iceberg"],
    doc_md="""
    ## Iceberg Table Maintenance

    Weekly maintenance for all Iceberg tables:
    - Compaction (rewrite small files into larger ones)
    - Snapshot expiration (remove old snapshots)
    - Orphan file cleanup (remove unreferenced files)
    - Manifest rewriting (optimize for faster query planning)

    **Schedule:** Weekly Sunday at 02:00 UTC
    **Tables:** All Bronze, Silver, and Gold tables
    """,
) as dag:

    for namespace, table in _TABLES:
        maintenance_task = SparkSubmitOperator(
            task_id=f"maintain_{namespace}_{table}",
            application="/opt/airflow/etl_src/iceberg_utils/maintenance.py",
            application_args=["--namespace", namespace, "--table", table],
            name=f"maintain-{namespace}-{table}",
            conf=_spark_iceberg_conf,
            packages=_spark_packages,
            verbose=False,
        )
