# Roadmap: Lakehouse Architecture Transformation

## Milestones

- [x] **v1.0 MVP** - Phases 1-4 (shipped 2026-03-13)
- [ ] **v1.1 Documentation** - Phases 5-8 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MVP (Phases 1-4) - SHIPPED 2026-03-13</summary>

- [x] **Phase 1: Foundation and Feasibility Validation** - Prove Iceberg/Trino/Teradata OTF multi-engine architecture with shared catalog, storage, CI/CD, and baseline security
- [x] **Phase 2: ETL Migration and Data Pipeline** - Python ETL framework replaces DataStage pilot jobs; medallion layers, data quality, lineage, and orchestration operational
- [x] **Phase 3: Governance, Security Hardening, and Platform** - Fine-grained access control, regulatory compliance dashboards, data catalog, and business glossary production-ready
- [x] **Phase 4: Semantic Layers and Consumer Migration** - BI and AI semantic layers serving Tableau, Power BI, and NL-to-SQL on curated domains

</details>

### v1.1 Documentation

- [ ] **Phase 5: HTML Foundation and SWOT Analyses** - Shared CSS template, version-stamped footers, Jinja2 renderer, all 6 SWOT analyses, cross-SWOT index, interactive and responsive design
- [ ] **Phase 6: Architecture Visualizations** - Marketecture and detailed architecture HTML pages with Mermaid diagrams, data flow paths, service dependencies, security/governance layers, environment table
- [ ] **Phase 7: Developer Documentation** - MkDocs Material site with onboarding guide, pipeline tutorial, testing/CI/CD guides, API reference, contributor guidelines, Day 1 checklist
- [ ] **Phase 8: Data Catalog and Glossary** - Business glossary from OpenMetadata, term-to-table mapping, medallion explanation, freshness SLAs, metric definitions, regulatory terms, lineage and relationship visualizations

## Phase Details

### Phase 5: HTML Foundation and SWOT Analyses
**Goal**: Leadership has all 6 SWOT analyses as polished standalone HTML with evidence-based recommendations, and the shared CSS template and version-stamped footer infrastructure is established for all downstream HTML deliverables
**Depends on**: Phase 4 (v1.0 platform must exist to document)
**Requirements**: SWOT-01, SWOT-02, SWOT-03, SWOT-04, SWOT-05, SWOT-06, SWOT-07, SWOT-08, SWOT-09, SWOT-10, ARCH-09
**Success Criteria** (what must be TRUE):
  1. Opening any SWOT HTML file from the local filesystem (file:// protocol, no internet) renders a professional document with consistent branding, print-friendly layout, and readable typography
  2. Each of the 6 SWOT analyses contains a 2x2 grid, executive summary with explicit recommendation, decision matrix, and mitigations for every threat -- with quantified evidence backing each item
  3. The 2 undecided SWOTs (Snowflake Strategy, Data Model Strategy) present balanced options with clear trade-offs that enable leadership to make a decision
  4. The cross-SWOT index page shows all 6 analyses with Decided/Undecided status badges and links to each standalone file
  5. Every HTML deliverable has a version-stamped footer with generation date; all SWOT pages have collapsible sections (CSS-only) and render correctly on tablet-width screens
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md -- Shared CSS template, Jinja2 SWOT renderer, version-stamped footer, Nessie SWOT, test scaffold
- [ ] 05-02-PLAN.md -- 5 remaining SWOT analyses (prioritizing undecided SWOTs), cross-SWOT index page

### Phase 6: Architecture Visualizations
**Goal**: Executives and engineers have accurate, audience-appropriate architecture documentation -- a plain-English marketecture for leadership and a detailed technical diagram with every service, port, and protocol for engineers
**Depends on**: Phase 5 (CSS template and footer infrastructure)
**Requirements**: ARCH-01, ARCH-02, ARCH-03, ARCH-04, ARCH-05, ARCH-06, ARCH-07, ARCH-08
**Success Criteria** (what must be TRUE):
  1. The marketecture HTML page communicates the platform value proposition to a non-technical executive using plain-English labels, boxes-and-arrows layout, and key numbers (1.5 PB, 300+ sources, 40+ engineers)
  2. The detailed architecture HTML page shows every platform service with its actual port number, protocol, and health check endpoint, and a data engineer can use it as a service reference
  3. Data flow diagrams show the complete path from source through Bronze/Silver/Gold to consumers, and service dependency, security (Ranger), and governance (OpenLineage/Marquez/Grafana) layers are each documented
  4. Environment differences (dev/staging/prod, Docker Compose vs Terraform) are documented in a clear comparison table
  5. Hovering over components in the detailed architecture diagram reveals descriptions via CSS tooltips
**Plans**: TBD

Plans:
- [ ] 06-01: Mermaid diagram source files and rendering pipeline, marketecture and detailed architecture HTML pages
- [ ] 06-02: Data flow, service dependency, security, governance diagrams, environment table, CSS tooltips

### Phase 7: Developer Documentation
**Goal**: A new developer can go from zero to running their first pipeline and submitting their first PR using only the documentation site, with auto-generated API reference covering all 8 packages
**Depends on**: Phase 5 (CSS template for any standalone HTML outputs)
**Requirements**: DEV-01, DEV-02, DEV-03, DEV-04, DEV-05, DEV-06, DEV-07, DEV-08, DEV-09, DEV-10, DEV-11, DEV-12
**Success Criteria** (what must be TRUE):
  1. A new developer can follow the onboarding guide from prerequisites through Docker Compose stack launch to running their first pipeline, with every command copy-pasteable and every step verifiable
  2. The API/module reference documents all 8 packages (config, governance, iceberg_utils, inventory, lineage, pipelines, quality, semantic) with public API signatures, import paths, and usage examples
  3. The contributor guidelines specify the complete PR workflow (branch naming, ruff style, pytest markers, commit format) and a developer can follow them to submit a conforming PR
  4. Service URLs for all platform services, CI/CD workflow stages, ETL patterns, testing strategy, and common troubleshooting solutions are findable in the documentation site
  5. A printable Day 1 checklist combines setup, first pipeline, and first PR into a single-page onboarding accelerator
**Plans**: TBD

Plans:
- [ ] 07-01: MkDocs Material site setup, onboarding guide, repo structure walkthrough, first pipeline tutorial, Day 1 checklist
- [ ] 07-02: ETL patterns reference, testing guide, CI/CD workflow, service URL table, troubleshooting FAQ
- [ ] 07-03: API/module reference (all 8 packages), class hierarchy visualization, contributor guidelines

### Phase 8: Data Catalog and Glossary
**Goal**: Business users and compliance officers have a searchable catalog with plain-language definitions linked to physical tables, metric calculations, data freshness SLAs, and regulatory terms -- all traceable to the live OpenMetadata instance for BCBS 239 auditability
**Depends on**: Phase 5 (CSS template for standalone HTML outputs)
**Requirements**: CAT-01, CAT-02, CAT-03, CAT-04, CAT-05, CAT-06, CAT-07, CAT-08
**Success Criteria** (what must be TRUE):
  1. A business user can look up any glossary term and find a plain-language definition linked to its physical table location in lakehouse.gold.*, with every term traceable to its OpenMetadata asset
  2. Metric definitions (total_notional, trade_count, VaR, expected shortfall, etc.) show exact calculation logic pulled from Cube YAML, so business users know precisely what each number means
  3. The medallion layer explanation communicates Bronze/Silver/Gold concepts to non-technical readers, and data freshness SLAs with RED/YELLOW/GREEN thresholds are documented for each layer
  4. Regulatory terms (BCBS 239, PII, VaR, Expected Shortfall) have precise compliance definitions, and a compliance officer can trace from any regulated term to its lineage path
  5. Data lineage and glossary term relationship visualizations show end-to-end flows and term connections across data domains
**Plans**: TBD

Plans:
- [ ] 08-01: OpenMetadata glossary export, business glossary HTML, term-to-table mapping, medallion layer explanation
- [ ] 08-02: Metric definitions from Cube YAML, freshness SLAs, regulatory terms, lineage visualization, term relationship graph

## Progress

**Execution Order:**
Phases execute in numeric order: 5 -> 6 -> 7 -> 8
Note: Phases 6 and 7 can execute in parallel after Phase 5 completes (no cross-dependency).

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation and Feasibility Validation | v1.0 | 4/4 | Complete | 2026-03-13 |
| 2. ETL Migration and Data Pipeline | v1.0 | 5/5 | Complete | 2026-03-13 |
| 3. Governance, Security Hardening, and Platform | v1.0 | 4/4 | Complete | 2026-03-13 |
| 4. Semantic Layers and Consumer Migration | v1.0 | 3/3 | Complete | 2026-03-13 |
| 5. HTML Foundation and SWOT Analyses | v1.1 | 0/2 | Planning complete | - |
| 6. Architecture Visualizations | v1.1 | 0/2 | Not started | - |
| 7. Developer Documentation | v1.1 | 0/3 | Not started | - |
| 8. Data Catalog and Glossary | v1.1 | 0/2 | Not started | - |
