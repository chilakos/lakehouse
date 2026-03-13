# Roadmap: Lakehouse Architecture Transformation

## Overview

This roadmap transforms a legacy Teradata/DataStage data warehouse into a modern lakehouse on Apache Iceberg and Trino, serving a regulated financial services organization with 1.5 PB of data across 300+ sources. The approach is feasibility-first: Phase 1 proves the core architecture (can Teradata OTF, Trino, and Snowflake share Iceberg tables through a common catalog?), Phase 2 builds the data pipelines and quality framework, Phase 3 hardens governance and security for production, and Phase 4 delivers value to BI and AI consumers. The 6-12 month timeline targets Phase 1-2 completion with Phase 3 well underway; research indicates 18-24 months for full delivery including semantic layers.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation and Feasibility Validation** - Prove Iceberg/Trino/Teradata OTF multi-engine architecture with shared catalog, storage, CI/CD, and baseline security
- [ ] **Phase 2: ETL Migration and Data Pipeline** - Python ETL framework replaces DataStage pilot jobs; medallion layers, data quality, lineage, and orchestration operational
- [ ] **Phase 3: Governance, Security Hardening, and Platform** - Fine-grained access control, regulatory compliance dashboards, data catalog, and business glossary production-ready
- [ ] **Phase 4: Semantic Layers and Consumer Migration** - BI and AI semantic layers serving Tableau, Power BI, and NL-to-SQL on curated domains

## Phase Details

### Phase 1: Foundation and Feasibility Validation
**Goal**: Every query engine (Trino, Teradata OTF, Snowflake) reads the same Iceberg tables through a shared Nessie catalog on both cloud (S3) and on-prem (MinIO) storage, with CI/CD pipelines and baseline security in place
**Depends on**: Nothing (first phase)
**Requirements**: FNDTN-01, FNDTN-02, FNDTN-03, FNDTN-04, FNDTN-05, FNDTN-06, QUERY-01, QUERY-02, QUERY-03, QUERY-04, QUERY-05, QUERY-06, CICD-01, CICD-02, CICD-03, CICD-04, SEC-01, SEC-02, SEC-05, SEC-06
**Success Criteria** (what must be TRUE):
  1. A data engineer can create an Iceberg table on S3, and the same table is queryable from Trino, Teradata OTF, and Snowflake without any data copying
  2. A data engineer can create an Iceberg table on the on-prem S3-compatible store (MinIO), and Trino queries it identically to S3-hosted tables
  3. Schema evolution (add column, widen type) applied to an Iceberg table is visible to all three engines without data rewrites
  4. A developer can push ETL or infrastructure code to GitHub and it flows through automated CI/CD to dev, staging, and production environments
  5. Users authenticate via SSO/LDAP, and RBAC restricts catalog/schema/table access; all data at rest is encrypted (S3 SSE-KMS) and all traffic uses TLS
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md -- Mono-repo structure, Docker Compose local dev environment, Python test infrastructure
- [x] 01-02-PLAN.md -- Synthetic data generators, Iceberg catalog utilities, schema/partition evolution, table maintenance
- [x] 01-03-PLAN.md -- Terraform IaC modules (Nessie, Trino, S3, MinIO, networking), GitHub Actions CI/CD workflows, encryption
- [ ] 01-04-PLAN.md -- Multi-engine query validation (Trino, Teradata OTF, Snowflake), RBAC, LDAP auth, benchmarks

### Phase 2: ETL Migration and Data Pipeline
**Goal**: Python ETL framework is operational with pilot DataStage jobs migrated, medallion layers (Bronze/Silver/Gold) populated, data quality enforced on every pipeline, end-to-end lineage captured, and orchestration running in Airflow
**Depends on**: Phase 1
**Requirements**: FNDTN-07, ETL-01, ETL-02, ETL-03, ETL-04, ETL-05, ETL-06, ETL-07, QUAL-01, QUAL-02, QUAL-03, QUAL-04, GOVN-01, PLAT-02
**Success Criteria** (what must be TRUE):
  1. 5-10 representative DataStage jobs (including at least one mainframe source) are running as Python ETL in Airflow, writing Iceberg tables through Bronze/Silver/Gold layers with matching output to legacy pipelines
  2. Every ETL pipeline enforces schema validation before writes and runs data quality checks (null rates, range validation, uniqueness), with automated alerts on degradation
  3. End-to-end data lineage from source to consumption layer is captured via OpenLineage for every migrated pipeline and viewable in the governance tool
  4. Source-to-lakehouse reconciliation (row counts, checksums, aggregates) confirms data accuracy for all migrated tables
  5. A pipeline observability dashboard shows SLA status, failure rates, and run history for all active Airflow DAGs
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD
- [ ] 02-03: TBD

### Phase 3: Governance, Security Hardening, and Platform
**Goal**: Production-grade security with column-level and row-level controls, regulatory compliance lineage dashboards, data catalog for self-service discovery, and business glossary accessible to business users
**Depends on**: Phase 2
**Requirements**: SEC-03, SEC-04, GOVN-02, GOVN-03, GOVN-04, GOVN-05, PLAT-01, PLAT-03
**Success Criteria** (what must be TRUE):
  1. PII and sensitive financial fields are automatically masked for unauthorized roles via column-level security, and row-level security restricts data access by business unit -- enforced across Trino queries
  2. A compliance officer can view end-to-end lineage for any regulated report (BCBS 239) from source system through transformations to final output, with full audit trail of data access across Trino, Teradata, and Snowflake
  3. A business user can search the data catalog, find datasets by name or description, see data profiling statistics, and read business glossary definitions for key terms
  4. Data freshness for key business tables is tracked and visible to business users, with clear indicators of when data was last updated
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Semantic Layers and Consumer Migration
**Goal**: BI tools (Tableau, Power BI) query the lakehouse through a unified semantic layer with performance parity to direct Teradata queries, and NL-to-SQL is deployed on curated pilot domains
**Depends on**: Phase 3
**Requirements**: BISEM-01, BISEM-02, BISEM-03, BISEM-04, AISEM-01, AISEM-02, AISEM-03
**Success Criteria** (what must be TRUE):
  1. Unified metric definitions (revenue, risk exposure, etc.) are defined once in the semantic layer and serve consistent values to both Tableau and Power BI
  2. Tableau and Power BI analysts query the lakehouse through the semantic layer instead of direct Teradata connections, with query performance meeting or exceeding current Teradata baselines on representative dashboards
  3. A business user can ask a natural-language question about a curated data domain and receive an accurate SQL-generated answer, with accuracy meeting the defined threshold on pilot domains
  4. NL-to-SQL leverages the BI semantic layer metric definitions for accuracy, so business terms resolve to the same calculations as BI dashboards
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and Feasibility Validation | 3/4 | Executing | - |
| 2. ETL Migration and Data Pipeline | 0/3 | Not started | - |
| 3. Governance, Security Hardening, and Platform | 0/2 | Not started | - |
| 4. Semantic Layers and Consumer Migration | 0/2 | Not started | - |
