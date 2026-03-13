"""Common audit schema definition for cross-engine audit aggregation.

Provides:
- AuditRecord dataclass: common format for audit events from Trino, Teradata, and Snowflake
- AUDIT_SCHEMA: SQL column type mapping for DDL table creation
- normalize_trino_audit(): convert Trino HTTP event listener payload to AuditRecord
- normalize_teradata_audit(): convert Teradata DBQL row to AuditRecord
- normalize_snowflake_audit(): convert Snowflake ACCESS_HISTORY row to AuditRecord

Usage::

    from src.governance.audit_schema import (
        AuditRecord,
        AUDIT_SCHEMA,
        normalize_trino_audit,
        normalize_teradata_audit,
        normalize_snowflake_audit,
    )

    # Normalize Trino event listener payload
    record = normalize_trino_audit(trino_event_payload)
    row = record.to_insert_values()
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# SQL type mapping for audit table DDL creation
AUDIT_SCHEMA: dict[str, str] = {
    "audit_id": "VARCHAR(36) PRIMARY KEY",
    "timestamp": "TIMESTAMPTZ NOT NULL",
    "engine": "VARCHAR(20) NOT NULL",
    "user_name": "VARCHAR(255) NOT NULL",
    "query_id": "VARCHAR(255) NOT NULL",
    "query_text": "TEXT",
    "tables_accessed": "JSONB",
    "columns_accessed": "JSONB",
    "rows_returned": "BIGINT DEFAULT 0",
    "bytes_scanned": "BIGINT DEFAULT 0",
    "masked_columns": "JSONB",
    "access_granted": "BOOLEAN NOT NULL DEFAULT TRUE",
    "source_engine_audit_id": "VARCHAR(255)",
}


@dataclass
class AuditRecord:
    """Common audit record format for cross-engine audit aggregation.

    Normalizes access events from Trino, Teradata, and Snowflake into a
    consistent format for compliance reporting and anomaly detection.

    Attributes:
        audit_id: UUID string identifying this audit record uniquely
        timestamp: UTC datetime when the query was executed
        engine: Source engine ("trino" | "teradata" | "snowflake")
        user_name: User who executed the query
        query_id: Engine-native query identifier
        query_text: SQL text of the query
        tables_accessed: List of {"schema": str, "table": str} dicts
        columns_accessed: List of {"schema": str, "table": str, "column": str} dicts
        rows_returned: Number of rows returned by the query
        bytes_scanned: Bytes read during query execution
        masked_columns: Columns where masking was applied by Ranger policies
        access_granted: True if query completed, False if access was denied
        source_engine_audit_id: The native audit ID from the source engine
    """

    audit_id: str
    timestamp: datetime
    engine: str
    user_name: str
    query_id: str
    query_text: str
    tables_accessed: list[dict[str, str]]
    columns_accessed: list[dict[str, str]]
    rows_returned: int
    bytes_scanned: int
    masked_columns: list[dict[str, str]]
    access_granted: bool
    source_engine_audit_id: str

    def to_dict(self) -> dict[str, Any]:
        """Convert AuditRecord to a plain dictionary for serialization.

        Returns:
            dict with all fields, JSON-serializable. Lists are kept as Python
            objects (not JSON strings) for use with psycopg2 JSONB.
        """
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp,
            "engine": self.engine,
            "user_name": self.user_name,
            "query_id": self.query_id,
            "query_text": self.query_text,
            "tables_accessed": self.tables_accessed,
            "columns_accessed": self.columns_accessed,
            "rows_returned": self.rows_returned,
            "bytes_scanned": self.bytes_scanned,
            "masked_columns": self.masked_columns,
            "access_granted": self.access_granted,
            "source_engine_audit_id": self.source_engine_audit_id,
        }

    def to_insert_values(self) -> tuple:
        """Return ordered tuple matching AUDIT_SCHEMA column order for INSERT statements.

        Returns:
            Tuple of values in AUDIT_SCHEMA key order. List fields are JSON-encoded
            for PostgreSQL compatibility.
        """
        d = self.to_dict()
        values = []
        for col in AUDIT_SCHEMA:
            val = d[col]
            # JSON-encode list/dict fields for PostgreSQL
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            values.append(val)
        return tuple(values)


def normalize_trino_audit(event_payload: dict) -> AuditRecord:
    """Convert a Trino HTTP event listener JSON payload to AuditRecord.

    Handles Trino's QueryCompletedEvent format emitted by the
    io.trino.spi.eventlistener.EventListener HTTP plugin.

    Args:
        event_payload: Dictionary from Trino query event JSON with keys:
            - queryId: Trino query identifier
            - query: SQL text
            - user: Authenticated user name
            - queryState: "FINISHED" | "FAILED" | "CANCELED"
            - queryCompletedEvent.metadata.tables: List of accessed tables
            - queryCompletedEvent.statistics: outputRows, outputBytes

    Returns:
        AuditRecord with engine="trino"
    """
    query_id = event_payload.get("queryId", "")
    query_text = event_payload.get("query", "")
    user_name = event_payload.get("user", "")
    query_state = event_payload.get("queryState", "FINISHED")

    completed = event_payload.get("queryCompletedEvent", {})
    metadata = completed.get("metadata", {})
    statistics = completed.get("statistics", {})
    context = completed.get("context", {})

    # Extract user from context if not at top level
    if not user_name:
        user_name = context.get("user", "unknown")

    # Parse tables accessed
    tables_accessed = []
    raw_tables = metadata.get("tables", [])
    for t in raw_tables:
        tables_accessed.append({
            "schema": t.get("schema", ""),
            "table": t.get("table", ""),
        })

    # Parse column-level access (columns are per-table in Trino event)
    columns_accessed = []
    for t in raw_tables:
        schema = t.get("schema", "")
        table = t.get("table", "")
        for col in t.get("columns", []):
            columns_accessed.append({
                "schema": schema,
                "table": table,
                "column": col if isinstance(col, str) else col.get("name", ""),
            })

    rows_returned = int(statistics.get("outputRows", 0))
    bytes_scanned = int(statistics.get("outputBytes", 0))

    # Access is granted if query completed (FINISHED), denied if FAILED with security error
    access_granted = query_state not in ("FAILED", "CANCELED")

    # Determine timestamp
    ts_str = metadata.get("queryStartTime") or completed.get("createTime")
    if ts_str:
        try:
            timestamp = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.now(timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)

    return AuditRecord(
        audit_id=str(uuid.uuid4()),
        timestamp=timestamp,
        engine="trino",
        user_name=user_name,
        query_id=query_id,
        query_text=query_text,
        tables_accessed=tables_accessed,
        columns_accessed=columns_accessed,
        rows_returned=rows_returned,
        bytes_scanned=bytes_scanned,
        masked_columns=[],  # Ranger masking info not available in Trino event
        access_granted=access_granted,
        source_engine_audit_id=query_id,
    )


def normalize_teradata_audit(dbql_row: dict) -> AuditRecord:
    """Convert a Teradata DBC.QryLogV row to AuditRecord.

    Handles Teradata DBQL (Database Query Log) rows from DBC.QryLogV view.
    Column-level access can be enriched from DBC.DBQLObjTbl joined by QueryID.

    Args:
        dbql_row: Dictionary from Teradata DBQL query with keys:
            - QueryID: Long integer query identifier
            - UserName: Teradata user name
            - QueryText: SQL text (may be truncated to 10,000 chars in DBQL)
            - StartTime: "YYYY-MM-DD HH:MM:SS" timestamp string
            - NumResultRows: Rows returned
            - ReqIOKB: KB of data read (multiply by 1024 for bytes)
            - ErrorCode: 0 means success; non-zero means failure/denial
            - columns: Optional list of {"DatabaseName", "TableName", "ColumnName"} from DBQLObjTbl

    Returns:
        AuditRecord with engine="teradata"
    """
    query_id = str(dbql_row.get("QueryID", ""))
    user_name = str(dbql_row.get("UserName", ""))
    query_text = str(dbql_row.get("QueryText", ""))
    error_code = dbql_row.get("ErrorCode", 0)

    # Parse timestamp
    ts_str = dbql_row.get("StartTime", "")
    try:
        timestamp = datetime.strptime(str(ts_str), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        timestamp = datetime.now(timezone.utc)

    rows_returned = int(dbql_row.get("NumResultRows", 0) or 0)
    req_io_kb = float(dbql_row.get("ReqIOKB", 0) or 0)
    bytes_scanned = int(req_io_kb * 1024)

    # Access is granted if no error; common denial codes: 3523 (no SELECT access),
    # 5012 (no access to database), etc.
    access_granted = (error_code == 0)

    # Extract tables from primary database + table in row
    # Note: full table list requires joining DBC.DBQLObjTbl
    db_name = dbql_row.get("DatabaseName", "")
    tables_accessed = []
    if db_name:
        tables_accessed.append({"schema": db_name, "table": "unknown"})

    # Extract columns from enriched DBQLObjTbl data if available
    columns_accessed = []
    raw_columns = dbql_row.get("columns", [])
    for col in raw_columns:
        columns_accessed.append({
            "schema": col.get("DatabaseName", ""),
            "table": col.get("TableName", ""),
            "column": col.get("ColumnName", ""),
        })
        # Add table to tables_accessed if not already present
        tbl_entry = {"schema": col.get("DatabaseName", ""), "table": col.get("TableName", "")}
        if tbl_entry not in tables_accessed:
            tables_accessed.append(tbl_entry)

    # Remove placeholder if we have real table data
    if len(tables_accessed) > 1 and tables_accessed[0].get("table") == "unknown":
        tables_accessed = tables_accessed[1:]

    return AuditRecord(
        audit_id=str(uuid.uuid4()),
        timestamp=timestamp,
        engine="teradata",
        user_name=user_name,
        query_id=query_id,
        query_text=query_text,
        tables_accessed=tables_accessed,
        columns_accessed=columns_accessed,
        rows_returned=rows_returned,
        bytes_scanned=bytes_scanned,
        masked_columns=[],  # Teradata masking managed by Row Level Security
        access_granted=access_granted,
        source_engine_audit_id=query_id,
    )


def normalize_snowflake_audit(access_history_row: dict) -> AuditRecord:
    """Convert a Snowflake ACCESS_HISTORY view row to AuditRecord.

    Handles Snowflake SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY rows.
    NOTE: ACCESS_HISTORY requires Snowflake Enterprise edition (per pitfall #7).
    Fallback to QUERY_HISTORY fields when ACCESS_HISTORY not available.

    Args:
        access_history_row: Dictionary from Snowflake ACCESS_HISTORY with keys:
            - QUERY_ID: Snowflake query UUID
            - QUERY_START_TIME: ISO timestamp
            - USER_NAME: Snowflake user name
            - QUERY_TEXT: SQL text
            - DIRECT_OBJECTS_ACCESSED: JSONB list of objects accessed
            - BYTES_SCANNED: Bytes scanned
            - ROWS_PRODUCED: Rows returned
            - EXECUTION_STATUS: "SUCCESS" | "FAILED"

    Returns:
        AuditRecord with engine="snowflake"
    """
    query_id = str(access_history_row.get("QUERY_ID", ""))
    user_name = str(access_history_row.get("USER_NAME", ""))
    query_text = str(access_history_row.get("QUERY_TEXT", ""))
    execution_status = str(access_history_row.get("EXECUTION_STATUS", "SUCCESS"))

    # Parse timestamp
    ts_str = access_history_row.get("QUERY_START_TIME", "")
    try:
        # Handle "2024-01-15 10:30:00.000 +0000" format
        ts_clean = str(ts_str).strip()
        if " +0000" in ts_clean or " +00:00" in ts_clean:
            ts_clean = ts_clean.replace(" +0000", "+00:00").replace(" +00:00", "+00:00")
            ts_clean = ts_clean.split("+00:00")[0] + "+00:00"
        timestamp = datetime.fromisoformat(ts_clean.replace(".000+00:00", "+00:00").replace("+00:00+00:00", "+00:00"))
    except (ValueError, TypeError):
        try:
            timestamp = datetime.strptime(str(ts_str)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            timestamp = datetime.now(timezone.utc)

    rows_returned = int(access_history_row.get("ROWS_PRODUCED", 0) or 0)
    bytes_scanned = int(access_history_row.get("BYTES_SCANNED", 0) or 0)
    access_granted = execution_status.upper() == "SUCCESS"

    # Parse tables and columns from DIRECT_OBJECTS_ACCESSED JSONB
    tables_accessed = []
    columns_accessed = []

    direct_objects = access_history_row.get("DIRECT_OBJECTS_ACCESSED", [])
    if isinstance(direct_objects, str):
        try:
            direct_objects = json.loads(direct_objects)
        except json.JSONDecodeError:
            direct_objects = []

    for obj in direct_objects:
        obj_name = obj.get("objectName", "")
        # Snowflake object names are fully qualified: DATABASE.SCHEMA.TABLE
        parts = obj_name.split(".")
        if len(parts) >= 3:
            schema = parts[1]
            table = parts[2]
        elif len(parts) == 2:
            schema = parts[0]
            table = parts[1]
        else:
            schema = ""
            table = obj_name

        table_entry = {"schema": schema, "table": table}
        if table_entry not in tables_accessed:
            tables_accessed.append(table_entry)

        # Extract column-level access
        for col in obj.get("columns", []):
            col_name = col.get("columnName", "")
            if col_name:
                columns_accessed.append({
                    "schema": schema,
                    "table": table,
                    "column": col_name,
                })

    return AuditRecord(
        audit_id=str(uuid.uuid4()),
        timestamp=timestamp,
        engine="snowflake",
        user_name=user_name,
        query_id=query_id,
        query_text=query_text,
        tables_accessed=tables_accessed,
        columns_accessed=columns_accessed,
        rows_returned=rows_returned,
        bytes_scanned=bytes_scanned,
        masked_columns=[],  # Snowflake masking policies tracked separately
        access_granted=access_granted,
        source_engine_audit_id=query_id,
    )
