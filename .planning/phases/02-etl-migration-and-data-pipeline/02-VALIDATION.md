---
phase: 02
slug: etl-migration-and-data-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0.0 (already configured) |
| **Config file** | `etl/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `cd /home/azureuser/lakehouse/etl && python -m pytest tests/unit/ -x --tb=short` |
| **Full suite command** | `docker compose -f docker-compose.test.yml up --build --abort-on-container-exit` |
| **Estimated runtime** | ~30 seconds (unit), ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd /home/azureuser/lakehouse/etl && python -m pytest tests/unit/ -x --tb=short`
- **After every plan wave:** Run `docker compose -f docker-compose.test.yml up --build --abort-on-container-exit`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | FNDTN-07 | integration | `pytest tests/integration/test_medallion_layers.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | ETL-01 | unit | `pytest tests/unit/test_base_pipeline.py -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | QUAL-01 | unit | `pytest tests/unit/test_schema_validation.py -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | ETL-04 | unit | `pytest tests/unit/test_dag_integrity.py -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | GOVN-01 | integration | `pytest tests/integration/test_lineage_capture.py -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | ETL-02 | integration | `pytest tests/integration/test_pilot_reconciliation.py -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 2 | ETL-03 | integration | `pytest tests/integration/test_mainframe_ingest.py -x` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 2 | ETL-05 | integration | `pytest tests/integration/test_incremental_loading.py -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | QUAL-02 | integration | `pytest tests/integration/test_quality_checks.py -x` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 2 | QUAL-03 | unit | `pytest tests/unit/test_reconciliation.py -x` | ❌ W0 | ⬜ pending |
| 02-04-03 | 04 | 2 | QUAL-04 | integration | `pytest tests/integration/test_quality_alerting.py -x` | ❌ W0 | ⬜ pending |
| 02-05-01 | 05 | 3 | ETL-06 | unit | `pytest tests/unit/test_etl_patterns.py -x` | ❌ W0 | ⬜ pending |
| 02-05-02 | 05 | 3 | ETL-07 | unit | `pytest tests/unit/test_job_inventory.py -x` | ❌ W0 | ⬜ pending |
| 02-05-03 | 05 | 3 | PLAT-02 | unit | `pytest tests/unit/test_dashboard_config.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `etl/tests/unit/test_base_pipeline.py` — stubs for ETL-01
- [ ] `etl/tests/unit/test_schema_validation.py` — stubs for QUAL-01
- [ ] `etl/tests/unit/test_reconciliation.py` — stubs for QUAL-03
- [ ] `etl/tests/unit/test_dag_integrity.py` — stubs for ETL-04
- [ ] `etl/tests/unit/test_job_inventory.py` — stubs for ETL-07
- [ ] `etl/tests/unit/test_etl_patterns.py` — stubs for ETL-06
- [ ] `etl/tests/unit/test_dashboard_config.py` — stubs for PLAT-02
- [ ] `etl/tests/integration/test_medallion_layers.py` — stubs for FNDTN-07
- [ ] `etl/tests/integration/test_quality_checks.py` — stubs for QUAL-02
- [ ] `etl/tests/integration/test_lineage_capture.py` — stubs for GOVN-01
- [ ] `etl/tests/integration/test_incremental_loading.py` — stubs for ETL-05
- [ ] `etl/tests/integration/test_mainframe_ingest.py` — stubs for ETL-03
- [ ] `etl/tests/integration/test_pilot_reconciliation.py` — stubs for ETL-02
- [ ] `etl/tests/integration/test_quality_alerting.py` — stubs for QUAL-04
- [ ] Docker Compose extension for Airflow + Marquez services
- [ ] `soda-core-spark-df` added to `pyproject.toml` dependencies
- [ ] Cobrix Spark package added to test Spark session configuration

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Airflow UI shows DAG run history | PLAT-02 | Visual UI validation | Navigate to Airflow UI, confirm DAG list shows run status and history |
| Marquez UI shows lineage graph | GOVN-01 | Visual graph validation | Open Marquez UI, confirm lineage graph shows source→Bronze→Silver→Gold flow |
| Grafana dashboard renders metrics | PLAT-02 | Visual dashboard validation | Open Grafana, confirm SLA/failure/duration panels render with data |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
