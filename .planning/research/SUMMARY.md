# Project Research Summary

**Project:** Lakehouse Architecture Transformation
**Domain:** Enterprise Data Platform -- Financial Services (Teradata/DataStage to Iceberg/Trino)
**Researched:** 2026-03-13
**Confidence:** MEDIUM-HIGH

## Executive Summary

This project transforms a legacy Teradata/DataStage data warehouse into an open lakehouse built on Apache Iceberg and Trino, serving a regulated financial services organization with 1.5 PB of data across 300+ sources. The expert consensus is clear: Iceberg is the winning open table format for multi-engine lakehouse architectures, Trino is the best open query engine for interactive analytics, and PySpark is the only viable ETL engine at petabyte scale. The stack is mature and battle-tested at organizations like Netflix, Apple, and LinkedIn. The architectural pattern -- medallion layers (Bronze/Silver/Gold) with a shared Iceberg catalog and write-engine separation -- is well-documented and proven. This is not a bleeding-edge bet; it is an industry-standard transformation.

The recommended approach is a feasibility-first, phased migration over 18-24 months. Phase 1 validates the core premise: can Teradata, Trino, and Snowflake all read and write the same Iceberg tables through a shared catalog? The answer depends entirely on catalog interoperability, which is the single highest-risk decision in the project. AWS Glue is the only catalog confirmed to work with all four engines (Teradata OTF, Trino, Snowflake, PySpark) and should be the Phase 1 choice, with a planned migration to Apache Polaris (REST catalog) once Teradata's REST catalog support is confirmed or Teradata's role diminishes. The on-premises storage strategy needs urgent reassessment: MinIO entered maintenance mode in late 2025, and RustFS or Ceph should replace it.

The key risks are: (1) Teradata OTF catalog mismatch locking the project into a dead-end catalog, (2) Iceberg file explosion at 1.5 PB scale without automated compaction from day one, (3) DataStage migration complexity being severely underestimated (the 40% of complex jobs will consume 80% of effort), and (4) governance/lineage gaps during transition creating regulatory exposure under BCBS 239. All four risks are manageable with early validation, dedicated platform team standards, and treating governance as a Phase 1 requirement rather than a Phase 3 afterthought. The 6-12 month timeline in the PROJECT.md is aggressive for full delivery but realistic for proving feasibility and migrating the first 50 ETL jobs.

## Key Findings

### Recommended Stack

The stack centers on Apache Iceberg as the universal table format, with Trino as the primary open query engine and PySpark as the ETL workhorse. The transformation layer uses dbt-trino for SQL-based Silver-to-Gold modeling, orchestrated by Apache Airflow 3.0. Data quality runs through Soda Core (primary, YAML-based data contracts) supplemented by Great Expectations for complex statistical validation. Governance and lineage use OpenMetadata with OpenLineage as the event standard. The semantic layer for BI uses Cube (API-first, pre-aggregation caching, Trino-native), with NL-to-SQL deferred to Phase 3+ starting through Cube's AI API. See [STACK.md](STACK.md) for full rationale and alternatives analysis.

**Core technologies:**
- **Apache Iceberg 1.10.x (V2):** Open table format -- only OTF with first-class support across Teradata, Trino, Snowflake, and Spark
- **Apache Polaris 1.2.x:** Iceberg REST catalog -- Apache TLP, vendor-neutral, RBAC built-in (Phase 2+ target; AWS Glue for Phase 1)
- **Trino 479+:** Primary query engine -- Iceberg connector with full DML, 100+ federation connectors, interactive performance
- **PySpark 3.5.x:** ETL engine -- only viable option at 1.5 PB distributed scale, native Iceberg writes
- **dbt-core 1.9.x + dbt-trino:** SQL transformation layer -- Silver-to-Gold modeling, semantic layer integration, massive community
- **Apache Airflow 3.0:** Orchestration -- asset-aware scheduling, 80K+ org adoption, AWS MWAA managed option
- **Soda Core 4.1.x:** Data quality -- Data Contracts model, reconciliation checks purpose-built for migration validation
- **OpenMetadata 1.12.x + OpenLineage:** Governance -- unified catalog/lineage/quality, PII auto-classification, column-level lineage
- **Cube 1.6.x:** BI semantic layer -- API-first, pre-aggregation caching, Trino integration, Tableau/Power BI connectors
- **AWS S3 + RustFS/Ceph (on-prem):** Storage -- S3 API for cloud, S3-compatible replacement for abandoned MinIO on-prem

**Critical version notes:** Iceberg V3 spec is ratified but engine support is incomplete -- stay on V2. MinIO open-source is archived; budget for commercial alternative or migrate to RustFS/Ceph.

### Expected Features

See [FEATURES.md](FEATURES.md) for full feature landscape, dependency graph, and prioritization matrix.

**Must have (table stakes -- Phase 1-2):**
- TS-1: Iceberg tables on S3 and MinIO with ACID transactions, schema evolution, time travel
- TS-2: Multi-engine query access (Trino + Teradata OTF + Snowflake reading same Iceberg tables)
- TS-3: Centralized Iceberg catalog supporting all engines and both storage backends
- TS-4: Python ETL framework replacing DataStage (PySpark + Airflow)
- TS-5: End-to-end data lineage (OpenLineage -- regulatory non-negotiable under BCBS 239)
- TS-6: Security and access control (SSO, RBAC, column-level masking, encryption)
- TS-7: Data quality framework (schema validation, reconciliation, monitoring)

**Should have (differentiators -- Phase 2-3):**
- D-1: BI semantic layer (Cube over Trino, serving Tableau/Power BI)
- D-2: Query federation (Trino joining Iceberg + Teradata + other sources)
- D-4: Pipeline observability and SLA monitoring

**Defer to v2+ (Phase 3+):**
- D-1 AI: NL-to-SQL semantic layer (requires BI semantic layer as prerequisite; accuracy too low without curated context)
- D-3: Self-service data marketplace (organizational change, not just tooling)
- D-5: Cost management / FinOps chargeback (meaningful only at scale)
- D-6: Data mesh domain ownership (pilot with 2-3 domains, not organization-wide)
- Real-time streaming (batch-first; Iceberg supports streaming writes when ready)

**Anti-features (deliberately avoid):**
- Full Teradata decommission in Phase 1
- Multi-cloud deployment (AWS + MinIO is sufficient)
- NL-to-SQL for all data on day one (accuracy collapses to 10-20% without semantic curation)
- Custom ETL framework from scratch (use Airflow + standardized patterns)
- Row-level lineage tracking (wait for Iceberg V3 ecosystem maturity)

### Architecture Approach

The architecture follows a layered pattern with clear separation of concerns: source systems feed a Python ETL framework (PySpark + Airflow) that writes data through Bronze/Silver/Gold medallion layers into Iceberg tables on S3/MinIO. A shared Iceberg catalog (Glue in Phase 1, Polaris target for Phase 2+) provides unified metadata access for all engines. Write operations are owned by a single engine per table (PySpark for ETL, dbt-on-Trino for Gold aggregations) to avoid optimistic concurrency conflicts. Read operations are distributed: Trino for interactive analytics, Teradata OTF for legacy workloads, Snowflake for external consumers. The BI semantic layer (Cube) sits between Trino and BI tools. See [ARCHITECTURE.md](ARCHITECTURE.md) for full component diagrams and data flow.

**Major components:**
1. **Ingestion Layer (PySpark + Airflow):** Extracts from 300+ sources (mainframe primary), writes Bronze Iceberg tables, orchestrates all ETL
2. **Medallion Layers (Bronze/Silver/Gold):** Progressive data quality layers -- raw, cleansed, business-ready -- all as Iceberg tables
3. **Iceberg Catalog (Glue -> Polaris):** Central metadata registry, the architectural linchpin for multi-engine access
4. **Query Engine Layer (Trino + Teradata OTF + Snowflake):** Multi-engine read access with write-engine separation
5. **Semantic Layer (Cube):** Unified metrics for BI tools with pre-aggregation caching
6. **Governance Layer (OpenMetadata + OpenLineage):** Lineage, quality metrics, PII classification, audit trails
7. **Storage Layer (S3 + on-prem S3-compatible):** Hybrid cloud/on-prem with data stored in one location per table

**Key architectural patterns:**
- Multi-engine Iceberg with shared catalog (core pattern)
- Medallion architecture (Bronze/Silver/Gold) for progressive quality
- Write-engine separation (one writer per table)
- Hybrid cloud storage with unified catalog
- Semantic layer abstraction between query engine and BI tools

### Critical Pitfalls

See [PITFALLS.md](PITFALLS.md) for all 11 pitfalls with full prevention and recovery strategies.

1. **Teradata OTF catalog mismatch** -- Teradata OTF does not support REST catalogs (Polaris/Nessie). Use AWS Glue as Phase 1 common denominator; validate REST support before committing to Polaris. This is a gate decision.
2. **Iceberg file explosion at PB scale** -- Without automated compaction, tables accumulate millions of small files and queries degrade to 10+ minute planning times. Implement compaction, snapshot expiration, and orphan cleanup as Day 1 operational requirements, not afterthoughts.
3. **MinIO is effectively abandoned** -- Open-source MinIO entered maintenance mode Dec 2025. Do not deploy for new on-prem storage. Evaluate RustFS (Apache 2.0, 2.3x faster) or Ceph RGW as replacements immediately.
4. **DataStage migration complexity underestimated** -- 40% of 300+ jobs contain complex logic requiring 10x migration effort. Tier all jobs by complexity before starting. Budget 3-5x more effort for complex jobs. Run parallel validation for every migrated job.
5. **Governance gaps create regulatory exposure** -- BCBS 239 requires attribute-level lineage from source to report. Lineage must be a Day 1 requirement. Deploy OpenLineage from the first migrated ETL job. Engage compliance team early.
6. **BI performance regression kills adoption** -- Trino-over-Iceberg is 2-10x slower than optimized Teradata for BI dashboards without pre-aggregated Gold tables and a semantic layer. Benchmark top 50 dashboards before any BI cutover.
7. **Timeline underestimation** -- Full scope is 18-24 months, not 6-12. Redefine success at 6 months as "Phase 1 validated, first 50 jobs migrated" rather than full migration complete.

## Implications for Roadmap

Based on combined research across stack, features, architecture, and pitfalls, the following phase structure is recommended. The ordering is driven by three principles: (1) validate the riskiest assumptions first, (2) establish governance from day one, (3) build infrastructure before consumers.

### Phase 0: Team Setup and Standards (Weeks 1-3)
**Rationale:** Pitfall research is emphatic -- 40+ engineers working in parallel without coordination infrastructure creates integration hell. Standards must exist before code is written.
**Delivers:** Platform team (5-7 engineers), Iceberg table creation policies, shared development environment, CI/CD templates, naming conventions, communication cadence
**Addresses:** Team coordination (Pitfall 10), timeline expectations (Pitfall 11)
**Avoids:** Schema/partition inconsistency, integration failures, scope confusion

### Phase 1: Foundation and Feasibility Validation (Months 1-4)
**Rationale:** The entire architecture depends on catalog interoperability and storage layer viability. These must be proven before any migration begins. This is the gate decision phase.
**Delivers:** Proven catalog (Glue), validated storage (S3 + on-prem alternative), Trino + Teradata OTF reading same Iceberg tables, first 10 ETL jobs migrated (Bronze layer), basic security (RBAC), governance framework (OpenLineage deployed), DataStage job complexity assessment
**Addresses:** TS-1 (Iceberg on storage), TS-2 (multi-engine access), TS-3 (catalog), TS-4 (pilot ETL), TS-6 (basic security), TS-7 (basic quality/reconciliation)
**Avoids:** Catalog mismatch (Pitfall 1), MinIO risk (Pitfall 4), Teradata OTF performance surprises (Pitfall 3)
**Gate criteria:** Cross-engine read/write through shared catalog succeeds at 1+ TB scale; on-prem storage alternative validated; OTF performance benchmarked

### Phase 2: Core Platform and ETL Migration (Months 5-10)
**Rationale:** With foundation proven, scale the migration. ETL jobs migrate in waves (Tier 1 simple jobs first, Tier 2 moderate second). Silver layer construction begins. Lineage enforcement for every migrated job.
**Delivers:** 100-150 ETL jobs migrated with parallel-run validation, Silver layer for priority domains, full data quality framework (Soda Core), column-level lineage in OpenMetadata, query federation (Trino across Teradata + Iceberg), pipeline observability, Snowflake Iceberg external table validation
**Addresses:** TS-4 (scaled ETL), TS-5 (lineage enforcement), TS-7 (full quality), D-2 (federation), D-4 (observability)
**Uses:** PySpark, Airflow 3.0, Soda Core, OpenLineage, OpenMetadata, dbt-trino (initial Gold models)
**Avoids:** DataStage migration underestimation (Pitfall 5), governance gaps (Pitfall 6), FSDM confusion (Pitfall 8)

### Phase 3: BI Migration and Semantic Layer (Months 11-15)
**Rationale:** BI migration requires stable Gold-layer data. Build the semantic layer, benchmark dashboards against Trino, and cut over only after performance parity is proven. FSDM Silver/Gold denormalization for high-use subject areas.
**Delivers:** Cube semantic layer serving Tableau and Power BI, Gold-layer pre-aggregates for top 50 dashboards, BI tools pointed at Cube/Trino (with Teradata fallback), Snowflake long-term strategy decided, catalog migration to Polaris (if Teradata REST support confirmed)
**Addresses:** D-1 (BI semantic layer), remaining TS-4 (ETL migration waves), Snowflake SWOT resolution
**Avoids:** BI performance regression (Pitfall 7), Snowflake feature incompatibility (Pitfall 9)

### Phase 4: AI Layer, Optimization, and Teradata Wind-Down (Months 16-24)
**Rationale:** AI semantic layer requires BI semantic layer as prerequisite. Teradata wind-down begins only after workloads are validated on Trino. Cost optimization and data mesh patterns become relevant at full scale.
**Delivers:** NL-to-SQL via Cube AI API (curated domains first), remaining ETL job migration (Tier 3 complex jobs), Teradata workload migration to Trino, FinOps showback, data mesh pilot (2-3 domains), full DataStage retirement
**Addresses:** D-1 AI (NL-to-SQL), D-5 (cost management), D-6 (data mesh pilot)
**Uses:** Cube AI API, Wren AI (if needed), Polaris (catalog upgrade)

### Phase Ordering Rationale

- **Catalog and storage first (Phase 1)** because every component in the architecture depends on them. The catalog compatibility matrix shows AWS Glue as the only safe choice for all engines -- start there, evolve later.
- **ETL before BI (Phase 2 before Phase 3)** because BI tools need business-ready Gold-layer data that does not exist until ETL pipelines build it. The feature dependency graph shows TS-4 (ingestion) enables TS-7 (quality) enables TS-5 (lineage) enables D-1 (semantic layer).
- **BI semantic layer before AI semantic layer (Phase 3 before Phase 4)** because NL-to-SQL accuracy collapses from 86-95% to 10-20% without curated metric definitions. The AI layer reads from the BI layer's semantic model.
- **Governance throughout, not at the end** because BCBS 239 does not grant grace periods. OpenLineage deploys in Phase 1, enforces in Phase 2, dashboards in Phase 3.
- **18-24 month total timeline** because comparable enterprise migrations at this scale (300+ sources, 1.5 PB) consistently take 18-24 months. The 6-month milestone should be "Phase 1 complete and first 50 jobs migrated," not "done."

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** HIGH priority. Catalog interoperability testing (Teradata OTF + Glue + Trino + Snowflake), on-prem storage alternative evaluation (RustFS vs Ceph vs MinIO AIStor commercial), Teradata OTF performance benchmarking at 1+ TB. Sparse public documentation on Teradata REST catalog support.
- **Phase 2:** MEDIUM priority. Mainframe source connectivity from Python (COBOL copybook parsing, EBCDIC handling), DataStage job complexity tiers, Soda Core data contracts for medallion layer boundaries.
- **Phase 3:** MEDIUM priority. Cube performance tuning for Trino pre-aggregation, Tableau/Power BI connector optimization, Polaris operational maturity (HA/DR story for self-hosted catalog).

Phases with standard patterns (skip deep research):
- **Phase 0:** Team setup is organizational, not technical. Standard platform team patterns apply.
- **Phase 2 (ETL core):** PySpark + Airflow + dbt-trino is extremely well-documented. Focus research on the Teradata-specific and mainframe-specific integration points, not the core ETL patterns.
- **Phase 4 (NL-to-SQL):** Rapidly evolving space; research at Phase 3 completion will be more current than research now.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Iceberg, Trino, PySpark, Airflow, dbt are industry-standard with extensive production evidence. Polaris is newer (TLP Feb 2026) but REST catalog is well-specified. |
| Features | HIGH | Feature landscape and prioritization are well-grounded in enterprise lakehouse patterns. Regulatory requirements (BCBS 239, SOX) are well-documented. Feature dependency graph is clear. |
| Architecture | MEDIUM-HIGH | Core patterns (medallion, multi-engine Iceberg, write-engine separation) are proven. Teradata OTF + Polaris/Nessie interop is LOW confidence -- limited direct evidence of REST catalog support. Hybrid cloud storage pattern is MEDIUM -- depends on on-prem storage choice. |
| Pitfalls | MEDIUM-HIGH | Strong evidence for Iceberg operational issues (file explosion, compaction), MinIO abandonment, and DataStage migration complexity from multiple documented cases. Teradata OTF-specific pitfalls have moderate evidence (official docs + limited production reports). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

These could not be fully resolved by research and need validation during planning or Phase 1 execution:

- **Teradata OTF REST catalog support:** No documentation confirms or denies REST catalog (Polaris) compatibility with Teradata OTF. This is the single biggest architectural uncertainty. Validate with Teradata engineering or hands-on testing in Phase 1 week 1.
- **On-prem storage replacement for MinIO:** RustFS is promising (Apache 2.0, direct replacement, faster) but very new. Ceph RGW is battle-tested but operationally heavy. Neither has been validated against full Iceberg operational patterns (atomic renames, multipart uploads, listing consistency) at PB scale. Needs hands-on PoC.
- **MinIO AIStor (commercial) viability:** If commercial MinIO (AIStor) is acceptable, it may still be viable despite open-source abandonment. Needs pricing inquiry and contractual assessment.
- **Spark cluster sizing for 1.5 PB:** AWS EMR vs self-managed Kubernetes vs spark-on-k8s-operator. Sizing depends on ETL job profiles not yet cataloged. Defer to Phase 1 job assessment.
- **Snowflake catalog-linked database costs:** Billing started Dec 2025. Projected costs at expected query volumes are unknown. Model before Phase 2 architecture solidifies.
- **FSDM subject area active usage:** Nobody has audited which of the 300+ FSDM subject areas are actively queried. This inventory is prerequisite to efficient Silver/Gold layer design.
- **Mainframe connectivity from Python:** DataStage mainframe connectors have no direct Python equivalent. COBOL copybook parsing libraries (cobrix for Spark) exist but need validation against this organization's specific mainframe formats.
- **Polaris HA/DR:** Self-hosted Polaris requires PostgreSQL backend. HA/DR story for production catalog is not well-documented. Must be designed before Polaris becomes the primary catalog.

## Sources

### Primary (HIGH confidence)
- [Apache Iceberg Releases](https://iceberg.apache.org/releases/) -- Iceberg 1.10.1, V2 spec stability
- [Trino Iceberg Connector](https://trino.io/docs/current/connector/iceberg.html) -- Full DML, REST/Glue/HMS/Nessie catalogs
- [Teradata OTF Documentation](https://docs.teradata.com/r/Enterprise_IntelliFlex_Lake_VMware/Teradata-Open-Table-Format-for-Apache-Iceberg-and-Delta-Lake-User-Guide) -- Catalog support, performance guidelines, limitations
- [Snowflake Iceberg Tables](https://docs.snowflake.com/en/user-guide/tables-iceberg) -- External table capabilities and limitations
- [Apache Airflow 3.0](https://airflow.apache.org/blog/airflow-three-point-oh-is-here/) -- Asset-aware scheduling, DAG versioning
- [AWS Iceberg Compaction Best Practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/apache-iceberg-on-aws/best-practices-compaction.html) -- File maintenance patterns
- [BCBS 239 Compliance](https://www.ovaledge.com/blog/bcbs-239-data-lineage) -- Attribute-level lineage requirement
- [OpenLineage](https://openlineage.io/) -- Lineage event standard specification
- [MinIO Maintenance Mode (InfoQ)](https://www.infoq.com/news/2025/12/minio-s3-api-alternatives/) -- Confirmed project archival
- [RustFS (GitHub)](https://github.com/rustfs/rustfs) -- MinIO replacement candidate

### Secondary (MEDIUM confidence)
- [Apache Polaris GitHub / TLP Announcement](https://github.com/apache/polaris) -- REST catalog, TLP graduation Feb 2026
- [Iceberg Catalogs 2025 Survey](https://www.e6data.com/blog/iceberg-catalogs-2025-emerging-catalogs-modern-metadata-management) -- Adoption data: Glue 39.3%, Nessie 28.6%, Polaris 21.4%
- [Cube Semantic Layer](https://cube.dev/docs/product/configuration/data-sources/trino) -- Trino integration, pre-aggregation
- [Soda Core v4](https://docs.soda.io/soda-v4/release-notes/soda-core-release-notes) -- Data Contracts feature
- [OpenMetadata 1.12.x](https://docs.open-metadata.org/v1.12.x) -- Unified catalog, lineage, governance
- [DataStage to PySpark Migration](https://medium.com/@one.step.analytics.on.data/my-first-data-engineering-project-phase-2-migrating-datastage-etl-jobs-to-pyspark-161a8b4e5f18) -- Enterprise case study
- [Iceberg Production Anti-Patterns 2026](https://iomete.com/resources/blog/apache-iceberg-production-antipatterns-2026) -- File explosion, compaction failures
- [NL-to-SQL Enterprise Guide](https://www.blazesql.com/blog/natural-language-to-sql) -- Accuracy challenges with raw vs semantic-enhanced approaches

### Tertiary (LOW confidence -- needs validation)
- Teradata OTF REST catalog support -- NO documentation found; assumed unsupported pending validation
- RustFS at PB-scale Iceberg operations -- too new for production evidence
- Polaris HA/DR patterns -- limited operational documentation for self-hosted deployment
- Wren AI / Vanna AI production deployments in financial services -- limited evidence

---
*Research completed: 2026-03-13*
*Ready for roadmap: yes*
