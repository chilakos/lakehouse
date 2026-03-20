"""Airflow DAG: Daily cross-engine audit aggregation.

Extracts audit records from Trino (HTTP event listener), Teradata (DBQL),
and Snowflake (ACCESS_HISTORY) then inserts into PostgreSQL audit table.
Teradata and Snowflake extractors are skipped gracefully if connection
environment variables are not set.

Schedule: Daily at 02:00 UTC (runs after all ETL pipelines complete)
Owner: governance-team
"""

from __future__ import annotations

import contextlib
import logging
import os
from datetime import UTC, datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

# Default connection parameters from environment
_AUDIT_RECEIVER_URL = os.environ.get("TRINO_AUDIT_RECEIVER_URL", "http://trino-audit-receiver:8888")
_AUDIT_DB_CONN = os.environ.get(
    "AUDIT_DB_CONNECTION",
    "postgresql://marquez:marquez@marquez-db:5432/marquez",
)

default_args = {
    "owner": "governance-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
}


def _extract_trino_audit(**context) -> int:
    """Extract Trino audit events from HTTP event receiver."""
    from src.governance.audit_aggregator import TrinoAuditExtractor

    # Extract yesterday's records
    logical_date = context["logical_date"]
    since = datetime(logical_date.year, logical_date.month, logical_date.day, tzinfo=UTC) - timedelta(days=1)

    extractor = TrinoAuditExtractor(_AUDIT_RECEIVER_URL)
    records = extractor.extract(since=since)

    # Push records to XCom (convert to dict for serialization)
    context["ti"].xcom_push(key="trino_records_count", value=len(records))
    # Store serialized records in a temp file for aggregate step
    import json
    import tempfile

    if records:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix=f"trino_audit_{since.strftime('%Y%m%d')}_",
            delete=False,
        ) as tmp:
            json.dump([r.to_dict() for r in records], tmp, default=str)
        context["ti"].xcom_push(key="trino_records_file", value=tmp.name)
        logger.info("Extracted %d Trino audit records, saved to %s", len(records), tmp.name)
    else:
        context["ti"].xcom_push(key="trino_records_file", value=None)

    return len(records)


def _extract_teradata_audit(**context) -> int:
    """Extract Teradata DBQL audit records. Skips if TERADATA_HOST not set."""
    from src.governance.audit_aggregator import TeradataAuditExtractor

    if not os.environ.get("TERADATA_HOST"):
        logger.info("TERADATA_HOST not set -- skipping Teradata audit extraction")
        context["ti"].xcom_push(key="teradata_records_file", value=None)
        return 0

    logical_date = context["logical_date"]
    since = datetime(logical_date.year, logical_date.month, logical_date.day, tzinfo=UTC) - timedelta(days=1)

    extractor = TeradataAuditExtractor()
    records = extractor.extract(since=since)

    import json
    import tempfile

    if records:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix=f"td_audit_{since.strftime('%Y%m%d')}_",
            delete=False,
        ) as tmp:
            json.dump([r.to_dict() for r in records], tmp, default=str)
        context["ti"].xcom_push(key="teradata_records_file", value=tmp.name)
    else:
        context["ti"].xcom_push(key="teradata_records_file", value=None)

    return len(records)


def _extract_snowflake_audit(**context) -> int:
    """Extract Snowflake ACCESS_HISTORY audit records. Skips if SNOWFLAKE_ACCOUNT not set."""
    from src.governance.audit_aggregator import SnowflakeAuditExtractor

    if not os.environ.get("SNOWFLAKE_ACCOUNT"):
        logger.info("SNOWFLAKE_ACCOUNT not set -- skipping Snowflake audit extraction")
        context["ti"].xcom_push(key="snowflake_records_file", value=None)
        return 0

    logical_date = context["logical_date"]
    since = datetime(logical_date.year, logical_date.month, logical_date.day, tzinfo=UTC) - timedelta(days=1)

    extractor = SnowflakeAuditExtractor()
    records = extractor.extract(since=since)

    import json
    import tempfile

    if records:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix=f"sf_audit_{since.strftime('%Y%m%d')}_",
            delete=False,
        ) as tmp:
            json.dump([r.to_dict() for r in records], tmp, default=str)
        context["ti"].xcom_push(key="snowflake_records_file", value=tmp.name)
    else:
        context["ti"].xcom_push(key="snowflake_records_file", value=None)

    return len(records)


def _aggregate_records(**context) -> int:
    """Aggregate all extracted audit records into PostgreSQL."""
    import json
    import os as _os

    from src.governance.audit_aggregator import aggregate_audit_records
    from src.governance.audit_schema import AuditRecord

    all_records = []
    for key in ["trino_records_file", "teradata_records_file", "snowflake_records_file"]:
        file_path = context["ti"].xcom_pull(key=key)
        if file_path and _os.path.exists(file_path):
            with open(file_path) as f:
                raw_records = json.load(f)
            for r in raw_records:
                # Reconstruct AuditRecord from dict
                try:
                    from datetime import datetime

                    r["timestamp"] = datetime.fromisoformat(r["timestamp"])
                    all_records.append(AuditRecord(**r))
                except Exception as e:
                    logger.warning("Failed to reconstruct AuditRecord from dict: %s", e)
            # Clean up temp file
            with contextlib.suppress(Exception):
                _os.unlink(file_path)

    logger.info("Aggregating %d total audit records", len(all_records))
    inserted = aggregate_audit_records(all_records, _AUDIT_DB_CONN)
    return inserted


def _archive_old_records(**context) -> int:
    """Archive audit records older than 90 days to S3 Parquet."""
    from src.governance.audit_archiver import archive_old_records

    s3_bucket = os.environ.get("AUDIT_ARCHIVE_S3_BUCKET", "lakehouse-audit-archive")

    try:
        count = archive_old_records(
            db_connection_string=_AUDIT_DB_CONN,
            s3_bucket=s3_bucket,
            archive_after_days=90,
        )
        logger.info("Archived %d records to s3://%s/audit", count, s3_bucket)
        return count
    except Exception as e:
        logger.warning("Audit archival failed (non-critical): %s", e)
        return 0


with DAG(
    dag_id="governance_audit_aggregation",
    description="Daily cross-engine audit ETL: Trino + Teradata + Snowflake -> PostgreSQL",
    schedule="0 2 * * *",  # Daily at 02:00 UTC
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    catchup=False,
    default_args=default_args,
    tags=["governance", "audit", "compliance"],
    doc_md=__doc__,
) as dag:
    extract_trino_audit = PythonOperator(
        task_id="extract_trino_audit",
        python_callable=_extract_trino_audit,
    )

    extract_teradata_audit = PythonOperator(
        task_id="extract_teradata_audit",
        python_callable=_extract_teradata_audit,
    )

    extract_snowflake_audit = PythonOperator(
        task_id="extract_snowflake_audit",
        python_callable=_extract_snowflake_audit,
    )

    aggregate_records = PythonOperator(
        task_id="aggregate_records",
        python_callable=_aggregate_records,
    )

    archive_old_records = PythonOperator(
        task_id="archive_old_records",
        python_callable=_archive_old_records,
    )

    # All extract tasks run in parallel, then aggregate, then archive
    [extract_trino_audit, extract_teradata_audit, extract_snowflake_audit] >> aggregate_records
    aggregate_records >> archive_old_records
