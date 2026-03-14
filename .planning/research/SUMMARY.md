# Project Research Summary

**Project:** Lakehouse Documentation Deliverables (v1.1)
**Domain:** Executive and developer documentation for an enterprise financial services data lakehouse
**Researched:** 2026-03-14
**Confidence:** HIGH

## Executive Summary

This milestone delivers documentation on top of a fully operational lakehouse platform (Nessie/Trino/Iceberg, PySpark ETL, Airflow, Ranger, OpenMetadata, Cube BI, NL-to-SQL AI, 480+ tests). The deliverables divide into two distinct tracks: standalone HTML artifacts for leadership (6 SWOT analyses, marketecture diagram, detailed architecture page) and developer-facing docs integrated into the repository (onboarding guide, API reference, contributor guidelines, data catalog). The two tracks have different consumers, different build toolchains, and different maintenance models -- treating them as one homogeneous task is the single most common structural mistake.

The recommended approach is minimal new tooling layered on existing dependencies. Jinja2 (already installed) renders SWOT and architecture HTML from YAML/Markdown content. Mermaid.js (CDN or local bundle) generates architecture diagrams as code. Only two truly new Python packages are needed: `pdoc` for API reference and `markdown` for guide conversion. All standalone HTML must be rigorously self-contained -- no CDN links, no web fonts, file size under 500 KB -- because financial services environments routinely restrict network access and executives email these files as attachments. A parallel docs-as-code site (MkDocs Material + mkdocstrings) serves the engineering team.

The critical risks are: (1) SWOT analyses that read as opinion rather than evidence -- every item must be backed by benchmark data, vendor specifications, or internal test results; (2) architecture diagrams that drift from the actual infrastructure within weeks unless diagram source is in git and rendered by CI; (3) the data catalog becoming a second source of truth that conflicts with OpenMetadata -- catalog docs must be generated from or tightly linked to the live OpenMetadata instance to satisfy BCBS 239 auditability requirements; and (4) developer docs going stale as the platform evolves, which is prevented by auto-generating API reference from docstrings and running onboarding commands in CI.

---

## Key Findings

### Recommended Stack

The documentation stack deliberately reuses existing platform dependencies. Jinja2 3.1.6 is already installed via Airflow and handles standalone HTML rendering with template inheritance. PyYAML and Pydantic -- both already in the stack -- manage SWOT content files and data validation. Mermaid.js 11.x loads from CDN (or local bundle for air-gapped delivery) and renders diagrams client-side with no build dependency. The only net-new packages are `pdoc >= 15.0` for zero-config API reference and `Markdown >= 3.7` for converting existing `.md` guides to HTML. A MkDocs Material + mkdocstrings layer is added by ARCHITECTURE.md research for the developer-facing documentation site. See [STACK.md](STACK.md) for full version matrix and configuration examples.

**Core technologies:**
- **Jinja2 3.1.6**: HTML templating for all standalone deliverables -- already installed, template inheritance ensures consistent branding across 15+ pages
- **Mermaid.js 11.x (CDN/local)**: Diagram-as-code for marketecture and architecture diagrams -- text source is version-controllable, renders client-side with zero build deps
- **pdoc >= 15.0**: Zero-config Python API reference -- reads existing docstrings, outputs standalone HTML, far simpler than Sphinx for 47 source files
- **Markdown >= 3.7**: Converts existing `.md` content (etl-patterns.md, ADRs, guides) to styled HTML
- **MkDocs Material >= 9.5 + mkdocstrings[python] >= 0.27**: Searchable developer documentation site with auto-generated API reference from Python docstrings

**Critical version note:** Pygments should be upgraded from 2.17.2 to >= 2.19.0 for Python 3.12 syntax support. Net new packages are 2 (`pdoc`, `Markdown`). MkDocs Material and mkdocstrings are added in the docs optional dependency group.

### Expected Features

The deliverables split into three priority tiers. Two SWOTs (Snowflake Strategy, Data Model Strategy) have undecided outcomes that are actively blocking strategic decisions -- these are the highest-priority items. See [FEATURES.md](FEATURES.md) for the full content-readiness matrix per SWOT and the audience-specific requirements table.

**Must have (table stakes):**
- 6 SWOT analyses as standalone HTML -- standard 2x2 grid, executive summary with explicit recommendation, decision matrix, mitigations for every threat
- Marketecture HTML -- executive-facing layer diagram, plain English labels, key platform numbers (1.5 PB, 300+ sources, 40 engineers, 480+ tests)
- Shared CSS template -- print-friendly, system fonts, consistent color palette; must be built before any HTML deliverable
- Detailed architecture HTML -- every service with port/protocol, data flow arrows, Ranger security integration points, environment differences
- Developer onboarding guide -- testable step-by-step commands, repository structure walkthrough, first pipeline tutorial
- API/module reference -- auto-generated from docstrings, all 8 packages covered
- Contributor guidelines -- branch/PR process, ruff config, pytest markers, naming conventions
- Data catalog/glossary -- business-language definitions linked to OpenMetadata, metric calculation logic from Cube YAML, BCBS 239 term mapping

**Should have (differentiators):**
- Decision status badges (Decided/Pending) on SWOT pages -- immediately signals which analyses need leadership action
- Cross-SWOT index page -- single view of all 6 decisions with status and links
- Interactive collapsible sections using pure CSS `<details>`/`<summary>` -- no JavaScript required
- Responsive design for tablet (executives review on iPad)
- "Day 1 Checklist" -- printable single-page onboarding accelerator
- Version-stamped footers on all HTML pages -- enables audit trail

**Defer to v2+:**
- Data lineage visualization in catalog docs -- high complexity, requires validating OpenLineage completeness first
- Automated Sphinx/pdoc build pipeline for initial authoring -- manual authoring is faster and higher quality for first pass
- PDF generation pipeline -- browser Print-to-PDF is sufficient; WeasyPrint adds CI complexity
- Video walkthroughs -- high production effort, goes stale, not searchable
- Embedded UI screenshots -- stale immediately after UI updates

### Architecture Approach

The system uses a two-track output model. Track A produces standalone HTML files (self-contained, emailable, browser-openable) for SWOT analyses and architecture pages -- built by Jinja2 Python scripts reading YAML/Markdown source. Track B produces a searchable MkDocs Material site for developer documentation -- built by `mkdocs build` consuming Markdown guides and Python docstrings via mkdocstrings. Both tracks share a common source layer (same repo, same PR process) and are orchestrated by a single `docs.yml` GitHub Actions workflow. All generated output lives in `docs/_build/` which is gitignored. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full directory structure, configuration files, and build-order rationale.

**Major components:**
1. **Shared CSS template** (`docs/_static/style.css`) -- color palette, typography, print styles, status badges; required before any HTML deliverable
2. **Jinja2 SWOT renderer** (`docs/_scripts/render_swots.py`) -- parses YAML front matter from SWOT Markdown, converts body to HTML, inlines CSS into standalone file
3. **Mermaid diagram pipeline** (`docs/architecture/*.mmd` + `generate_diagrams.py`) -- diagram-as-code source rendered to SVG by CI; GitHub natively previews `.mmd` files in Markdown
4. **Architecture HTML renderer** (`docs/_scripts/render_architecture.py`) -- embeds SVG diagrams into standalone HTML pages with Jinja2
5. **MkDocs Material site** (`docs/mkdocs.yml`) -- developer guides, ETL patterns, contributor docs, API reference via mkdocstrings
6. **OpenMetadata glossary exporter** (`docs/_scripts/export_glossary.py`) -- pulls live glossary terms from OpenMetadata REST API; caches to `docs/catalog/glossary.md` in git; fails gracefully when OM unavailable
7. **GitHub Actions docs.yml** -- path-filtered workflow (triggers on `docs/**` or `etl/src/**` changes) that runs all build steps sequentially and uploads artifact

### Critical Pitfalls

The full pitfall catalog with recovery strategies is in [PITFALLS.md](PITFALLS.md). The top items with direct roadmap impact:

1. **SWOT analyses reflect author bias, not evidence** -- Every SWOT item must include quantified evidence (benchmark results, vendor spec citations, internal test data). Add a "Confidence" or "Evidence" column to the SWOT template. Use the existing Nessie SWOT (`docs/swot/nessie-catalog-swot.md`) as the quality bar. Warning sign: Strengths/Opportunities section is 2x longer than Weaknesses/Threats.

2. **Architecture diagrams diverge from reality on day one** -- Store all diagram source as `.mmd` files in git, add CI rendering on every merge, include a "Last verified" date on every diagram. The platform has 12+ major components still evolving through Phase 2 -- static images will be wrong within weeks.

3. **Data catalog fails BCBS 239 auditability** -- Static HTML glossary must be generated from or tightly linked to OpenMetadata. Only 2 of 31 G-SIBs are fully BCBS 239 compliant; the most common failure is exactly this documentation gap. Map every glossary term to its OpenMetadata asset ID, Ranger policy, OpenLineage lineage path, and Soda quality check results.

4. **Developer docs go stale within one sprint** -- API reference must be auto-generated from docstrings (pdoc or mkdocstrings), never hand-written. Add a CI smoke test that runs onboarding guide setup commands in a clean environment.

5. **SWOT HTML breaks in financial services environments** -- All HTML must pass the `file://` protocol test with no internet connection. No CDN links. No web fonts. Target under 500 KB per file. Print-to-PDF must produce readable output. Financial services IT blocks external CDN requests and executives email these files as attachments.

6. **Marketecture and architecture serve the wrong audience** -- Define audience personas before creating either diagram. Marketecture rule: no technical component names ("Data Catalog" not "OpenMetadata", "Query Engine" not "Trino 479"). Detailed architecture rule: every component shows actual deployment name, version, port, and protocol. Have the target audience review their respective diagram.

---

## Implications for Roadmap

### Phase 1: Foundation and SWOT Analyses

**Rationale:** Two of the six SWOTs (Snowflake Strategy, Data Model Strategy) have undecided outcomes blocking active strategic decisions. Leadership is waiting on these. The shared CSS template is a prerequisite for all HTML deliverables -- it must be approved before generating 6+ pages that will need retroactive rework if design changes. The existing Nessie SWOT validates the template with low authoring effort before tackling the full-research SWOTs.

**Delivers:** Shared CSS template (print-friendly, system fonts, color palette, status badges), Jinja2 SWOT renderer script, 6 SWOT analyses as standalone HTML, cross-SWOT index page

**Features from FEATURES.md:** Standard 2x2 SWOT grid, executive summary with recommendation, decision matrix, threat mitigations, decision status badges, collapsible sections, responsive design, consistent structure

**Avoids:** Pitfall 1 (SWOT bias -- establish evidence-based template and review process before writing all 6), Pitfall 6 (HTML accessibility -- establish `file://` test and 500 KB target before generating all 6 files)

**Content readiness note:** Nessie SWOT is complete (convert only, 1-2 hours). DataStage, BI Semantic Layer, and AI Semantic Layer are partial (2-4 hours each). Snowflake Strategy and Data Model Strategy require full research and domain expert input -- these are the longest-effort SWOTs and must be started immediately to avoid blocking leadership.

**Research flag: Needs `/gsd:research-phase`** -- Snowflake Strategy SWOT requires research on Snowflake ICEBERG_REST capabilities, cost model, and contract status. Data Model Strategy SWOT requires domain expert input on FSDM adoption level and medallion evolution path. These cannot be authored from existing repo content alone.

---

### Phase 2: Architecture Diagrams

**Rationale:** Architecture deliverables depend on the CSS template (Phase 1) and require a distinct toolchain (Mermaid CLI rendering pipeline). The marketecture is the second-highest leadership priority after SWOTs. The detailed architecture page serves engineers and requires the most content extraction work (20+ services from docker-compose.yml). Both share the same diagram-as-code infrastructure and HTML renderer.

**Delivers:** 3 Mermaid diagram source files (`marketecture.mmd`, `detailed-architecture.mmd`, `data-flow.mmd`), SVG rendering pipeline, 2 standalone architecture HTML pages

**Features from FEATURES.md:** Marketecture with plain-English labels and key numbers callout; detailed architecture with port numbers, protocols, service dependencies, security layer (Ranger integration), governance stack detail (OpenLineage -> Marquez -> Grafana), environment differences table

**Uses:** Mermaid.js 11.x for diagram-as-code, `render_architecture.py` script, shared Jinja2 template from Phase 1

**Avoids:** Pitfall 2 (architecture drift -- establish `.mmd` source-in-git and CI rendering before first diagram is published), Pitfall 5 (wrong audience -- define personas and conduct audience-specific reviews before finalizing either diagram)

**Research flag: Standard patterns** -- Mermaid diagram-as-code is well-documented with extensive official docs and native GitHub Markdown preview. No additional research phase needed. The main effort is content extraction from `docker-compose.yml` (574 lines, 20+ services) and `infra/terraform/`.

---

### Phase 3: Developer Documentation

**Rationale:** Developer docs (onboarding, API reference, contributor guidelines) can run in parallel with Phase 2 but share the same repo structure established in Phase 1. They use a different build system (MkDocs Material) from standalone HTML deliverables. Most content already exists in `etl-patterns.md` (565 lines), `ci/README.md`, and `README.md` -- this phase is primarily reorganization, formatting, and pipeline setup. API reference quality depends on docstring coverage, which must be assessed before committing to mkdocstrings output quality.

**Delivers:** MkDocs Material site with developer onboarding guide, repository structure walkthrough, pipeline authoring tutorial, testing guide, contributor guidelines, auto-generated API reference for all 8 packages (config, governance, iceberg_utils, inventory, lineage, pipelines, quality, semantic), Day 1 Checklist

**Features from FEATURES.md:** Prerequisites and local setup, first pipeline tutorial (from etl-patterns.md Sections 2-4), CI/CD workflow explanation, service URL reference table (10+ services), troubleshooting FAQ, API module listing with usage examples, import path quick reference, class hierarchy visualization

**Uses:** MkDocs Material >= 9.5.0, mkdocstrings[python] >= 0.27.0, `markdown` library for converting existing `.md` content

**Avoids:** Pitfall 4 (developer doc staleness -- auto-generate API reference from docstrings, add CI onboarding smoke test, reference CI config files by path not narrative description)

**Research flag: Docstring audit required** -- The 47 Python source files across 8 packages have unknown docstring coverage. A 1-hour audit of `etl/src/` is needed before starting this phase to determine whether mkdocstrings output will be acceptable or whether docstring improvement is a prerequisite sub-task that adds 1-2 days to the phase estimate.

---

### Phase 4: Data Catalog and Glossary

**Rationale:** Data catalog documentation has the highest regulatory risk (BCBS 239 compliance) and requires integration with OpenMetadata -- an external service dependency not needed by other phases. Placing this last allows validation of OpenMetadata API access and glossary export pipeline before building the generation infrastructure. The 17 glossary terms in `glossary-seed.json` and 4 Cube YAML model files provide content foundation, but all definitions must be reconciled with OpenMetadata as the authoritative source.

**Delivers:** Business glossary HTML with BCBS 239 term mapping, metric definitions from Cube YAML, medallion layer explanation for business users, term-to-table mapping, data freshness SLA documentation (Gold: 24h/48h, Silver: 12h/24h, Bronze: 6h/12h), OpenMetadata glossary export script with git-cached fallback

**Features from FEATURES.md:** Plain-language business glossary, term-to-table mapping, medallion layer explanation, data freshness SLAs, metric calculation logic (total_notional, trade_count, avg_price, VaR, expected shortfall), regulatory term definitions (BCBS 239, PII, VaR)

**Uses:** `export_glossary.py` with OpenMetadata Python SDK, Jinja2 catalog template, `glossary-seed.json` and Cube YAML models (`trading_metrics.yml`, `risk_exposure.yml`, views) as content sources

**Avoids:** Pitfall 3 (BCBS 239 catalog failure -- link every term to OpenMetadata asset ID, Ranger policy, and OpenLineage lineage path), Pitfall 7 (duplicate catalog vs OpenMetadata -- establish single source of truth rule, generate static docs from OpenMetadata API, never hand-write definitions OM already has)

**Research flag: Needs OpenMetadata API validation** -- Before building `export_glossary.py`, confirm: (1) which glossary terms already exist in the live OpenMetadata instance vs only in `glossary-seed.json`, (2) whether OpenMetadata SDK can be used in CI without a full OM service container, (3) what BCBS 239 principle-to-feature mapping already exists in OpenMetadata. This is a scoping/discovery question, not a technology research question.

---

### Phase 5: CI/CD Integration and Finalization

**Rationale:** The `docs.yml` GitHub Actions workflow consolidates all previous phases into a single automated pipeline. It should be built after individual components are working locally to avoid simultaneously debugging CI configuration and content issues. This phase also covers the "Looks Done But Isn't" audit checklist from PITFALLS.md: `file://` protocol testing of all HTML deliverables, print-to-PDF validation, security scan for real data in docs, and docs-freshness CI check setup.

**Delivers:** `docs.yml` GitHub Actions workflow (path-filtered triggers, sequential build steps, artifact upload), `.gitignore` update for `docs/_build/`, `pyproject.toml` docs optional dependency group, CI smoke test for onboarding guide commands, docs-freshness check, security scan for PII/real data in documentation

**Avoids:** All pitfalls -- this phase is the enforcement layer. CI rendering prevents diagram drift. Smoke tests prevent stale onboarding docs. Security scan prevents real data exposure per PITFALLS.md security section. Freshness check flags docs that lag behind code changes.

**Research flag: Standard patterns** -- GitHub Actions workflow for MkDocs Material documentation builds is fully covered by MkDocs Material's official publishing guide. No additional research phase needed.

---

### Phase Ordering Rationale

- **CSS template before HTML deliverables** -- All 15+ HTML pages inherit from the base template. Visual design approval before content generation prevents rework.
- **SWOTs before architecture diagrams** -- SWOTs are blocking strategic decisions, require the most stakeholder interaction (evidence review, cross-SWOT consistency checks), and have the longest content-authoring timeline for the two undecided topics.
- **Architecture diagrams as a distinct phase** -- Shares the CSS infrastructure from Phase 1 but requires a separate Mermaid toolchain and distinct audience review process. Decoupling avoids blocking diagram work on SWOT content completion.
- **Developer docs parallel to architecture diagrams** -- No cross-dependency between Phase 2 and Phase 3. The docstring audit should be the first Phase 3 task and can run immediately after Phase 1 CSS template work begins.
- **Data catalog last** -- External dependency (OpenMetadata API), highest regulatory complexity, and the need to reconcile with the live catalog make this the highest-risk phase. Isolating it last prevents OpenMetadata availability from blocking leadership deliverables.
- **CI/CD integration as a finishing phase** -- Building the workflow after components work locally is less risky than debugging component logic inside CI. Path filters also require all deliverable output paths to be known before the workflow can be written correctly.

---

### Research Flags

**Needs `/gsd:research-phase` during planning:**
- **Phase 1 (Snowflake Strategy SWOT):** Snowflake ICEBERG_REST table format capabilities, cost model vs Teradata/Trino, contract status -- external vendor research required, cannot be authored from repo content
- **Phase 1 (Data Model Strategy SWOT):** FSDM adoption rate in current pipelines, medallion evolution path, backward compatibility constraints -- requires domain expert sessions
- **Phase 4 (Data Catalog):** OpenMetadata API validation, BCBS 239 principle-to-feature mapping audit, OpenLineage lineage completeness assessment -- discovery/scoping research before building

**Standard patterns (skip research-phase):**
- **Phase 1 CSS + Jinja2 renderer:** Jinja2 template inheritance is well-documented; already proven in this project via Airflow
- **Phase 2 Architecture Diagrams:** Mermaid diagram-as-code has complete official documentation and native GitHub preview
- **Phase 3 MkDocs Material + mkdocstrings:** Both tools are mature with extensive documentation; configuration examples are fully specified in ARCHITECTURE.md
- **Phase 5 GitHub Actions:** MkDocs Material's official publishing guide covers this exact pattern

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended tools are mature Python ecosystem staples. Jinja2 and PyYAML are already installed. pdoc and Markdown are straightforward additions. Minor divergence between STACK.md (pdoc-focused) and ARCHITECTURE.md (MkDocs-focused) -- both are valid and complementary, not conflicting. |
| Features | HIGH | Deliverable scope is well-defined. Content sources are inventoried in FEATURES.md's content source table. Two SWOTs require full authoring -- effort is bounded but content depends on domain expert availability. |
| Architecture | HIGH | Two-track output model is proven. Build order is explicit with rationale. Configuration files are fully specified in ARCHITECTURE.md. Node.js is the only non-obvious CI dependency (required for Mermaid CLI). |
| Pitfalls | HIGH | Pitfalls are evidence-based (BCBS 239 literature, financial services specifics, behavioral economics research on SWOT bias). The "Looks Done But Isn't" checklist is actionable and directly maps to deliverable completion criteria. |

**Overall confidence:** HIGH

---

### Gaps to Address

- **Docstring coverage unknown:** The 47 Python source files have not been audited for docstring quality. mkdocstrings output will be poor if coverage is low. Audit `etl/src/` as the first Phase 3 task. If coverage is inadequate, docstring authoring becomes a prerequisite sub-task that adds 1-2 days to the phase estimate.

- **OpenMetadata API accessibility in CI:** `export_glossary.py` requires a live OpenMetadata instance (6 GB RAM, Elasticsearch, PostgreSQL). This cannot run as a CI service container on every commit. The git-cached fallback pattern (commit last-known-good export, refresh via scheduled/manual trigger) is the correct mitigation. Confirm with the team before Phase 4 planning that this pattern is acceptable for regulatory audit purposes.

- **Snowflake Strategy and Data Model Strategy SWOT content:** Both require inputs beyond documentation work. The Snowflake SWOT needs Snowflake ICEBERG_REST capability research. The Data Model SWOT needs architectural input on FSDM evolution. These have potential to slip if domain experts are not engaged at the start of Phase 1.

- **Toolchain note -- pdoc vs mkdocstrings:** STACK.md recommends pdoc (standalone HTML output). ARCHITECTURE.md recommends mkdocstrings within MkDocs Material (site-integrated). Both are valid for different use cases. Recommended resolution: use mkdocstrings for the MkDocs developer site (Phase 3); add pdoc as a fallback if standalone API reference HTML is separately requested. No decision needed before Phase 3 begins.

---

## Sources

### Primary (HIGH confidence)
- [Jinja2 Template Designer Documentation](https://jinja.palletsprojects.com/en/stable/templates/) -- Template inheritance, filters, autoescaping
- [pdoc documentation](https://pdoc.dev/) -- Zero-config usage, custom templates, output modes
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) -- MkDocs Material theme, v9.7.x
- [mkdocstrings documentation](https://mkdocstrings.github.io/) -- Python handler, Griffe AST parsing
- [Mermaid.js official site](https://mermaid.js.org/) -- Version 11.x, CDN usage guide
- [OpenMetadata Python SDK](https://docs.open-metadata.org/latest/sdk/python/api-reference) -- Glossary export API
- [BCBS 239 Guide 2025 -- Alation](https://www.alation.com/blog/bcbs-239-guide-compliance-best-practices-2025/) -- Compliance requirements for data catalog documentation
- [BCBS 239 compliance: findings, failures and fixes -- IBM](https://www.ibm.com/new/product-blog/bcbs239-compliance) -- G-SIB compliance rates (only 2 of 31 fully compliant)
- Existing project content: `docs/swot/nessie-catalog-swot.md`, `docs/etl-patterns.md`, `docs/adr/001-teradata-otf-nessie-feasibility.md`, `glossary-seed.json`, `docker-compose.yml`, `README.md`, `ci/README.md`

### Secondary (MEDIUM confidence)
- [Diagrams as Code comparison](https://simmering.dev/blog/diagrams/) -- Mermaid vs D2 vs Python diagrams tradeoffs
- [Making Documentation Simpler: Docs-as-Code Journey -- Squarespace Engineering](https://engineering.squarespace.com/blog/2025/making-documentation-simpler-and-practical-our-docs-as-code-journey) -- Real-world docs-as-code at scale
- [Your SWOT Analysis is Broken -- Psychology Today](https://www.psychologytoday.com/us/blog/intentional-insights/201911/your-swot-analysis-is-broken-heres-how-you-can-fix-it) -- Evidence-based SWOT methodology and confirmation bias research
- [Software Architecture: Marketecture vs Tarchitecture -- InformIT](https://www.informit.com/articles/article.aspx?p=31933) -- Audience separation principles for architecture documentation
- [Business Glossary Implementation Plan -- OvalEdge](https://www.ovaledge.com/blog/business-glossary-implementation-plan) -- Glossary-to-catalog integration patterns

---
*Research completed: 2026-03-14*
*Ready for roadmap: yes*
