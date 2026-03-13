"""Cross-engine audit ETL logic for aggregating audit records.

Provides:
- TrinoAuditExtractor: Fetch audit events from Trino HTTP event receiver
- TeradataAuditExtractor: Extract DBQL audit logs from Teradata
- SnowflakeAuditExtractor: Extract ACCESS_HISTORY from Snowflake (Enterprise)
- aggregate_audit_records(): Insert records into PostgreSQL audit table

Usage::

    from src.governance.audit_aggregator import (
        TrinoAuditExtractor,
        aggregate_audit_records,
    )

    extractor = TrinoAuditExtractor("http://trino-audit-receiver:8888")
    records = extractor.extract(since=datetime(2024, 1, 14, tzinfo=timezone.utc))
    count = aggregate_audit_records(records, "postgresql://user:pass@audit-db:5432/audit")
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class TrinoAuditExtractor:
    """Extract Trino audit events from the HTTP event listener receiver service.

    The Trino HTTP event listener (io.trino.spi.eventlistener.EventListener)
    POSTs query events to a configured receiver endpoint. This extractor
    queries that receiver's REST API to retrieve events since a given timestamp.

    Args:
        audit_receiver_url: Base URL of the Trino audit receiver service.
            E.g. "http://trino-audit-receiver:8888"
    """

    def __init__(self, audit_receiver_url: str):
        self.audit_receiver_url = audit_receiver_url.rstrip("/")
        self._session = None

    def _get_session(self):
        """Lazily create requests session."""
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
            except ImportError:
                raise RuntimeError("requests library required for TrinoAuditExtractor")
        return self._session

    def extract(self, since: datetime) -> list:
        """Fetch Trino audit events since the given timestamp.

        Args:
            since: Fetch events with timestamp >= since (UTC)

        Returns:
            List of AuditRecord objects normalized from Trino events.
            Returns empty list on connection failure (logs warning).
        """
        from src.governance.audit_schema import normalize_trino_audit

        since_iso = since.replace(tzinfo=timezone.utc).isoformat() if since.tzinfo is None else since.isoformat()
        url = f"{self.audit_receiver_url}/api/events"
        params = {"since": since_iso}

        try:
            session = self._get_session()
            response = session.get(url, params=params, timeout=30)
            response.raise_for_status()
            events = response.json()
            records = []
            for event in events:
                try:
                    records.append(normalize_trino_audit(event))
                except Exception as e:
                    logger.warning("Failed to normalize Trino event: %s", e)
            logger.info("Extracted %d Trino audit records since %s", len(records), since_iso)
            return records
        except Exception as e:
            logger.warning(
                "Trino audit extraction failed (receiver at %s): %s. Returning empty.",
                self.audit_receiver_url, e,
            )
            return []


class TeradataAuditExtractor:
    """Extract Teradata DBQL audit logs from DBC.QryLogV.

    Requires Teradata JDBC connectivity. If TERADATA_HOST environment variable
    is not set, extraction is skipped gracefully.

    Args:
        connection_params: Dict with keys: host, username, password, database.
            If None, reads from environment variables (TERADATA_HOST, TERADATA_USER,
            TERADATA_PASSWORD).
    """

    def __init__(self, connection_params: Optional[dict] = None):
        if connection_params:
            self.host = connection_params.get("host", "")
            self.username = connection_params.get("username", "")
            self.password = connection_params.get("password", "")
            self.database = connection_params.get("database", "DBC")
        else:
            self.host = os.environ.get("TERADATA_HOST", "")
            self.username = os.environ.get("TERADATA_USER", "")
            self.password = os.environ.get("TERADATA_PASSWORD", "")
            self.database = os.environ.get("TERADATA_DATABASE", "DBC")

    def _is_available(self) -> bool:
        """Check if Teradata host is configured."""
        return bool(self.host)

    def extract(self, since: datetime) -> list:
        """Extract Teradata DBQL records since the given timestamp.

        Queries DBC.QryLogV and enriches with column-level access from
        DBC.DBQLObjTbl joined by QueryID.

        Args:
            since: Fetch records with StartTime >= since

        Returns:
            List of AuditRecord. Returns empty list if TERADATA_HOST not set
            or connection fails.
        """
        from src.governance.audit_schema import normalize_teradata_audit

        if not self._is_available():
            logger.info("TERADATA_HOST not set -- skipping Teradata audit extraction")
            return []

        try:
            import teradatasql  # type: ignore
        except ImportError:
            logger.info("teradatasql not installed -- skipping Teradata audit extraction")
            return []

        since_str = since.strftime("%Y-%m-%d %H:%M:%S")

        try:
            conn = teradatasql.connect(
                host=self.host,
                user=self.username,
                password=self.password,
            )
            cursor = conn.cursor()

            # Main query log
            cursor.execute("""
                SELECT q.QueryID, q.UserName, q.QueryText, q.StartTime,
                       q.NumResultRows, q.ReqIOKB, q.ErrorCode, q.ErrorText,
                       q.DatabaseName, q.StatementType
                FROM DBC.QryLogV q
                WHERE q.StartTime >= ?
                ORDER BY q.StartTime
            """, [since_str])

            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            dbql_rows = [dict(zip(columns, row)) for row in rows]

            # Enrich with column-level access
            for dbql_row in dbql_rows:
                query_id = dbql_row["QueryID"]
                cursor.execute("""
                    SELECT DatabaseName, TableName, ColumnName
                    FROM DBC.DBQLObjTbl
                    WHERE QueryID = ? AND ObjectType = 'Column'
                """, [query_id])
                col_columns = [col[0] for col in cursor.description]
                col_rows = cursor.fetchall()
                dbql_row["columns"] = [dict(zip(col_columns, r)) for r in col_rows]

            conn.close()

            records = []
            for row in dbql_rows:
                try:
                    records.append(normalize_teradata_audit(row))
                except Exception as e:
                    logger.warning("Failed to normalize Teradata DBQL row: %s", e)

            logger.info("Extracted %d Teradata audit records since %s", len(records), since_str)
            return records

        except Exception as e:
            logger.warning(
                "Teradata audit extraction failed (host=%s): %s. Returning empty.",
                self.host, e,
            )
            return []


class SnowflakeAuditExtractor:
    """Extract Snowflake ACCESS_HISTORY audit records.

    NOTE: ACCESS_HISTORY view requires Snowflake Enterprise edition (pitfall #7).
    Falls back to QUERY_HISTORY when ACCESS_HISTORY is unavailable.

    If SNOWFLAKE_ACCOUNT environment variable is not set, extraction is skipped gracefully.

    Args:
        connection_params: Dict with keys: account, user, password, database, schema, warehouse.
            If None, reads from environment variables (SNOWFLAKE_ACCOUNT, etc.).
    """

    def __init__(self, connection_params: Optional[dict] = None):
        if connection_params:
            self.account = connection_params.get("account", "")
            self.user = connection_params.get("user", "")
            self.password = connection_params.get("password", "")
            self.database = connection_params.get("database", "SNOWFLAKE")
            self.schema = connection_params.get("schema", "ACCOUNT_USAGE")
            self.warehouse = connection_params.get("warehouse", "")
        else:
            self.account = os.environ.get("SNOWFLAKE_ACCOUNT", "")
            self.user = os.environ.get("SNOWFLAKE_USER", "")
            self.password = os.environ.get("SNOWFLAKE_PASSWORD", "")
            self.database = os.environ.get("SNOWFLAKE_DATABASE", "SNOWFLAKE")
            self.schema = os.environ.get("SNOWFLAKE_SCHEMA", "ACCOUNT_USAGE")
            self.warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "")

    def _is_available(self) -> bool:
        """Check if Snowflake account is configured."""
        return bool(self.account)

    def extract(self, since: datetime) -> list:
        """Extract Snowflake access history records since the given timestamp.

        Tries ACCESS_HISTORY first (Enterprise only), falls back to QUERY_HISTORY.

        Args:
            since: Fetch records with QUERY_START_TIME >= since

        Returns:
            List of AuditRecord. Returns empty list if SNOWFLAKE_ACCOUNT not set
            or connection fails.
        """
        from src.governance.audit_schema import normalize_snowflake_audit

        if not self._is_available():
            logger.info("SNOWFLAKE_ACCOUNT not set -- skipping Snowflake audit extraction")
            return []

        try:
            import snowflake.connector  # type: ignore
        except ImportError:
            logger.info("snowflake-connector-python not installed -- skipping Snowflake extraction")
            return []

        since_str = since.strftime("%Y-%m-%d %H:%M:%S")

        try:
            conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                database=self.database,
                schema=self.schema,
                warehouse=self.warehouse,
            )
            cursor = conn.cursor(snowflake.connector.DictCursor)

            # Try ACCESS_HISTORY first (Enterprise edition)
            try:
                cursor.execute("""
                    SELECT
                        QUERY_ID,
                        QUERY_START_TIME,
                        USER_NAME,
                        QUERY_TEXT,
                        DIRECT_OBJECTS_ACCESSED,
                        OBJECTS_MODIFIED,
                        BYTES_SCANNED,
                        ROWS_PRODUCED,
                        EXECUTION_STATUS
                    FROM SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY
                    WHERE QUERY_START_TIME >= %s
                    ORDER BY QUERY_START_TIME
                """, [since_str])
                rows = cursor.fetchall()
                logger.info("Using Snowflake ACCESS_HISTORY (%d rows)", len(rows))

            except Exception as e:
                logger.info(
                    "ACCESS_HISTORY unavailable (may need Enterprise edition): %s. "
                    "Falling back to QUERY_HISTORY.", e
                )
                cursor.execute("""
                    SELECT
                        QUERY_ID,
                        START_TIME AS QUERY_START_TIME,
                        USER_NAME,
                        QUERY_TEXT,
                        '[]'::VARIANT AS DIRECT_OBJECTS_ACCESSED,
                        '[]'::VARIANT AS OBJECTS_MODIFIED,
                        BYTES_SCANNED,
                        ROWS_PRODUCED,
                        EXECUTION_STATUS
                    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
                    WHERE START_TIME >= %s
                    ORDER BY START_TIME
                """, [since_str])
                rows = cursor.fetchall()
                logger.info("Using Snowflake QUERY_HISTORY fallback (%d rows)", len(rows))

            conn.close()

            records = []
            for row in rows:
                row_dict = dict(row) if not isinstance(row, dict) else row
                try:
                    records.append(normalize_snowflake_audit(row_dict))
                except Exception as e:
                    logger.warning("Failed to normalize Snowflake row: %s", e)

            logger.info("Extracted %d Snowflake audit records since %s", len(records), since_str)
            return records

        except Exception as e:
            logger.warning(
                "Snowflake audit extraction failed (account=%s): %s. Returning empty.",
                self.account, e,
            )
            return []


def aggregate_audit_records(records: list, db_connection_string: str) -> int:
    """Insert normalized audit records into the PostgreSQL audit table.

    Creates the audit table if it doesn't exist. Uses batch INSERT for efficiency.
    Skips records that already exist (upsert by audit_id).

    Args:
        records: List of AuditRecord to insert
        db_connection_string: PostgreSQL connection string.
            E.g. "postgresql://audit:audit@marquez-db:5432/audit"

    Returns:
        Count of records successfully inserted (excludes duplicates skipped).

    Raises:
        RuntimeError: If psycopg2 not installed or connection fails.
    """
    if not records:
        logger.info("No audit records to aggregate")
        return 0

    try:
        import psycopg2  # type: ignore
        import psycopg2.extras  # type: ignore
    except ImportError:
        raise RuntimeError("psycopg2-binary required for aggregate_audit_records")

    from src.governance.audit_schema import AUDIT_SCHEMA

    try:
        conn = psycopg2.connect(db_connection_string)
        cursor = conn.cursor()

        # Create audit table if not exists
        col_defs = ", ".join(f"{col} {sql_type}" for col, sql_type in AUDIT_SCHEMA.items())
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS audit_records (
                {col_defs},
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Create indexes for common query patterns
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_records(timestamp);
            CREATE INDEX IF NOT EXISTS idx_audit_engine ON audit_records(engine);
            CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_records(user_name);
        """)

        conn.commit()

        # Batch insert with ON CONFLICT DO NOTHING (idempotent)
        col_names = list(AUDIT_SCHEMA.keys())
        placeholders = ", ".join(["%s"] * len(col_names))
        cols_str = ", ".join(col_names)

        insert_sql = f"""
            INSERT INTO audit_records ({cols_str})
            VALUES ({placeholders})
            ON CONFLICT (audit_id) DO NOTHING
        """

        batch = [r.to_insert_values() for r in records]
        psycopg2.extras.execute_batch(cursor, insert_sql, batch, page_size=500)
        conn.commit()

        inserted = cursor.rowcount if cursor.rowcount >= 0 else len(batch)
        conn.close()

        logger.info("Aggregated %d audit records into PostgreSQL", inserted)
        return inserted

    except Exception as e:
        logger.error("Failed to aggregate audit records: %s", e)
        raise
