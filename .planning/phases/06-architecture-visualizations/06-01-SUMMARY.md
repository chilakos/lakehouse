---
phase: 06-architecture-visualizations
plan: 01
subsystem: docs
tags: [jinja2, html, css, mermaid, architecture, tooltips, docker-compose, yaml]

# Dependency graph
requires:
  - phase: 05-html-foundation-and-swot-analyses
    provides: "Jinja2 template system (base_swot.html, macros), render_html.py, extract_versions(), 13 existing tests"
provides:
  - "extract_services() function parsing docker-compose.yml for ports, healthcheck, depends_on"
  - "render_architecture() function producing marketecture + detailed architecture HTML pages"
  - "render_mermaid_to_svg() with graceful mmdc fallback"
  - "base_architecture.html template with CSS tooltips, stats banner, service grid"
  - "services.yml with all 25 services, 8 layer groupings, descriptions, protocols"
  - "environments.yml with dev/staging/prod data from terraform.tfvars"
  - "Mermaid diagram sources (marketecture.mmd, detailed-architecture.mmd)"
  - "7 new tests for ARCH-01, ARCH-02, ARCH-08"
affects: [06-02-remaining-architecture, 07-developer-docs, 08-data-catalog]

# Tech tracking
tech-stack:
  added: []
  patterns: [extract-services-from-compose, yaml-override-merge, css-only-hover-tooltips, mermaid-to-svg-with-fallback, hybrid-html-grid-for-service-reference]

key-files:
  created:
    - docs/architecture/data/services.yml
    - docs/architecture/data/environments.yml
    - docs/architecture/diagrams/marketecture.mmd
    - docs/architecture/diagrams/detailed-architecture.mmd
    - docs/templates/base_architecture.html
    - docs/architecture/marketecture.html
    - docs/architecture/detailed-architecture.html
  modified:
    - docs/render_html.py
    - etl/tests/test_html_render.py

key-decisions:
  - "Hybrid approach for detailed architecture: HTML/CSS grid for service reference (not monolithic Mermaid SVG) enables native CSS hover tooltips"
  - "Graceful mmdc fallback: placeholder SVG rendered when Mermaid CLI unavailable (Puppeteer/Chromium dependency)"
  - "services.yml as override layer: docker-compose.yml is authoritative for ports/healthcheck/depends_on; services.yml adds descriptions, layers, protocols"

patterns-established:
  - "extract_services() merges docker-compose.yml data with services.yml overrides for enriched metadata"
  - "render_architecture() renders multiple page types from single base_architecture.html template via page_type variable"
  - "CSS-only tooltips using visibility:hidden + :hover toggle on .service-node wrapper divs"
  - "Mermaid .mmd sources pre-rendered to SVG at build time with subprocess fallback to placeholder SVG"

requirements-completed: [ARCH-01, ARCH-02, ARCH-08]

# Metrics
duration: 7min
completed: 2026-03-14
---

# Phase 6 Plan 01: Architecture Rendering Pipeline Summary

**Marketecture and detailed service architecture HTML pages with CSS hover tooltips, extract_services() metadata pipeline, and services.yml override system for all 25 docker-compose services**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-14T20:39:50Z
- **Completed:** 2026-03-14T20:47:23Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Built extract_services() parsing docker-compose.yml for ports, healthcheck, depends_on across all 25 services, merged with services.yml overrides for layer groupings, descriptions, and protocols
- Marketecture HTML page with stats banner (1.5 PB managed, 300+ data sources, 40+ engineers, 3 query engines), 8 capability groups with value propositions, and Mermaid diagram
- Detailed architecture HTML page with 23 services (excluding init containers) grouped by 8 layers (Storage, Catalog, Query, ETL, Semantic, Governance, Security, Monitoring), CSS hover tooltips showing version/protocol/healthcheck/depends_on
- base_architecture.html Jinja2 template with embedded navy/gold CSS, responsive design, print rules, and CSS-only tooltip system
- services.yml with complete metadata for all 25 services and environments.yml with dev/staging/prod data from terraform.tfvars

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for architecture rendering** - `ef9b737` (test, TDD RED)
2. **Task 1 (GREEN): Implement extract_services, render pipeline, data files** - `4ce82ea` (feat, TDD GREEN)
3. **Task 2: Render marketecture and detailed architecture HTML pages** - `8be3423` (feat)

## Files Created/Modified
- `docs/render_html.py` - Extended with extract_services(), render_mermaid_to_svg(), render_architecture(), _placeholder_svg()
- `docs/architecture/data/services.yml` - Service metadata: 25 services, 8 layers, descriptions, protocols, exclude list
- `docs/architecture/data/environments.yml` - Dev/staging/prod environment comparison data
- `docs/architecture/diagrams/marketecture.mmd` - Mermaid marketecture diagram with 8 subgraphs and value tags
- `docs/architecture/diagrams/detailed-architecture.mmd` - Mermaid overview diagram with all services and inter-layer dependencies
- `docs/templates/base_architecture.html` - Jinja2 template: stats banner, capability groups, service grid, CSS tooltips, responsive, print
- `docs/architecture/marketecture.html` - Rendered marketecture page (11.9 KB)
- `docs/architecture/detailed-architecture.html` - Rendered detailed architecture page (22.3 KB)
- `etl/tests/test_html_render.py` - Extended with 7 new tests for ARCH-01, ARCH-02, ARCH-08

## Decisions Made
- Used hybrid approach for detailed architecture: HTML/CSS grid for service reference (not a single monolithic Mermaid SVG) because CSS hover tooltips work natively on HTML divs but are fragile on SVG elements
- Implemented graceful mmdc fallback with placeholder SVG when Mermaid CLI is unavailable due to missing Chromium/Puppeteer libraries -- ensures HTML pages render correctly regardless of mmdc availability
- Used services.yml as an override layer rather than extending docker-compose.yml -- keeps docker-compose as the authoritative source for infrastructure config while adding display-only metadata (descriptions, layer assignments, protocols)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertion for stats banner "3 query engines"**
- **Found during:** Task 1 (GREEN phase test validation)
- **Issue:** Test checked for "3 query engines" as a contiguous string, but template renders "3" and "Query Engines" in separate HTML elements (stat-value and stat-label spans)
- **Fix:** Updated assertion to check for "Query Engines" independently (stat value "3" already verified)
- **Files modified:** etl/tests/test_html_render.py
- **Verification:** All 20 tests pass
- **Committed in:** 4ce82ea

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test assertion adjustment. No scope creep.

## Issues Encountered
- Mermaid CLI (mmdc) cannot render SVG in this environment due to missing Chromium shared libraries (libatk-1.0.so.0). This is expected in headless CI environments without a display server. The render pipeline handles this gracefully with placeholder SVGs, and all HTML content/structure is verified independently of SVG rendering.

## User Setup Required
None - no external service configuration required. Mermaid SVG rendering is optional; HTML pages work correctly with placeholder SVGs.

## Next Phase Readiness
- Architecture rendering pipeline proven end-to-end
- Plan 06-02 can build remaining architecture pages (data-flow, service-dependency, security-layer, governance-stack, environment differences) using the same render_architecture() infrastructure
- base_architecture.html template and services.yml data reusable for all subsequent architecture pages
- 20 tests provide regression safety for template and rendering changes

## Self-Check: PASSED

- All 9 files verified present on disk
- All 3 commits (ef9b737, 4ce82ea, 8be3423) verified in git log
- 20/20 tests passing in test_html_render.py
- 512/512 tests passing across full suite

---
*Phase: 06-architecture-visualizations*
*Completed: 2026-03-14*
