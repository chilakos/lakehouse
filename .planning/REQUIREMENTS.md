# Requirements: Lakehouse Architecture Transformation

**Defined:** 2026-03-13
**Core Value:** A single, governed copy of data in Iceberg format that every consumer -- Teradata, Trino, Snowflake, BI tools, and AI -- can access without creating additional copies.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

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
- [ ] **QUERY-05**: All three engines (Trino, Teradata OTF, Snowflake) see consistent table metadata from shared catalog
- [ ] **QUERY-06**: Query performance benchmarked: Trino vs Teradata OTF vs direct Teradata on representative workloads

### ETL & Ingestion

- [x] **ETL-01**: Python ETL framework established using PySpark + PyIceberg for Iceberg writes
- [x] **ETL-02**: Pilot ETL migration of 5-10 representative DataStage jobs to Python
- [x] **ETL-03**: Mainframe source connectivity validated in Python (COBOL copybook parsing, DB2 z/OS, flat files)
- [x] **ETL-04**: Apache Airflow deployed for workflow orchestration with DAG dependency management
- [x] **ETL-05**: Incremental/delta loading patterns implemented (watermark-based, CDC where available)
- [ ] **ETL-06**: Standardized ETL patterns documented and reusable across 40+ engineer team
- [ ] **ETL-07**: Full DataStage job inventory cataloged with complexity classification (simple/medium/complex)

### CI/CD & DevOps

- [x] **CICD-01**: GitHub repository structure established for ETL code, dbt models, and infrastructure
- [x] **CICD-02**: CI/CD pipeline deployed via GitHub Actions for automated testing and deployment
- [x] **CICD-03**: Environment promotion workflow (dev -> staging -> production) for ETL and infrastructure changes
- [x] **CICD-04**: Infrastructure as Code for lakehouse components (Trino, Airflow, catalog, storage)

### Governance & Lineage

- [x] **GOVN-01**: End-to-end data lineage captured via OpenLineage from source to consumption layer
- [ ] **GOVN-02**: Lineage visualization available for regulatory reporting (BCBS 239, SOX compliance)
- [x] **GOVN-03**: Data classification and sensitivity labeling applied to PII and regulated financial data
- [x] **GOVN-04**: Business glossary with data definitions accessible to business users
- [ ] **GOVN-05**: Audit trail capturing all data access across Trino, Teradata, and Snowflake

### Security & Access Control

- [ ] **SEC-01**: SSO/LDAP/Active Directory authentication integrated with Trino
- [ ] **SEC-02**: Role-based access control (RBAC) enforced on catalogs, schemas, and tables
- [x] **SEC-03**: Column-level security (masking PII and sensitive financial fields) via Apache Ranger
- [x] **SEC-04**: Row-level security for multi-business-unit data access via Apache Ranger
- [x] **SEC-05**: Encryption at rest (S3 SSE-KMS, MinIO equivalent) for all Iceberg data
- [x] **SEC-06**: Encryption in transit (TLS) for all data movement and query traffic

### Data Quality

- [x] **QUAL-01**: Schema validation enforced on all ingestion pipelines before Iceberg writes
- [x] **QUAL-02**: Data quality checks (null rates, range validation, uniqueness) integrated into ETL
- [x] **QUAL-03**: Source-to-lakehouse reconciliation (row counts, checksums, aggregates) for migrated tables
- [x] **QUAL-04**: Data quality monitoring with alerting for degradation detection

### BI Semantic Layer

- [ ] **BISEM-01**: Unified metric definitions (revenue, risk exposure, etc.) in a semantic layer
- [ ] **BISEM-02**: Tableau connected to lakehouse via semantic layer (replacing direct Teradata queries)
- [ ] **BISEM-03**: Power BI connected to lakehouse via semantic layer (replacing direct Teradata queries)
- [ ] **BISEM-04**: BI query performance validated against current Teradata direct-query baselines

### AI Semantic Layer

- [ ] **AISEM-01**: NL-to-SQL capability deployed on curated high-confidence data domains
- [ ] **AISEM-02**: NL-to-SQL leverages BI semantic layer definitions for accuracy
- [ ] **AISEM-03**: NL-to-SQL accuracy benchmarked and meeting target threshold on pilot domains

### Self-Service & Observability

- [x] **PLAT-01**: Data catalog deployed for self-service data discovery (search, profiling, glossary)
- [ ] **PLAT-02**: Pipeline observability dashboard with SLA monitoring and failure alerting
- [x] **PLAT-03**: Data freshness tracking visible to business users

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### ETL Migration Scale

- **ETL-V2-01**: Full migration of all 300+ DataStage jobs to Python ETL
- **ETL-V2-02**: DataStage fully decommissioned

### Advanced Platform

- **PLAT-V2-01**: Cost management with showback/chargeback by domain/team
- **PLAT-V2-02**: Data mesh domain ownership model (pilot 2-3 domains)
- **PLAT-V2-03**: Data contracts between producer and consumer domains
- **PLAT-V2-04**: Self-service SQL workspace for analysts

### Teradata Transition

- **TERA-V2-01**: Teradata OTF writing Iceberg tables (ETL output from Teradata)
- **TERA-V2-02**: Teradata workload migration plan to Trino
- **TERA-V2-03**: Teradata decommission roadmap

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real-time streaming ingestion (Kafka/Flink) | Batch-first migration; streaming adds massive complexity. Add for specific use cases after batch is stable |
| Full Teradata decommission | This phase validates OTF/Iceberg feasibility. Decommission requires full ETL migration first |
| Multi-cloud (Azure/GCP) | AWS S3 + MinIO is the stated architecture. Iceberg is cloud-agnostic; add clouds later if needed |
| Enterprise-wide data mesh | Organizational transformation that requires working infrastructure. Pilot 2-3 domains in v2 |
| Row-level lineage tracking | Iceberg V3 feature, still bleeding edge. Column-level and dataset-level lineage is sufficient for now |
| Custom-built data catalog | Mature open-source options exist (DataHub, OpenMetadata). Invest engineering in quality and lineage instead |
| Unified query gateway/proxy | Adds latency and single point of failure. Let Trino handle federation; direct access during transition |
| NL-to-SQL for all data domains | Accuracy requires curated semantic context per domain. Deploy incrementally, not enterprise-wide |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FNDTN-01 | Phase 1 | Complete |
| FNDTN-02 | Phase 1 | Complete |
| FNDTN-03 | Phase 1 | Complete |
| FNDTN-04 | Phase 1 | Complete |
| FNDTN-05 | Phase 1 | Complete |
| FNDTN-06 | Phase 1 | Complete |
| FNDTN-07 | Phase 2 | Complete |
| QUERY-01 | Phase 1 | Pending |
| QUERY-02 | Phase 1 | Pending |
| QUERY-03 | Phase 1 | Pending |
| QUERY-04 | Phase 1 | Pending |
| QUERY-05 | Phase 1 | Pending |
| QUERY-06 | Phase 1 | Pending |
| ETL-01 | Phase 2 | Complete |
| ETL-02 | Phase 2 | Complete |
| ETL-03 | Phase 2 | Complete |
| ETL-04 | Phase 2 | Complete |
| ETL-05 | Phase 2 | Complete |
| ETL-06 | Phase 2 | Pending |
| ETL-07 | Phase 2 | Pending |
| CICD-01 | Phase 1 | Complete (01-01) |
| CICD-02 | Phase 1 | Complete (01-03) |
| CICD-03 | Phase 1 | Complete (01-03) |
| CICD-04 | Phase 1 | Complete (01-01) |
| GOVN-01 | Phase 2 | Complete |
| GOVN-02 | Phase 3 | Pending |
| GOVN-03 | Phase 3 | Complete |
| GOVN-04 | Phase 3 | Complete |
| GOVN-05 | Phase 3 | Pending |
| SEC-01 | Phase 1 | Pending |
| SEC-02 | Phase 1 | Pending |
| SEC-03 | Phase 3 | Complete |
| SEC-04 | Phase 3 | Complete |
| SEC-05 | Phase 1 | Complete (01-03) |
| SEC-06 | Phase 1 | Complete (01-03) |
| QUAL-01 | Phase 2 | Complete |
| QUAL-02 | Phase 2 | Complete |
| QUAL-03 | Phase 2 | Complete |
| QUAL-04 | Phase 2 | Complete |
| BISEM-01 | Phase 4 | Pending |
| BISEM-02 | Phase 4 | Pending |
| BISEM-03 | Phase 4 | Pending |
| BISEM-04 | Phase 4 | Pending |
| AISEM-01 | Phase 4 | Pending |
| AISEM-02 | Phase 4 | Pending |
| AISEM-03 | Phase 4 | Pending |
| PLAT-01 | Phase 3 | Complete |
| PLAT-02 | Phase 2 | Pending |
| PLAT-03 | Phase 3 | Complete |

**Coverage:**
- v1 requirements: 49 total
- Mapped to phases: 49
- Unmapped: 0

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-13 after roadmap creation*
