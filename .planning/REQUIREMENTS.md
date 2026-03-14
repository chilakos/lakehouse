# Requirements: Lakehouse Architecture Transformation

**Defined:** 2026-03-13
**Core Value:** A single, governed copy of data in Iceberg format that every consumer — Teradata, Trino, Snowflake, BI tools, and AI — can access without creating additional copies.

## v1.1 Requirements

Requirements for v1.1 Documentation milestone. Each maps to roadmap phases.

### SWOT Analyses

- [x] **SWOT-01**: Shared CSS template with embedded styles, print-friendly layout, professional typography, and consistent color palette across all HTML deliverables
- [x] **SWOT-02**: Iceberg Catalog SWOT (Glue vs Nessie vs HMS vs Polaris) as standalone HTML with 2x2 grid, executive summary, decision matrix, and recommendation (Decided: Nessie)
- [x] **SWOT-03**: Snowflake Strategy SWOT (Retire vs Keep vs Maintain) as standalone HTML with full research, competitive analysis, and recommendation (Undecided)
- [x] **SWOT-04**: DataStage Migration SWOT (Big-bang vs phased vs parallel-run) as standalone HTML with evidence from existing ETL framework (Decided: Phased Python)
- [x] **SWOT-05**: Data Model Strategy SWOT (Keep FSDM vs evolve vs new medallion) as standalone HTML with backward compatibility analysis (Undecided)
- [x] **SWOT-06**: BI Semantic Layer SWOT (Direct vs dbt vs AtScale vs Cube) as standalone HTML with comparison analysis (Decided: Cube)
- [x] **SWOT-07**: AI Semantic Layer SWOT (Build vs buy) as standalone HTML with commercial alternative analysis (Decided: Build-own)
- [x] **SWOT-08**: Cross-SWOT index page linking all 6 SWOTs with decision status summary, badges (Decided/Undecided), and recommendation overview
- [x] **SWOT-09**: Interactive collapsible sections (CSS-only details/summary) in all SWOT documents
- [x] **SWOT-10**: Responsive tablet-friendly design across all SWOT HTML deliverables

### Architecture Visualizations

- [x] **ARCH-01**: Marketecture HTML page with boxes-and-arrows platform overview, technology labels with value propositions, key numbers callout (1.5 PB, 300+ sources, 40+ engineers)
- [x] **ARCH-02**: Detailed architecture HTML page with every component, port numbers, protocols, health check endpoints for all 20+ services
- [ ] **ARCH-03**: Data flow direction diagrams showing Bronze-Silver-Gold paths and consumer-semantic-query engine paths
- [ ] **ARCH-04**: Service dependency graph showing which services depend on which
- [ ] **ARCH-05**: Security layer visualization showing Ranger integration points and RBAC flow
- [ ] **ARCH-06**: Governance stack detail (OpenLineage-Marquez-Grafana flow for BCBS 239)
- [ ] **ARCH-07**: Environment differences table (dev/staging/prod) showing Terraform vs Docker Compose deployment
- [x] **ARCH-08**: CSS hover tooltips on detailed architecture diagram showing component descriptions
- [x] **ARCH-09**: Version-stamped footers on all HTML deliverables with generation date and component versions

### Developer Documentation

- [ ] **DEV-01**: Developer onboarding guide with prerequisites, local environment setup, and step-by-step Docker Compose stack launch
- [ ] **DEV-02**: Repository structure walkthrough explaining each directory and key files
- [ ] **DEV-03**: "Write your first pipeline" hands-on tutorial (extend BasePipeline, define schema, add quality checks, create DAG, run tests)
- [ ] **DEV-04**: ETL pattern reference incorporating etl-patterns.md content (medallion, quality, DAGs, incremental, mainframe)
- [ ] **DEV-05**: Testing guide covering unit tests, integration tests, pytest markers, CI gate behavior
- [ ] **DEV-06**: CI/CD workflow explanation (PR-dev-staging-prod flow, checks at each gate, environment promotion)
- [ ] **DEV-07**: Service URL reference table for all 10+ platform services (Trino UI, Airflow, MinIO, Grafana, etc.)
- [ ] **DEV-08**: Common troubleshooting FAQ (Docker memory, Nessie health, Spark JARs, Airflow init, Ranger startup)
- [ ] **DEV-09**: Day 1 checklist — printable single-page onboarding checklist combining setup, first pipeline, and first PR
- [ ] **DEV-10**: API/module reference with complete module listing, public API signatures, import paths, and usage examples for all 8 packages
- [ ] **DEV-11**: Class hierarchy visualization showing BasePipeline inheritance tree and all concrete implementations
- [ ] **DEV-12**: Contributor guidelines covering branch naming, PR process, testing requirements, code style (Ruff), naming conventions, commit format

### Data Catalog

- [ ] **CAT-01**: Business glossary with plain-language definitions for all terms in glossary-seed.json
- [ ] **CAT-02**: Term-to-table mapping linking glossary terms to physical table locations in lakehouse.gold.*
- [ ] **CAT-03**: Medallion layer explanation for non-technical users (Bronze/Silver/Gold narrative)
- [ ] **CAT-04**: Data freshness SLA documentation with thresholds and RED/YELLOW/GREEN status definitions
- [ ] **CAT-05**: Metric definitions with calculation logic pulled from Cube YAML measure definitions
- [ ] **CAT-06**: Regulatory term definitions section (BCBS 239, PII, VaR, Expected Shortfall) with precise compliance definitions
- [ ] **CAT-07**: Data lineage visualization showing end-to-end flow from source through Bronze-Silver-Gold to Cube to BI/AI per data domain
- [ ] **CAT-08**: Glossary term relationship graph visualizing connections between related terms

## v1.0 Requirements (Validated)

Requirements shipped and confirmed in v1.0 milestone (2026-03-13). 16 plans, 4 phases, 480 tests.

### Foundation & Storage

- [x] **FNDTN-01**: Iceberg tables created and queryable on AWS S3 (cloud storage)
- [x] **FNDTN-02**: Iceberg tables created and queryable on MinIO/replacement (on-prem S3-compatible storage)
- [x] **FNDTN-03**: Centralized Iceberg catalog deployed supporting both S3 and MinIO storage backends
- [x] **FNDTN-04**: Iceberg schema evolution works without data rewrites across all engines
- [x] **FNDTN-05**: Iceberg partition evolution supported for query performance optimization
- [x] **FNDTN-06**: Automated Iceberg table maintenance (compaction, snapshot expiration, orphan file cleanup)
- [x] **FNDTN-07**: Medallion architecture (Bronze/Silver/Gold) implemented with clear layer boundaries

### Multi-Engine Query Access

- [ ] **QUERY-01**: Trino reads Iceberg tables from both S3 and MinIO via shared catalog
- [ ] **QUERY-02**: Trino writes Iceberg tables (ETL output, Silver/Gold transformations)
- [ ] **QUERY-03**: Teradata OTF reads Iceberg tables from S3 via shared catalog (feasibility validated)
- [ ] **QUERY-04**: Snowflake reads Iceberg tables via external tables (compute-only, no data copies)
- [ ] **QUERY-05**: All three engines see consistent table metadata from shared catalog
- [ ] **QUERY-06**: Query performance benchmarked: Trino vs Teradata OTF vs direct Teradata

### ETL & Ingestion

- [x] **ETL-01**: Python ETL framework established using PySpark + PyIceberg for Iceberg writes
- [x] **ETL-02**: Pilot ETL migration of 5-10 representative DataStage jobs to Python
- [x] **ETL-03**: Mainframe source connectivity validated in Python (COBOL copybook parsing)
- [x] **ETL-04**: Apache Airflow deployed for workflow orchestration with DAG dependency management
- [x] **ETL-05**: Incremental/delta loading patterns implemented (watermark-based)
- [ ] **ETL-06**: Standardized ETL patterns documented and reusable across 40+ engineer team
- [ ] **ETL-07**: Full DataStage job inventory cataloged with complexity classification

### CI/CD & DevOps

- [x] **CICD-01**: GitHub repository structure established for ETL code and infrastructure
- [x] **CICD-02**: CI/CD pipeline deployed via GitHub Actions for automated testing and deployment
- [x] **CICD-03**: Environment promotion workflow (dev -> staging -> production)
- [x] **CICD-04**: Infrastructure as Code for lakehouse components

### Governance & Lineage

- [x] **GOVN-01**: End-to-end data lineage captured via OpenLineage
- [x] **GOVN-02**: Lineage visualization available for regulatory reporting (BCBS 239)
- [x] **GOVN-03**: Data classification and sensitivity labeling applied to PII and regulated data
- [x] **GOVN-04**: Business glossary with data definitions accessible to business users
- [x] **GOVN-05**: Audit trail capturing all data access across Trino, Teradata, and Snowflake

### Security & Access Control

- [ ] **SEC-01**: SSO/LDAP/Active Directory authentication integrated with Trino
- [ ] **SEC-02**: Role-based access control (RBAC) enforced on catalogs, schemas, and tables
- [x] **SEC-03**: Column-level security (masking PII) via Apache Ranger
- [x] **SEC-04**: Row-level security for multi-business-unit data access via Apache Ranger
- [x] **SEC-05**: Encryption at rest (S3 SSE-KMS, MinIO equivalent)
- [x] **SEC-06**: Encryption in transit (TLS)

### Data Quality

- [x] **QUAL-01**: Schema validation enforced on all ingestion pipelines
- [x] **QUAL-02**: Data quality checks integrated into ETL
- [x] **QUAL-03**: Source-to-lakehouse reconciliation
- [x] **QUAL-04**: Data quality monitoring with alerting

### BI Semantic Layer

- [x] **BISEM-01**: Unified metric definitions in a semantic layer
- [x] **BISEM-02**: Tableau connected to lakehouse via semantic layer
- [x] **BISEM-03**: Power BI connected to lakehouse via semantic layer
- [x] **BISEM-04**: BI query performance validated

### AI Semantic Layer

- [x] **AISEM-01**: NL-to-SQL capability deployed on curated domains
- [x] **AISEM-02**: NL-to-SQL leverages BI semantic layer definitions
- [x] **AISEM-03**: NL-to-SQL accuracy benchmarked and meeting targets

### Self-Service & Observability

- [x] **PLAT-01**: Data catalog deployed for self-service discovery
- [ ] **PLAT-02**: Pipeline observability dashboard with SLA monitoring
- [x] **PLAT-03**: Data freshness tracking visible to business users

## Future Requirements

Deferred to future milestone.

### Documentation Automation

- **AUTO-01**: Automated API docs generation pipeline (Sphinx/pdoc) integrated into CI/CD
- **AUTO-02**: OpenMetadata API integration for live glossary sync
- **AUTO-03**: Automated architecture diagram generation from docker-compose.yml
- **AUTO-04**: Documentation freshness CI checks with staleness alerts

### ETL Migration Scale

- **ETL-V2-01**: Full migration of all 300+ DataStage jobs to Python ETL
- **ETL-V2-02**: DataStage fully decommissioned

### Advanced Platform

- **PLAT-V2-01**: Cost management with showback/chargeback by domain/team
- **PLAT-V2-02**: Data mesh domain ownership model (pilot 2-3 domains)
- **PLAT-V2-03**: Data contracts between producer and consumer domains
- **PLAT-V2-04**: Self-service SQL workspace for analysts

### Teradata Transition

- **TERA-V2-01**: Teradata OTF writing Iceberg tables
- **TERA-V2-02**: Teradata workload migration plan to Trino
- **TERA-V2-03**: Teradata decommission roadmap

## Out of Scope

Explicitly excluded for v1.1.

| Feature | Reason |
|---------|--------|
| JavaScript-dependent interactivity | Standalone HTML must work in email clients, SharePoint, corporate intranets that strip JS |
| External CSS framework (Bootstrap, Tailwind CDN) | CDN links break offline/email viewing; custom embedded CSS is sufficient |
| Multi-page HTML site with navigation | Contradicts standalone single-file requirement |
| PDF generation pipeline | @media print CSS rules allow browser-native PDF |
| Video walkthroughs | High production effort, not searchable, impossible to update incrementally |
| Custom web fonts | External font loading fails in restricted networks |
| TOGAF/ArchiMate formal notation | Overkill; plain English boxes-and-arrows is more accessible |
| Embedded UI screenshots | Go stale immediately; text descriptions with URLs are maintainable |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SWOT-01 | Phase 5 | Complete |
| SWOT-02 | Phase 5 | Complete |
| SWOT-03 | Phase 5 | Complete |
| SWOT-04 | Phase 5 | Complete |
| SWOT-05 | Phase 5 | Complete |
| SWOT-06 | Phase 5 | Complete |
| SWOT-07 | Phase 5 | Complete |
| SWOT-08 | Phase 5 | Complete |
| SWOT-09 | Phase 5 | Complete |
| SWOT-10 | Phase 5 | Complete |
| ARCH-01 | Phase 6 | Complete |
| ARCH-02 | Phase 6 | Complete |
| ARCH-03 | Phase 6 | Pending |
| ARCH-04 | Phase 6 | Pending |
| ARCH-05 | Phase 6 | Pending |
| ARCH-06 | Phase 6 | Pending |
| ARCH-07 | Phase 6 | Pending |
| ARCH-08 | Phase 6 | Complete |
| ARCH-09 | Phase 5 | Complete |
| DEV-01 | Phase 7 | Pending |
| DEV-02 | Phase 7 | Pending |
| DEV-03 | Phase 7 | Pending |
| DEV-04 | Phase 7 | Pending |
| DEV-05 | Phase 7 | Pending |
| DEV-06 | Phase 7 | Pending |
| DEV-07 | Phase 7 | Pending |
| DEV-08 | Phase 7 | Pending |
| DEV-09 | Phase 7 | Pending |
| DEV-10 | Phase 7 | Pending |
| DEV-11 | Phase 7 | Pending |
| DEV-12 | Phase 7 | Pending |
| CAT-01 | Phase 8 | Pending |
| CAT-02 | Phase 8 | Pending |
| CAT-03 | Phase 8 | Pending |
| CAT-04 | Phase 8 | Pending |
| CAT-05 | Phase 8 | Pending |
| CAT-06 | Phase 8 | Pending |
| CAT-07 | Phase 8 | Pending |
| CAT-08 | Phase 8 | Pending |

**Coverage:**
- v1.1 requirements: 39 total
- Mapped to phases: 39/39
- Unmapped: 0

**Phase distribution:**
- Phase 5 (HTML Foundation + SWOTs): 11 requirements (SWOT-01 through SWOT-10, ARCH-09)
- Phase 6 (Architecture Visualizations): 8 requirements (ARCH-01 through ARCH-08)
- Phase 7 (Developer Documentation): 12 requirements (DEV-01 through DEV-12)
- Phase 8 (Data Catalog and Glossary): 8 requirements (CAT-01 through CAT-08)

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-14 after roadmap creation -- all 39 requirements mapped to phases*
