"""Quality monitoring report DAG.

Runs quality checks across all tables and outputs structured results
for Grafana dashboard consumption. Executes after all daily pipelines.

Schedule: Daily at 09:00 UTC (after all pipelines complete).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
from airflow.sdk import DAG

logger = logging.getLogger(__name__)


def _on_failure_callback(context):
    """Failure callback for alerting."""
    dag_id = context.get("dag", {}).dag_id if hasattr(context.get("dag", {}), "dag_id") else "unknown"
    task_id = (
        context.get("task_instance", {}).task_id if hasattr(context.get("task_instance", {}), "task_id") else "unknown"
    )
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

# Spark configuration for quality checks
_spark_conf = {
    "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    "spark.sql.catalog.lakehouse": "org.apache.iceberg.spark.SparkCatalog",
    "spark.sql.catalog.lakehouse.type": "rest",
    "spark.sql.catalog.lakehouse.uri": "{{ var.value.get('nessie_iceberg_uri', 'http://nessie:19120/iceberg') }}",
    "spark.sql.catalog.lakehouse.warehouse": "lakehouse",
    "spark.sql.catalog.lakehouse.io-impl": "org.apache.iceberg.aws.s3.S3FileIO",
    "spark.sql.defaultCatalog": "lakehouse",
}

_spark_packages = "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1"

# Quality check configurations: (table_path, checks_yaml)
_QUALITY_CHECKS = [
    ("bronze.trades", "/opt/airflow/etl_src/quality/checks/bronze_trades.yml"),
    ("silver.trades", "/opt/airflow/etl_src/quality/checks/silver_trades.yml"),
    ("gold.trading_metrics", "/opt/airflow/etl_src/quality/checks/gold_trading_metrics.yml"),
]


with DAG(
    dag_id="quality_monitoring_report",
    schedule="0 9 * * *",
    start_date=None,
    catchup=False,
    default_args=default_args,
    tags=["quality", "monitoring"],
    doc_md="""
    ## Quality Monitoring Report

    Runs comprehensive quality checks across all data layers and
    outputs structured results for Grafana dashboard consumption.

    **Schedule:** Daily at 09:00 UTC (after all pipelines)
    **Output:** Structured quality metrics for observability dashboard
    **Checks:** SodaCL definitions per table
    """,
) as dag:
    # Wait for Gold pipeline to finish (implies Bronze/Silver done too)
    wait_for_gold = ExternalTaskSensor(
        task_id="wait_for_gold_metrics",
        external_dag_id="gold_trading_metrics",
        external_task_id=None,
        timeout=7200,
        poke_interval=60,
        mode="reschedule",
    )

    quality_tasks = []
    for table_path, checks_yaml in _QUALITY_CHECKS:
        namespace, table = table_path.split(".")
        task = SparkSubmitOperator(
            task_id=f"quality_{namespace}_{table}",
            application="/opt/airflow/etl_src/quality/scanner.py",
            application_args=["--checks", checks_yaml, "--table", table_path],
            name=f"quality-{namespace}-{table}",
            conf=_spark_conf,
            packages=_spark_packages,
            verbose=False,
        )
        quality_tasks.append(task)

    # Wait for Gold, then run all quality checks in parallel
    wait_for_gold >> quality_tasks
