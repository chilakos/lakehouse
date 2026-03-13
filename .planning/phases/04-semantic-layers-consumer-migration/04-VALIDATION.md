---
phase: 4
slug: semantic-layers-consumer-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-benchmark |
| **Config file** | etl/pyproject.toml (existing `[tool.pytest.ini_options]`) |
| **Quick run command** | `cd etl && python -m pytest tests/unit -x -q` |
| **Full suite command** | `cd etl && python -m pytest tests/ -x --strict-markers` |
| **Estimated runtime** | ~30 seconds (unit), ~120 seconds (full with integration) |

---

## Sampling Rate

- **After every task commit:** Run `cd etl && python -m pytest tests/unit -x -q`
- **After every plan wave:** Run `cd etl && python -m pytest tests/ -x --strict-markers`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | BISEM-01 | unit | `cd etl && python -m pytest tests/unit/test_cube_models.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | BISEM-02 | integration | `cd etl && python -m pytest tests/integration/test_cube_tableau.py -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | BISEM-03 | integration | `cd etl && python -m pytest tests/integration/test_cube_powerbi.py -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | BISEM-04 | integration | `cd etl && python -m pytest tests/integration/test_performance_benchmark.py -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | AISEM-01 | unit | `cd etl && python -m pytest tests/unit/test_nl_to_sql.py -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | AISEM-02 | unit | `cd etl && python -m pytest tests/unit/test_metric_context.py -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | AISEM-03 | integration | `cd etl && python -m pytest tests/integration/test_nl_accuracy.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `etl/tests/unit/test_cube_models.py` — stubs for BISEM-01 (Cube YAML validation)
- [ ] `etl/tests/unit/test_metric_context.py` — stubs for AISEM-02 (context parser)
- [ ] `etl/tests/unit/test_nl_to_sql.py` — stubs for AISEM-01 (NL-to-SQL prompt building, mocked LLM)
- [ ] `etl/tests/unit/test_risk_exposure_pipeline.py` — stubs for risk exposure Gold pipeline
- [ ] `etl/tests/integration/test_cube_tableau.py` — stubs for BISEM-02 (Cube SQL API smoke test)
- [ ] `etl/tests/integration/test_cube_powerbi.py` — stubs for BISEM-03 (Cube SQL API smoke test)
- [ ] `etl/tests/integration/test_performance_benchmark.py` — stubs for BISEM-04 (benchmark harness)
- [ ] `etl/tests/integration/test_nl_accuracy.py` — stubs for AISEM-03 (golden dataset evaluation)
- [ ] Golden datasets: `etl/src/semantic/golden_datasets/trading_questions.json` and `risk_questions.json`
- [ ] Add `pyyaml` and `boto3` to pyproject.toml dependencies
- [ ] Add `pytest-benchmark` to dev dependencies

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tableau visual rendering | BISEM-02 | Requires Tableau Desktop GUI | Connect Tableau to Cube SQL API (localhost:15432), verify dashboard loads with correct data |
| Power BI visual rendering | BISEM-03 | Requires Power BI Desktop GUI | Connect Power BI to Cube SQL API (localhost:15432), verify report loads with correct data |
| NL question UX | AISEM-01 | Natural language quality is subjective | Ask 10 sample questions from golden dataset, verify answers are readable and accurate |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
