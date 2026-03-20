"""Production Gold trading metrics pipeline DAG.

Reads from Silver trades table and computes aggregated trading metrics.
Follows the hybrid DAG pattern: separate Gold DAG for cross-source aggregation.
Uses ExternalTaskSensor to wait for Bronze/Silver DAGs to complete.

Lineage: Tracked via OpenLineage -> Marquez.
Schedule: Daily at 08:00 UTC (after Bronze/Silver pipelines complete).
"""

from __future__ import annotations

import logging
from datetime import timedelta

from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.standard.sensors.external_task import ExternalTaskSensor
from airflow.sdk import DAG

logger = logging.getLogger(__name__)


def _on_failure_callback(context):
    """Failure callback for alerting (PagerDuty/Slack in production)."""
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
_spark_packages = "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1,io.openlineage:openlineage-spark_2.12:1.25.0"


with DAG(
    dag_id="gold_trading_metrics",
    schedule="0 8 * * *",
    start_date=None,
    catchup=False,
    default_args=default_args,
    tags=["gold", "metrics"],
    doc_md="""
    ## Gold Trading Metrics Pipeline

    Reads cleaned Silver trades and computes pre-aggregated metrics
    (total_notional, trade_count, avg_price) per symbol and side.

    **Schedule:** Daily at 08:00 UTC (after Bronze/Silver complete)
    **Dependencies:** Waits for bronze_silver_trades and bronze_silver_positions DAGs
    **Lineage:** Tracked via OpenLineage -> Marquez
    """,
) as dag:
    # Wait for Bronze/Silver trades pipeline to complete
    wait_for_trades = ExternalTaskSensor(
        task_id="wait_for_trades_silver",
        external_dag_id="bronze_silver_trades",
        external_task_id=None,  # Wait for entire DAG
        timeout=7200,  # 2 hours max wait
        poke_interval=60,
        mode="reschedule",
    )

    # Wait for Bronze/Silver positions pipeline to complete
    wait_for_positions = ExternalTaskSensor(
        task_id="wait_for_positions_silver",
        external_dag_id="bronze_silver_positions",
        external_task_id=None,
        timeout=7200,
        poke_interval=60,
        mode="reschedule",
    )

    # Compute Gold trading metrics
    compute_trading_metrics = SparkSubmitOperator(
        task_id="compute_trading_metrics",
        application="/opt/airflow/etl_src/pipelines/gold/trading_metrics.py",
        name="gold-trading-metrics",
        conf=_spark_conf,
        packages=_spark_packages,
        verbose=False,
    )

    # Wait for both Bronze/Silver DAGs before computing Gold
    [wait_for_trades, wait_for_positions] >> compute_trading_metrics
