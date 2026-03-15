# Phase 8: Data Catalog and Glossary - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce business-facing data catalog HTML pages: a searchable glossary with plain-language definitions linked to physical tables, metric calculation logic from Cube YAML, medallion layer explanation for non-technical users, data freshness SLA documentation with traffic-light thresholds, regulatory term definitions for BCBS 239 compliance, and lineage/relationship visualizations. Target audiences: business users, compliance officers, and data engineers. All pages use the shared Jinja2/CSS infrastructure from Phase 5 and rendering pipeline from Phase 6.

</domain>

<decisions>
## Implementation Decisions

### Content Tone & Depth
- Layered detail approach: one-line plain-language definition first, then expandable "Technical Detail" section with SQL/table references via CSS-only collapsible sections
- Metric definitions (total_notional, VaR, expected_shortfall) show human-readable formula by default with collapsible section revealing actual Cube SQL for analysts
- Medallion layer explanation uses light technical approach: Bronze/Silver/Gold with real table examples from the platform ("Bronze: raw trade records, Silver: cleaned and validated, Gold: aggregated trading_metrics")
- Regulatory terms (BCBS 239, PII, VaR, Expected Shortfall) paraphrase clearly with regulation name referenced but not quoted verbatim

### Glossary Organization
- Terms grouped by business domain: Trading terms, Risk terms, Governance terms, Infrastructure terms
- Multi-page by topic: separate pages for glossary, metrics, regulatory, freshness, lineage — each focused, with a catalog index page linking them
- Term-to-table mapping shown both ways: inline in each term definition (e.g., "Source: gold.risk_exposure.total_var_95") AND a consolidated mapping table for quick reference
- Catalog index page uses audience-tagged cards (consistent with Phase 7 developer docs index): "Business Users" (glossary, metrics, medallion), "Compliance" (regulatory, lineage), "Data Engineers" (freshness SLAs, term mapping)

### Visualization Approach
- Lineage diagrams (CAT-07) use Mermaid flowcharts rendered to SVG with graceful placeholder fallback — same approach as Phase 6 architecture diagrams
- Term relationship graph (CAT-08) shows domain clusters: related terms grouped by domain (Trading, Risk) with cross-domain connections visualized
- Per-domain focused lineage diagrams (~2-3) plus a simplified overview showing how domains connect at the Gold layer
- Diagram labels use both: friendly label as primary ("Trading Metrics"), table name in smaller text or tooltip (gold.trading_metrics)

### Freshness & Compliance
- Freshness SLA display uses dashboard-style traffic-light badges with color per layer — visual impact for business users
- SLA thresholds extracted from freshness_tracker.py's DEFAULT_SLAS at render time — same pattern as extract_services(), docs always match code
- BCBS 239 compliance tracing shows full audit trail: each regulatory term traces from term → Gold table → Silver source → Bronze ingestion
- OpenMetadata references included: each term shows "View in OpenMetadata: /glossary/term-name" — shows traceability to live system even if links don't work offline

### Claude's Discretion
- Exact page file naming convention within `docs/catalog/`
- How to structure Jinja2 templates for catalog docs (new base_catalog.html vs extend base_developer.html)
- How to extract metric definitions from Cube YAML (parse YAML directly vs manual)
- How to extract freshness SLA thresholds from freshness_tracker.py (import vs AST parse)
- Section ordering within each individual page
- Exact number and scope of lineage diagrams per domain
- Mermaid diagram layout and styling choices

</decisions>

<specifics>
## Specific Ideas

- Catalog pages should feel accessible to non-technical business users — not developer documentation
- The layered detail pattern (plain definition + expandable technical detail) serves both audiences without cluttering the page
- Freshness dashboard should look like a status page, not a configuration reference
- BCBS 239 compliance traces should give a compliance officer confidence they can audit any regulated metric end-to-end
- OpenMetadata references create a bridge between static docs and the live catalog system

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/render_html.py`: Existing render pipeline — extend with `render_catalog_docs()` and extraction functions
- `docs/templates/base_developer.html`: Base template with page_type variants (guide, reference, checklist, faq, visualization) — extend or create `base_catalog.html`
- `docs/templates/macros/collapsible.html`: CSS-only details/summary — reuse for layered detail pattern
- `docs/templates/macros/code_block.html`: Code block macro — reuse for SQL formula display
- `docs/templates/base_arch_index.html`: Index template with audience-tagged cards — reuse for catalog index
- `semantic/model/cubes/trading_metrics.yml`: Cube YAML with measures, descriptions, and `meta.glossary_term` cross-references
- `semantic/model/cubes/risk_exposure.yml`: Cube YAML with VaR, expected shortfall, market value measures
- `etl/src/governance/freshness_tracker.py`: DEFAULT_SLAS with GREEN/YELLOW/RED thresholds, FreshnessStatus enum, get_freshness_badge()
- `etl/src/governance/classification.py`: SensitivityLevel enum (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) for PII classification context
- `etl/src/governance/lineage_stubs.py`: Legacy source registration in Marquez — defines known lineage paths
- `docker-compose.yml` (574 lines): OpenMetadata service URL for catalog references

### Established Patterns
- YAML data files drive content, Jinja2 templates render HTML (Phase 5+)
- All HTML standalone with embedded CSS, no JavaScript, no external dependencies
- Version-stamped footer automatically included via base template
- `extract_services()` pattern: parse source code/config at render time for always-accurate docs
- Mermaid → SVG rendering with graceful mmdc fallback (Phase 6)
- Audience-tagged card index pages (Phase 7)
- `bullet_items` key in YAML (not `items`) to avoid Jinja2 dict.items() collision

### Integration Points
- New files: `docs/catalog/*.html` (rendered output)
- New templates: `docs/templates/base_catalog.html` (or extend existing)
- Render pipeline: `docs/render_html.py` gains `render_catalog_docs()`, `extract_cube_metrics()`, `extract_freshness_slas()`
- Data files: `docs/catalog/data/*.yml` for glossary terms, regulatory definitions, lineage paths
- Diagrams: `docs/catalog/diagrams/*.mmd` for lineage and relationship Mermaid sources
- Tests: `etl/tests/test_html_render.py` gains catalog docs rendering tests

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-data-catalog-and-glossary*
*Context gathered: 2026-03-15*
