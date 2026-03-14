# Phase 5: HTML Foundation and SWOT Analyses - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the shared CSS template infrastructure (embedded styles, print-friendly, responsive) and produce all 6 SWOT analysis HTML pages for leadership, plus a cross-SWOT index page. Establishes the version-stamped footer pattern used by all downstream HTML deliverables (Phases 6-8).

</domain>

<decisions>
## Implementation Decisions

### Visual Design & Branding
- Corporate navy & gold palette: dark navy (#1a2332) headers, gold (#c8a961) accents — traditional financial services aesthetic
- Plain document style header: title, date, and status only — McKinsey/Gartner report feel, no logo image
- Color-coded SWOT quadrants: green (Strengths), blue (Opportunities), yellow (Weaknesses), red (Threats) — classic executive format
- System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif`) — no external fonts
- All CSS embedded in `<style>` block — truly standalone HTML files
- `@media print` rules for clean print-to-PDF
- Responsive design for tablet reading (CSS media queries)
- Collapsible `<details>`/`<summary>` sections — CSS-only, no JavaScript

### SWOT Content Depth
- **4 decided SWOTs** (Nessie, Phased Python, Cube, Build-own NL-to-SQL): Full competitive analysis of each alternative with pros/cons — shows leadership the rigor behind each choice
- **2 undecided SWOTs** (Snowflake Strategy, Data Model Strategy): Present balanced analysis with a clear recommendation backed by evidence — leadership can override
- Each SWOT includes: executive summary with recommendation, 2x2 grid, detailed S/W/O/T sections with evidence, decision matrix/comparison table, mitigations for every threat
- Existing Nessie SWOT markdown (docs/swot/nessie-catalog-swot.md, 176 lines) is the content template — convert and enhance for all 6

### Undecided SWOT Input
- Snowflake and Data Model SWOTs: Use web research for market positioning and infer from codebase — no additional domain-specific input provided
- Snowflake: research current Iceberg REST catalog support, consumption pricing model, competitive positioning vs Trino
- Data Model: infer FSDM coverage from existing schema definitions, research medallion evolution patterns in financial services

### Cross-SWOT Index Page
- Dashboard-style card layout with status badges
- Brief paragraph per SWOT with visual grouping of decided vs undecided
- Decided badges (green), Undecided/Pending Decision badges (amber)
- Links to each standalone SWOT HTML file

### Version-Stamped Footer (ARCH-09)
- Every HTML deliverable includes footer with: generation date, platform component versions (Nessie 0.107.4, Trino 479, Cube 0.36.0, Ranger 2.8.0, etc.), next review date
- Footer template built into the shared CSS/Jinja2 base template so all downstream phases inherit it

### Claude's Discretion
- Exact CSS spacing, margins, and typography sizing
- Jinja2 template structure and YAML data file format for SWOT content
- How deep to go on each alternative in the decided SWOTs
- Collapsible section grouping (which sections are collapsed by default)
- Exact responsive breakpoints

</decisions>

<specifics>
## Specific Ideas

- "Very execu polished HTML" — executive-grade quality, not developer docs aesthetic
- SWOTs should feel like professional strategy documents (McKinsey/Gartner quality)
- The 2 undecided SWOTs (Snowflake, Data Model) are the highest-value deliverables — they unblock active leadership decisions
- Marketecture slide mentioned as "very clean" — carries the same visual polish standard into Phase 6

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/swot/nessie-catalog-swot.md` (176 lines): Complete SWOT content for Nessie — convert to HTML template
- `docs/etl-patterns.md` (565 lines): DataStage migration evidence for SWOT-04
- `docs/adr/001-teradata-otf-nessie-feasibility.md` (155 lines): Architecture decision context
- `docker-compose.yml` (574 lines): Definitive service inventory with versions for footer
- `glossary-seed.json`: FSDM and data model terms for SWOT-05 context
- `semantic/model/`: Cube YAML files providing BI semantic layer evidence for SWOT-06
- `etl/src/semantic/`: NL-to-SQL modules providing AI semantic layer evidence for SWOT-07

### Established Patterns
- Existing Nessie SWOT follows: Executive Summary → Strengths → Weaknesses → Opportunities → Threats → Decision Matrix → Recommendation structure
- All v1.0 code is Python — documentation tooling should use Python (Jinja2) not Node.js

### Integration Points
- HTML files go in `docs/swot/` (HTML versions alongside existing markdown)
- Shared CSS template in `docs/templates/` or similar
- Cross-SWOT index at `docs/swot/index.html`
- Version-stamped footer reads versions from a central config (docker-compose.yml or dedicated versions file)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-html-foundation-and-swot-analyses*
*Context gathered: 2026-03-14*
