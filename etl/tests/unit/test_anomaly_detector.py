"""Unit tests for anomaly_detector module.

Tests AnomalyType enum, AnomalyReport dataclass, detect_anomalies() heuristics,
and format_anomaly_report() output formatting.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest


def _make_record(
    user_name="alice",
    rows_returned=0,
    bytes_scanned=0,
    hour=10,
    tables=None,
    engine="trino",
    access_granted=True,
):
    """Helper to create AuditRecord for tests."""
    from src.governance.audit_schema import AuditRecord
    if tables is None:
        tables = [{"schema": "gold", "table": "trades"}]
    ts = datetime(2024, 1, 15, hour, 30, 0, tzinfo=timezone.utc)
    return AuditRecord(
        audit_id=str(uuid.uuid4()),
        timestamp=ts,
        engine=engine,
        user_name=user_name,
        query_id=str(uuid.uuid4()),
        query_text="SELECT 1",
        tables_accessed=tables,
        columns_accessed=[],
        rows_returned=rows_returned,
        bytes_scanned=bytes_scanned,
        masked_columns=[],
        access_granted=access_granted,
        source_engine_audit_id=str(uuid.uuid4()),
    )


class TestAnomalyTypeEnum:
    """Test AnomalyType enum has required values."""

    def test_anomaly_type_has_bulk_download(self):
        from src.governance.anomaly_detector import AnomalyType
        assert AnomalyType.BULK_DOWNLOAD is not None

    def test_anomaly_type_has_after_hours_access(self):
        from src.governance.anomaly_detector import AnomalyType
        assert AnomalyType.AFTER_HOURS_ACCESS is not None

    def test_anomaly_type_has_unusual_restricted_access(self):
        from src.governance.anomaly_detector import AnomalyType
        assert AnomalyType.UNUSUAL_RESTRICTED_ACCESS is not None

    def test_anomaly_type_has_high_frequency_query(self):
        from src.governance.anomaly_detector import AnomalyType
        assert AnomalyType.HIGH_FREQUENCY_QUERY is not None

    def test_anomaly_type_values_are_strings(self):
        from src.governance.anomaly_detector import AnomalyType
        for member in AnomalyType:
            assert isinstance(member.value, str)


class TestAnomalyReport:
    """Test AnomalyReport dataclass."""

    def test_anomaly_report_has_anomaly_type(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType
        report = AnomalyReport(
            anomaly_type=AnomalyType.BULK_DOWNLOAD,
            severity="medium",
            description="Bulk download detected",
            audit_records=[_make_record(rows_returned=200000)],
            detected_at=datetime.now(timezone.utc),
        )
        assert report.anomaly_type == AnomalyType.BULK_DOWNLOAD

    def test_anomaly_report_has_severity(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType
        report = AnomalyReport(
            anomaly_type=AnomalyType.BULK_DOWNLOAD,
            severity="high",
            description="Test",
            audit_records=[],
            detected_at=datetime.now(timezone.utc),
        )
        assert report.severity == "high"

    def test_anomaly_report_has_description(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType
        report = AnomalyReport(
            anomaly_type=AnomalyType.AFTER_HOURS_ACCESS,
            severity="low",
            description="Query submitted at 03:00 UTC",
            audit_records=[],
            detected_at=datetime.now(timezone.utc),
        )
        assert "03:00" in report.description

    def test_anomaly_report_has_audit_records(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType
        records = [_make_record(), _make_record()]
        report = AnomalyReport(
            anomaly_type=AnomalyType.HIGH_FREQUENCY_QUERY,
            severity="medium",
            description="Test",
            audit_records=records,
            detected_at=datetime.now(timezone.utc),
        )
        assert len(report.audit_records) == 2

    def test_anomaly_report_has_detected_at(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType
        now = datetime.now(timezone.utc)
        report = AnomalyReport(
            anomaly_type=AnomalyType.UNUSUAL_RESTRICTED_ACCESS,
            severity="high",
            description="Test",
            audit_records=[],
            detected_at=now,
        )
        assert report.detected_at == now


class TestDetectAnomaliesBulkDownload:
    """Test detect_anomalies flags bulk download (>100k rows returned)."""

    def test_bulk_download_flagged_at_threshold(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(rows_returned=100001)]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.BULK_DOWNLOAD in types

    def test_bulk_download_flagged_well_above_threshold(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(rows_returned=5000000)]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.BULK_DOWNLOAD in types

    def test_bulk_download_not_flagged_below_threshold(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(rows_returned=99999)]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.BULK_DOWNLOAD not in types

    def test_bulk_download_severity_is_medium(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(rows_returned=200000)]
        anomalies = detect_anomalies(records)
        bulk = [a for a in anomalies if a.anomaly_type == AnomalyType.BULK_DOWNLOAD]
        assert len(bulk) >= 1
        assert bulk[0].severity == "medium"

    def test_bulk_download_includes_audit_record(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(rows_returned=500000, user_name="bulk_user")]
        anomalies = detect_anomalies(records)
        bulk = [a for a in anomalies if a.anomaly_type == AnomalyType.BULK_DOWNLOAD]
        assert len(bulk) >= 1
        assert any(r.user_name == "bulk_user" for r in bulk[0].audit_records)


class TestDetectAnomaliesAfterHours:
    """Test detect_anomalies flags after-hours access (outside 06:00-22:00)."""

    def test_after_hours_flagged_at_midnight(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(hour=0)]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.AFTER_HOURS_ACCESS in types

    def test_after_hours_flagged_at_3am(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(hour=3)]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.AFTER_HOURS_ACCESS in types

    def test_after_hours_flagged_at_23(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(hour=23)]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.AFTER_HOURS_ACCESS in types

    def test_after_hours_not_flagged_during_business_hours(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(hour=10)]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.AFTER_HOURS_ACCESS not in types

    def test_after_hours_not_flagged_at_business_start(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(hour=6)]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.AFTER_HOURS_ACCESS not in types

    def test_after_hours_severity_low_for_non_restricted(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(hour=2, tables=[{"schema": "gold", "table": "trades"}])]
        anomalies = detect_anomalies(records)
        after_hours = [a for a in anomalies if a.anomaly_type == AnomalyType.AFTER_HOURS_ACCESS]
        assert len(after_hours) >= 1
        assert after_hours[0].severity == "low"

    def test_after_hours_severity_high_for_restricted_tables(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(
            hour=2,
            tables=[{"schema": "sensitive_ns", "table": "customers"}]
        )]
        anomalies = detect_anomalies(records)
        after_hours = [a for a in anomalies if a.anomaly_type == AnomalyType.AFTER_HOURS_ACCESS]
        assert len(after_hours) >= 1
        assert after_hours[0].severity == "high"

    def test_custom_business_hours_respected(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        # 08:00 is after-hours if business hours = (9, 17)
        records = [_make_record(hour=8)]
        anomalies = detect_anomalies(records, business_hours=(9, 17))
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.AFTER_HOURS_ACCESS in types


class TestDetectAnomaliesRestrictedAccess:
    """Test detect_anomalies flags unusual restricted table access."""

    def test_restricted_access_flagged_for_sensitive_ns(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(
            tables=[{"schema": "sensitive_ns", "table": "pii_customers"}],
            user_name="analyst_user",
            hour=10,
        )]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.UNUSUAL_RESTRICTED_ACCESS in types

    def test_restricted_access_severity_high(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(
            tables=[{"schema": "sensitive_ns", "table": "pii_customers"}],
            user_name="analyst_user",
            hour=10,
        )]
        anomalies = detect_anomalies(records)
        restricted = [a for a in anomalies if a.anomaly_type == AnomalyType.UNUSUAL_RESTRICTED_ACCESS]
        assert len(restricted) >= 1
        assert restricted[0].severity == "high"

    def test_unrestricted_schema_not_flagged(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        records = [_make_record(
            tables=[{"schema": "gold", "table": "public_metrics"}],
            user_name="analyst_user",
            hour=10,
        )]
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.UNUSUAL_RESTRICTED_ACCESS not in types


class TestDetectAnomaliesHighFrequency:
    """Test detect_anomalies flags high-frequency queries (>1000 in 1 hour)."""

    def test_high_frequency_flagged_over_threshold(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        # Create 1001 records from same user within same hour
        base_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        from src.governance.audit_schema import AuditRecord
        records = []
        for i in range(1001):
            records.append(AuditRecord(
                audit_id=str(uuid.uuid4()),
                timestamp=base_time + timedelta(seconds=i * 3),  # spread over ~50 min
                engine="trino",
                user_name="heavy_user",
                query_id=str(uuid.uuid4()),
                query_text=f"SELECT {i}",
                tables_accessed=[{"schema": "gold", "table": "metrics"}],
                columns_accessed=[],
                rows_returned=1,
                bytes_scanned=100,
                masked_columns=[],
                access_granted=True,
                source_engine_audit_id=str(uuid.uuid4()),
            ))
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.HIGH_FREQUENCY_QUERY in types

    def test_high_frequency_not_flagged_below_threshold(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        # 500 queries from same user -- below threshold
        base_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        from src.governance.audit_schema import AuditRecord
        records = []
        for i in range(500):
            records.append(AuditRecord(
                audit_id=str(uuid.uuid4()),
                timestamp=base_time + timedelta(seconds=i * 7),
                engine="trino",
                user_name="moderate_user",
                query_id=str(uuid.uuid4()),
                query_text=f"SELECT {i}",
                tables_accessed=[{"schema": "gold", "table": "metrics"}],
                columns_accessed=[],
                rows_returned=1,
                bytes_scanned=100,
                masked_columns=[],
                access_granted=True,
                source_engine_audit_id=str(uuid.uuid4()),
            ))
        anomalies = detect_anomalies(records)
        types = [a.anomaly_type for a in anomalies]
        assert AnomalyType.HIGH_FREQUENCY_QUERY not in types

    def test_high_frequency_severity_is_medium(self):
        from src.governance.anomaly_detector import AnomalyType, detect_anomalies
        base_time = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        from src.governance.audit_schema import AuditRecord
        records = []
        for i in range(1001):
            records.append(AuditRecord(
                audit_id=str(uuid.uuid4()),
                timestamp=base_time + timedelta(seconds=i * 3),
                engine="trino",
                user_name="heavy_user",
                query_id=str(uuid.uuid4()),
                query_text=f"SELECT {i}",
                tables_accessed=[{"schema": "gold", "table": "metrics"}],
                columns_accessed=[],
                rows_returned=1,
                bytes_scanned=100,
                masked_columns=[],
                access_granted=True,
                source_engine_audit_id=str(uuid.uuid4()),
            ))
        anomalies = detect_anomalies(records)
        hf = [a for a in anomalies if a.anomaly_type == AnomalyType.HIGH_FREQUENCY_QUERY]
        assert len(hf) >= 1
        assert hf[0].severity == "medium"


class TestDetectAnomaliesNormalActivity:
    """Test detect_anomalies returns empty list for normal activity."""

    def test_normal_activity_no_anomalies(self):
        from src.governance.anomaly_detector import detect_anomalies
        records = [
            _make_record(rows_returned=100, hour=10, user_name="alice"),
            _make_record(rows_returned=50, hour=14, user_name="bob"),
            _make_record(rows_returned=200, hour=9, user_name="charlie"),
        ]
        anomalies = detect_anomalies(records)
        assert anomalies == []

    def test_empty_records_no_anomalies(self):
        from src.governance.anomaly_detector import detect_anomalies
        anomalies = detect_anomalies([])
        assert anomalies == []


class TestFormatAnomalyReport:
    """Test format_anomaly_report produces markdown output."""

    def test_format_report_returns_string(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType, format_anomaly_report
        anomalies = [
            AnomalyReport(
                anomaly_type=AnomalyType.BULK_DOWNLOAD,
                severity="medium",
                description="alice downloaded 200k rows",
                audit_records=[_make_record(rows_returned=200000)],
                detected_at=datetime.now(timezone.utc),
            )
        ]
        report = format_anomaly_report(anomalies)
        assert isinstance(report, str)

    def test_format_report_contains_anomaly_type(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType, format_anomaly_report
        anomalies = [
            AnomalyReport(
                anomaly_type=AnomalyType.BULK_DOWNLOAD,
                severity="medium",
                description="Test description",
                audit_records=[],
                detected_at=datetime.now(timezone.utc),
            )
        ]
        report = format_anomaly_report(anomalies)
        assert "BULK_DOWNLOAD" in report or "Bulk Download" in report or "bulk_download" in report.lower()

    def test_format_report_contains_severity(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType, format_anomaly_report
        anomalies = [
            AnomalyReport(
                anomaly_type=AnomalyType.UNUSUAL_RESTRICTED_ACCESS,
                severity="high",
                description="Restricted access detected",
                audit_records=[],
                detected_at=datetime.now(timezone.utc),
            )
        ]
        report = format_anomaly_report(anomalies)
        assert "high" in report.lower()

    def test_format_report_has_markdown_structure(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType, format_anomaly_report
        anomalies = [
            AnomalyReport(
                anomaly_type=AnomalyType.AFTER_HOURS_ACCESS,
                severity="low",
                description="After-hours query",
                audit_records=[],
                detected_at=datetime.now(timezone.utc),
            )
        ]
        report = format_anomaly_report(anomalies)
        # Should contain markdown headers
        assert "#" in report

    def test_format_empty_report(self):
        from src.governance.anomaly_detector import format_anomaly_report
        report = format_anomaly_report([])
        assert isinstance(report, str)
        assert len(report) > 0  # should produce some output, even for no anomalies

    def test_format_report_contains_description(self):
        from src.governance.anomaly_detector import AnomalyReport, AnomalyType, format_anomaly_report
        anomalies = [
            AnomalyReport(
                anomaly_type=AnomalyType.HIGH_FREQUENCY_QUERY,
                severity="medium",
                description="user heavy_bot made 1500 queries in 45 minutes",
                audit_records=[],
                detected_at=datetime.now(timezone.utc),
            )
        ]
        report = format_anomaly_report(anomalies)
        assert "heavy_bot" in report or "1500" in report
