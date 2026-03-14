# Phase 6: Architecture Visualizations - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Create audience-appropriate architecture documentation as standalone HTML: a plain-English marketecture for executives and detailed technical diagrams for engineers. Includes data flow, service dependency, security layer, governance stack visualizations, environment comparison, and CSS hover tooltips. Uses the shared template infrastructure from Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Diagram Rendering Approach
- Mermaid source files (.mmd) pre-rendered to inline SVG at build time — no JavaScript in final HTML
- Extend existing `docs/render_html.py` with `render_architecture()` function alongside `render_swots()` and `render_index()`
- Mermaid source files live in `docs/architecture/diagrams/`, rendered HTML output in `docs/architecture/`
- CSS `:hover` on SVG elements for tooltips (ARCH-08) — inject CSS classes into rendered SVG, hovering shows styled tooltip div with description, port, protocol, health check

### Marketecture Visual Language
- Horizontal layer stacking: Sources (top) → Ingestion → Storage/Lakehouse → Processing → Consumers (bottom)
- 8-10 grouped capability boxes: 'Sources (300+)', 'ETL/Ingestion', 'Iceberg Lakehouse', 'Query Engines', 'Semantic Layers', 'BI/AI Consumers', 'Governance', 'Security' — individual tech names as labels inside each box
- Prominent stats banner across the top: '1.5 PB managed | 300+ data sources | 40+ engineers | 3 query engines'
- Brief value tags on each layer: 'Single source of truth', 'Query anything, anywhere', 'Self-service analytics' — communicates benefit, not just technology

### Detailed Architecture Organization
- Group 25 services by infrastructure layer: Storage, Catalog, Query, ETL/Orchestration, Semantic, Governance, Security, Monitoring — each layer as a swim-lane
- Service boxes show name + primary port number always visible; image version, protocol (HTTP/gRPC/JDBC), health check endpoint, depends_on in hover tooltip
- One comprehensive diagram showing all 25 services with connections — scrollable, authoritative reference view
- Service data auto-extracted from docker-compose.yml (extend extract_versions()), with a separate overrides YAML for descriptions, groupings, and labels that docker-compose doesn't have

### Data Flow & Specialized Diagrams
- Separate standalone HTML pages per topic: data-flow.html, service-dependency.html, security-layer.html, governance-stack.html — consistent with SWOT standalone pattern
- Data flow diagram (ARCH-03): One representative end-to-end path (e.g., market data → Bronze → Silver → Gold → Cube → BI) as main diagram, summary showing other domains follow same pattern
- Environment differences (ARCH-07): HTML table with rows per service/aspect, columns per environment (Dev/Docker Compose, Staging/Terraform+Docker, Prod/Terraform+EKS)
- Architecture index page at docs/architecture/index.html linking all architecture HTML files — mirrors SWOT index pattern with cards

### Claude's Discretion
- Exact Mermaid diagram syntax and node styling
- SVG post-processing approach for tooltip injection
- How to handle Mermaid CLI dependency (mmdc) in the build pipeline
- Exact layer colors and gradient choices within the navy/gold palette
- Connection line routing and arrow styles between services
- How much detail to show in service dependency graph vs data flow diagram
- Collapsible section grouping on multi-diagram pages

</decisions>

<specifics>
## Specific Ideas

- Marketecture should match the "very clean" executive polish standard from Phase 5 SWOT documents — McKinsey/Gartner report quality
- The detailed architecture diagram is meant as a working reference for data engineers — they should be able to look up any service's port and health check endpoint quickly
- Environment table should make it obvious what changes between dev and prod — deployment teams use this during promotion
- Security (Ranger) and governance (OpenLineage/Marquez/Grafana) get dedicated diagrams because they span multiple services — they're cross-cutting concerns, not just boxes in the main diagram

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/render_html.py`: Existing render pipeline with `extract_versions()`, `render_swots()`, `render_index()` — extend with `render_architecture()`
- `docs/templates/base_swot.html`: Base template with embedded CSS (navy/gold), print rules, responsive design — create `base_architecture.html` following same pattern
- `docs/templates/base_index.html`: Index page template with card grid — reuse for architecture index
- `docs/templates/macros/collapsible.html`: CSS-only details/summary wrapper — reuse for collapsible diagram sections
- `docker-compose.yml` (574 lines, 25 services): Definitive source for service names, images, versions, ports, health checks, depends_on

### Established Patterns
- YAML data files drive content, Jinja2 templates render HTML — architecture should follow same pattern
- `extract_versions()` parses docker-compose.yml for service metadata — extend to extract ports, health checks, depends_on
- All HTML files are standalone with embedded CSS, no external dependencies
- Version-stamped footer automatically included via base template

### Integration Points
- New files: `docs/architecture/*.html` (rendered output), `docs/architecture/diagrams/*.mmd` (Mermaid sources)
- Override metadata: `docs/architecture/services.yml` (descriptions, groupings, labels for docker-compose services)
- Render pipeline: `docs/render_html.py` gains `render_architecture()` function
- Tests: `etl/tests/test_html_render.py` gains architecture rendering tests

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-architecture-visualizations*
*Context gathered: 2026-03-14*
