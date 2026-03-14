# Phase 7: Developer Documentation - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Produce 12 developer-facing documentation HTML pages covering onboarding, pipeline development, API reference, testing, CI/CD, troubleshooting, service reference, contributor guidelines, and a Day 1 checklist. All pages use the shared Jinja2/CSS infrastructure from Phase 5 and the rendering pipeline from Phase 6. Target audience: 40+ data engineers building on the lakehouse platform.

</domain>

<decisions>
## Implementation Decisions

### Document Structure
- Standalone HTML page per DEV requirement (12 pages total) — consistent with SWOT and architecture patterns
- Developer docs index page at `docs/developer/index.html` with audience-tagged cards: "New Engineers" (onboarding, checklist, first pipeline), "All Engineers" (testing, CI/CD, patterns, service URLs, troubleshooting), "Contributors" (PR process, code style, API reference)
- Class hierarchy visualization (DEV-11) uses Mermaid class diagram rendered to SVG — same approach as Phase 6 architecture diagrams
- ETL patterns reference (DEV-04) converts existing `docs/etl-patterns.md` (564 lines) to HTML as-is — content is already well-structured with code examples, minimal rewriting needed

### Content Depth & Tone
- Concise and direct tone — short paragraphs, bullet points, code-first ("Run this command. You should see this output."). Respects experienced engineers' time
- Onboarding guide (DEV-01) assumes competent Python engineers — list prerequisites without install instructions, focus on project-specific setup (clone, docker-compose up, verify services)
- API reference (DEV-10) documents public API only — signatures, parameters, return types, one usage example per function. Covers all 8 packages: pipelines, config, governance, quality, semantic, iceberg_utils, lineage, inventory
- Troubleshooting FAQ (DEV-08) uses Symptom → Fix → Why format — engineers learn the system while fixing issues

### Code Examples
- First pipeline tutorial (DEV-03) uses a new synthetic pipeline ("hello world" CSV → Bronze) — clearly a teaching example, avoids coupling to production code. Builds step by step
- All code examples show full import paths — copy-paste-ready, zero ambiguity for 40+ engineers
- Service URL reference (DEV-07) auto-extracted from docker-compose.yml with manual annotations YAML override — base URLs from extract_services(), add friendly descriptions, default credentials, common actions via services.yml pattern from Phase 6
- Testing guide (DEV-05) includes formatted pytest output snippets showing passing/failing examples

### Audience Targeting
- Assume Python/PySpark proficiency throughout — no primers on language features, focus on project-specific patterns (BasePipeline, Iceberg, Airflow DAGs)
- Day 1 checklist (DEV-09) is literally a single printed A4/Letter page — compact checkboxes via @media print CSS, covering: setup done, first pipeline run, first PR opened
- Contributor guidelines (DEV-12) include rules with brief rationale ("Branch naming: feature/TICKET-description. Why: CI parses branch prefix for environment routing")
- CI/CD workflow (DEV-06) includes a Mermaid flowchart showing PR → CI checks → dev → staging → prod promotion path

### Claude's Discretion
- Exact page file naming convention within `docs/developer/`
- How to structure the Jinja2 templates for developer docs (new base template vs extend existing)
- Specific troubleshooting entries in the FAQ (derive from docker-compose.yml and common failure modes)
- How to extract public API signatures from Python source (inspect, AST, or manual)
- Section ordering within each individual page
- How many concrete pipelines to reference in the tutorial alongside the synthetic one

</decisions>

<specifics>
## Specific Ideas

- Developer docs should be practical and action-oriented — "the docs a senior engineer wants to read on their first day"
- The Day 1 checklist should work as a literal printout that a new engineer checks off at their desk
- API reference should enable engineers to find any function's import path and usage without reading source code
- Troubleshooting FAQ should cover the specific services in this stack: Docker memory for Spark, Nessie health checks, Spark JAR conflicts, Airflow init sequences, Ranger startup dependencies

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/render_html.py`: Existing render pipeline with `extract_versions()`, `extract_services()`, `render_swots()`, `render_index()`, `render_architecture()`, `render_arch_index()` — extend with `render_developer_docs()`
- `docs/templates/base_swot.html`: Base template with navy/gold CSS, print rules, responsive design — create `base_developer.html` or reuse
- `docs/templates/base_arch_index.html`: Index template with audience-tagged cards — reuse for developer docs index
- `docs/templates/macros/collapsible.html`: CSS-only details/summary — reuse for long code examples and FAQ answers
- `docs/etl-patterns.md` (564 lines): Complete ETL patterns content ready for HTML conversion (DEV-04)
- `docs/architecture/data/services.yml`: Service metadata with descriptions, layers, protocols — extend for developer-facing annotations
- `docker-compose.yml` (574 lines): Authoritative service definitions, ports, health checks for DEV-07 and DEV-08
- `etl/src/pipelines/base.py`: BasePipeline class with full docstrings — source for class hierarchy and API reference
- 8 ETL packages (pipelines, config, governance, quality, semantic, iceberg_utils, lineage, inventory): Source for API reference (DEV-10)
- `docs/adr/001-teradata-otf-nessie-feasibility.md`: ADR content for CI/CD and architecture context
- `.pre-commit-config.yaml`: Pre-commit hooks for contributor guidelines (DEV-12)

### Established Patterns
- YAML data files drive content, Jinja2 templates render HTML — developer docs should follow same pattern
- All HTML standalone with embedded CSS, no JavaScript, no external dependencies
- Version-stamped footer automatically included via base template
- `extract_services()` parses docker-compose.yml for service metadata — reuse for DEV-07
- Mermaid → SVG rendering pipeline available for class hierarchy (DEV-11) and CI/CD flow (DEV-06)

### Integration Points
- New files: `docs/developer/*.html` (rendered output)
- New templates: `docs/templates/base_developer.html` (or extend existing base)
- Render pipeline: `docs/render_html.py` gains `render_developer_docs()` and related functions
- Data files: `docs/developer/data/*.yml` for structured content (FAQ entries, service annotations, etc.)
- Tests: `etl/tests/test_html_render.py` gains developer docs rendering tests

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-developer-documentation*
*Context gathered: 2026-03-14*
