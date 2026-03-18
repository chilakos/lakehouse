"""Daily anomaly detection heuristics for audit data.

Provides:
- AnomalyType enum: BULK_DOWNLOAD, AFTER_HOURS_ACCESS, UNUSUAL_RESTRICTED_ACCESS, HIGH_FREQUENCY_QUERY
- AnomalyReport dataclass: structured anomaly report with severity and audit evidence
- detect_anomalies(): run all 4 heuristics against a list of AuditRecord
- format_anomaly_report(): markdown-formatted daily anomaly report

Usage::

    from src.governance.anomaly_detector import detect_anomalies, format_anomaly_report

    # Load audit records for yesterday
    records = load_yesterday_records()
    anomalies = detect_anomalies(records)
    report_md = format_anomaly_report(anomalies)
    with open(f"/tmp/anomaly_report_{date.today()}.md", "w") as f:
        f.write(report_md)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

# Schemas considered "restricted" for unusual access detection
_RESTRICTED_SCHEMAS = {"sensitive_ns", "restricted", "pii", "confidential"}

# Default thresholds (all configurable via parameters)
_BULK_DOWNLOAD_THRESHOLD = 100_000  # rows returned in a single query
_HIGH_FREQ_THRESHOLD = 1_000  # queries per user per hour


class AnomalyType(Enum):
    """Types of suspicious access patterns detected by the anomaly detector.

    Values:
        BULK_DOWNLOAD: Single query returns more than threshold rows
        AFTER_HOURS_ACCESS: Query executed outside business hours
        UNUSUAL_RESTRICTED_ACCESS: User accessing restricted schema unexpectedly
        HIGH_FREQUENCY_QUERY: User exceeding query rate threshold in a time window
    """

    BULK_DOWNLOAD = "bulk_download"
    AFTER_HOURS_ACCESS = "after_hours_access"
    UNUSUAL_RESTRICTED_ACCESS = "unusual_restricted_access"
    HIGH_FREQUENCY_QUERY = "high_frequency_query"


@dataclass
class AnomalyReport:
    """Structured anomaly report with evidence and severity classification.

    Attributes:
        anomaly_type: The category of suspicious activity detected
        severity: Risk severity ("low" | "medium" | "high")
        description: Human-readable description of the specific anomaly instance
        audit_records: List of AuditRecord evidence for this anomaly
        detected_at: UTC datetime when the anomaly was detected by the detector
    """

    anomaly_type: AnomalyType
    severity: str
    description: str
    audit_records: list
    detected_at: datetime


def detect_anomalies(
    records: list,
    business_hours: tuple[int, int] = (6, 22),
    bulk_download_threshold: int = _BULK_DOWNLOAD_THRESHOLD,
    high_freq_threshold: int = _HIGH_FREQ_THRESHOLD,
    restricted_schemas: set[str] | None = None,
) -> list[AnomalyReport]:
    """Run all anomaly detection heuristics against audit records.

    Applies 4 independent heuristics to identify suspicious access patterns:
    1. BULK_DOWNLOAD: Any single query returning more than bulk_download_threshold rows
    2. AFTER_HOURS_ACCESS: Queries submitted outside business_hours window
    3. UNUSUAL_RESTRICTED_ACCESS: Access to restricted schemas (low baseline expectation)
    4. HIGH_FREQUENCY_QUERY: User exceeding high_freq_threshold queries in a rolling hour

    Args:
        records: List of AuditRecord to analyze (typically yesterday's records)
        business_hours: Tuple of (start_hour, end_hour) in UTC, inclusive start exclusive end.
            Default (6, 22) = 06:00 to 22:00 UTC.
        bulk_download_threshold: Row count above which BULK_DOWNLOAD is flagged. Default 100,000.
        high_freq_threshold: Query count per user per hour above which HIGH_FREQUENCY_QUERY
            is flagged. Default 1,000.
        restricted_schemas: Set of schema names considered restricted. Defaults to
            {"sensitive_ns", "restricted", "pii", "confidential"}.

    Returns:
        List of AnomalyReport objects, one per anomaly detected. Empty list if no anomalies.
    """
    if restricted_schemas is None:
        restricted_schemas = _RESTRICTED_SCHEMAS

    now = datetime.now(UTC)
    anomalies: list[AnomalyReport] = []

    anomalies.extend(_detect_bulk_downloads(records, bulk_download_threshold, now))
    anomalies.extend(_detect_after_hours(records, business_hours, restricted_schemas, now))
    anomalies.extend(_detect_restricted_access(records, restricted_schemas, business_hours, now))
    anomalies.extend(_detect_high_frequency(records, high_freq_threshold, now))

    return anomalies


def _detect_bulk_downloads(
    records: list,
    threshold: int,
    detected_at: datetime,
) -> list[AnomalyReport]:
    """Flag queries returning more than threshold rows."""
    anomalies = []
    for record in records:
        if record.rows_returned > threshold:
            anomalies.append(
                AnomalyReport(
                    anomaly_type=AnomalyType.BULK_DOWNLOAD,
                    severity="medium",
                    description=(
                        f"User '{record.user_name}' returned {record.rows_returned:,} rows "
                        f"in query {record.query_id} on engine {record.engine} "
                        f"(threshold: {threshold:,})"
                    ),
                    audit_records=[record],
                    detected_at=detected_at,
                )
            )
    return anomalies


def _is_after_hours(timestamp: datetime, business_hours: tuple[int, int]) -> bool:
    """Return True if timestamp is outside business hours."""
    start_hour, end_hour = business_hours
    hour = timestamp.hour
    # Outside hours: before start OR at/after end
    return hour < start_hour or hour >= end_hour


def _touches_restricted_schema(record, restricted_schemas: set[str]) -> bool:
    """Return True if any accessed table is in a restricted schema."""
    return any(t.get("schema", "") in restricted_schemas for t in record.tables_accessed)


def _detect_after_hours(
    records: list,
    business_hours: tuple[int, int],
    restricted_schemas: set[str],
    detected_at: datetime,
) -> list[AnomalyReport]:
    """Flag queries submitted outside business hours."""
    anomalies = []
    for record in records:
        ts = record.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        if _is_after_hours(ts, business_hours):
            touches_restricted = _touches_restricted_schema(record, restricted_schemas)
            severity = "high" if touches_restricted else "low"
            anomalies.append(
                AnomalyReport(
                    anomaly_type=AnomalyType.AFTER_HOURS_ACCESS,
                    severity=severity,
                    description=(
                        f"User '{record.user_name}' ran query at {ts.strftime('%H:%M UTC')} "
                        f"(outside business hours {business_hours[0]:02d}:00-{business_hours[1]:02d}:00 UTC)"
                        + (" on RESTRICTED schema" if touches_restricted else "")
                    ),
                    audit_records=[record],
                    detected_at=detected_at,
                )
            )
    return anomalies


def _detect_restricted_access(
    records: list,
    restricted_schemas: set[str],
    business_hours: tuple[int, int],
    detected_at: datetime,
) -> list[AnomalyReport]:
    """Flag access to restricted schemas as potentially unusual."""
    anomalies = []
    for record in records:
        ts = record.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        # Only flag during business hours (after-hours restricted access is caught above)
        if _is_after_hours(ts, business_hours):
            continue

        if _touches_restricted_schema(record, restricted_schemas):
            anomalies.append(
                AnomalyReport(
                    anomaly_type=AnomalyType.UNUSUAL_RESTRICTED_ACCESS,
                    severity="high",
                    description=(
                        f"User '{record.user_name}' accessed restricted schema(s) "
                        f"{[t['schema'] for t in record.tables_accessed if t.get('schema') in restricted_schemas]} "
                        f"in query {record.query_id} on {record.engine}"
                    ),
                    audit_records=[record],
                    detected_at=detected_at,
                )
            )
    return anomalies


def _detect_high_frequency(
    records: list,
    threshold: int,
    detected_at: datetime,
) -> list[AnomalyReport]:
    """Flag users with more than threshold queries in a rolling 1-hour window."""
    if not records:
        return []

    # Group records by user, sort by timestamp
    user_records: dict[str, list] = defaultdict(list)
    for record in records:
        user_records[record.user_name].append(record)

    anomalies = []
    for user_name, user_recs in user_records.items():
        sorted_recs = sorted(user_recs, key=lambda r: r.timestamp)

        # Sliding window: count queries in each 1-hour window
        max_count = 0
        window_records = []
        for i, rec in enumerate(sorted_recs):
            window_start = rec.timestamp - timedelta(hours=1)
            # Keep only records within the 1-hour window
            window_records = [r for r in sorted_recs[: i + 1] if r.timestamp >= window_start]
            if len(window_records) > max_count:
                max_count = len(window_records)

        if max_count > threshold:
            anomalies.append(
                AnomalyReport(
                    anomaly_type=AnomalyType.HIGH_FREQUENCY_QUERY,
                    severity="medium",
                    description=(
                        f"User '{user_name}' submitted {max_count:,} queries in a 1-hour window "
                        f"(threshold: {threshold:,})"
                    ),
                    audit_records=sorted_recs[:10],  # Include first 10 as evidence
                    detected_at=detected_at,
                )
            )

    return anomalies


def format_anomaly_report(anomalies: list[AnomalyReport]) -> str:
    """Generate a markdown-formatted daily anomaly report.

    Args:
        anomalies: List of AnomalyReport to include in the report.
            Pass empty list to generate a "clean" report.

    Returns:
        Markdown string suitable for saving as .md file or sending via email.
        Includes summary counts, severity breakdown, and individual anomaly details.
    """
    now = datetime.now(UTC)
    lines = [
        "# Daily Audit Anomaly Report",
        "",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Total Anomalies Detected:** {len(anomalies)}",
        "",
    ]

    if not anomalies:
        lines.extend(
            [
                "## Status: CLEAN",
                "",
                "No suspicious access patterns detected in the audit data.",
            ]
        )
        return "\n".join(lines)

    # Summary by severity
    severity_counts: dict[str, int] = defaultdict(int)
    type_counts: dict[str, int] = defaultdict(int)
    for a in anomalies:
        severity_counts[a.severity] += 1
        type_counts[a.anomaly_type.value] += 1

    lines.extend(
        [
            "## Summary",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ]
    )
    for sev in ["high", "medium", "low"]:
        count = severity_counts.get(sev, 0)
        if count:
            lines.append(f"| {sev.upper()} | {count} |")

    lines.extend(
        [
            "",
            "| Anomaly Type | Count |",
            "|-------------|-------|",
        ]
    )
    for atype, count in sorted(type_counts.items()):
        lines.append(f"| {atype} | {count} |")

    lines.append("")

    # Detail section grouped by type
    by_type: dict[AnomalyType, list[AnomalyReport]] = defaultdict(list)
    for a in anomalies:
        by_type[a.anomaly_type].append(a)

    for atype, type_anomalies in sorted(by_type.items(), key=lambda x: x[0].value):
        lines.extend(
            [
                f"## {atype.value.replace('_', ' ').title()} ({len(type_anomalies)} events)",
                "",
            ]
        )
        for idx, anomaly in enumerate(type_anomalies, 1):
            lines.extend(
                [
                    f"### Event {idx} - Severity: {anomaly.severity.upper()}",
                    "",
                    f"**Description:** {anomaly.description}",
                    f"**Detected at:** {anomaly.detected_at.strftime('%Y-%m-%d %H:%M UTC')}",
                    f"**Evidence records:** {len(anomaly.audit_records)}",
                    "",
                ]
            )
            if anomaly.audit_records:
                lines.extend(
                    [
                        "| Timestamp | User | Engine | Query ID |",
                        "|-----------|------|--------|----------|",
                    ]
                )
                for rec in anomaly.audit_records[:5]:  # Show first 5 records
                    ts = rec.timestamp.strftime("%Y-%m-%d %H:%M")
                    lines.append(f"| {ts} | {rec.user_name} | {rec.engine} | {rec.query_id[:20]}... |")
                lines.append("")

    return "\n".join(lines)
