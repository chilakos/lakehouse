---
phase: 06-architecture-visualizations
plan: 02
subsystem: docs
tags: [jinja2, html, css, mermaid, architecture, data-flow, security, governance, environment-table]

# Dependency graph
requires:
  - phase: 06-architecture-visualizations
    plan: 01
    provides: "extract_services(), render_architecture(), base_architecture.html, services.yml, environments.yml"
provides:
  - "4 specialized architecture HTML pages: data-flow, service-dependency, security-layer, governance-stack"
  - "4 Mermaid .mmd diagram sources with layer-colored node styles"
  - "environment_table.html Jinja2 macro for dev/staging/prod comparison"
  - "Architecture index page with card links to all 6 architecture pages"
  - "render_arch_index() function for architecture index rendering"
  - "6 new tests for ARCH-03 through ARCH-07 and architecture index"
affects: [07-developer-docs, 08-data-catalog]

# Tech tracking
tech-stack:
  added: []
  patterns: [mermaid-medallion-diagram, env-comparison-table-macro, arch-index-card-grid, audience-tagged-cards]

key-files:
  created:
    - docs/architecture/diagrams/data-flow.mmd
    - docs/architecture/diagrams/service-dependency.mmd
    - docs/architecture/diagrams/security-layer.mmd
    - docs/architecture/diagrams/governance-stack.mmd
    - docs/templates/macros/environment_table.html
    - docs/templates/base_arch_index.html
    - docs/architecture/data-flow.html
    - docs/architecture/service-dependency.html
    - docs/architecture/security-layer.html
    - docs/architecture/governance-stack.html
    - docs/architecture/index.html
  modified:
    - docs/templates/base_architecture.html
    - docs/render_html.py
    - etl/tests/test_html_render.py

key-decisions:
  - "Environment comparison table placed on governance-stack.html since environment differences relate most closely to operational governance and deployment planning"
  - "Architecture index uses audience-tagged cards (Executives, Engineers, Security, Compliance) for content discoverability by role"

patterns-established:
  - "environment_table macro: Jinja2 macro rendering YAML environment data as responsive HTML table with navy headers and alternating row stripes"
  - "Audience-tagged card grid: base_arch_index.html template with role-based color-coded badges for content navigation"
  - "Narrative sections: .narrative CSS class with gold left border for contextual explanations alongside Mermaid diagrams"

requirements-completed: [ARCH-03, ARCH-04, ARCH-05, ARCH-06, ARCH-07]

# Metrics
duration: 8min
completed: 2026-03-14
---

# Phase 6 Plan 02: Specialized Architecture Diagrams and Index Summary

**4 specialized architecture HTML pages (data-flow, service-dependency, security-layer, governance-stack) with Mermaid diagrams, environment comparison table, and architecture index linking all 6 pages with audience-tagged cards**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-14T20:51:04Z
- **Completed:** 2026-03-14T20:59:04Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Data flow page showing complete Bronze-Silver-Gold medallion path from source to consumer with transformation labels at each stage
- Service dependency page with graph auto-extracted from docker-compose.yml depends_on relationships showing all 6 key dependency chains (Query, ETL, Lineage, Monitoring, Security, Metadata)
- Security layer page documenting Ranger RBAC architecture with three access tiers (data_readers, data_engineers, data_admin), column-level PII masking, and row-level security
- Governance stack page with OpenLineage-Marquez-Grafana lineage flow, BCBS 239 compliance narrative, and environment comparison table showing dev/staging/prod differences
- Architecture index page with 6 cards linking all architecture pages, audience-tagged (Executives, Engineers, Security, Compliance)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for ARCH-03 through ARCH-07** - `068196e` (test, TDD RED)
2. **Task 1 (GREEN): Implement 4 specialized architecture pages with diagrams and env table** - `125c4f7` (feat, TDD GREEN)
3. **Task 2: Architecture index page with card links to all 6 pages** - `e65a7c6` (feat)

## Files Created/Modified
- `docs/architecture/diagrams/data-flow.mmd` - Mermaid flowchart with Bronze/Silver/Gold medallion layers and transformation labels
- `docs/architecture/diagrams/service-dependency.mmd` - Mermaid flowchart with all depends_on relationships from docker-compose.yml, grouped by layer subgraphs
- `docs/architecture/diagrams/security-layer.mmd` - Mermaid flowchart showing Ranger RBAC flow: User -> Trino -> Ranger Plugin -> Policy Check -> Allow/Deny
- `docs/architecture/diagrams/governance-stack.mmd` - Mermaid flowchart showing lineage capture, observability, metadata catalog, and BCBS 239 compliance
- `docs/templates/macros/environment_table.html` - Jinja2 macro rendering environment comparison table with navy headers and alternating rows
- `docs/templates/base_arch_index.html` - Architecture index template with card grid and audience badges
- `docs/templates/base_architecture.html` - Extended with data-flow, service-dependency, security-layer, governance-stack page types and env-table CSS
- `docs/render_html.py` - Extended render_architecture() for 4 new pages + render_arch_index() function
- `docs/architecture/data-flow.html` - Rendered data flow page (12.6 KB)
- `docs/architecture/service-dependency.html` - Rendered service dependency page (12.5 KB)
- `docs/architecture/security-layer.html` - Rendered security layer page (13.2 KB)
- `docs/architecture/governance-stack.html` - Rendered governance stack page (14.9 KB)
- `docs/architecture/index.html` - Rendered architecture index page (7.5 KB)
- `etl/tests/test_html_render.py` - Extended with 6 new tests for ARCH-03 through ARCH-07 and architecture index

## Decisions Made
- Placed the environment comparison table (ARCH-07) on governance-stack.html rather than as a standalone page, because environment differences relate most closely to operational governance and capacity planning
- Used audience-tagged cards (Executives, Engineers, Security, Compliance) on the architecture index for role-based content discoverability, matching the SWOT index card pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Mermaid CLI (mmdc) cannot render SVG in this environment due to missing Chromium shared libraries (libatk-1.0.so.0). This is expected in headless CI environments and was already handled gracefully by the fallback mechanism from Plan 01. All HTML content/structure is verified independently of SVG rendering.

## User Setup Required
None - no external service configuration required. Mermaid SVG rendering is optional; HTML pages work correctly with placeholder SVGs.

## Next Phase Readiness
- Phase 6 (Architecture Visualizations) is now fully complete
- All 7 architecture HTML files rendered and verified (index + 6 pages)
- 26 HTML render tests and 518 total tests passing
- Architecture documentation ready for reference by Phase 7 (Developer Docs) and Phase 8 (Data Catalog)

## Self-Check: PASSED

- All 14 files verified present on disk
- All 3 commits (068196e, 125c4f7, e65a7c6) verified in git log
- 26/26 tests passing in test_html_render.py
- 518/518 tests passing across full suite

---
*Phase: 06-architecture-visualizations*
*Completed: 2026-03-14*
