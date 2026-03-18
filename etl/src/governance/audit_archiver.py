"""Audit record archival to S3 Parquet for long-term retention.

Provides:
- archive_old_records(): Archive PostgreSQL audit records older than N days to S3 Parquet

Retention policy (configure on S3 bucket):
- Active in PostgreSQL: 0-90 days
- S3 Standard (Parquet): 90 days - 3 years
- S3 Intelligent-Tiering or S3-IA: 3-7 years
- Glacier Deep Archive: 7+ years (regulatory minimum for BCBS 239)

S3 Bucket policy example (configure via Terraform in infra/):
    {
        "Rules": [
            {
                "ID": "AuditArchiveToInfrequentAccess",
                "Status": "Enabled",
                "Filter": {"Prefix": "audit/"},
                "Transitions": [
                    {"Days": 1095, "StorageClass": "STANDARD_IA"},   // 3 years
                    {"Days": 2555, "StorageClass": "GLACIER"}          // 7 years
                ]
            }
        ]
    }

Usage::

    from src.governance.audit_archiver import archive_old_records

    count = archive_old_records(
        db_connection_string="postgresql://audit:audit@marquez-db:5432/audit",
        s3_bucket="lakehouse-audit-archive",
        archive_after_days=90,
    )
    print(f"Archived {count} records to S3")
"""

from __future__ import annotations

import io
import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


def archive_old_records(
    db_connection_string: str,
    s3_bucket: str,
    archive_after_days: int = 90,
    s3_prefix: str = "audit",
    dry_run: bool = False,
) -> int:
    """Archive audit records older than archive_after_days to S3 Parquet.

    Query audit records older than the cutoff date, write them to S3 as Parquet
    files partitioned by year/month, then delete archived records from PostgreSQL.

    Args:
        db_connection_string: PostgreSQL connection string for the audit database
        s3_bucket: S3 bucket name for archive storage
        archive_after_days: Records older than this many days are archived. Default 90.
        s3_prefix: S3 key prefix for archived files. Default "audit".
            Files written as: s3://{bucket}/{prefix}/year={Y}/month={M}/audit_{Y}{M}.parquet
        dry_run: If True, query and log records to archive but don't write S3 or delete.
            Default False.

    Returns:
        Count of records archived (written to S3 and deleted from PostgreSQL).
        Returns 0 if no records to archive or in dry_run mode.

    Raises:
        RuntimeError: If required libraries (psycopg2, boto3, pyarrow) are not installed.
        Exception: On PostgreSQL connection failure or S3 write failure.
    """
    try:
        import psycopg2  # type: ignore
        import psycopg2.extras  # type: ignore
    except ImportError as err:
        raise RuntimeError("psycopg2-binary required for archive_old_records") from err

    try:
        import boto3  # type: ignore
    except ImportError as err:
        raise RuntimeError("boto3 required for archive_old_records") from err

    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except ImportError as err:
        raise RuntimeError("pyarrow required for archive_old_records") from err

    cutoff_date = datetime.now(UTC) - timedelta(days=archive_after_days)
    logger.info(
        "Archiving audit records older than %s (%d days) from %s to s3://%s/%s",
        cutoff_date.strftime("%Y-%m-%d"),
        archive_after_days,
        db_connection_string.split("@")[-1],  # Log host only, not credentials
        s3_bucket,
        s3_prefix,
    )

    conn = psycopg2.connect(db_connection_string)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Query records to archive
    cursor.execute(
        """
        SELECT
            audit_id, timestamp, engine, user_name, query_id, query_text,
            tables_accessed, columns_accessed, rows_returned, bytes_scanned,
            masked_columns, access_granted, source_engine_audit_id
        FROM audit_records
        WHERE timestamp < %s
        ORDER BY timestamp
    """,
        [cutoff_date],
    )

    rows = cursor.fetchall()

    if not rows:
        logger.info("No audit records older than %d days to archive", archive_after_days)
        conn.close()
        return 0

    logger.info("Found %d records to archive", len(rows))

    if dry_run:
        logger.info("Dry run mode: skipping S3 write and PostgreSQL delete")
        conn.close()
        return 0

    # Group records by year/month for partitioned Parquet files
    by_month: dict[tuple[int, int], list] = {}
    for row in rows:
        ts = row["timestamp"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        key = (ts.year, ts.month)
        by_month.setdefault(key, []).append(dict(row))

    s3_client = boto3.client("s3")
    total_archived = 0

    for (year, month), month_rows in sorted(by_month.items()):
        # Convert to PyArrow table
        # Convert complex fields from JSON string to str for Parquet
        for row in month_rows:
            for field in ["tables_accessed", "columns_accessed", "masked_columns"]:
                if isinstance(row[field], (list, dict)):
                    import json

                    row[field] = json.dumps(row[field])
            # Convert datetime to ISO string for Parquet compatibility
            if isinstance(row["timestamp"], datetime):
                row["timestamp"] = row["timestamp"].isoformat()

        schema = pa.schema(
            [
                pa.field("audit_id", pa.string()),
                pa.field("timestamp", pa.string()),
                pa.field("engine", pa.string()),
                pa.field("user_name", pa.string()),
                pa.field("query_id", pa.string()),
                pa.field("query_text", pa.string()),
                pa.field("tables_accessed", pa.string()),
                pa.field("columns_accessed", pa.string()),
                pa.field("rows_returned", pa.int64()),
                pa.field("bytes_scanned", pa.int64()),
                pa.field("masked_columns", pa.string()),
                pa.field("access_granted", pa.bool_()),
                pa.field("source_engine_audit_id", pa.string()),
            ]
        )

        arrays = {col: [row.get(col) for row in month_rows] for col in schema.names}
        table = pa.table(arrays, schema=schema)

        # Write to Parquet buffer
        buf = io.BytesIO()
        pq.write_table(table, buf, compression="snappy")
        buf.seek(0)

        # Upload to S3
        s3_key = f"{s3_prefix}/year={year}/month={month:02d}/audit_{year}{month:02d}.parquet"
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_key,
            Body=buf.read(),
            ContentType="application/octet-stream",
        )
        logger.info(
            "Archived %d records to s3://%s/%s",
            len(month_rows),
            s3_bucket,
            s3_key,
        )
        total_archived += len(month_rows)

    # Delete archived records from PostgreSQL
    audit_ids = [row["audit_id"] for row in rows]
    cursor.execute(
        "DELETE FROM audit_records WHERE audit_id = ANY(%s)",
        [audit_ids],
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    logger.info(
        "Archive complete: %d records written to S3, %d deleted from PostgreSQL",
        total_archived,
        deleted,
    )
    return total_archived
