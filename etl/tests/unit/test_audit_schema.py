"""Unit tests for audit_schema module.

Tests AuditRecord dataclass, AUDIT_SCHEMA constant, and cross-engine
normalization functions (Trino, Teradata, Snowflake).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest


class TestAuditRecordFields:
    """Test AuditRecord dataclass has all required fields."""

    def test_audit_record_has_audit_id(self):
        from src.governance.audit_schema import AuditRecord
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.audit_id is not None
        assert isinstance(r.audit_id, str)

    def test_audit_record_has_timestamp(self):
        from src.governance.audit_schema import AuditRecord
        ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=ts,
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.timestamp == ts

    def test_audit_record_has_engine(self):
        from src.governance.audit_schema import AuditRecord
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="snowflake",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.engine == "snowflake"

    def test_audit_record_has_user_name(self):
        from src.governance.audit_schema import AuditRecord
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="bob_analyst",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.user_name == "bob_analyst"

    def test_audit_record_has_query_id(self):
        from src.governance.audit_schema import AuditRecord
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="20240115_103000_12345_xyz",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.query_id == "20240115_103000_12345_xyz"

    def test_audit_record_has_query_text(self):
        from src.governance.audit_schema import AuditRecord
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT account_id, balance FROM gold.accounts LIMIT 10",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=10,
            bytes_scanned=1024,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert "gold.accounts" in r.query_text

    def test_audit_record_has_tables_accessed(self):
        from src.governance.audit_schema import AuditRecord
        tables = [{"schema": "gold", "table": "trades_daily"}]
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=tables,
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.tables_accessed == tables
        assert r.tables_accessed[0]["schema"] == "gold"
        assert r.tables_accessed[0]["table"] == "trades_daily"

    def test_audit_record_has_columns_accessed(self):
        from src.governance.audit_schema import AuditRecord
        columns = [{"schema": "gold", "table": "accounts", "column": "account_id"}]
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=columns,
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.columns_accessed == columns

    def test_audit_record_has_rows_returned(self):
        from src.governance.audit_schema import AuditRecord
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=150000,
            bytes_scanned=1024 * 1024,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.rows_returned == 150000

    def test_audit_record_has_bytes_scanned(self):
        from src.governance.audit_schema import AuditRecord
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=52428800,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.bytes_scanned == 52428800

    def test_audit_record_has_masked_columns(self):
        from src.governance.audit_schema import AuditRecord
        masked = [{"schema": "sensitive_ns", "table": "customers", "column": "ssn"}]
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=masked,
            access_granted=True,
            source_engine_audit_id="src-001",
        )
        assert r.masked_columns == masked

    def test_audit_record_has_access_granted(self):
        from src.governance.audit_schema import AuditRecord
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=[],
            access_granted=False,
            source_engine_audit_id="src-001",
        )
        assert r.access_granted is False

    def test_audit_record_has_source_engine_audit_id(self):
        from src.governance.audit_schema import AuditRecord
        r = AuditRecord(
            audit_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT 1",
            tables_accessed=[],
            columns_accessed=[],
            rows_returned=0,
            bytes_scanned=0,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="trino-event-listener-id-abc123",
        )
        assert r.source_engine_audit_id == "trino-event-listener-id-abc123"


class TestAuditRecordMethods:
    """Test AuditRecord.to_dict() and to_insert_values()."""

    def _make_record(self):
        from src.governance.audit_schema import AuditRecord
        return AuditRecord(
            audit_id="test-uuid-1234",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            engine="trino",
            user_name="alice",
            query_id="q-001",
            query_text="SELECT * FROM gold.trades",
            tables_accessed=[{"schema": "gold", "table": "trades"}],
            columns_accessed=[{"schema": "gold", "table": "trades", "column": "trade_id"}],
            rows_returned=500,
            bytes_scanned=1024000,
            masked_columns=[],
            access_granted=True,
            source_engine_audit_id="src-001",
        )

    def test_to_dict_produces_complete_dictionary(self):
        r = self._make_record()
        d = r.to_dict()
        assert isinstance(d, dict)
        expected_keys = [
            "audit_id", "timestamp", "engine", "user_name", "query_id",
            "query_text", "tables_accessed", "columns_accessed",
            "rows_returned", "bytes_scanned", "masked_columns",
            "access_granted", "source_engine_audit_id",
        ]
        for key in expected_keys:
            assert key in d, f"Missing key: {key}"

    def test_to_dict_values_are_correct(self):
        r = self._make_record()
        d = r.to_dict()
        assert d["audit_id"] == "test-uuid-1234"
        assert d["engine"] == "trino"
        assert d["user_name"] == "alice"
        assert d["rows_returned"] == 500
        assert d["access_granted"] is True

    def test_to_insert_values_returns_tuple_or_list(self):
        r = self._make_record()
        vals = r.to_insert_values()
        assert isinstance(vals, (tuple, list))

    def test_to_insert_values_length_matches_schema(self):
        from src.governance.audit_schema import AUDIT_SCHEMA, AuditRecord
        r = self._make_record()
        vals = r.to_insert_values()
        assert len(vals) == len(AUDIT_SCHEMA)


class TestAuditSchema:
    """Test AUDIT_SCHEMA constant."""

    def test_audit_schema_is_dict(self):
        from src.governance.audit_schema import AUDIT_SCHEMA
        assert isinstance(AUDIT_SCHEMA, dict)

    def test_audit_schema_has_all_field_definitions(self):
        from src.governance.audit_schema import AUDIT_SCHEMA
        expected_fields = [
            "audit_id", "timestamp", "engine", "user_name", "query_id",
            "query_text", "tables_accessed", "columns_accessed",
            "rows_returned", "bytes_scanned", "masked_columns",
            "access_granted", "source_engine_audit_id",
        ]
        for field in expected_fields:
            assert field in AUDIT_SCHEMA, f"AUDIT_SCHEMA missing field: {field}"

    def test_audit_schema_values_are_strings(self):
        from src.governance.audit_schema import AUDIT_SCHEMA
        for field, sql_type in AUDIT_SCHEMA.items():
            assert isinstance(sql_type, str), f"AUDIT_SCHEMA[{field}] should be string SQL type"


class TestNormalizeTrinoAudit:
    """Test normalize_trino_audit converts Trino HTTP event listener payload to AuditRecord."""

    def _sample_trino_payload(self):
        return {
            "queryId": "20240115_103000_12345_xyz",
            "query": "SELECT t.trade_id, t.notional FROM gold.trades t LIMIT 100",
            "user": "alice",
            "source": "trino-cli",
            "queryState": "FINISHED",
            "queryCompletedEvent": {
                "metadata": {
                    "queryId": "20240115_103000_12345_xyz",
                    "queryState": "FINISHED",
                    "tables": [
                        {
                            "catalog": "iceberg",
                            "schema": "gold",
                            "table": "trades",
                            "columns": ["trade_id", "notional"],
                        }
                    ],
                },
                "statistics": {
                    "outputRows": 100,
                    "outputBytes": 8192,
                },
                "context": {
                    "user": "alice",
                    "source": "trino-cli",
                },
            },
        }

    def test_normalize_trino_audit_returns_audit_record(self):
        from src.governance.audit_schema import AuditRecord, normalize_trino_audit
        payload = self._sample_trino_payload()
        result = normalize_trino_audit(payload)
        assert isinstance(result, AuditRecord)

    def test_normalize_trino_audit_sets_engine(self):
        from src.governance.audit_schema import normalize_trino_audit
        result = normalize_trino_audit(self._sample_trino_payload())
        assert result.engine == "trino"

    def test_normalize_trino_audit_sets_user(self):
        from src.governance.audit_schema import normalize_trino_audit
        result = normalize_trino_audit(self._sample_trino_payload())
        assert result.user_name == "alice"

    def test_normalize_trino_audit_sets_query_id(self):
        from src.governance.audit_schema import normalize_trino_audit
        result = normalize_trino_audit(self._sample_trino_payload())
        assert result.query_id == "20240115_103000_12345_xyz"

    def test_normalize_trino_audit_sets_query_text(self):
        from src.governance.audit_schema import normalize_trino_audit
        result = normalize_trino_audit(self._sample_trino_payload())
        assert "gold.trades" in result.query_text

    def test_normalize_trino_audit_extracts_tables(self):
        from src.governance.audit_schema import normalize_trino_audit
        result = normalize_trino_audit(self._sample_trino_payload())
        assert len(result.tables_accessed) >= 1
        table_names = [t["table"] for t in result.tables_accessed]
        assert "trades" in table_names

    def test_normalize_trino_audit_sets_rows_returned(self):
        from src.governance.audit_schema import normalize_trino_audit
        result = normalize_trino_audit(self._sample_trino_payload())
        assert result.rows_returned == 100

    def test_normalize_trino_audit_sets_bytes_scanned(self):
        from src.governance.audit_schema import normalize_trino_audit
        result = normalize_trino_audit(self._sample_trino_payload())
        assert result.bytes_scanned == 8192

    def test_normalize_trino_audit_generates_uuid(self):
        from src.governance.audit_schema import normalize_trino_audit
        result = normalize_trino_audit(self._sample_trino_payload())
        assert result.audit_id is not None
        assert len(result.audit_id) > 0

    def test_normalize_trino_audit_sets_access_granted_finished(self):
        from src.governance.audit_schema import normalize_trino_audit
        result = normalize_trino_audit(self._sample_trino_payload())
        assert result.access_granted is True

    def test_normalize_trino_audit_sets_access_denied_for_failed(self):
        from src.governance.audit_schema import normalize_trino_audit
        payload = self._sample_trino_payload()
        payload["queryState"] = "FAILED"
        payload["queryCompletedEvent"]["metadata"]["queryState"] = "FAILED"
        result = normalize_trino_audit(payload)
        assert result.access_granted is False


class TestNormalizeTeradataAudit:
    """Test normalize_teradata_audit converts Teradata DBQL row to AuditRecord."""

    def _sample_dbql_row(self):
        return {
            "QueryID": "12345678901234567",
            "UserName": "tduser01",
            "QueryText": "SELECT account_id, balance FROM sensitive_ns.accounts WHERE region='US'",
            "StartTime": "2024-01-15 10:30:00",
            "NumResultRows": 5000,
            "AMPCPUTime": 2.5,
            "ReqIOKB": 10240,
            "ErrorCode": 0,
            "ErrorText": None,
            "DatabaseName": "sensitive_ns",
            "StatementType": "Select",
            "columns": [
                {"DatabaseName": "sensitive_ns", "TableName": "accounts", "ColumnName": "account_id"},
                {"DatabaseName": "sensitive_ns", "TableName": "accounts", "ColumnName": "balance"},
            ],
        }

    def test_normalize_teradata_audit_returns_audit_record(self):
        from src.governance.audit_schema import AuditRecord, normalize_teradata_audit
        result = normalize_teradata_audit(self._sample_dbql_row())
        assert isinstance(result, AuditRecord)

    def test_normalize_teradata_audit_sets_engine(self):
        from src.governance.audit_schema import normalize_teradata_audit
        result = normalize_teradata_audit(self._sample_dbql_row())
        assert result.engine == "teradata"

    def test_normalize_teradata_audit_sets_user(self):
        from src.governance.audit_schema import normalize_teradata_audit
        result = normalize_teradata_audit(self._sample_dbql_row())
        assert result.user_name == "tduser01"

    def test_normalize_teradata_audit_sets_query_id(self):
        from src.governance.audit_schema import normalize_teradata_audit
        result = normalize_teradata_audit(self._sample_dbql_row())
        assert result.query_id == "12345678901234567"

    def test_normalize_teradata_audit_sets_rows_returned(self):
        from src.governance.audit_schema import normalize_teradata_audit
        result = normalize_teradata_audit(self._sample_dbql_row())
        assert result.rows_returned == 5000

    def test_normalize_teradata_audit_access_granted_no_error(self):
        from src.governance.audit_schema import normalize_teradata_audit
        result = normalize_teradata_audit(self._sample_dbql_row())
        assert result.access_granted is True

    def test_normalize_teradata_audit_access_denied_with_error(self):
        from src.governance.audit_schema import normalize_teradata_audit
        row = self._sample_dbql_row()
        row["ErrorCode"] = 3523  # Teradata "No SELECT access" error
        result = normalize_teradata_audit(row)
        assert result.access_granted is False

    def test_normalize_teradata_audit_source_engine_id(self):
        from src.governance.audit_schema import normalize_teradata_audit
        result = normalize_teradata_audit(self._sample_dbql_row())
        assert result.source_engine_audit_id == "12345678901234567"


class TestNormalizeSnowflakeAudit:
    """Test normalize_snowflake_audit converts Snowflake ACCESS_HISTORY row to AuditRecord."""

    def _sample_access_history_row(self):
        return {
            "QUERY_ID": "01a2b3c4-0000-1111-2222-333344445555",
            "QUERY_START_TIME": "2024-01-15 10:30:00.000 +0000",
            "USER_NAME": "SNOWFLAKE_USER",
            "QUERY_TEXT": "SELECT risk_metric, value FROM risk_metrics.trading WHERE date = '2024-01-14'",
            "DIRECT_OBJECTS_ACCESSED": [
                {
                    "objectDomain": "Table",
                    "objectName": "RISK_METRICS.PUBLIC.TRADING",
                    "columns": [
                        {"columnName": "RISK_METRIC"},
                        {"columnName": "VALUE"},
                    ],
                }
            ],
            "OBJECTS_MODIFIED": [],
            "BYTES_SCANNED": 2048000,
            "ROWS_PRODUCED": 2500,
            "EXECUTION_STATUS": "SUCCESS",
        }

    def test_normalize_snowflake_audit_returns_audit_record(self):
        from src.governance.audit_schema import AuditRecord, normalize_snowflake_audit
        result = normalize_snowflake_audit(self._sample_access_history_row())
        assert isinstance(result, AuditRecord)

    def test_normalize_snowflake_audit_sets_engine(self):
        from src.governance.audit_schema import normalize_snowflake_audit
        result = normalize_snowflake_audit(self._sample_access_history_row())
        assert result.engine == "snowflake"

    def test_normalize_snowflake_audit_sets_user(self):
        from src.governance.audit_schema import normalize_snowflake_audit
        result = normalize_snowflake_audit(self._sample_access_history_row())
        assert result.user_name == "SNOWFLAKE_USER"

    def test_normalize_snowflake_audit_sets_query_id(self):
        from src.governance.audit_schema import normalize_snowflake_audit
        result = normalize_snowflake_audit(self._sample_access_history_row())
        assert result.query_id == "01a2b3c4-0000-1111-2222-333344445555"

    def test_normalize_snowflake_audit_sets_rows_returned(self):
        from src.governance.audit_schema import normalize_snowflake_audit
        result = normalize_snowflake_audit(self._sample_access_history_row())
        assert result.rows_returned == 2500

    def test_normalize_snowflake_audit_sets_bytes_scanned(self):
        from src.governance.audit_schema import normalize_snowflake_audit
        result = normalize_snowflake_audit(self._sample_access_history_row())
        assert result.bytes_scanned == 2048000

    def test_normalize_snowflake_audit_extracts_tables(self):
        from src.governance.audit_schema import normalize_snowflake_audit
        result = normalize_snowflake_audit(self._sample_access_history_row())
        assert len(result.tables_accessed) >= 1

    def test_normalize_snowflake_audit_access_granted_success(self):
        from src.governance.audit_schema import normalize_snowflake_audit
        result = normalize_snowflake_audit(self._sample_access_history_row())
        assert result.access_granted is True

    def test_normalize_snowflake_audit_access_denied_failed(self):
        from src.governance.audit_schema import normalize_snowflake_audit
        row = self._sample_access_history_row()
        row["EXECUTION_STATUS"] = "FAILED"
        result = normalize_snowflake_audit(row)
        assert result.access_granted is False

    def test_normalize_snowflake_audit_source_engine_id(self):
        from src.governance.audit_schema import normalize_snowflake_audit
        result = normalize_snowflake_audit(self._sample_access_history_row())
        assert result.source_engine_audit_id == "01a2b3c4-0000-1111-2222-333344445555"
