---
phase: 03-governance-security-hardening-and-platform
plan: "03"
subsystem: audit-compliance
tags: [audit, anomaly-detection, grafana, bcbs239, compliance, lineage, freshness, grafana-reporter, infinity-plugin]

# Dependency graph
requires:
  - phase: 03-governance-security-hardening-and-platform
    provides: Ranger Docker deployment and governance classification module (03-01)
  - phase: 03-governance-security-hardening-and-platform
    provides: OpenMetadata catalog, freshness tracker, lineage stubs (03-02)
  - phase: 02-etl-migration-and-data-pipeline
    provides: Marquez lineage backend, Trino/Iceberg schemas, Grafana observability

provides:
  - AuditRecord dataclass (13 fields) + AUDIT_SCHEMA DDL for cross-engine audit aggregation
  - normalize_trino_audit(), normalize_teradata_audit(), normalize_snowflake_audit() converters
  - TrinoAuditExtractor, TeradataAuditExtractor (TERADATA_HOST-gated), SnowflakeAuditExtractor (SNOWFLAKE_ACCOUNT-gated, ACCESS_HISTORY/QUERY_HISTORY fallback)
  - aggregate_audit_records() with batch INSERT + ON CONFLICT DO NOTHING upsert to PostgreSQL
  - AnomalyType enum (BULK_DOWNLOAD, AFTER_HOURS_ACCESS, UNUSUAL_RESTRICTED_ACCESS, HIGH_FREQUENCY_QUERY)
  - AnomalyReport dataclass + detect_anomalies() with 4 configurable heuristics
  - format_anomaly_report() markdown daily anomaly report
  - audit_archiver.py: archive_old_records() to S3 Parquet partitioned by year/month (90-day default)
  - DAG governance_audit_aggregation (02:00 UTC daily) with extract-parallel + aggregate + archive tasks
  - DAG governance_anomaly_report (06:00 UTC daily) with anomaly detection + grafana-reporter PDF export
  - DAG governance_freshness_check (every 2h) with freshness check + PostgreSQL metrics upsert
  - BCBS 239 compliance Grafana dashboard (11 panels: accuracy/completeness/timeliness + lineage explorer)
  - Data freshness SLA Grafana dashboard (4 panels: overview stat, per-table table, timeline, SLA breaches)
  - Audit trail overview Grafana dashboard (7 panels: query volume, top users, restricted access, masked columns, access denied)
  - Marquez-API Infinity datasource + Audit-DB PostgreSQL datasource auto-provisioned
  - grafana-reporter service (izakmarais/grafana-reporter:8686) for PDF/HTML compliance export
  - yesoreyeram-infinity-datasource plugin enabled via GF_INSTALL_PLUGINS

affects:
  - 03-04-platform (audit infrastructure ready for platform hardening)
  - Compliance reporting (BCBS 239 dashboards exportable as PDF evidence)

# Tech tracking
tech-stack:
  added:
    - yesoreyeram-infinity-datasource (Grafana plugin for Marquez lineage API queries)
    - izakmarais/grafana-reporter:latest (PDF/HTML dashboard export service on port 8686)
    - audit_schema.py (stdlib only, no new deps)
    - anomaly_detector.py (stdlib only, no new deps)
    - audit_archiver.py (requires boto3 + pyarrow at runtime, optional)
  patterns:
    - TDD Red-Green for audit schema and anomaly detector
    - Cross-engine normalization pattern: each engine -> AuditRecord via normalize_*() function
    - Graceful skip pattern: env-var gated extractors (TERADATA_HOST, SNOWFLAKE_ACCOUNT)
    - Enterprise edition fallback: Snowflake ACCESS_HISTORY -> QUERY_HISTORY when unavailable
    - Upsert pattern: ON CONFLICT (audit_id) DO NOTHING for idempotent audit ingestion
    - Sliding window frequency detection for HIGH_FREQUENCY_QUERY heuristic
    - Traffic-light Grafana: color-coded table rows via fieldConfig.overrides with badge_status mapping
    - Infinity datasource: Marquez REST API queries embedded directly in Grafana dashboard JSON
    - Deep-link pattern: OpenMetadata catalog URLs as cell links in Grafana table panels

key-files:
  created:
    - etl/src/governance/audit_schema.py
    - etl/src/governance/audit_aggregator.py
    - etl/src/governance/anomaly_detector.py
    - etl/src/governance/audit_archiver.py
    - etl/dags/governance/__init__.py
    - etl/dags/governance/dag_audit_aggregation.py
    - etl/dags/governance/dag_anomaly_report.py
    - etl/dags/governance/dag_freshness_check.py
    - etl/tests/unit/test_audit_schema.py
    - etl/tests/unit/test_anomaly_detector.py
    - etl/tests/integration/test_audit_pipeline.py
    - etl/tests/integration/test_compliance_lineage.py
    - infra/docker/grafana/dashboards/bcbs239_compliance.json
    - infra/docker/grafana/dashboards/data_freshness.json
    - infra/docker/grafana/dashboards/audit_overview.json
    - infra/docker/grafana-reporter/grafana-reporter.env
  modified:
    - etl/src/governance/__init__.py
    - infra/docker/grafana/provisioning/datasources.yml
    - docker-compose.yml

key-decisions:
  - "Cross-engine audit normalized to common AuditRecord dataclass (13 fields including masked_columns for Ranger masking evidence)"
  - "TeradataAuditExtractor and SnowflakeAuditExtractor skip gracefully when env vars not set (TERADATA_HOST, SNOWFLAKE_ACCOUNT) -- matching existing pattern from other optional integrations"
  - "Snowflake ACCESS_HISTORY -> QUERY_HISTORY fallback: ACCESS_HISTORY requires Enterprise edition (documented as pitfall #7); fallback preserves functionality on Standard tier"
  - "Audit storage reuses marquez-db PostgreSQL (new audit_records table in marquez schema) rather than adding new infrastructure -- avoids new service requirement"
  - "grafana-reporter izakmarais image: lightweight sidecar that renders Grafana dashboards to PDF without Grafana Enterprise requirement"
  - "Anomaly thresholds as function parameters (not config files): simplifies testing, allows per-call overrides, avoids config management overhead for heuristics"
  - "BCBS 239 dashboard uid=bcbs239-compliance for cross-dashboard deep-links from audit-overview"

# Metrics
duration: 13min
completed: 2026-03-13
---

# Phase 3 Plan 03: BCBS 239 Compliance Dashboards and Audit Trail Summary

**Cross-engine audit trail aggregation (Trino/Teradata/Snowflake->PostgreSQL), 4-heuristic anomaly detector, 3 governance DAGs, and 3 auto-provisioned Grafana compliance dashboards for BCBS 239 regulatory evidence with Marquez lineage API integration via Infinity plugin**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-13T17:55:48Z
- **Completed:** 2026-03-13T18:08:32Z
- **Tasks:** 2 (Task 1 with TDD)
- **Files modified:** 18

## Accomplishments

- Audit schema module: AuditRecord dataclass with 13 fields (audit_id, timestamp, engine, user_name, query_id, query_text, tables_accessed, columns_accessed, rows_returned, bytes_scanned, masked_columns, access_granted, source_engine_audit_id). AUDIT_SCHEMA maps each field to PostgreSQL SQL type for DDL. to_dict() and to_insert_values() for DB operations.

- Cross-engine normalization: normalize_trino_audit() parses Trino HTTP event listener JSON (queryCompletedEvent.metadata.tables for table/column extraction), normalize_teradata_audit() parses DBC.QryLogV rows with optional DBQLObjTbl column enrichment, normalize_snowflake_audit() parses DIRECT_OBJECTS_ACCESSED JSONB with dot-notation object name parsing.

- Audit aggregator: TrinoAuditExtractor connects to HTTP receiver service, TeradataAuditExtractor skips when TERADATA_HOST not set, SnowflakeAuditExtractor tries ACCESS_HISTORY first then falls back to QUERY_HISTORY for Standard edition accounts. aggregate_audit_records() creates audit_records table + indexes if not exists, batch inserts with ON CONFLICT DO NOTHING.

- Anomaly detector: 4 heuristics -- BULK_DOWNLOAD (>100k rows, severity medium), AFTER_HOURS_ACCESS (outside 06:00-22:00 UTC, low for normal tables, high for sensitive_ns), UNUSUAL_RESTRICTED_ACCESS (access to sensitive_ns/restricted/pii/confidential schemas, severity high), HIGH_FREQUENCY_QUERY (>1000 queries/hour per user via sliding window, severity medium). All thresholds configurable via parameters. format_anomaly_report() produces markdown with summary table and per-anomaly detail.

- Audit archiver: archive_old_records() queries records older than N days, writes Parquet partitioned by year/month to S3, deletes from PostgreSQL. S3 lifecycle policy (3yr->IA, 7yr->Glacier) documented in module docstring.

- 3 governance DAGs: governance_audit_aggregation (02:00 UTC, extract-parallel->aggregate->archive, retries=3 exponential), governance_anomaly_report (06:00 UTC, fetch->detect->report->pdf_export), governance_freshness_check (every 2h, check->upsert_metrics).

- BCBS 239 compliance dashboard (bcbs239_compliance.json, uid=bcbs239-compliance): 11 panels across 4 rows -- Accuracy (quality scores table + trend timeseries via Prometheus), Completeness (lineage coverage stat + missing sources table via Marquez Infinity), Timeliness (pipeline SLA gauge + late runs table from freshness_metrics), Lineage Explorer (dataset variable dropdown -> Marquez /api/v1-beta/lineage?nodeId query -> node table). All dataset names deep-link to OpenMetadata catalog.

- Data freshness SLA dashboard (data_freshness.json): 4 panels -- overview stat (GREEN/YELLOW/RED counts), per-table status table (color-coded rows by badge_status), 7-day freshness timeline, SLA breaches table (YELLOW/RED tables with hours_overdue column). All table names deep-link to OpenMetadata.

- Audit trail overview dashboard (audit_overview.json, uid=audit-overview): 7 panels -- query volume by engine timeseries, top 10 users barchart, restricted data access table (sensitive_ns filter), masked column access log, daily anomaly count stat, access denied trend, access denied events table.

- Grafana infrastructure: GF_INSTALL_PLUGINS=yesoreyeram-infinity-datasource added to Grafana container, datasources.yml updated with Marquez-API (Infinity, http://marquez:5000) and Audit-DB (PostgreSQL, marquez-db:5432). grafana-reporter:8686 service added to docker-compose.yml for PDF export.

## Task Commits

1. **TDD RED: Audit schema and anomaly detector tests** - `f446819` (86 failing tests)
2. **TDD GREEN: All governance modules and DAGs** - `f4be61d` (404 unit tests passing)
3. **Grafana dashboards, datasources, and reporter service** - `14fc1d2`

## Files Created/Modified

- `etl/src/governance/audit_schema.py` - AuditRecord, AUDIT_SCHEMA, normalize_trino_audit(), normalize_teradata_audit(), normalize_snowflake_audit()
- `etl/src/governance/audit_aggregator.py` - TrinoAuditExtractor, TeradataAuditExtractor, SnowflakeAuditExtractor, aggregate_audit_records()
- `etl/src/governance/anomaly_detector.py` - AnomalyType, AnomalyReport, detect_anomalies(), format_anomaly_report()
- `etl/src/governance/audit_archiver.py` - archive_old_records() to S3 Parquet with 90-day default retention
- `etl/src/governance/__init__.py` - Updated to export new audit_schema and anomaly_detector symbols
- `etl/dags/governance/__init__.py` - Package init
- `etl/dags/governance/dag_audit_aggregation.py` - Daily audit ETL DAG (02:00 UTC, parallel extract + aggregate + archive)
- `etl/dags/governance/dag_anomaly_report.py` - Daily anomaly report DAG (06:00 UTC, detect + report + PDF export)
- `etl/dags/governance/dag_freshness_check.py` - Bi-hourly freshness SLA check DAG
- `etl/tests/unit/test_audit_schema.py` - 86 unit tests for AuditRecord, AUDIT_SCHEMA, normalize_*()
- `etl/tests/unit/test_anomaly_detector.py` - Tests for all 4 anomaly heuristics + format_anomaly_report()
- `etl/tests/integration/test_audit_pipeline.py` - Integration tests (auto-skip, PostgreSQL probe)
- `etl/tests/integration/test_compliance_lineage.py` - Integration tests (auto-skip, Marquez probe)
- `infra/docker/grafana/dashboards/bcbs239_compliance.json` - 11-panel BCBS 239 compliance dashboard
- `infra/docker/grafana/dashboards/data_freshness.json` - 4-panel freshness SLA dashboard
- `infra/docker/grafana/dashboards/audit_overview.json` - 7-panel audit trail overview dashboard
- `infra/docker/grafana/provisioning/datasources.yml` - Added Marquez-API and Audit-DB datasources
- `infra/docker/grafana-reporter/grafana-reporter.env` - grafana-reporter service configuration
- `docker-compose.yml` - Added GF_INSTALL_PLUGINS, grafana-reporter service

## Decisions Made

- **Cross-engine normalization via dedicated functions**: Each engine has its own normalize_*() function rather than a class hierarchy. Keeps the schema module flat and testable without subclassing.
- **Teradata/Snowflake graceful skip**: Env-var gated (TERADATA_HOST, SNOWFLAKE_ACCOUNT) -- matching the established pattern from lineage_stubs.py. DAGs log INFO and return empty list, so partial environments still produce valid audit runs.
- **Snowflake ACCESS_HISTORY -> QUERY_HISTORY fallback**: Per documented pitfall #7, ACCESS_HISTORY requires Enterprise edition. The fallback maintains feature parity at the cost of losing column-level access detail.
- **Audit DB reuses marquez-db**: Creates audit_records table in the marquez PostgreSQL instance rather than adding new infrastructure. Simplifies deployment; can be migrated to dedicated DB if needed.
- **grafana-reporter sidecar**: izakmarais/grafana-reporter is a lightweight Go binary that renders Grafana panels to PDF without requiring Grafana Enterprise Image Renderer. Non-critical: PDF export failure in DAG is logged and does not fail the anomaly report task.
- **Anomaly thresholds as function parameters**: bulk_download_threshold=100_000, high_freq_threshold=1_000, business_hours=(6,22), restricted_schemas configurable per call. No config files needed -- simplifies testing and allows different thresholds per environment.

## Deviations from Plan

None - plan executed exactly as written.

## User Setup Required

No external configuration required for unit tests (404 pass immediately).

For live audit pipeline operation:
1. `docker compose up -d grafana grafana-reporter marquez-db`
2. Install Infinity plugin (auto-installed via GF_INSTALL_PLUGINS on first start)
3. Navigate to Grafana at http://localhost:3001 (admin/admin)
4. All 3 compliance dashboards auto-provisioned from /var/lib/grafana/dashboards
5. For Marquez lineage queries: ensure `docker compose up -d marquez` (port 5000)
6. For audit aggregation: `docker compose up -d airflow-webserver airflow-scheduler`
7. Optional Teradata: set TERADATA_HOST, TERADATA_USER, TERADATA_PASSWORD in Airflow environment
8. Optional Snowflake: set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD in Airflow environment

For BCBS 239 compliance PDF export:
```bash
curl "http://localhost:8686/render?dashboard=bcbs239-compliance&from=now-24h&to=now" \
  --output bcbs239_$(date +%Y%m%d).pdf
```

## Next Phase Readiness

- Audit infrastructure ready for 03-04 (platform hardening)
- 3 compliance dashboards deployable for regulatory evidence
- Anomaly detection runs daily on all audit records
- PDF export available for audit evidence archive

## Self-Check: PASSED

All files present and all commits verified:
- audit_schema.py: FOUND
- audit_aggregator.py: FOUND
- anomaly_detector.py: FOUND
- audit_archiver.py: FOUND
- dag_audit_aggregation.py: FOUND
- dag_anomaly_report.py: FOUND
- dag_freshness_check.py: FOUND
- bcbs239_compliance.json: FOUND
- data_freshness.json: FOUND
- audit_overview.json: FOUND
- grafana-reporter.env: FOUND
- Commit f446819: FOUND
- Commit f4be61d: FOUND
- Commit 14fc1d2: FOUND
- 404 unit tests: PASSING

---
*Phase: 03-governance-security-hardening-and-platform*
*Completed: 2026-03-13*
