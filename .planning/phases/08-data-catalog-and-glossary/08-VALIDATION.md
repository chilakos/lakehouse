---
phase: 08
slug: data-catalog-and-glossary
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | etl/tests/test_html_render.py |
| **Quick run command** | `cd etl && python -m pytest tests/test_html_render.py -x -q` |
| **Full suite command** | `cd etl && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd etl && python -m pytest tests/test_html_render.py -x -q`
- **After every plan wave:** Run `cd etl && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | CAT-01, CAT-02, CAT-03, CAT-04 | unit | `cd etl && python -m pytest tests/test_html_render.py -x -q` | ✅ | ⬜ pending |
| 08-01-02 | 01 | 1 | CAT-01, CAT-02, CAT-03, CAT-04 | content | `cd etl && python -m pytest tests/test_html_render.py -x -q` | ✅ | ⬜ pending |
| 08-02-01 | 02 | 2 | CAT-05, CAT-06, CAT-07, CAT-08 | unit | `cd etl && python -m pytest tests/test_html_render.py -x -q` | ✅ | ⬜ pending |
| 08-02-02 | 02 | 2 | CAT-05, CAT-06, CAT-07, CAT-08 | content | `cd etl && python -m pytest tests/test_html_render.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Test file `etl/tests/test_html_render.py` already has 46 tests and the TDD pattern is established from Phases 5-7.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Traffic-light badge colors render correctly | CAT-04 | Visual CSS verification | Open freshness.html in browser, verify GREEN/YELLOW/RED badges display with correct colors |
| Mermaid lineage diagrams render if mmdc available | CAT-07 | External dependency | Run `mmdc` if available, verify SVG output; otherwise verify placeholder renders |
| Catalog index card navigation works | CAT-01-08 | Browser interaction | Open index.html, click each card link, verify target page loads |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
