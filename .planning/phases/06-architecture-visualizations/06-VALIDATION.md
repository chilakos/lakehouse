---
phase: 6
slug: architecture-visualizations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3.3 |
| **Config file** | `etl/pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `python3 -m pytest etl/tests/test_html_render.py -x -q --timeout=30` |
| **Full suite command** | `python3 -m pytest etl/tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest etl/tests/test_html_render.py -x -q --timeout=30`
- **After every plan wave:** Run `python3 -m pytest etl/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | ARCH-01 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_marketecture_stats_banner -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | ARCH-01 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_marketecture_capability_groups -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | ARCH-02 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_detailed_arch_all_services -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | ARCH-02 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_extract_services_ports -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | ARCH-08 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_css_hover_tooltips -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | ARCH-03 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_data_flow_medallion_path -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | ARCH-04 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_service_dependency_edges -x` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 2 | ARCH-05 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_security_ranger_services -x` | ❌ W0 | ⬜ pending |
| 06-02-04 | 02 | 2 | ARCH-06 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_governance_lineage_flow -x` | ❌ W0 | ⬜ pending |
| 06-02-05 | 02 | 2 | ARCH-07 | unit | `python3 -m pytest etl/tests/test_html_render.py::test_environment_table_columns -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `etl/tests/test_html_render.py` — extend with test functions for ARCH-01 through ARCH-08 (file exists, needs new tests)
- [ ] `render_architecture()` function — must exist in render_html.py for tests to call
- [ ] `extract_services()` function — must exist in render_html.py for tests to call
- [ ] `@mermaid-js/mermaid-cli` — npx availability for Mermaid rendering (tests can validate HTML output without mmdc if SVG is pre-generated)

*Wave 0 extends existing test infrastructure from Phase 5.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Marketecture communicates value to executives | ARCH-01 | Visual communication quality requires human judgment | Open marketecture.html → verify plain-English labels, professional layout, key numbers prominent |
| CSS tooltips show service details on hover | ARCH-08 | Hover interaction requires browser rendering | Open detailed-architecture.html → hover over service boxes → verify tooltip appears with port, protocol, health check |
| Mermaid SVG diagrams render correctly | ARCH-03/04/05/06 | SVG rendering varies by browser | Open each diagram HTML → verify boxes, arrows, labels render cleanly without overlap |
| Print layout for architecture pages | ARCH-01/02 | Browser print rendering | Open HTML → Ctrl+P → verify no cut-off sections |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
