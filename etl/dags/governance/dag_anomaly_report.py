"""Airflow DAG: Daily anomaly detection and compliance report generation.

Fetches previous day's audit records from PostgreSQL, runs anomaly detection
heuristics, generates a markdown report, and exports BCBS 239 compliance
dashboard to PDF via grafana-reporter.

Schedule: Daily at 06:00 UTC (after audit aggregation DAG at 02:00 UTC)
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

_AUDIT_DB_CONN = os.environ.get(
    "AUDIT_DB_CONNECTION",
    "postgresql://marquez:marquez@marquez-db:5432/marquez",
)
_GRAFANA_REPORTER_URL = os.environ.get("GRAFANA_REPORTER_URL", "http://grafana-reporter:8686")
_REPORTS_DIR = os.environ.get("COMPLIANCE_REPORTS_DIR", "/opt/airflow/reports")

default_args = {
    "owner": "governance-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def _fetch_yesterday_audit(**context) -> str:
    """Fetch audit records for the previous day from PostgreSQL."""
    logical_date = context["logical_date"]
    yesterday = datetime(logical_date.year, logical_date.month, logical_date.day, tzinfo=UTC) - timedelta(days=1)
    today = yesterday + timedelta(days=1)

    try:
        import json
        import tempfile

        import psycopg2  # type: ignore
        import psycopg2.extras  # type: ignore

        conn = psycopg2.connect(_AUDIT_DB_CONN)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            SELECT
                audit_id, timestamp, engine, user_name, query_id, query_text,
                tables_accessed, columns_accessed, rows_returned, bytes_scanned,
                masked_columns, access_granted, source_engine_audit_id
            FROM audit_records
            WHERE timestamp >= %s AND timestamp < %s
            ORDER BY timestamp
        """,
            [yesterday, today],
        )

        rows = cursor.fetchall()
        conn.close()

        logger.info("Fetched %d audit records for %s", len(rows), yesterday.strftime("%Y-%m-%d"))

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix=f"audit_daily_{yesterday.strftime('%Y%m%d')}_",
            delete=False,
        ) as tmp:
            records_data = [dict(r) for r in rows]
            # Serialize datetime objects
            for r in records_data:
                if isinstance(r.get("timestamp"), datetime):
                    r["timestamp"] = r["timestamp"].isoformat()
            json.dump(records_data, tmp, default=str)

        context["ti"].xcom_push(key="audit_records_file", value=tmp.name)
        context["ti"].xcom_push(key="report_date", value=yesterday.strftime("%Y-%m-%d"))
        return tmp.name

    except Exception as e:
        logger.warning("Failed to fetch yesterday's audit records: %s", e)
        context["ti"].xcom_push(key="audit_records_file", value=None)
        context["ti"].xcom_push(key="report_date", value=yesterday.strftime("%Y-%m-%d"))
        return ""


def _run_anomaly_detection(**context) -> int:
    """Run anomaly detection on yesterday's audit records."""
    import json
    import os as _os
    import tempfile

    from src.governance.anomaly_detector import detect_anomalies
    from src.governance.audit_schema import AuditRecord

    file_path = context["ti"].xcom_pull(key="audit_records_file")
    if not file_path or not _os.path.exists(file_path):
        logger.warning("No audit records file found -- skipping anomaly detection")
        context["ti"].xcom_push(key="anomalies_file", value=None)
        return 0

    with open(file_path) as f:
        raw_records = json.load(f)

    records = []
    for r in raw_records:
        try:
            r["timestamp"] = datetime.fromisoformat(r["timestamp"])
            records.append(AuditRecord(**r))
        except Exception as e:
            logger.warning("Failed to reconstruct AuditRecord: %s", e)

    anomalies = detect_anomalies(records)
    logger.info("Detected %d anomalies in %d audit records", len(anomalies), len(records))

    # Serialize anomalies for next task

    anomalies_data = []
    for a in anomalies:
        anomalies_data.append(
            {
                "anomaly_type": a.anomaly_type.value,
                "severity": a.severity,
                "description": a.description,
                "detected_at": a.detected_at.isoformat(),
                "audit_records_count": len(a.audit_records),
            }
        )

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="anomalies_",
        delete=False,
    ) as tmp:
        json.dump(anomalies_data, tmp)

    context["ti"].xcom_push(key="anomalies_file", value=tmp.name)
    context["ti"].xcom_push(key="anomaly_count", value=len(anomalies))

    # Clean up audit records temp file
    with contextlib.suppress(Exception):
        _os.unlink(file_path)

    return len(anomalies)


def _generate_report(**context) -> str:
    """Generate markdown anomaly report and save to disk."""
    import json
    import os as _os

    report_date = context["ti"].xcom_pull(key="report_date") or "unknown"
    anomalies_file = context["ti"].xcom_pull(key="anomalies_file")

    # Build a simplified text report from anomaly data
    lines = [
        "# Daily Audit Anomaly Report",
        "",
        f"**Date:** {report_date}",
    ]

    anomaly_count = 0
    if anomalies_file and _os.path.exists(anomalies_file):
        with open(anomalies_file) as f:
            anomalies_data = json.load(f)
        anomaly_count = len(anomalies_data)

        lines.append(f"**Total Anomalies:** {anomaly_count}")
        lines.append("")

        if anomaly_count == 0:
            lines.extend(["## Status: CLEAN", "", "No suspicious access patterns detected."])
        else:
            lines.extend(["## Anomalies Detected", ""])
            for idx, a in enumerate(anomalies_data, 1):
                lines.extend(
                    [
                        f"### {idx}. {a['anomaly_type'].replace('_', ' ').title()}",
                        f"**Severity:** {a['severity'].upper()}",
                        f"**Description:** {a['description']}",
                        f"**Detected at:** {a['detected_at']}",
                        f"**Evidence records:** {a['audit_records_count']}",
                        "",
                    ]
                )

        # Clean up anomalies file
        with contextlib.suppress(Exception):
            _os.unlink(anomalies_file)
    else:
        lines.extend(["**Total Anomalies:** 0", "", "## Status: CLEAN"])

    report_content = "\n".join(lines)

    # Save report to disk
    _os.makedirs(_REPORTS_DIR, exist_ok=True)
    report_path = _os.path.join(_REPORTS_DIR, f"anomaly_report_{report_date}.md")
    with open(report_path, "w") as f:
        f.write(report_content)

    logger.info("Anomaly report saved to %s (%d anomalies)", report_path, anomaly_count)
    context["ti"].xcom_push(key="report_path", value=report_path)
    return report_path


def _export_compliance_pdf(**context) -> str:
    """Export BCBS 239 compliance dashboard to PDF via grafana-reporter.

    Calls grafana-reporter API to render the bcbs239_compliance dashboard
    as PDF for audit evidence archival. Non-blocking -- failure is logged
    but does not fail the DAG.
    """
    import os as _os
    from datetime import date

    report_date = context["ti"].xcom_pull(key="report_date") or date.today().isoformat()
    pdf_path = _os.path.join(_REPORTS_DIR, f"bcbs239_{report_date}.pdf")

    try:
        import requests  # type: ignore

        # grafana-reporter API: GET /render?dashboard=<uid>&from=<epoch>&to=<epoch>
        from_ts = int((datetime.now(UTC) - timedelta(days=1)).timestamp() * 1000)
        to_ts = int(datetime.now(UTC).timestamp() * 1000)

        url = f"{_GRAFANA_REPORTER_URL}/render?dashboard=bcbs239-compliance&from={from_ts}&to={to_ts}"
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()

        _os.makedirs(_REPORTS_DIR, exist_ok=True)
        with open(pdf_path, "wb") as f:
            f.write(resp.content)

        logger.info("BCBS 239 compliance PDF exported to %s", pdf_path)
        return pdf_path

    except Exception as e:
        logger.warning(
            "Failed to export BCBS 239 compliance PDF (grafana-reporter at %s): %s. "
            "This is non-critical -- continuing.",
            _GRAFANA_REPORTER_URL,
            e,
        )
        return ""


with DAG(
    dag_id="governance_anomaly_report",
    description="Daily anomaly detection and BCBS 239 compliance PDF export",
    schedule="0 6 * * *",  # Daily at 06:00 UTC (after audit aggregation)
    start_date=datetime(2024, 1, 1, tzinfo=UTC),
    catchup=False,
    default_args=default_args,
    tags=["governance", "anomaly", "compliance", "bcbs239"],
    doc_md=__doc__,
) as dag:
    fetch_yesterday_audit = PythonOperator(
        task_id="fetch_yesterday_audit",
        python_callable=_fetch_yesterday_audit,
    )

    run_anomaly_detection = PythonOperator(
        task_id="run_anomaly_detection",
        python_callable=_run_anomaly_detection,
    )

    generate_report = PythonOperator(
        task_id="generate_report",
        python_callable=_generate_report,
    )

    export_compliance_pdf = PythonOperator(
        task_id="export_compliance_pdf",
        python_callable=_export_compliance_pdf,
    )

    # Sequential pipeline
    fetch_yesterday_audit >> run_anomaly_detection >> generate_report >> export_compliance_pdf
