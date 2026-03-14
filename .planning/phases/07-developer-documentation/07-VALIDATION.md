---
phase: 07
slug: developer-documentation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | etl/tests/conftest.py |
| **Quick run command** | `python -m pytest etl/tests/test_html_render.py -x -q` |
| **Full suite command** | `python -m pytest etl/tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest etl/tests/test_html_render.py -x -q`
- **After every plan wave:** Run `python -m pytest etl/tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | DEV-01, DEV-02, DEV-09 | unit | `python -m pytest etl/tests/test_html_render.py -x -q -k "developer"` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | DEV-03 | unit | `python -m pytest etl/tests/test_html_render.py -x -q -k "tutorial"` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | DEV-04, DEV-05, DEV-06 | unit | `python -m pytest etl/tests/test_html_render.py -x -q -k "patterns or testing or cicd"` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | DEV-07, DEV-08 | unit | `python -m pytest etl/tests/test_html_render.py -x -q -k "service_url or troubleshoot"` | ❌ W0 | ⬜ pending |
| 07-03-01 | 03 | 2 | DEV-10, DEV-11 | unit | `python -m pytest etl/tests/test_html_render.py -x -q -k "api_ref or class_hierarchy"` | ❌ W0 | ⬜ pending |
| 07-03-02 | 03 | 2 | DEV-12 | unit | `python -m pytest etl/tests/test_html_render.py -x -q -k "contributor"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `etl/tests/test_html_render.py` — extend with developer docs rendering tests (TDD RED stubs)
- [ ] Existing test infrastructure and conftest.py cover all phase requirements

*Existing infrastructure covers framework needs. Only test stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Day 1 checklist fits on single printed page | DEV-09 | Requires browser print preview | Open in browser, Ctrl+P, verify single A4 page |
| Mermaid class hierarchy SVG rendering | DEV-11 | Requires mmdc/Chromium | Run render_html.py with mmdc installed, verify SVG |
| Service URLs resolve to running services | DEV-07 | Requires Docker stack running | docker-compose up, click each URL in browser |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
