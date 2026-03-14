---
phase: 5
slug: html-foundation-and-swot-analyses
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ (from pyproject.toml dev dependencies) |
| **Config file** | `etl/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `cd etl && python -m pytest tests/test_html_render.py -x --timeout=30` |
| **Full suite command** | `cd etl && python -m pytest tests/ -ra` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd etl && python -m pytest tests/test_html_render.py -x --timeout=30`
- **After every plan wave:** Run `cd etl && python -m pytest tests/ -ra`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | SWOT-01 | unit | `python -m pytest tests/test_html_render.py::test_css_embedded -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | ARCH-09 | unit | `python -m pytest tests/test_html_render.py::test_version_footer -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | SWOT-02 | unit | `python -m pytest tests/test_html_render.py::test_nessie_swot -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | SWOT-03 | unit | `python -m pytest tests/test_html_render.py::test_snowflake_swot -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | SWOT-04 | unit | `python -m pytest tests/test_html_render.py::test_datastage_swot -x` | ❌ W0 | ⬜ pending |
| 05-02-04 | 02 | 2 | SWOT-05 | unit | `python -m pytest tests/test_html_render.py::test_data_model_swot -x` | ❌ W0 | ⬜ pending |
| 05-02-05 | 02 | 2 | SWOT-06 | unit | `python -m pytest tests/test_html_render.py::test_bi_semantic_swot -x` | ❌ W0 | ⬜ pending |
| 05-02-06 | 02 | 2 | SWOT-07 | unit | `python -m pytest tests/test_html_render.py::test_ai_semantic_swot -x` | ❌ W0 | ⬜ pending |
| 05-02-07 | 02 | 2 | SWOT-08 | unit | `python -m pytest tests/test_html_render.py::test_index_page -x` | ❌ W0 | ⬜ pending |
| 05-02-08 | 02 | 2 | SWOT-09 | unit | `python -m pytest tests/test_html_render.py::test_collapsible_sections -x` | ❌ W0 | ⬜ pending |
| 05-02-09 | 02 | 2 | SWOT-10 | unit | `python -m pytest tests/test_html_render.py::test_responsive_meta -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `etl/tests/test_html_render.py` — stubs for SWOT-01 through SWOT-10, ARCH-09 (validates rendered HTML structure)
- [ ] Test fixtures: sample YAML data files for template rendering tests
- [ ] Render script must be importable (not just a CLI script) for test usage

*Wave 0 installs test infrastructure before any feature code runs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Print-friendly layout renders correctly | SWOT-01 | Browser print rendering cannot be automated without headless browser | Open HTML in browser → Ctrl+P → verify no cut-off sections, readable fonts |
| Tablet-width responsive layout | SWOT-10 | Visual responsiveness requires viewport simulation | Open HTML → resize browser to 768px width → verify 2x2 grid stacks properly |
| Collapsible sections expand in print | SWOT-09 | Print CSS `::details-content` requires real browser engine | Print preview → verify all details sections expanded |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
