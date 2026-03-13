# Feature Research

**Domain:** Enterprise Lakehouse Architecture for Financial Services (Teradata/DataStage Migration to Iceberg/Trino)
**Researched:** 2026-03-13
**Confidence:** HIGH (core features well-documented across multiple enterprise implementations; financial services regulatory requirements well-established)

## Feature Landscape

### Table Stakes (Must Have or the Lakehouse Fails)

These are non-negotiable. Without them, the platform cannot serve a regulated financial services organization with 1.5 PB of data across 300+ sources.

#### TS-1: Iceberg Table Format on Object Storage (S3/MinIO)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Iceberg tables on AWS S3 (cloud) | Core architectural premise -- single copy of data in open format | MEDIUM | Well-supported by all target engines; use Parquet as underlying file format |
| Iceberg tables on MinIO (on-prem) | On-prem consumers need S3-compatible access without cloud dependency | MEDIUM | MinIO provides native S3 API compatibility; Iceberg reads/writes identically to AWS S3 |
| ACID transactions on Iceberg | Financial data requires consistency guarantees; concurrent reads/writes from multiple engines | LOW | Native to Iceberg spec; no additional tooling needed |
| Schema evolution | 300+ sources will evolve schemas over time; breaking changes are unacceptable | LOW | Native Iceberg capability -- add, rename, reorder columns without rewriting data |
| Partition evolution | Query performance optimization must not require full data rewrites | LOW | Iceberg unique advantage over Hive-style partitioning; change partition strategy without rewrite |
| Time travel and snapshot management | Regulatory audit requirements; rollback capability for data corrections | LOW | Native Iceberg -- configurable snapshot retention; critical for SOX audit trails |

#### TS-2: Multi-Engine Query Access

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Trino reading/writing Iceberg tables | Primary open-source query engine for the lakehouse | LOW | Trino Iceberg connector is mature and well-documented |
| Teradata OTF reading Iceberg tables | Must coexist during transition; existing workloads stay on Teradata | MEDIUM | Teradata OTF supports Iceberg read/write via AWS Glue, Hive, Unity catalogs. CAUTION: Java API layer has CPU overhead and memory issues under high concurrency |
| Teradata OTF writing Iceberg tables | Enables Teradata-driven ETL to produce Iceberg output during transition | HIGH | CPU-intensive due to Parquet-to-Java-to-Teradata format conversion; recommend using Compute Clusters for workload isolation |
| Snowflake reading Iceberg external tables | Snowflake users continue their workflows without data copies | LOW | Snowflake Iceberg external tables are GA; read-only compute-over-Iceberg pattern |
| Cross-engine catalog consistency | All engines must see the same tables, schemas, and data | HIGH | Requires a shared Iceberg catalog (REST catalog like Polaris or Nessie) accessible by Trino, Teradata, and Snowflake |

#### TS-3: Iceberg Catalog Management

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Centralized Iceberg REST catalog | Single source of truth for table metadata across all engines | HIGH | Catalog choice is a critical decision (Nessie vs Polaris vs Glue vs HMS). Polaris offers REST catalog standard and multi-engine interop; Nessie adds Git-like versioning. SWOT analysis pending per PROJECT.md |
| Catalog supporting both S3 and MinIO storage | Hybrid cloud/on-prem pattern requires unified catalog | HIGH | Must resolve single catalog spanning two storage backends, or federate two catalogs |
| Namespace/schema organization | 300+ sources need logical organization for discoverability | MEDIUM | Iceberg namespaces map to database/schema concepts; design taxonomy early |
| Table metadata caching | Query performance depends on fast metadata resolution | MEDIUM | Trino and Teradata both cache metadata; cache invalidation across engines is the hard problem |

#### TS-4: Batch Data Ingestion (Python ETL)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Python ETL framework replacing DataStage | Full DataStage retirement is an active requirement | HIGH | 40+ engineers must adopt; need standardized patterns, not ad-hoc scripts. Use PySpark or PyIceberg for Iceberg writes |
| Mainframe source connectivity | Primary upstream is mainframe; must maintain connectivity | HIGH | Existing DataStage mainframe connectors need Python equivalents. Evaluate Qlik Replicate for mainframe CDC, or custom COBOL/flat-file parsers |
| Workflow orchestration | Hundreds of ETL jobs need scheduling, dependency management, retry logic | MEDIUM | Apache Airflow is the standard (30K+ GitHub stars, massive enterprise adoption). Dagster is the modern alternative with asset-centric model and built-in lineage. Airflow recommended for team of 40+ due to hiring pool and ecosystem |
| CI/CD for ETL code | GitHub-based pipeline per PROJECT.md; testable, version-controlled ETL | MEDIUM | Standard GitHub Actions or similar; dbt for SQL transforms, pytest for Python transforms |
| Incremental/delta loading patterns | 1.5 PB cannot be full-refreshed; incremental loads are essential | MEDIUM | Iceberg merge-on-read or copy-on-write strategies; watermark-based incremental patterns |

#### TS-5: Data Governance and Lineage

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| End-to-end data lineage | Financial services regulatory requirement (SOX, BCBS 239); non-negotiable | HIGH | OpenLineage as the open standard; integrates with Airflow, Spark, dbt. Marquez as reference implementation for lineage storage and visualization |
| Data classification and sensitivity labeling | PII, financial data, and regulatory data must be tagged | MEDIUM | Column-level tags in catalog; drives access control policies |
| Business glossary / metadata layer | Business users must understand data meaning, not just technical schema | MEDIUM | Catalog must store business definitions alongside technical metadata; consider Atlan, DataHub, or OpenMetadata |
| Audit trail for all data access | SOX requirement -- who accessed what data, when, for what purpose | HIGH | Must capture query logs from Trino, Teradata, and Snowflake; centralized audit store |
| Data retention and purge policies | Regulatory retention requirements vary by data type | MEDIUM | Iceberg snapshot expiration + custom retention logic; some data must be retained 7+ years |

#### TS-6: Security and Access Control

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Authentication (SSO/LDAP/AD integration) | Enterprise identity management; no standalone credentials | MEDIUM | Trino supports LDAP, Kerberos, OAuth2; must integrate with existing AD/SSO infrastructure |
| Role-based access control (RBAC) | Standard enterprise authorization model | MEDIUM | Apache Ranger for Trino provides fine-grained RBAC on catalogs, schemas, tables, columns |
| Column-level security | PII and sensitive financial fields must be masked or restricted | HIGH | Apache Ranger on Trino supports column masking and row-level filtering at query time. Native in Trino since v466 |
| Row-level security | Different business units see different subsets of data | HIGH | Apache Ranger row-filtering policies; critical for multi-tenant data access |
| Encryption at rest | Regulatory and security baseline requirement | LOW | S3 server-side encryption (SSE-S3 or SSE-KMS); MinIO supports equivalent. Parquet-level encryption also available |
| Encryption in transit | Standard TLS for all data movement | LOW | TLS configuration on Trino, object storage, and all connectors |
| Key management | Customer-managed keys for sensitive data | MEDIUM | AWS KMS for cloud; equivalent KMS for on-prem MinIO deployment |

#### TS-7: Data Quality Framework

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Schema validation on ingestion | Prevent garbage data from entering the lakehouse | MEDIUM | Iceberg schema enforcement is native; add pre-write validation in ETL |
| Data quality checks (null rates, ranges, uniqueness) | Financial reporting depends on data accuracy (BCBS 239 compliance) | MEDIUM | Great Expectations (GX) is the standard open-source framework; dbt-expectations package for SQL-layer checks. Integrate into ETL pipeline as gate |
| Data quality monitoring and alerting | Must detect degradation, not just point-in-time checks | MEDIUM | GX + alerting integration (Slack, PagerDuty); track quality metrics over time |
| Reconciliation between source and lakehouse | Proving data completeness after migration from Teradata | HIGH | Build row-count, checksum, and aggregate reconciliation for every migrated table |

### Differentiators (Competitive Advantage Within the Organization)

These features are not required for the lakehouse to function, but they transform it from "data infrastructure" into "strategic data platform." They justify the investment.

#### D-1: Semantic Layers

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| BI semantic layer (metrics, dimensions, business logic) | Single source of business metric definitions for Tableau/Power BI; eliminates "whose numbers are right" debates | HIGH | Three viable approaches: dbt Semantic Layer (MetricFlow) for dbt-native teams, AtScale for enterprise-grade with SML open standard, Cube for API-first/embedded. Recommend dbt Semantic Layer if dbt is already in the stack; AtScale if enterprise BI governance is critical |
| AI semantic layer (NL-to-SQL) | Business users query data in natural language; 300x accuracy improvement over raw LLM-to-SQL when using semantic context | HIGH | Production NL-to-SQL accuracy drops from 85% benchmark to 10-20% in real enterprise data without proper semantic context. Requires: semantic layer, business glossary, curated schema documentation. Build incrementally; do not promise "ask anything" on day one |
| Unified metric definitions | One definition of "revenue," "risk exposure," etc. across all consumers | MEDIUM | Part of semantic layer implementation; prevents BI tool sprawl creating conflicting metrics |

#### D-2: Query Federation

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Cross-source queries via Trino | Join Iceberg lakehouse data with Teradata, Snowflake, or other sources in a single SQL query | MEDIUM | Trino federation connectors support Teradata (JDBC), Snowflake, PostgreSQL, and many others. Full query passthrough is 2x faster than connector pushdown for Teradata. Key value during transition: query both old and new data locations |
| Virtual data products | Expose federated views as logical "data products" without physical data movement | MEDIUM | Trino views over federated sources; consumers do not need to know where data physically lives |

#### D-3: Self-Service Analytics Platform

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Self-service data discovery | Business users find and understand data without asking the data team | MEDIUM | Data catalog with search, profiling, and business glossary. DataHub (open-source) or Atlan (commercial) are strong options |
| Self-service SQL workspace | Analysts write and execute queries without provisioning infrastructure | LOW | Trino + SQL IDE (e.g., DBeaver, Superset, or Starburst-hosted). Snowflake already provides this for its users |
| Data product marketplace | Domains publish curated, documented datasets for organizational consumption | HIGH | Organizational pattern, not just tooling. Requires domain ownership model, SLAs, and documentation standards |

#### D-4: Advanced Observability

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Pipeline observability (SLA monitoring, failure alerting) | Proactive detection of ETL failures, late data, quality regressions | MEDIUM | OpenLineage events + monitoring dashboards; Dagster provides this natively if adopted as orchestrator |
| Query performance monitoring | Identify slow queries, resource bottlenecks across Trino/Teradata/Snowflake | MEDIUM | Trino query history + Teradata DBQL + Snowflake query history; unified dashboard |
| Data freshness tracking | Business users see when data was last updated; trust is built on transparency | LOW | Iceberg snapshot timestamps; expose via catalog or semantic layer |

#### D-5: Cost Management and FinOps

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Cost visibility by domain/team | Understand which teams drive compute and storage costs | MEDIUM | Tag resources (S3 prefixes, Trino queries, Snowflake warehouses) by cost center. Showback reporting as first step |
| Chargeback model | Business units pay for their data consumption; drives cost accountability | HIGH | Requires organizational alignment, not just tooling. 59% of orgs now run dedicated FinOps teams. Start with showback, graduate to chargeback |
| Storage tiering and lifecycle | Optimize cost of 1.5 PB by tiering cold data to cheaper storage | MEDIUM | S3 Intelligent Tiering or lifecycle policies; Iceberg metadata supports querying across tiers transparently |

#### D-6: Data Mesh Patterns

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Domain ownership model | Data managed by the teams who know it best; scalable governance | HIGH | Organizational transformation, not just technology. Assign domains (e.g., Risk, Trading, Operations) ownership of their Iceberg namespaces, quality, and documentation |
| Federated governance | Central policies (security, quality standards) with domain autonomy on implementation | HIGH | Central team defines standards; domain teams implement. Tooling supports policy-as-code |
| Data contracts between domains | Explicit schema and SLA agreements between producer and consumer teams | MEDIUM | Schema registry or catalog-based contracts; breaking change detection in CI/CD |

### Anti-Features (Deliberately NOT Build in Phase 1)

These are features that seem valuable but create premature complexity, scope creep, or architectural risk if attempted too early.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time streaming ingestion | "We need real-time data" is a common ask | Streaming adds massive complexity (Kafka, Flink, exactly-once semantics) for a batch-first migration. PROJECT.md explicitly marks this out of scope. Most financial reporting is T+1 or batch-compatible | Start with batch/micro-batch. Add streaming for specific use cases (fraud detection) only after batch migration is complete. Iceberg supports streaming writes when ready |
| Custom-built data catalog from scratch | "We need a catalog tailored to our needs" | Building a catalog is a multi-year effort. Mature open-source options exist (DataHub, OpenMetadata, Atlan) | Adopt an existing catalog; customize with plugins/extensions. Invest engineering time in data quality and lineage instead |
| Full Teradata decommission in phase 1 | "Why maintain two systems?" | 1.5 PB migration with 300+ sources cannot be big-bang. Teradata OTF enables coexistence. Per PROJECT.md, this phase validates feasibility | Coexist via OTF. Migrate tables incrementally. Decommission only after workloads are validated on Trino/Iceberg |
| Multi-cloud deployment (AWS + Azure + GCP) | "We might need other clouds later" | Supporting multiple cloud providers triples infrastructure complexity for no current requirement | AWS S3 (cloud) + MinIO (on-prem) is the stated architecture. Iceberg is cloud-agnostic; add clouds later if needed |
| Enterprise-wide data mesh overnight | "We should adopt data mesh organization-wide" | Data mesh is an organizational transformation, not a technology deployment. Forcing it on 40+ engineers across all domains simultaneously causes chaos | Start with 2-3 pilot domains. Establish patterns. Expand based on what works. Most successful implementations are hybrid, not pure mesh |
| NL-to-SQL for all data on day one | "Business users should be able to ask anything" | Production NL-to-SQL accuracy collapses to 10-20% without curated semantic context. Promising "ask anything" and delivering hallucinated answers destroys trust | Build the semantic layer first (BI metrics, business glossary). Add NL-to-SQL on top of curated, high-confidence domains. Expand scope incrementally |
| Custom ETL framework from scratch | "DataStage is unique; we need custom tooling" | Reinventing orchestration/ETL framework is a multi-year distraction | Use Airflow (or Dagster) with standardized patterns. Build reusable operators/assets for common ingestion patterns, not a framework |
| Unified query gateway / proxy | "Route all queries through a single endpoint" | Adds latency, becomes single point of failure, and each engine has different SQL dialects and optimization strategies | Let Trino handle federation. Direct Teradata/Snowflake users to their native interfaces during transition. Consolidate to Trino over time |
| Row-level lineage tracking | "Track every row from source to target" | Iceberg V3 spec introduces row-level lineage but it is bleeding edge. Column-level and dataset-level lineage is mature | Implement dataset-level and column-level lineage first (OpenLineage). Add row-level when Iceberg V3 ecosystem matures |

## Feature Dependencies

```
[TS-1: Iceberg on Object Storage]
    |
    +---requires--> [TS-3: Iceberg Catalog]
    |                   |
    |                   +---enables--> [TS-2: Multi-Engine Query Access]
    |                   |                   |
    |                   |                   +---enables--> [D-2: Query Federation]
    |                   |
    |                   +---enables--> [D-3: Self-Service Discovery]
    |
    +---enables--> [TS-4: Batch Data Ingestion (Python ETL)]
    |                   |
    |                   +---enables--> [TS-7: Data Quality Framework]
    |                   |
    |                   +---enables--> [TS-5: Data Governance & Lineage]
    |                                       |
    |                                       +---enables--> [D-1: BI Semantic Layer]
    |                                       |                   |
    |                                       |                   +---enables--> [D-1: AI Semantic Layer (NL-to-SQL)]
    |                                       |
    |                                       +---enables--> [D-6: Data Mesh Patterns]
    |
    +---requires--> [TS-6: Security & Access Control]
                        |
                        +---enables--> [D-5: Cost Management / FinOps]

[TS-4: Batch Ingestion] ---enables--> [D-4: Advanced Observability]
```

### Dependency Notes

- **TS-1 (Iceberg) requires TS-3 (Catalog):** Cannot have multi-engine access without a shared catalog. Catalog choice is THE foundational decision.
- **TS-2 (Multi-Engine) requires TS-3 (Catalog):** Trino, Teradata OTF, and Snowflake must all point to the same catalog for consistency.
- **TS-5 (Governance) requires TS-4 (Ingestion):** Lineage tracking needs data flowing through instrumented pipelines (OpenLineage in Airflow/Spark).
- **D-1 AI Semantic Layer requires D-1 BI Semantic Layer:** NL-to-SQL needs curated metric definitions and business glossary. Without the BI semantic layer, LLM accuracy collapses.
- **D-6 (Data Mesh) requires TS-5 (Governance) + TS-6 (Security):** Domain ownership without governance and access control is just chaos.
- **TS-6 (Security) is parallel to TS-1:** Must be designed alongside storage/catalog, not bolted on afterward. Apache Ranger policies need to be in place before data is queryable.

## MVP Definition

### Launch With (Phase 1 -- Validate Feasibility)

The minimum to prove Iceberg/Trino can coexist with Teradata and replace the current architecture.

- [ ] **TS-1: Iceberg tables on S3 and MinIO** -- Core architectural foundation; without this, nothing else works
- [ ] **TS-3: Iceberg catalog (chosen and deployed)** -- Foundational decision that all engines depend on
- [ ] **TS-2: Trino + Teradata OTF reading same Iceberg tables** -- Proves multi-engine access is real, not theoretical
- [ ] **TS-4: First Python ETL pipelines (pilot scope)** -- Validates DataStage replacement pattern on 5-10 representative jobs
- [ ] **TS-6: Basic security (authentication + RBAC)** -- Cannot expose data without access control; even POC needs this
- [ ] **TS-7: Basic data quality (schema validation + row counts)** -- Reconciliation proves data integrity after migration

### Add After Validation (Phase 2 -- Scale Migration)

Features to add once the core is proven and the team is confident.

- [ ] **TS-4: Full Python ETL migration (all DataStage jobs)** -- Scale from pilot to full 300+ source migration
- [ ] **TS-5: End-to-end lineage with OpenLineage** -- Trigger: when pipeline count exceeds manual tracking
- [ ] **TS-6: Column-level and row-level security (Apache Ranger)** -- Trigger: when multiple business units access the lakehouse
- [ ] **TS-7: Full data quality framework (Great Expectations)** -- Trigger: when batch ingestion is the primary path
- [ ] **D-2: Query federation (Trino across Teradata + Iceberg)** -- Trigger: when users need to join old and new data locations
- [ ] **D-4: Pipeline observability and SLA monitoring** -- Trigger: when pipeline count makes manual monitoring impossible

### Future Consideration (Phase 3+ -- Strategic Platform)

Features to defer until the lakehouse is the proven, primary data platform.

- [ ] **D-1: BI semantic layer** -- Why defer: requires stable, migrated data models before metrics layer adds value
- [ ] **D-1: AI semantic layer (NL-to-SQL)** -- Why defer: requires BI semantic layer + business glossary as prerequisites; accuracy is too low without them
- [ ] **D-3: Self-service data marketplace** -- Why defer: requires organizational data mesh adoption, not just tooling
- [ ] **D-5: Cost management and chargeback** -- Why defer: meaningful only at scale; start with showback after compute usage is significant
- [ ] **D-6: Data mesh domain ownership** -- Why defer: organizational change that needs working infrastructure first; pilot with 2-3 domains
- [ ] **Snowflake Iceberg external tables** -- Why defer: dependent on Snowflake long-term strategy decision (SWOT pending)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority | Phase |
|---------|------------|---------------------|----------|-------|
| Iceberg tables on S3/MinIO (TS-1) | HIGH | MEDIUM | P1 | 1 |
| Iceberg catalog deployment (TS-3) | HIGH | HIGH | P1 | 1 |
| Trino Iceberg connector (TS-2) | HIGH | LOW | P1 | 1 |
| Teradata OTF Iceberg read (TS-2) | HIGH | MEDIUM | P1 | 1 |
| Basic Python ETL (pilot) (TS-4) | HIGH | MEDIUM | P1 | 1 |
| Authentication + RBAC (TS-6) | HIGH | MEDIUM | P1 | 1 |
| Schema validation + reconciliation (TS-7) | HIGH | MEDIUM | P1 | 1 |
| Full Python ETL migration (TS-4) | HIGH | HIGH | P1 | 2 |
| End-to-end lineage (TS-5) | HIGH | HIGH | P1 | 2 |
| Column/row-level security (TS-6) | HIGH | HIGH | P1 | 2 |
| Full data quality framework (TS-7) | HIGH | MEDIUM | P2 | 2 |
| Query federation (D-2) | MEDIUM | MEDIUM | P2 | 2 |
| Pipeline observability (D-4) | MEDIUM | MEDIUM | P2 | 2 |
| BI semantic layer (D-1) | HIGH | HIGH | P2 | 3 |
| AI semantic layer / NL-to-SQL (D-1) | MEDIUM | HIGH | P3 | 3+ |
| Self-service data marketplace (D-3) | MEDIUM | HIGH | P3 | 3+ |
| Cost management / FinOps (D-5) | MEDIUM | MEDIUM | P3 | 3+ |
| Data mesh patterns (D-6) | MEDIUM | HIGH | P3 | 3+ |
| Teradata OTF Iceberg write (TS-2) | MEDIUM | HIGH | P2 | 2 |
| Snowflake Iceberg external tables | LOW | LOW | P3 | 3 |

**Priority key:**
- P1: Must have -- blocks the architecture or is a regulatory requirement
- P2: Should have -- adds significant value once foundations are in place
- P3: Nice to have -- strategic differentiator for future phases

## Competitor/Reference Architecture Feature Analysis

| Feature | Databricks Lakehouse | Snowflake + Iceberg | Cloudera Open Lakehouse | Our Approach (Trino + Iceberg) |
|---------|---------------------|---------------------|------------------------|-------------------------------|
| Table format | Delta Lake (primary), Iceberg (supported) | Iceberg (native external tables) | Iceberg (native via Cloudera) | Iceberg (native, vendor-neutral) |
| Catalog | Unity Catalog (proprietary, now open-source) | Snowflake-managed Iceberg catalog | Cloudera SDX / HMS | REST catalog (Polaris or Nessie) -- fully open |
| Query engine | Spark SQL, Photon | Snowflake engine | Trino, Hive, Impala | Trino (primary), Teradata OTF (transition) |
| Governance | Unity Catalog lineage, tags, access control | Snowflake governance features | Apache Ranger, Atlas, SDX | Apache Ranger + OpenLineage + catalog metadata |
| Data quality | Lakehouse Monitoring, Delta Live Tables expectations | Snowflake data quality monitoring | Cloudera Data Quality | Great Expectations + dbt tests |
| Semantic layer | Databricks AI/BI, Unity metric views | Snowflake Cortex Analyst | Partner integrations | dbt Semantic Layer or AtScale |
| NL-to-SQL | LakehouseIQ + AI/BI dashboards | Cortex Analyst | Partner integrations | Custom build on semantic layer (phased) |
| Multi-engine | Spark only (primarily) | Snowflake only | Trino + Spark + Impala | Trino + Teradata OTF + Snowflake |
| Hybrid cloud | Databricks on AWS/Azure/GCP | Snowflake on AWS/Azure/GCP | On-prem + cloud (Cloudera) | AWS S3 + MinIO (on-prem) -- true hybrid |
| Cost model | Per-DBU compute pricing | Per-credit compute pricing | Subscription licensing | Open-source Trino (self-managed compute) + storage costs |

**Key advantage of our approach:** Vendor neutrality. No single vendor lock-in. Trino + Iceberg + open catalog means any engine can participate. The trade-off is higher operational complexity -- we build and manage what Databricks/Snowflake provide as managed services.

## Sources

- [Teradata OTF for Iceberg](https://www.teradata.com/platform/open-table-formats) -- Teradata OTF capabilities and limitations (HIGH confidence)
- [Teradata OTF Performance Analysis](https://celiamuriel.com/teradata-db-e-20-otf-performance/) -- CPU overhead and concurrency issues (MEDIUM confidence)
- [Teradata OTF General Limitations](https://docs.teradata.com/r/Enterprise_IntelliFlex_Lake_VMware/Teradata-Open-Table-Format-for-Apache-Iceberg-and-Delta-Lake-User-Guide/General-Limitations) -- Official documentation (HIGH confidence)
- [Trino Iceberg Connector](https://trino.io/docs/current/connector/iceberg.html) -- Official Trino documentation (HIGH confidence)
- [Trino Ranger Access Control](https://trino.io/docs/current/security/ranger-access-control.html) -- Column masking, row filtering (HIGH confidence)
- [Trino Query Federation](https://www.starburst.io/blog/introducing-full-query-passthrough-for-faster-query-federation/) -- Full query passthrough performance (MEDIUM confidence)
- [Apache Iceberg Benefits](https://atlan.com/know/iceberg/apache-iceberg-benefits/) -- Schema/partition evolution, time travel (HIGH confidence)
- [OpenLineage](https://openlineage.io/) -- Open standard for data lineage (HIGH confidence)
- [Marquez](https://marquezproject.ai/) -- Reference implementation for OpenLineage (HIGH confidence)
- [Great Expectations Lakehouse Engine](https://greatexpectations.io/blog/data-quality-for-your-lakehouse-lakehouse-engine-gx/) -- Data quality on lakehouse (HIGH confidence)
- [dbt-expectations](https://www.datafold.com/blog/dbt-expectations/) -- dbt data quality testing (MEDIUM confidence)
- [AtScale Semantic Lakehouse](https://www.atscale.com/blog/semantic-lakehouse-for-ai-bi/) -- BI/AI semantic layer (MEDIUM confidence)
- [Semantic Layer 2025 Review](https://www.atscale.com/blog/semantic-layer-2025-in-review/) -- Semantic layer landscape (MEDIUM confidence)
- [Cube Semantic Layer](https://kaelio.com/blog/best-semantic-layer-solutions-for-data-teams-2026-guide) -- Cube, dbt, AtScale comparison (MEDIUM confidence)
- [NL-to-SQL Enterprise Guide](https://www.blazesql.com/blog/natural-language-to-sql) -- Production accuracy challenges (MEDIUM confidence)
- [AWS NL-to-SQL](https://aws.amazon.com/blogs/machine-learning/enterprise-grade-natural-language-to-sql-generation-using-llms-balancing-accuracy-latency-and-scale/) -- Enterprise NL-to-SQL patterns (HIGH confidence)
- [Iceberg Catalogs 2025](https://www.e6data.com/blog/iceberg-catalogs-2025-emerging-catalogs-modern-metadata-management) -- Nessie, Polaris, Unity comparison (MEDIUM confidence)
- [Apache Polaris](https://celerdata.com/glossary/polaris-catalog) -- REST catalog standard (MEDIUM confidence)
- [MinIO Lakehouse Architecture](https://blog.min.io/lakehouse-architecture-iceberg-minio/) -- Hybrid deployment patterns (HIGH confidence)
- [Hybrid Iceberg Lakehouse with MinIO](https://www.dremio.com/blog/hybrid-lakehouse-storage-solutions-minio/) -- Dremio + MinIO hybrid (MEDIUM confidence)
- [Lakehouse Security Best Practices](https://www.onehouse.ai/blog/securing-your-data-lakehouse-best-practices-for-data-encryption-access-control-and-compliance) -- Encryption, access control, compliance (MEDIUM confidence)
- [MinIO Lakehouse Security](https://blog.min.io/data-lakehouse-security-supporting-scalable-analytics-and-ai-workloads/) -- Object storage security (MEDIUM confidence)
- [FinOps Chargeback](https://www.finops.org/framework/capabilities/invoicing-chargeback/) -- Cost allocation framework (HIGH confidence)
- [Data Mesh Principles](https://atlan.com/data-mesh-principles/) -- Four pillars of data mesh (HIGH confidence)
- [Dagster Pipeline Frameworks](https://dagster.io/guides/data-pipeline-frameworks-key-features-10-tools-to-know-in-2025) -- Orchestration landscape (MEDIUM confidence)

---
*Feature research for: Enterprise Lakehouse Architecture -- Financial Services*
*Researched: 2026-03-13*
