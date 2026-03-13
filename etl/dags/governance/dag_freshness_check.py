"""Airflow DAG: Data freshness SLA monitoring every 2 hours.

Checks freshness status for all monitored tables using the freshness_tracker
module and writes results to a PostgreSQL metrics table for Grafana queries.

Schedule: Every 2 hours (*/2 * * * *)
Owner: governance-team
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

_AUDIT_DB_CONN = os.environ.get(
    "AUDIT_DB_CONNECTION",
    "postgresql://marquez:marquez@marquez-db:5432/marquez",
)

# Tables to monitor with their SLA configs (key: table name, value: SLA pattern)
_MONITORED_TABLES = {
    "gold.trades_daily": "gold.*",
    "gold.positions_daily": "gold.*",
    "gold.counterparty_master": "gold.*",
    "gold.trading_metrics": "gold.*",
    "silver.trades_enriched": "silver.*",
    "silver.positions_enriched": "silver.*",
    "bronze.raw_trades": "bronze.*",
    "bronze.raw_positions": "bronze.*",
}

default_args = {
    "owner": "governance-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def _check_freshness(**context) -> list[dict]:
    """Check data freshness for all monitored tables.

    Queries the Iceberg table metadata (or a dedicated last_updated table)
    for the latest update timestamp, then evaluates SLA status.
    """
    from src.governance.freshness_tracker import DEFAULT_SLAS, FreshnessSLA, get_all_freshness

    # Build SLA map for monitored tables
    table_slas = {}
    for table_name, pattern in _MONITORED_TABLES.items():
        sla_template = DEFAULT_SLAS.get(pattern)
        if sla_template:
            table_slas[table_name] = FreshnessSLA(
                table_name=table_name,
                expected_update_interval_hours=sla_template.expected_update_interval_hours,
                warning_threshold_hours=sla_template.warning_threshold_hours,
                critical_threshold_hours=sla_template.critical_threshold_hours,
            )

    # Fetch last_updated timestamps from PostgreSQL metadata table
    last_updated_map = {}
    try:
        import psycopg2  # type: ignore

        conn = psycopg2.connect(_AUDIT_DB_CONN)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT table_name, last_updated
            FROM table_freshness_metadata
            WHERE table_name = ANY(%s)
        """, [list(table_slas.keys())])
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            last_updated_map[row[0]] = row[1]

    except Exception as e:
        logger.warning(
            "Could not fetch table metadata from PostgreSQL: %s. "
            "Using None (all tables will show RED status).", e
        )

    # Run freshness check
    results = get_all_freshness(table_slas, last_updated_map)
    logger.info(
        "Freshness check complete: %d GREEN, %d YELLOW, %d RED",
        sum(1 for r in results if r["status"].value == "On time"),
        sum(1 for r in results if r["status"].value == "Warning"),
        sum(1 for r in results if r["status"].value == "Stale"),
    )

    # Serialize for XCom (convert enum to string)
    serializable = []
    for r in results:
        serializable.append({
            "table": r["table"],
            "status": r["status"].value,
            "hours_since_update": r["hours_since_update"],
            "sla_hours": r["sla_hours"],
            "badge_status": r["badge"]["status"],
            "badge_label": r["badge"]["label"],
        })

    context["ti"].xcom_push(key="freshness_results", value=serializable)
    return serializable


def _update_metrics(**context) -> int:
    """Write freshness status results to PostgreSQL metrics table for Grafana.

    Creates the freshness_metrics table if it doesn't exist.
    Upserts one row per table with the latest status check timestamp.
    """
    results = context["ti"].xcom_pull(key="freshness_results")
    if not results:
        logger.warning("No freshness results to write")
        return 0

    try:
        import psycopg2  # type: ignore

        conn = psycopg2.connect(_AUDIT_DB_CONN)
        cursor = conn.cursor()

        # Create metrics table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS freshness_metrics (
                table_name VARCHAR(255) PRIMARY KEY,
                status VARCHAR(20) NOT NULL,
                hours_since_update FLOAT,
                sla_hours FLOAT,
                badge_status VARCHAR(10),
                badge_label VARCHAR(20),
                checked_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()

        # Upsert freshness status per table
        for result in results:
            cursor.execute("""
                INSERT INTO freshness_metrics
                    (table_name, status, hours_since_update, sla_hours, badge_status, badge_label, checked_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (table_name) DO UPDATE SET
                    status = EXCLUDED.status,
                    hours_since_update = EXCLUDED.hours_since_update,
                    sla_hours = EXCLUDED.sla_hours,
                    badge_status = EXCLUDED.badge_status,
                    badge_label = EXCLUDED.badge_label,
                    checked_at = NOW()
            """, [
                result["table"],
                result["status"],
                result["hours_since_update"],
                result["sla_hours"],
                result["badge_status"],
                result["badge_label"],
            ])

        conn.commit()
        conn.close()

        logger.info("Updated freshness metrics for %d tables", len(results))
        return len(results)

    except Exception as e:
        logger.warning("Failed to update freshness metrics in PostgreSQL: %s", e)
        return 0


with DAG(
    dag_id="governance_freshness_check",
    description="Data freshness SLA check every 2 hours, writes to PostgreSQL for Grafana",
    schedule="0 */2 * * *",  # Every 2 hours
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    default_args=default_args,
    tags=["governance", "freshness", "sla", "monitoring"],
    doc_md=__doc__,
) as dag:

    check_freshness = PythonOperator(
        task_id="check_freshness",
        python_callable=_check_freshness,
    )

    update_metrics = PythonOperator(
        task_id="update_metrics",
        python_callable=_update_metrics,
    )

    check_freshness >> update_metrics
