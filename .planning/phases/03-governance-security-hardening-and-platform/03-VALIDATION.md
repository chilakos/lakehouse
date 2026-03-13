---
phase: 3
slug: governance-security-hardening-and-platform
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | `etl/pyproject.toml` ([tool.pytest.ini_options]) |
| **Quick run command** | `cd etl && python -m pytest tests/unit -x -q` |
| **Full suite command** | `cd etl && python -m pytest tests/ -x -q --strict-markers` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd etl && python -m pytest tests/unit -x -q`
- **After every plan wave:** Run `cd etl && python -m pytest tests/ -x -q --strict-markers`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SEC-03 | integration | `cd etl && python -m pytest tests/integration/test_ranger_masking.py -x` | No -- Wave 0 | ⬜ pending |
| 03-01-02 | 01 | 1 | SEC-04 | integration | `cd etl && python -m pytest tests/integration/test_ranger_row_filter.py -x` | No -- Wave 0 | ⬜ pending |
| 03-02-01 | 02 | 1 | GOVN-03 | unit | `cd etl && python -m pytest tests/unit/test_classification.py -x` | No -- Wave 0 | ⬜ pending |
| 03-03-01 | 03 | 2 | GOVN-02 | integration | `cd etl && python -m pytest tests/integration/test_compliance_lineage.py -x` | No -- Wave 0 | ⬜ pending |
| 03-03-02 | 03 | 2 | GOVN-05 | unit + integration | `cd etl && python -m pytest tests/unit/test_audit_schema.py tests/integration/test_audit_pipeline.py -x` | No -- Wave 0 | ⬜ pending |
| 03-04-01 | 04 | 2 | GOVN-04 | integration | `cd etl && python -m pytest tests/integration/test_catalog_glossary.py -x` | No -- Wave 0 | ⬜ pending |
| 03-04-02 | 04 | 2 | PLAT-01 | integration | `cd etl && python -m pytest tests/integration/test_catalog_ingestion.py -x` | No -- Wave 0 | ⬜ pending |
| 03-04-03 | 04 | 2 | PLAT-03 | unit | `cd etl && python -m pytest tests/unit/test_freshness_tracker.py -x` | No -- Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `etl/tests/unit/test_classification.py` — stubs for GOVN-03 tag classification logic
- [ ] `etl/tests/unit/test_audit_schema.py` — stubs for GOVN-05 common audit schema validation
- [ ] `etl/tests/unit/test_anomaly_detector.py` — stubs for GOVN-05 anomaly detection heuristics
- [ ] `etl/tests/unit/test_ranger_policies.py` — stubs for SEC-03, SEC-04 policy definition structure
- [ ] `etl/tests/unit/test_freshness_tracker.py` — stubs for PLAT-03 freshness logic
- [ ] `etl/tests/integration/test_ranger_masking.py` — stubs for SEC-03 column masking with Ranger
- [ ] `etl/tests/integration/test_ranger_row_filter.py` — stubs for SEC-04 row filtering with Ranger
- [ ] `etl/tests/integration/test_compliance_lineage.py` — stubs for GOVN-02 lineage visualization data
- [ ] `etl/tests/integration/test_catalog_glossary.py` — stubs for GOVN-04 glossary functionality
- [ ] `etl/tests/integration/test_audit_pipeline.py` — stubs for GOVN-05 audit aggregation
- [ ] `etl/tests/integration/test_catalog_ingestion.py` — stubs for PLAT-01 catalog discovery
- [ ] `etl/src/governance/__init__.py` — governance module package init
- [ ] Docker Compose additions: Ranger (admin + db + solr + zk), OpenMetadata (server + ingestion + elasticsearch)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Grafana BCBS 239 dashboard visual layout | GOVN-02 | Visual verification of panel arrangement and data presentation | Open http://localhost:3001, navigate to BCBS 239 dashboard, verify lineage + quality overlay |
| OpenMetadata catalog search UX | PLAT-01 | Visual verification of search results and profiling display | Open http://localhost:8585, search for "trades", verify profiling stats display |
| Business glossary browsing | GOVN-04 | Visual verification of glossary UI and approval workflow | Open http://localhost:8585/glossary, verify terms, definitions, approval states |
| PDF/HTML compliance report export | GOVN-02 | File output quality verification | Run grafana-reporter, verify PDF contains lineage graph and quality overlay |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
