# Feature Landscape

**Domain:** Executive-grade and developer-grade documentation for a financial services lakehouse platform
**Researched:** 2026-03-14
**Milestone context:** v1.1 Documentation -- adding documentation deliverables to an existing, fully built lakehouse platform (Nessie/Trino/Iceberg, Python ETL, Airflow, Ranger, OpenMetadata, Cube BI, NL-to-SQL AI, CI/CD, 480+ tests)

---

## Table Stakes

Features users expect. Missing = documentation milestone feels incomplete or unprofessional.

### SWOT Analyses (6 documents)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Standard 2x2 SWOT grid per analysis | Universal executive format; audiences know how to read it instantly | Low | Grid is the anchor visual -- every SWOT presentation needs one |
| Executive summary with clear recommendation | Leadership reads summary first, may never read details; decision must be on page 1 | Low | 2-3 paragraphs max; state the recommendation and its one-line rationale up front |
| Decision matrix / comparison table | Multiple options per SWOT (e.g., Nessie vs Polaris vs Glue vs HMS); side-by-side comparison is expected for technology choices in financial services | Med | Already present in existing Nessie SWOT markdown -- replicate pattern for all 6 |
| Mitigations for each threat | Identifying threats without mitigations is analysis without action; executives want to know "so what do we do about it" | Med | Each threat entry needs a concrete mitigation paragraph |
| Standalone HTML with embedded CSS | Deliverable spec requires single-file HTML -- must open in any browser, email-friendly, no external dependencies | Med | All CSS in `<style>` block, no CDN links, no JavaScript dependencies, print-friendly |
| Professional typography and color palette | Financial services executives expect polished, branded-looking deliverables, not raw markdown or developer-style pages | Med | System fonts (avoid web font CDN), consistent color scheme across all 6 SWOTs |
| Print-friendly layout | SWOTs will be printed for board meetings and attached to strategy decks | Low | `@media print` CSS rules, page-break controls, suppress dark background colors that waste toner |
| Consistent structure across all 6 SWOTs | Reader should learn the format once and apply it across all 6 documents; inconsistent structure undermines professionalism | Low | Same section ordering, same CSS template, same header/footer pattern |

### Marketecture HTML Page

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Boxes-and-arrows diagram showing platform layers | Marketecture = simplified architecture for non-technical executives; must show what the platform does, not how it works internally | Med | Layers: Sources (300+), Ingestion (Python ETL), Storage (S3/MinIO + Iceberg), Compute (Trino/Teradata/Snowflake), Semantic (Cube), Consumption (Tableau/Power BI/NL-to-SQL) |
| Pure HTML/CSS diagram (no image dependencies) | Standalone HTML requirement -- diagram must render from markup, not embedded PNGs that break on email forwarding | High | CSS Grid or Flexbox for layout; styled divs for boxes, CSS borders/pseudo-elements for connection lines |
| One clear message per section | Marketecture best practice: each section conveys one idea ("a single governed copy of data"); avoid cramming 20 component logos into one view | Med | Use visual hierarchy: large boxes for major layers, smaller elements for specific tools within each layer |
| Technology labels with brief value propositions | Executives want to know "what does Trino do for us" not just "we use Trino" | Low | One-liner value prop per technology: "Trino -- Open-source SQL engine replacing Teradata for analytics" |
| Consistent visual language with SWOT documents | All deliverables should look like they came from the same team and same brand | Low | Shared CSS color palette, fonts, header styles across marketecture and SWOTs |
| Key numbers callout | Executives anchor on numbers: 1.5 PB, 300+ sources, 40+ engineers, 480+ tests, 6 environments | Low | Callout boxes or highlighted stats at the top of the page |

### Detailed Architecture HTML Page

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Every component with port numbers and protocols | Engineers and architects need exact connection details: Nessie:19120, Trino:8080, MinIO:9000/9001, Cube SQL:15432, Ranger:6080, OpenMetadata:8585, Grafana:3001, etc. | Med | 20+ services in docker-compose.yml -- all must be documented with ports, protocols, health check endpoints |
| Data flow direction arrows | Must show Bronze -> Silver -> Gold data flow, source -> Nessie -> storage paths, consumer -> semantic -> query engine paths | High | CSS-based directional indicators or Unicode box-drawing characters with clear flow direction |
| Service dependency graph | Local dev environment has complex service dependencies -- architecture doc must show which services depend on which | High | Dependency chains: Airflow-worker -> Airflow-scheduler -> Airflow-db + Redis, Nessie -> Postgres + MinIO, Trino -> Nessie, Cube -> Trino + Cubestore, Grafana -> Prometheus -> StatsD, etc. |
| Security layer showing Ranger integration points | Ranger policies, RBAC, column masking must be visible in the architecture | Med | Show where Ranger intercepts Trino queries, which connections carry authentication tokens |
| Environment differences (dev/staging/prod) | Engineers need to know what changes between environments (docker-compose local vs Terraform-managed cloud) | Med | Table or callout showing which Terraform modules deploy which services per environment |
| Governance stack detail | OpenLineage -> Marquez -> Grafana flow for BCBS 239 compliance dashboards; OpenMetadata for catalog/glossary | Med | Show Airflow emitting OpenLineage events, Marquez storing them, Grafana querying Marquez API via Infinity plugin |
| Standalone HTML with embedded CSS | Same standalone requirement as SWOTs | Med | Single file, no external dependencies |

### Developer Onboarding Guide

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Prerequisites and local environment setup | First thing any new engineer needs; "what do I install, how do I start the stack" | Low | Docker, Docker Compose, Python 3.11+, Git -- already in README but onboarding guide needs step-by-step commands with expected output |
| Repository structure walkthrough | 40+ engineers need to find things fast; directory tree with what each directory and key file does | Low | Expand on README structure; explain each package in etl/src/ (governance, quality, semantic, lineage, iceberg_utils, inventory, pipelines, config) |
| "Write your first pipeline" tutorial | Hands-on onboarding best practice; new engineers should have a working pipeline within their first session | Med | Step-by-step: extend BasePipeline, define schema, add quality checks, create DAG, run unit tests, run integration tests. Most content in etl-patterns.md Sections 2-4 |
| ETL pattern reference | 40+ engineers contributing need authoritative, standardized patterns; must be findable and unambiguous | Low | etl-patterns.md is comprehensive and already written -- incorporate or cross-reference (medallion architecture, quality checks, DAG patterns, incremental loading, mainframe sources, testing) |
| Testing guide (unit + integration) | Testing standards must be explicit: how to mock Spark, where fixtures go, pytest markers, CI gate behavior | Low | Section 7 of etl-patterns.md covers this -- needs prominence in onboarding flow |
| CI/CD workflow explanation | Engineers need to know the PR -> dev -> staging -> prod flow, what checks run at each gate, how environment promotion works | Low | ci/README.md has this content -- needs incorporation into the onboarding narrative |
| Service URL reference table | New engineers need to know where to find Trino UI, Airflow UI, MinIO Console, Grafana dashboards, Marquez lineage, Nessie API, Ranger admin, OpenMetadata, Cube playground | Low | Table in README Quick Start exists -- onboarding guide needs the full list with all 10+ services |
| Common troubleshooting / FAQ | New engineers hit the same issues: Docker memory limits, Nessie health check timeout, Spark JAR conflicts, Cobrix JAR unavailability, Airflow init delay, Ranger startup time (120s), OpenMetadata memory (6GB+ required) | Med | Collect from team experience; symptoms + solutions format |

### API/Module Reference Documentation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Complete module listing with descriptions | Engineers need to discover available utilities without reading all 55 source files | Med | 8 packages in etl/src/: config, governance (7 modules), iceberg_utils (4), inventory (2), lineage (1), pipelines (10 across bronze/silver/gold), quality (2), semantic (6), synthetic (1) |
| Public API per module (function signatures, parameters, return types) | Developers need to know what functions exist and how to call them without reading source | Med | Quality depends on existing docstring coverage -- likely variable across modules |
| Import path quick reference | "How do I import the reconciliation module?" must be instantly findable | Low | etl-patterns.md Quick Reference already has this for major modules -- expand to cover all public APIs |
| Usage examples for major modules | Show concrete usage of BasePipeline, JobInventory, reconciliation, Soda scanner, incremental loader, NL-to-SQL, anomaly detector, freshness tracker | Med | Many examples already in etl-patterns.md -- link or expand |
| Class hierarchy visualization | Pipeline inheritance (BasePipeline -> TradesBronzePipeline, PositionsBronzePipeline, MainframeBronzePipeline, etc.) should be visible | Low | Simple text tree or HTML table showing base class and all concrete implementations |

### Contributor Guidelines

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Branch naming and PR process | 40+ engineers need consistent workflow: branch naming convention, required reviewers, approval count, merge strategy | Low | Standard CONTRIBUTING.md content |
| Testing requirements before PR | Minimum test expectations: all unit tests pass, new code has tests, integration tests for pipeline changes | Low | Reference existing pytest markers (`@pytest.mark.unit`, `@pytest.mark.integration`) and CI gates |
| Code style and linting | Ruff config exists in pyproject.toml -- document the rules and how to auto-fix before committing | Low | "Run `ruff check . --fix` and `ruff format .` before committing" |
| Naming conventions | Pipeline classes, DAG IDs, table names, quality check files, test files -- all defined in etl-patterns.md Quick Reference | Low | Copy or reference the naming convention table |
| Commit message format | Standardized commit messages help with changelog generation and git log readability | Low | Choose conventional commits or project-specific format |
| Quality check authoring guide | New SodaCL checks are a common contribution type; needs its own section | Low | Reference etl-patterns.md Section 3 (SodaCL YAML format, critical vs advisory) |

### Data Catalog/Glossary Documentation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Business glossary with plain-language definitions | Business users and data stewards need definitions they can understand without engineering context | Low | glossary-seed.json has 17 terms already defined with descriptions, synonyms, related terms, and tags |
| Term-to-table mapping | "Where does this metric live?" -- link glossary terms to their physical table locations in the lakehouse | Med | Cross-reference Cube YAML `meta.glossary_term` fields with glossary terms; map to `lakehouse.gold.*` tables |
| Medallion layer explanation for non-technical users | Business users need to understand Bronze/Silver/Gold without needing to know Iceberg or Spark | Low | Already in glossary seed (Bronze/Silver/Gold Layer terms) -- needs friendlier narrative format |
| Data freshness SLA documentation | Business users need to know when their data updates, what the SLA thresholds are, and what RED/YELLOW/GREEN means | Low | SLA term already in glossary seed with specific thresholds (Gold: 24h expected / 48h critical, Silver: 12h/24h, Bronze: 6h/12h) |
| Metric definitions with calculation logic | "How is notional_value calculated?" -- business users must trust the numbers by understanding the formula | Med | Pull from Cube YAML measure definitions: total_notional = sum(price * quantity), trade_count = count of trades, avg_price = average execution price |
| Regulatory term definitions | BCBS 239, PII, VaR, Expected Shortfall -- compliance-relevant terms need precise definitions | Low | All present in glossary seed; render as a dedicated compliance section |

---

## Differentiators

Features that set this documentation apart. Not expected, but create significant value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Interactive collapsible sections in SWOTs | Executives can drill into details on demand without being overwhelmed by wall-of-text; better UX than static PDF | Med | Pure CSS `<details>`/`<summary>` elements -- no JavaScript needed, works in all modern browsers, degrades gracefully to visible content in print |
| Decision status badges (Decided/Undecided) | Three SWOTs have decided outcomes, three are undecided -- visual status badges immediately communicate which analyses need leadership action | Low | CSS-styled `<span>` badges: green "Decided" for Nessie/Cube/Phased Python, amber "Pending Decision" for Snowflake/Data Model |
| Cross-SWOT index page | Single HTML page linking all 6 SWOTs with decision status summary; executives see the full decision landscape at a glance | Low | Simple HTML page with 6-row summary table: topic, status, recommendation, link |
| Responsive design (tablet readability) | Executives review on iPad during meetings; responsive layout adds professionalism and practical usability | Med | CSS media queries for tablet breakpoints; `@media print` already needed -- extend for screen sizes |
| Architecture diagram with hover tooltips | Detailed architecture page with CSS `:hover` tooltips showing component descriptions without cluttering the visual diagram | Med | Pure CSS tooltips using `::after` pseudo-elements and `position: absolute` -- no JS needed |
| "Day 1 Checklist" in onboarding guide | Printable single-page checklist: accounts to request, tools to install, first pipeline to run, tests to execute, first PR to submit | Low | Checkbox-styled HTML list that combines setup + first task into one scannable document; high onboarding impact |
| Data lineage visualization in catalog docs | Show end-to-end flow from source -> Bronze -> Silver -> Gold -> Cube -> BI/AI for each data domain (trades, positions, risk) | High | Extremely valuable for BCBS 239 audit documentation; requires diagramming actual pipeline chains from DAG definitions |
| Glossary term relationship visualization | Visual or table showing which glossary terms relate to each other (Trade -> Position -> Risk Metrics -> VaR 95 -> BCBS 239) | Med | glossary-seed.json already has `relatedTerms` data -- render as a cross-reference table or simple graph |
| Version-stamped deliverables | Each HTML doc includes generation date, platform version numbers (Nessie 0.107.4, Trino 479, Cube 0.36.0, Ranger 2.8.0, etc.), and next review date | Low | Footer metadata on every page; enables audit trail for when documentation was current; aligns with quarterly review cycle |
| Governance dashboard screenshots or mockups in catalog docs | Show what the Grafana BCBS 239 compliance dashboard, data freshness dashboard, and pipeline observability dashboard look like | Med | Static annotated mockups (HTML/CSS) rather than screenshots; screenshots go stale but styled mockups convey the intent |

---

## Anti-Features

Features to explicitly NOT build. These add complexity without proportional value for this documentation milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| JavaScript-dependent interactivity | Standalone HTML must work in email clients, SharePoint, corporate intranets that strip or block JS; JS adds testing burden and cross-browser fragility | Use pure HTML/CSS patterns: `<details>`/`<summary>` for collapse, `:hover` for tooltips, CSS Grid for layouts |
| External CSS framework (Bootstrap, Tailwind CDN) | CDN links break offline/email viewing; framework CSS is 150-300KB of bloat for a single-page document | Write custom embedded CSS -- these are single-purpose documents, not web applications; 3-8KB of targeted CSS per document is sufficient |
| Auto-generated docs from docstrings (Sphinx/pdoc build pipeline) | Setting up a Sphinx build pipeline adds infrastructure complexity to CI/CD; docstring quality across 55 modules is likely uneven; deliverable format is standalone HTML, not a hosted documentation site | Write API reference as curated HTML or Markdown; pull key signatures and descriptions manually from well-documented modules; revisit automated docs-as-code when the team establishes a docs pipeline |
| Live data integration in architecture diagrams | Pulling real-time Docker container status or health checks into architecture docs adds fragility, staleness risk, and build pipeline complexity | Static diagrams with version stamps; update manually when infrastructure changes (quarterly review cycle per existing SWOT pattern) |
| Embedded UI screenshots (Grafana, Airflow, Ranger, OpenMetadata) | Screenshots become stale immediately after any UI update, are inaccessible to screen readers, inflate HTML file size, and cannot be updated without retaking them | Describe UIs textually with port/URL references; link to running instances for live exploration; use text-based diagrams or CSS mockups |
| Multi-page HTML site with navigation sidebar | Adds complexity of relative links, multi-file management, broken navigation when emailed; contradicts the standalone single-file requirement | Each deliverable is one self-contained HTML file; cross-reference between documents by title and filename, not by fragile hyperlink |
| PDF generation build pipeline | PDF tooling (wkhtmltopdf, Puppeteer, WeasyPrint) adds CI/CD complexity, font rendering issues, and another build step to maintain | Design HTML with `@media print` CSS rules; any user can File -> Print -> Save as PDF from their browser with identical formatting |
| Video walkthroughs or animated diagrams | High production effort, impossible to update incrementally, not searchable, accessibility challenges, large file sizes | Written guides with code examples; video can be added later as supplementary content, not as a primary deliverable |
| Custom web fonts (Google Fonts, Adobe Fonts) | External font loading fails offline, adds network latency, may violate corporate proxy/firewall policies | Use system font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` |
| Internationalization / multi-language docs | Single-language organization (English); translation effort is not justified at current scale | English-only; revisit only if explicit organizational need arises |
| Comprehensive TOGAF / ArchiMate architecture artifacts | Formal enterprise architecture notation is overkill for this documentation scope; adds jargon that reduces accessibility for the primary audiences | Boxes-and-arrows diagrams with plain English labels; architects who need formal notation can derive it from the detailed architecture page |

---

## Feature Dependencies

```
Shared CSS Template (colors, typography, grid system)
  |
  +-- SWOT Analyses (6 HTML files)
  |     |-- Nessie Catalog SWOT: content exists (docs/swot/nessie-catalog-swot.md)
  |     |-- Snowflake Strategy SWOT: content authoring required (UNDECIDED)
  |     |-- DataStage Migration SWOT: partial content (etl-patterns.md, inventory module)
  |     |-- Data Model Strategy SWOT: content authoring required (UNDECIDED)
  |     |-- BI Semantic Layer SWOT: partial content (Cube config, model YAML)
  |     |-- AI Semantic Layer SWOT: partial content (NL-to-SQL module, evaluation framework)
  |     '-- Cross-SWOT Index Page: depends on all 6 SWOTs complete
  |
  +-- Marketecture HTML
  |     |-- Content source: README.md architecture diagram, docker-compose.yml
  |     '-- No dependency on SWOTs (parallel work)
  |
  +-- Detailed Architecture HTML
  |     |-- Content source: docker-compose.yml (definitive 20+ service inventory)
  |     |-- Content source: infra/docker/ configs (ports, protocols, health checks)
  |     |-- Content source: infra/terraform/ (environment-specific deployment)
  |     '-- Shared CSS template
  |
  +-- Developer Onboarding Guide
  |     |-- Primary content: etl-patterns.md (comprehensive, already written)
  |     |-- Content source: ci/README.md (CI/CD workflow)
  |     |-- Content source: README.md (quick start, repo structure)
  |     |-- Can reference: Detailed Architecture HTML for component details
  |     '-- Can reference: Contributor Guidelines for PR process
  |
  +-- API/Module Reference
  |     |-- Source: etl/src/ Python modules (55 files, 8 packages)
  |     |-- Source: existing docstrings in modules
  |     |-- Starting point: etl-patterns.md Quick Reference (import paths)
  |     '-- No cross-dependency on other deliverables
  |
  +-- Contributor Guidelines
  |     |-- Content source: ci/README.md (workflow and promotion)
  |     |-- Content source: etl-patterns.md Section 7 (testing) + Quick Reference (naming)
  |     |-- Content source: pyproject.toml (ruff config, pytest settings)
  |     '-- Lightweight; can be authored in parallel or last
  |
  '-- Data Catalog/Glossary
        |-- Content source: glossary-seed.json (17 terms)
        |-- Content source: semantic/model/ (4 Cube YAML files with glossary_term metadata)
        |-- Content source: pipeline source code (table names, schemas)
        '-- Can reference: Architecture HTML for medallion layer context
```

### Parallel Work Streams

These groups have no cross-dependencies and can be authored simultaneously:

```
Stream A: SWOT Analyses (6 files) + Cross-SWOT Index
Stream B: Marketecture HTML + Detailed Architecture HTML
Stream C: Developer Onboarding + API Reference + Contributor Guidelines
Stream D: Data Catalog/Glossary Documentation

All streams depend on: Shared CSS template (build first, ~1-2 hours)
```

---

## MVP Recommendation

Prioritize deliverables leadership is waiting on for active strategic decisions:

### Priority 1: Build First

1. **Shared CSS template** -- Foundation for all HTML deliverables. Build once, apply to all. One shared `<style>` block with color palette, typography, grid layout, print styles, and status badges. Estimated: 1-2 hours.

2. **6 SWOT Analyses as standalone HTML** -- Highest leadership priority. Two SWOTs (Snowflake Strategy, Data Model Strategy) have undecided outcomes that are actively blocking strategic planning. The existing Nessie SWOT markdown (`docs/swot/nessie-catalog-swot.md`) provides a proven content template with executive summary, S/W/O/T sections, mitigations, decision matrix, and recommendation. Estimated per SWOT: 2-4 hours for content + HTML/CSS formatting. Nessie SWOT (conversion only): 1-2 hours.

3. **Marketecture HTML** -- Second priority for leadership. Executives need a shareable, professional architecture overview for stakeholder communication, board presentations, and vendor discussions. Content is available from README.md and docker-compose.yml. Estimated: 3-5 hours.

### Priority 2: Build Next

4. **Developer Onboarding Guide** -- Critical for team velocity with 40+ engineers. Most content already exists in etl-patterns.md (560+ lines covering all ETL patterns) -- this is primarily a reorganization, expansion, and formatting task. Estimated: 4-6 hours.

5. **Detailed Architecture HTML** -- Important for engineering leads and platform architects. docker-compose.yml (574 lines, 20+ services) is the definitive content source; this is primarily a rendering and annotation task. Estimated: 4-6 hours.

6. **Data Catalog/Glossary** -- Important for business users and data stewards. glossary-seed.json (17 terms) and Cube YAML models (4 files) provide the starting content. Estimated: 3-4 hours.

### Priority 3: Build Last

7. **API/Module Reference** -- Important for developer productivity but lowest urgency since active developers can read source code directly. Quality depends on docstring coverage. Estimated: 4-8 hours depending on docstring quality.

8. **Contributor Guidelines** -- Important but teams survive with informal conventions initially. Most content exists in ci/README.md and etl-patterns.md. Estimated: 1-2 hours.

9. **Cross-SWOT Index Page** -- Depends on all 6 SWOTs being complete. Very lightweight once SWOTs are done. Estimated: 30 minutes.

**Defer:** Automated documentation generation pipeline (Sphinx autodoc, pdoc). Revisit when documentation maintenance becomes a recurring burden, not during initial authoring. The initial set of documents is small enough that manual authoring is faster and higher quality than setting up a build pipeline.

---

## SWOT-Specific Content Readiness

The 6 SWOTs have different content availability and authoring effort:

| SWOT Topic | Content Status | Decision Status | Authoring Effort | Key Content Sources |
|-----------|---------------|-----------------|------------------|---------------------|
| Iceberg Catalog Choice (Glue vs Nessie vs HMS vs Polaris) | **Complete** -- 176-line markdown with full SWOT, decision matrix, recommendation | Decided: Nessie | **Low** -- convert existing markdown to HTML, apply CSS template | `docs/swot/nessie-catalog-swot.md` |
| Snowflake Strategy (Retire vs Keep vs Maintain) | **Not started** -- needs research on Snowflake ICEBERG_REST capabilities, cost model, contract status, team skill overlap | **Undecided** | **High** -- full research and authoring required | Project context in PROJECT.md; docker-compose.yml shows no Snowflake service (compute-only role) |
| DataStage Migration (Big-bang vs phased vs parallel-run) | **Partial** -- etl-patterns.md documents the chosen Python patterns; job inventory module exists with complexity classification | Decided: Phased Python | **Med** -- SWOT structure needs authoring, but supporting evidence is available | `docs/etl-patterns.md`, `etl/src/inventory/`, ADR-001 |
| Data Model Strategy (Keep FSDM vs evolve vs new medallion) | **Not started** -- needs analysis of current FSDM adoption level, medallion evolution path, backward compatibility constraints | **Undecided** | **High** -- domain expertise input needed; complex organizational implications | PROJECT.md constraints section, glossary-seed.json FSDM terms |
| BI Semantic Layer (Direct vs dbt vs AtScale vs Cube) | **Partial** -- Cube is deployed (docker-compose), YAML models written (4 files), Cube-Trino integration proven | Decided: Cube | **Med** -- need comparison analysis of alternatives considered (dbt, AtScale, direct access) | `docker-compose.yml` Cube config, `semantic/model/`, `infra/docker/cube/cube.js` |
| AI Semantic Layer (Build vs buy) | **Partial** -- NL-to-SQL module exists with prompt builder, evaluation framework, cross-tool validation | Decided: Build own | **Med** -- need competitive analysis of commercial alternatives (Cortex Analyst, LakehouseIQ, etc.) | `etl/src/semantic/` (6 modules), evaluation tests |

---

## Audience-Specific Requirements Matrix

Each deliverable targets a distinct audience with different expectations and reading patterns:

| Deliverable | Primary Audience | Secondary Audience | Reading Mode | Key Expectation | Success Metric |
|-------------|------------------|--------------------|--------------|-----------------|----------------|
| SWOT Analyses | C-suite, VP Engineering, Architecture Review Board | Data architects, Technical leads | Skim executive summary + deep-read if interested | Clear recommendation, professional design, printable for board packets | Reader knows the decision and rationale within 60 seconds |
| Marketecture | C-suite, Board, External stakeholders, Vendors | New hires for orientation | Glance (< 30 seconds to grasp the platform) | Single-page visual, zero jargon, "what does this platform do for us" | Non-technical person can explain the platform to a colleague |
| Detailed Architecture | Engineering leads, Platform team, Architects, DevOps | New data engineers (reference), External auditors (BCBS 239) | Reference lookup (find a specific port, protocol, dependency) | Complete, accurate, every port and protocol, every service dependency | Engineer can find any connection detail in < 30 seconds |
| Developer Onboarding | New data engineers (40+ team members) | Contractors, Internal transfers from other teams | Step-by-step follow on first day | Works on first try, copy-paste commands, no missing steps, expected output shown | New engineer has a working local environment and has run tests within 2 hours |
| API/Module Reference | Active developers writing pipelines | Data engineers debugging production issues | Reference lookup (find function, understand parameters) | Searchable, accurate signatures, usage examples | Developer finds the right module and understands its API without reading source |
| Contributor Guidelines | All contributors (40+ engineers) | Reviewers and tech leads (enforcement) | Skim once, reference before PRs | Concise, actionable, not bureaucratic | PR meets standards on first submission |
| Data Catalog/Glossary | Business analysts, Data stewards, Compliance officers | Executive sponsors, External auditors | Browse/search for term definitions | Plain language, no code, links metrics to business meaning, regulatory definitions precise | Business user understands a metric definition without asking an engineer |

---

## Content Source Inventory

Existing content that feeds the documentation deliverables (dependencies on existing platform):

| Source File | Lines | Feeds Into | Content Quality |
|------------|-------|-----------|-----------------|
| `docs/swot/nessie-catalog-swot.md` | 176 | Nessie SWOT HTML | Complete -- exec summary, full SWOT, decision matrix, recommendation |
| `docs/etl-patterns.md` | 565 | Developer Onboarding, DataStage SWOT, Contributor Guidelines | Comprehensive -- 8 sections covering all ETL patterns, testing, naming |
| `docs/adr/001-teradata-otf-nessie-feasibility.md` | 155 | Detailed Architecture, Nessie SWOT context | Complete -- 3 options analyzed with architecture diagrams and recommendations |
| `docker-compose.yml` | 574 | Detailed Architecture, Marketecture, Onboarding (service URLs) | Definitive -- 20+ services with ports, configs, dependencies, health checks |
| `README.md` | 244 | Marketecture, Onboarding (repo structure, quick start, tech stack) | Good -- ASCII architecture diagram, service URLs, repo structure tree |
| `ci/README.md` | 36 | Contributor Guidelines, Onboarding (CI/CD flow) | Concise -- workflow table, promotion diagram |
| `glossary-seed.json` | 168 | Data Catalog/Glossary | Good -- 17 terms with descriptions, synonyms, related terms, tags |
| `semantic/model/cubes/trading_metrics.yml` | 47 | Data Catalog (metric definitions) | Good -- measures with descriptions and glossary_term references |
| `semantic/model/cubes/risk_exposure.yml` | ~50 | Data Catalog (risk metric definitions) | Good -- VaR, expected shortfall measures |
| `semantic/model/views/*.yml` | ~50 | Data Catalog (consumer-facing view definitions) | Good |
| `etl/src/` (55 Python files) | ~3000+ | API/Module Reference | Variable -- docstring quality unknown without full source review |
| `infra/terraform/` | ~30 files | Detailed Architecture (environment configs) | Structured -- modules for nessie, trino, s3, minio, networking |
| `infra/docker/grafana/dashboards/` | 4 JSON files | Data Catalog (dashboard descriptions), Architecture | Complete -- pipeline_observability, bcbs239_compliance, data_freshness, audit_overview |

---

## Sources

- [SWOT Analysis: Examples and Templates 2026 - Asana](https://asana.com/resources/swot-analysis)
- [How to present SWOT analysis - Prezent](https://www.prezent.ai/blog/how-to-present-swot-analysis)
- [Build your best marketecture - Product Marketing Alliance](https://www.productmarketingalliance.com/build-your-best-marketecture/)
- [Designing a Marketecture Diagram - Bantrr](https://bantrr.com/product-marketing/designing-a-marketecture-diagram/)
- [The Difference between Marketecture and Tarchitecture - Martin Fowler](https://martinfowler.com/ieeeSoftware/marketecture.pdf)
- [Developer Onboarding: Checklist and Best Practices 2025 - Cortex](https://www.cortex.io/post/developer-onboarding-guide)
- [Developer onboarding: documentation must-haves - Multiplayer](https://www.multiplayer.app/blog/developer-onboarding-documentation/)
- [8 Developer Onboarding Best Practices 2025 - DocuWriter](https://www.docuwriter.ai/posts/developer-onboarding-best-practices)
- [Business Glossary vs Data Catalog vs Data Dictionary - Decube](https://www.decube.io/post/business-glossary-vs-data-catalog-vs-data-dictionary)
- [Business Glossary: The Key to Data Discovery - Atlan](https://atlan.com/business-glossary-101/)
- [Data Architecture Best Practices in Financial Services - McKinsey](https://www.mckinsey.com/capabilities/tech-and-ai/our-insights/tech-forward/next-gen-banking-success-starts-with-the-right-data-architecture)
- [15 Data Engineering Best Practices 2026 - lakeFS](https://lakefs.io/blog/data-engineering-best-practices/)
- [Sphinx autodoc documentation](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html)
- [Create architecture design diagrams - Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/design-diagrams)
- Existing project content: `docs/swot/nessie-catalog-swot.md`, `docs/etl-patterns.md`, `docs/adr/001-teradata-otf-nessie-feasibility.md`, `glossary-seed.json`, `docker-compose.yml`, `README.md`, `ci/README.md`
