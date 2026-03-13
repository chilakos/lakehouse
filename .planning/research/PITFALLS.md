# Pitfalls Research

**Domain:** Enterprise Lakehouse Transformation (Financial Services, Teradata to Iceberg)
**Researched:** 2026-03-13
**Confidence:** MEDIUM-HIGH (strong evidence for Iceberg/Trino operational issues, moderate for Teradata OTF specifics due to limited public production reports)

## Critical Pitfalls

### Pitfall 1: Teradata OTF Catalog Mismatch Locks You Into a Dead End

**What goes wrong:**
Teradata OTF currently supports Hive Metastore, AWS Glue, and Unity Catalog for Iceberg. It does not support the REST Catalog standard (Nessie, Polaris, Lakekeeper). The broader Iceberg ecosystem is converging on REST Catalog as the standard for multi-engine access. If you choose a REST-based catalog (which Trino, Snowflake, and the open-source ecosystem prefer), Teradata cannot participate in the same catalog. If you choose Hive Metastore to accommodate Teradata, you inherit lock contention under concurrent writes and poor hybrid cloud support.

**Why it happens:**
Teams pick a catalog based on what one engine needs (Teradata or Trino) without validating cross-engine compatibility upfront. Teradata's OTF is still maturing and lags the open-source catalog ecosystem by 6-12 months.

**How to avoid:**
- During Phase 1 OTF validation, explicitly test catalog interoperability between Teradata, Trino, and Snowflake before committing to a catalog.
- The pragmatic pattern: Use AWS Glue as the lowest-common-denominator catalog that Teradata, Trino (via Glue connector), and Snowflake (via Glue integration) all support. Accept Glue's limitations (no multi-table transactions, AWS-only) as a Phase 1 constraint.
- Plan to migrate to REST Catalog (Polaris or Nessie) in a later phase when Teradata adds REST support or when Teradata's role diminishes.
- Alternatively, run a dual-catalog pattern: Glue for Teradata-facing tables, Nessie/Polaris for Trino/Snowflake-facing tables, with metadata sync. This adds complexity but preserves future flexibility.

**Warning signs:**
- Teradata OTF documentation lists only Hive/Glue/Unity as supported catalogs
- Trino and Snowflake teams push for REST Catalog while Teradata team insists on Glue/Hive
- Nobody has tested whether Teradata can read tables written by Trino through the same catalog

**Phase to address:**
Phase 1 (OTF Feasibility). This is a gate decision -- do not proceed with full architecture until catalog interoperability is proven.

---

### Pitfall 2: Iceberg File Explosion Renders Queries Unusable at 1.5 PB Scale

**What goes wrong:**
Every modification to an Iceberg table creates new metadata files (manifest, manifest-list, table-metadata JSON) plus new data files. At 1.5 PB with hundreds of ETL jobs writing daily, tables accumulate millions of small files. Query planning degrades from milliseconds to 10+ minutes. Trino coordinators hit OOM errors scanning manifest lists. One documented case showed a 1.5x performance degradation from modifying just 3% of data. Streaming or frequent batch patterns can generate 432,000 new files per day.

**Why it happens:**
Teams treat Iceberg as a "write and forget" format like traditional database tables. They do not budget for compaction, snapshot expiration, orphan file cleanup, or manifest rewriting. When compaction falls behind ingestion rate, you enter a "death spiral" where file counts grow unbounded and compaction jobs themselves start failing due to the volume.

**How to avoid:**
- Implement table maintenance as a Day 1 operational requirement, not an afterthought.
- Enforce the correct maintenance order: compact data files -> expire snapshots (retain 7-14 days, minimum 10) -> remove orphan files -> rewrite manifests.
- Target 100-256 MB file sizes during compaction.
- Run compaction on a dedicated cluster separate from query processing to avoid resource contention.
- Monitor file counts, metadata sizes, snapshot counts, and delete file accumulation continuously.
- For high-write tables, trigger compaction on file count thresholds (100 files per partition) rather than fixed schedules.
- Set `write.metadata.delete-after-commit.enabled=true` with appropriate `write.metadata.previous-versions-max` to auto-clean metadata.

**Warning signs:**
- Query planning times exceed 5 seconds on tables that were previously fast
- `SELECT * FROM "table$files"` shows thousands of files under 100 MB
- Compaction jobs taking longer than the interval between runs
- S3/MinIO API costs spiking unexpectedly
- Trino coordinator memory pressure increasing without query volume changes

**Phase to address:**
Phase 1 (OTF Feasibility) for establishing the pattern. Phase 2 (ETL Migration) for operationalizing across all 300+ tables.

---

### Pitfall 3: Teradata OTF Performance Cliff -- Java Serialization Overhead

**What goes wrong:**
Teradata OTF reads/writes Iceberg through Java APIs, converting data from Parquet to Java SQL types to Teradata client format. This is extremely CPU-intensive. Unexpected CPU peaks occur, and memory issues arise under concurrent OTF query loads. Teradata recommends running OTF queries on separate Compute Clusters to avoid overloading the Primary Cluster, where OTF queries run at only medium priority. Cross-cloud OTF access (reading buckets in a different cloud provider) gateways through Valtix-controlled egress/ingress, creating additional bottlenecks.

**Why it happens:**
Teams benchmark OTF with small datasets and simple queries during PoC, then assume production workloads will scale linearly. They do not account for the Java serialization overhead, concurrent query contention, or network egress constraints of hybrid storage.

**How to avoid:**
- Benchmark OTF with production-representative data volumes (not toy datasets). Test with at least 1 TB tables.
- Allocate dedicated Compute Clusters for OTF workloads from the start.
- Measure CPU and memory under concurrent OTF query loads (10+ simultaneous queries).
- For hybrid S3/MinIO: benchmark cross-location reads specifically. If on-prem MinIO data must be read by cloud Teradata, the egress bottleneck may be a showstopper.
- Set realistic expectations: OTF reads will be 2-5x slower than native Teradata tables. Plan query patterns accordingly.
- Use OTF primarily for data sharing (read/write interop), not as a replacement for Teradata's native query engine on hot data.

**Warning signs:**
- PoC tests only use tables under 100 GB
- No separate Compute Cluster provisioned for OTF workloads
- CPU utilization spikes to 100% during OTF queries on Primary Cluster
- Business users complain that "Iceberg queries are slow" during early adoption

**Phase to address:**
Phase 1 (OTF Feasibility). Performance envelope must be established before committing to architecture.

---

### Pitfall 4: MinIO Is Effectively Dead -- On-Premises Storage Strategy at Risk

**What goes wrong:**
MinIO entered maintenance mode in December 2025 with no migration guide, no new features, no accepted PRs, and security fixes evaluated "case by case." The last community release shipped October 2025 (a CVE patch). Documented issues include Iceberg signature validation errors after 3 hours of continuous operation, HEAD request failures that work fine on AWS S3, and unpatched CVE vulnerabilities in official Docker images. The Iceberg community is already discussing replacing MinIO in its quickstart with RustFS.

**Why it happens:**
MinIO was the de facto open-source S3-compatible storage. Architecture decisions made 6-12 months ago assumed MinIO would continue active development. Teams are locked into MinIO for on-prem S3 compatibility without realizing the project is abandoned.

**How to avoid:**
- Do NOT commit to MinIO for new on-premises deployments. The project is effectively abandoned.
- Evaluate alternatives immediately: RustFS (Apache 2.0, direct MinIO replacement, 2.3x faster for small objects, supports Iceberg/Hudi/Delta), Ceph RGW via Rook (battle-tested, heavier operationally), SeaweedFS (distributed, Apache 2.0).
- If MinIO is already deployed, create a migration plan within 6 months. Security vulnerabilities will not be patched.
- Validate S3 API compatibility of any alternative with your specific Iceberg operations (especially metadata atomicity, multipart uploads, and listing consistency).
- For the hybrid S3/MinIO architecture in this project: consider whether on-prem S3 is actually required, or if all Iceberg data can live on AWS S3 with on-prem consumers accessing via network.

**Warning signs:**
- Architecture diagrams still show MinIO without acknowledging maintenance mode
- No evaluation of MinIO alternatives on the project backlog
- Security team flags unpatched CVEs in MinIO deployment
- Iceberg operations fail intermittently on MinIO but work on S3

**Phase to address:**
Phase 1 (OTF Feasibility). Storage layer must be validated before building anything on top of it. This is a blocking decision.

---

### Pitfall 5: DataStage-to-Python Migration Underestimates Hidden Complexity in 300+ Jobs

**What goes wrong:**
DataStage jobs contain deeply nested workflows, embedded SQL logic, proprietary transformation expressions, implicit error handling, and undocumented side effects. Teams attempt 1:1 translation to Python/PySpark and discover: (a) DataStage built-in components have no direct Python equivalents, requiring custom UDFs that introduce performance overhead; (b) implicit parallelism in DataStage must be explicitly re-engineered in Python; (c) error handling and recovery semantics differ fundamentally; (d) XML-based job definitions resist automated parsing; (e) undocumented business logic embedded in DataStage stages is lost during translation.

A documented enterprise case: migrating 112 DataStage jobs to PySpark required extensive custom UDF development, with UDFs becoming a performance bottleneck requiring iterative optimization.

**Why it happens:**
Teams estimate migration effort based on job count (300+) and average complexity, but the distribution is bimodal: 60% of jobs are simple (extract-load with basic transforms) while 40% contain complex logic that takes 10x the effort. The "long tail" of complex jobs is what kills timelines.

**How to avoid:**
- Catalog all 300+ DataStage jobs by complexity tier BEFORE starting migration. Use automated parsing of DataStage XML to extract: number of stages, types of transformations, embedded SQL, custom routines, and dependencies.
- Tier the jobs: Tier 1 (simple extract-load, automatable), Tier 2 (moderate transforms, template-driven), Tier 3 (complex logic, requires manual rewrite and SME involvement).
- Migrate Tier 1 first (build confidence and velocity), Tier 2 second (establish patterns), Tier 3 last (with dedicated senior engineers).
- Run DataStage and Python in parallel for each migrated job for a validation period (minimum 2 weeks). Compare outputs row-by-row.
- Use native Spark/Python functions wherever possible instead of UDFs. Cache intermediate DataFrames to reduce recomputation.
- Budget 3-5x more effort for Tier 3 jobs than initial estimates.

**Warning signs:**
- No job complexity assessment completed before migration begins
- Team estimates "2 days per job" uniformly across all 300 jobs
- First 10 migrated jobs are all simple ones, creating false confidence
- No parallel-run validation environment set up
- Mainframe-specific transformations (EBCDIC, packed decimal, COBOL copybook parsing) not identified early

**Phase to address:**
Phase 2 (ETL Migration). The job catalog and complexity assessment should happen in Phase 1 to inform Phase 2 timelines.

---

### Pitfall 6: Governance and Lineage Gaps Create Regulatory Exposure During Transition

**What goes wrong:**
During migration, data flows through both old (DataStage/Teradata) and new (Python/Iceberg/Trino) paths simultaneously. Lineage tools that track DataStage jobs cannot track Python jobs. Column-level lineage breaks at the Teradata-to-Iceberg boundary. Metadata about data origins, transformations, and quality checks exists in DataStage's proprietary format and does not transfer to the new stack. BCBS 239 requires attribute-level lineage from source to report -- regulators now explicitly require this. A lineage gap during migration means you cannot demonstrate compliance for data flowing through the new path.

**Why it happens:**
Lineage and governance are treated as "Phase 3" concerns while infrastructure migration happens in Phase 1-2. By the time governance catches up, months of data have flowed through ungoverned paths. Financial services regulators do not grant grace periods for "we're migrating."

**How to avoid:**
- Lineage must be a Day 1 requirement, not a Phase 3 add-on.
- Before migrating any DataStage job, document its lineage in a format that the new governance stack can consume (OpenLineage standard recommended).
- Deploy OpenLineage-compatible lineage collection in the Python ETL framework from the first job migration.
- Maintain a "lineage bridge" document mapping old DataStage job lineage to new Python pipeline lineage for every migrated job.
- Do not decommission any DataStage job until its lineage is fully captured in the new system.
- Engage compliance/audit teams EARLY to agree on what "acceptable lineage" looks like during transition.

**Warning signs:**
- No lineage tool selected or deployed when ETL migration begins
- Compliance team unaware that migration is happening
- Audit requests during migration cannot be answered for data flowing through new pipelines
- "We'll add lineage later" appears in project plans

**Phase to address:**
Phase 1 (establish lineage standards and tooling). Phase 2 (enforce for every migrated job). This is non-negotiable in financial services.

---

### Pitfall 7: BI Query Performance Regression Kills User Adoption

**What goes wrong:**
Tableau and Power BI users currently query Teradata directly via optimized ODBC/JDBC drivers with decades of query optimization, materialized views, and aggregate tables. When switched to Trino-over-Iceberg, they experience: (a) 2-10x slower query response for dashboards due to Iceberg metadata overhead and lack of indexes; (b) Trino query planning delays of 1-10 minutes on large partitioned tables; (c) no equivalent to Teradata's aggregate join indexes or materialized views; (d) JDBC/ODBC driver differences causing subtle query translation issues. BI users declare the migration "broken" and revert to Teradata, undermining the entire project.

**Why it happens:**
Teams optimize for data engineering (ETL, storage, catalog) and treat BI as "just point it at the new endpoint." They do not benchmark actual dashboard queries against the new stack before cutting over BI users.

**How to avoid:**
- Benchmark the top 50 most-used Tableau/Power BI dashboards against Trino/Iceberg BEFORE announcing any BI migration.
- Implement a BI semantic layer (dbt metrics, Cube, or AtScale) that abstracts the query engine from BI tools. This provides a stable interface during migration and enables optimization without changing dashboards.
- Use Iceberg's hidden partitioning and partition evolution to optimize for common BI query patterns (date range filters, department filters).
- Pre-aggregate Gold-layer tables in Iceberg for the most common dashboard queries. These replace Teradata's aggregate join indexes.
- Consider keeping Teradata as the BI query engine during Phase 1-2, reading from Iceberg via OTF. Users keep their Teradata connection while data gradually moves to Iceberg. Switch BI to Trino only after performance parity is proven.
- Use Trino's query result caching and materialized views (limited but improving) to close the gap.

**Warning signs:**
- No dashboard performance benchmarking before BI cutover
- BI users report "slow dashboards" within first week of migration
- Tableau extracts that took 5 minutes now take 30+ minutes
- BI team was not consulted during architecture planning
- No semantic layer in the architecture

**Phase to address:**
Phase 3 (BI Migration). But Phase 1 must include BI benchmarking to set expectations and Phase 2 must build Gold-layer aggregates.

---

### Pitfall 8: FSDM Data Model Migration Creates an Unmaintainable Hybrid

**What goes wrong:**
The Teradata Financial Services Data Model (FSDM) covers 300+ subject areas with a meta-modeling approach designed for Teradata's columnar/MPP architecture. Teams attempt to migrate FSDM tables directly to Iceberg without rethinking the model for a lakehouse. Results: (a) FSDM's normalized structure creates excessive JOINs that perform poorly on Trino/Iceberg (no join indexes, no columnar co-location); (b) FSDM's meta-model patterns (generic attribute tables, type-code-driven polymorphism) generate massive small-file problems in Iceberg; (c) partial FSDM alignment means some tables follow the model and others don't, creating confusion about which naming conventions and structures apply; (d) trying to evolve FSDM toward medallion architecture creates a third pattern that coexists with the other two.

**Why it happens:**
FSDM is deeply embedded in Teradata-specific optimizations. Nobody fully understands which parts of the model are actively used vs. vestigial. The model documentation is Teradata-centric and does not translate to lakehouse concepts.

**How to avoid:**
- Do NOT attempt a big-bang data model redesign. Migrate FSDM tables to Iceberg as-is in Phase 1-2 (Bronze/Silver layer).
- Introduce medallion architecture as a LAYER on top, not a replacement: Bronze = raw ingestion (FSDM structure preserved), Silver = cleansed and conformed (FSDM joins resolved into wider denormalized tables), Gold = consumption-ready aggregates.
- Map which FSDM subject areas are actively queried by BI and downstream systems. Only those need Silver/Gold layer treatment initially.
- Accept that the data model will be "messy" during transition. Define clear naming conventions that distinguish FSDM-legacy tables from new medallion-layer tables.
- Do NOT rename or restructure FSDM tables until their downstream consumers (reports, ETL jobs) are fully migrated and validated.

**Warning signs:**
- Architecture team proposes a new data model before any data is migrated
- Nobody can articulate which FSDM subject areas are actively used
- Data model meetings generate disagreement about "the right way" without producing decisions
- Tables are being renamed during migration, breaking downstream consumers

**Phase to address:**
Phase 1 (establish medallion layering strategy). Phase 2 (Bronze migration preserving FSDM). Phase 3 (Silver/Gold layer construction on most-used subject areas).

---

### Pitfall 9: Snowflake Iceberg External Tables Are Not a Drop-In Replacement

**What goes wrong:**
Teams assume Snowflake can seamlessly read/write Iceberg external tables as if they were native Snowflake tables. Reality: (a) no Fail-safe storage for Iceberg tables; (b) no clustering support on externally managed tables; (c) no standard or append-only streams (insert-only streams only); (d) no replication capabilities; (e) no native schema evolution; (f) `uuid` and `fixed(L)` Iceberg data types cannot be written; (g) multi-statement transactions unsupported for external writes; (h) excessive position deletes can prevent table creation and refresh operations; (i) S3 bucket names cannot contain dots; (j) Snowflake shows approximately 20% performance penalty vs. native tables.

**Why it happens:**
Snowflake's marketing emphasizes Iceberg support without highlighting the many restrictions on externally managed tables. Teams design the architecture assuming Snowflake has full feature parity.

**How to avoid:**
- Define Snowflake's role precisely: read-only compute for specific workloads, or full DML participant?
- If Snowflake must write to Iceberg, test every DML pattern against externally managed tables. Validate that position delete accumulation is manageable.
- Do not use Snowflake features that are incompatible with Iceberg (clustering, standard streams, replication) in your architecture design.
- Consider whether Snowflake is still needed if Trino handles the same workloads. The project should explicitly decide: keep Snowflake (with known limitations) or retire it.
- If keeping Snowflake, use it for workloads where the 20% penalty is acceptable (ad-hoc analytics, data science) rather than latency-sensitive dashboards.

**Warning signs:**
- Architecture assumes Snowflake Iceberg external tables are feature-equivalent to native tables
- Snowflake users encounter "unsupported operation" errors during testing
- Snowflake contract renewal approaching without a clear strategy for its long-term role
- No testing of Snowflake-specific Iceberg limitations before architecture commit

**Phase to address:**
Phase 1 (Snowflake SWOT analysis is already flagged). Must be resolved before Phase 2 architecture solidifies.

---

### Pitfall 10: 40+ Engineer Team Parallelism Creates Integration Hell

**What goes wrong:**
With 40+ data engineers working in parallel on ETL migration, storage setup, catalog management, BI, and governance, integration failures multiply: (a) teams make incompatible schema decisions; (b) ETL jobs write to Iceberg with different partition strategies, file sizes, and naming conventions; (c) catalog entries proliferate without governance; (d) testing environments diverge from production; (e) "works on my laptop" failures when jobs reach shared infrastructure. A documented case: a financial services firm spent $8M migrating to a modern platform that worked perfectly, but three months later business teams still ran reports on the old system because nobody had been trained.

**Why it happens:**
Large teams are parallelized for speed but without sufficient coordination infrastructure. Technical standards are documented but not enforced. Change management focuses on technology, not people.

**How to avoid:**
- Establish a "Platform Team" (5-7 engineers) that owns the shared infrastructure (catalog, storage, CI/CD templates, monitoring). All other teams build on top of their standards.
- Create an Iceberg table creation policy that mandates: partition strategy, target file size, compaction schedule, naming conventions. Enforce via CI/CD pipeline validation.
- Implement a shared development environment that mirrors production topology. No local-only development for ETL jobs.
- Run weekly integration testing across all workstreams from Week 1.
- Assign "super-users" from each business domain as migration champions who bridge engineering and business.
- Create a communication cadence: daily standups within workstreams, weekly cross-workstream sync, monthly stakeholder demos.
- Train business users on new tools BEFORE cutting them over. Budget 2-4 weeks for hands-on training per business unit.

**Warning signs:**
- No shared development environment by end of Month 1
- Teams cannot explain how their work integrates with other workstreams
- Schema or partition strategy varies across tables created by different teams
- Business users first see the new platform on cutover day
- No platform/standards team exists; every team makes independent decisions

**Phase to address:**
Phase 0 (pre-migration setup). Team structure, standards, and coordination must be established before parallel workstreams begin.

---

### Pitfall 11: Timeline Underestimation -- 6-12 Months Is Aggressive for This Scope

**What goes wrong:**
The project scope includes: Teradata OTF validation, catalog selection, storage layer setup (S3 + on-prem), 300+ ETL job migration, BI semantic layer, AI semantic layer, governance/lineage, Snowflake strategy, data model evolution, and CI/CD pipeline. At 6 months, this is approximately 2 weeks per major workstream. Teams discover that Phase 1 validation alone takes 3-4 months due to catalog compatibility testing, performance benchmarking, and storage validation. The ETL migration of 300+ jobs takes 9-15 months even with 40 engineers (based on comparable enterprise migrations). The result: either the timeline extends to 18-24 months, or corners are cut on governance and validation.

**Why it happens:**
Leadership expectations are set based on vendor demos and case studies from organizations with simpler architectures. The hybrid Teradata/Trino/Snowflake requirement adds complexity that pure-cloud migrations do not face. 1.5 PB of data cannot be physically moved in weeks -- network bandwidth alone limits transfer rates.

**How to avoid:**
- Redefine "show value in 6-12 months" to mean: "Phase 1 validated, first 50 ETL jobs migrated, one BI workload running on lakehouse" -- not full migration complete.
- Plan for 18-24 months total with clear 3-month milestone gates.
- Phase 1 (Months 1-4): OTF feasibility, catalog decision, storage validation, first 10 ETL jobs, governance framework.
- Phase 2 (Months 5-12): ETL migration waves (50 jobs per quarter), BI prototype, Gold layer for top use cases.
- Phase 3 (Months 13-18): Full ETL migration, BI cutover, AI semantic layer, Snowflake decision.
- Phase 4 (Months 19-24): Teradata decommission planning, full governance, optimization.
- For the 1.5 PB data migration: calculate actual network bandwidth. At 500 Mbps dedicated, 1 PB takes approximately 8 months to transfer. Plan for incremental migration, not big-bang.

**Warning signs:**
- Project plan shows all workstreams completing in 6 months
- No explicit Phase 1 gate/go-no-go decision point
- Data migration bandwidth not calculated
- Leadership expects "done" at 12 months without defining what "done" means
- No contingency time in any workstream

**Phase to address:**
Phase 0 (project planning). Set expectations and milestone definitions before any technical work begins.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip table compaction automation | Faster initial deployment | Query degradation within weeks, potential death spiral at PB scale | Never -- compaction is not optional |
| Use Hive Metastore as catalog | Teradata compatibility | Lock contention at scale, no multi-table transactions, poor hybrid cloud support | Only as Phase 1 stopgap with documented migration plan |
| 1:1 DataStage-to-Python translation | Faster migration velocity | Technical debt from preserved anti-patterns, UDF performance overhead | Only for Tier 1 simple jobs |
| Skip parallel-run validation for ETL | Faster DataStage retirement | Undetected data quality differences, regulatory risk | Never for financial services |
| Keep MinIO deployment as-is | Avoid on-prem storage migration | Unpatched security vulnerabilities, no community support | Never -- plan replacement within 6 months |
| Let each team choose their own partition strategy | Team autonomy | Inconsistent query performance, compaction complexity, catalog sprawl | Never -- enforce standards |
| Defer lineage tooling to Phase 3 | Faster infrastructure work | Months of ungoverned data flows, regulatory exposure, lineage gaps impossible to backfill | Never for financial services |
| Point BI directly at Trino without semantic layer | Simpler architecture | Every dashboard change requires ETL changes, performance regressions, no abstraction | Only for technical users in early testing |

## Integration Gotchas

Common mistakes when connecting components of this architecture.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Teradata OTF to Iceberg on S3 | Assuming OTF query performance matches native Teradata | Benchmark with production-scale data. Budget 2-5x performance overhead. Use dedicated Compute Clusters. |
| Trino to Iceberg | Not configuring metadata caching; default settings cause repeated S3 metadata reads | Enable Trino's metadata cache. Configure `iceberg.metadata-cache-ttl`. Use catalog-level caching for frequently accessed tables. |
| Snowflake to Iceberg external tables | Using Snowflake features (clustering, streams, replication) that are unsupported on external Iceberg tables | Audit every Snowflake feature used in existing workloads against the Iceberg external table limitation list before migration. |
| Python ETL to Iceberg | Writing many small files per commit (one file per partition per job run) | Configure `write.target-file-size-bytes` to 256 MB minimum. Batch writes. Use Spark's `coalesce()` or `repartition()` before writing. |
| BI tools to Trino via JDBC | Tableau/Power BI sending unoptimized queries that bypass partition pruning | Use a semantic layer (dbt, Cube, AtScale) to push down filters. Validate that generated SQL uses partition columns in WHERE clauses. |
| On-prem to cloud Iceberg access | Assuming S3 and MinIO/alternative behave identically | Test specific S3 API calls used by Iceberg (atomic renames via conditional writes, multipart uploads, listing consistency) on both storage backends. |
| Mainframe to Python ETL | Assuming EBCDIC/packed decimal handling works out of the box in Python | Build and test COBOL copybook parsing, EBCDIC-to-UTF8 conversion, and packed decimal handling as dedicated libraries before ETL migration begins. |
| Multiple engines writing to same Iceberg table | Concurrent writes from Teradata OTF and Trino to the same table | Iceberg uses optimistic concurrency -- conflicting commits fail and retry. Design write ownership: one engine writes per table, others read only. |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No partition strategy on large tables | Full table scans on every query, Trino coordinator OOM | Partition by moderate-cardinality columns (day, month, region). Use Iceberg hidden partitioning. | Tables > 1 million records or > 10 GB |
| High-cardinality partitioning | Millions of single-file partitions, compaction cannot consolidate | Use `bucket()` transforms for high-cardinality columns. Limit to < 10,000 partitions per table. | Tables with > 50,000 unique partition values |
| Merge-on-Read (MOR) with many delete files | Queries spending hours merging delete files with data files | Compact position deletes with `rewrite-position-deletes`. Convert to Copy-on-Write for read-heavy tables. | > 10,000 delete files per table |
| Teradata OTF concurrent query load | CPU spikes to 100%, memory exhaustion on Primary Cluster | Dedicate Compute Clusters for OTF. Limit concurrent OTF queries. | > 10 concurrent OTF queries |
| Unoptimized Trino query planning | Planning stage takes 1-10 minutes on tables with large partition counts | Enable column statistics pruning. Reduce manifest file count via rewrite. Increase coordinator memory. | Tables with > 100,000 partitions or > 50,000 manifest files |
| BI extract jobs scanning full tables | Tableau extract refresh takes hours instead of minutes | Use incremental extracts. Partition tables by the date column used in extract filters. Pre-aggregate Gold layer tables. | Tables > 100 GB with daily full extracts |
| Write amplification from single-row updates | 4+ blob storage writes per row update (data file + manifest + manifest-list + metadata JSON) | Batch updates. Use MERGE operations. Avoid row-level updates on Iceberg where possible. | > 1,000 individual row updates per minute |
| Network bandwidth for 1.5 PB migration | Transfer taking months, blocking downstream work | Calculate bandwidth upfront. Use incremental/CDC migration. Consider AWS Snowball for initial bulk load. | > 100 TB at < 1 Gbps dedicated bandwidth |

## Security Mistakes

Domain-specific security issues for financial services lakehouse.

| Mistake | Risk | Prevention |
|---------|------|------------|
| No column-level access control on Iceberg tables | PII/financial data exposed to unauthorized users. Iceberg has NO built-in column masking, row filtering, or data redaction. | Implement access control at the query engine layer (Trino's security plugins, Snowflake's native RBAC). Do not rely on Iceberg format for security. |
| MinIO with unpatched CVEs | Known vulnerabilities in on-prem storage layer holding regulated financial data | Replace MinIO with actively maintained alternative. Apply all available patches until migration complete. |
| S3 bucket misconfiguration for Iceberg data | Iceberg data files publicly accessible or deletable by unauthorized principals | Use bucket policies with least-privilege. Enable versioning. Block public access. Separate IAM roles for read vs. write. |
| Lineage gaps during transition period | Cannot prove data provenance to regulators during audit. BCBS 239 violations. | Implement lineage tracking before any data flows through new path. No exceptions. |
| Credential sprawl across multi-engine access | AWS credentials, Teradata passwords, Snowflake keys stored inconsistently across 300+ Python ETL jobs | Use a secrets manager (AWS Secrets Manager, HashiCorp Vault). Never store credentials in code or config files. Implement credential vending via catalog (Polaris supports this). |
| No audit trail for schema changes | Cannot demonstrate who changed what and when for regulatory compliance | Log all schema evolution events. Use Iceberg's snapshot metadata for data change tracking. Implement DDL audit logging at catalog level. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Iceberg table migration:** Often missing compaction schedule, snapshot expiration policy, and orphan file cleanup -- verify all three are automated and running
- [ ] **ETL job migration:** Often missing error handling parity with DataStage -- verify retry logic, dead letter queues, and alerting match the original job's recovery behavior
- [ ] **ETL parallel-run validation:** Often missing edge case comparison -- verify NULL handling, date boundary conditions, empty result sets, and EBCDIC character edge cases are compared
- [ ] **Catalog setup:** Often missing concurrent write testing -- verify that Teradata OTF and Trino writing to the same catalog do not create phantom conflicts or metadata corruption
- [ ] **BI dashboard migration:** Often missing performance regression testing -- verify that every dashboard loads within 2x of its Teradata response time before declaring "migrated"
- [ ] **Governance/lineage:** Often missing column-level lineage -- verify that lineage tracks individual columns through transformations, not just table-to-table dependencies
- [ ] **Snowflake Iceberg integration:** Often missing limitation testing -- verify that all existing Snowflake features used by consumers work with Iceberg external tables (streams, clustering, time travel)
- [ ] **On-prem storage:** Often missing failover testing -- verify that Iceberg operations recover gracefully when on-prem storage has transient failures (network blips, disk failures)
- [ ] **CI/CD pipeline:** Often missing Iceberg-specific validation -- verify that deployed ETL jobs include table property settings (file size targets, partition specs) and do not create tables with default (bad) settings
- [ ] **Data model migration:** Often missing downstream impact analysis -- verify that every renamed or restructured table has ALL its consumers updated, not just the known ones

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| File explosion / small files | MEDIUM | Run emergency compaction on affected tables. Increase compaction cluster size temporarily. Implement automated monitoring/compaction going forward. |
| Catalog mismatch (Teradata vs Trino) | HIGH | Dual-catalog pattern with metadata sync. Or accept separate catalogs per engine and sync via ETL. |
| BI performance regression | MEDIUM | Keep Teradata as BI backend while building pre-aggregated Gold layer in Iceberg. Switch BI only after Gold layer benchmarks pass. |
| ETL data quality differences | HIGH | Halt migration for affected jobs. Run detailed row-level comparison. Fix Python logic. Extend parallel-run period. |
| MinIO security vulnerability | MEDIUM-HIGH | Emergency patching if available. Accelerate migration to alternative storage. Network-isolate MinIO cluster. |
| Governance/lineage audit failure | HIGH | Manual lineage documentation sprint. Temporary freeze on new migrations until lineage catches up. |
| Timeline overrun | MEDIUM | Redefine scope for next milestone. Push lower-priority workstreams to later phase. Protect Phase 1 gate decision quality. |
| Team coordination failure | MEDIUM | Introduce platform team if not present. Implement mandatory integration testing. Weekly architecture review. |
| FSDM model confusion | LOW-MEDIUM | Freeze model changes. Document current state as-is. Establish naming convention and enforce going forward. |
| Snowflake feature incompatibility | LOW | Document limitations. Redesign affected workloads to avoid unsupported features. Or move workload to Trino. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Catalog mismatch (Teradata/Trino/Snowflake) | Phase 1 (OTF Feasibility) | Cross-engine read/write test through single catalog succeeds |
| File explosion at scale | Phase 1 (establish pattern), Phase 2 (operationalize) | Automated compaction running on all tables, file size monitoring dashboard green |
| Teradata OTF performance cliff | Phase 1 (OTF Feasibility) | Performance benchmarks with 1+ TB tables documented, Compute Cluster allocated |
| MinIO end-of-life | Phase 1 (Storage Validation) | Alternative storage selected, PoC validated, migration plan documented |
| DataStage migration complexity | Phase 1 (catalog jobs), Phase 2 (migration waves) | Job complexity tier assessment complete, parallel-run validation passing for each wave |
| Governance/lineage gaps | Phase 1 (framework), Phase 2 (enforcement) | Every migrated job has column-level lineage in governance tool, audit team sign-off |
| BI performance regression | Phase 1 (benchmarks), Phase 3 (cutover) | Top 50 dashboards benchmarked against Trino, Gold layer pre-aggregates built |
| FSDM model migration | Phase 1 (strategy), Phase 2 (Bronze), Phase 3 (Silver/Gold) | Medallion layer naming convention documented, no FSDM tables renamed during Bronze migration |
| Snowflake limitations | Phase 1 (SWOT analysis) | All Snowflake Iceberg limitations tested, long-term role documented |
| Team coordination | Phase 0 (pre-migration) | Platform team staffed, shared standards published, development environment live |
| Timeline underestimation | Phase 0 (project planning) | Milestone definitions documented with explicit go/no-go criteria, leadership aligned on phased delivery |

## Sources

- [Teradata OTF General Limitations](https://docs.teradata.com/r/Enterprise_IntelliFlex_Lake_VMware/Teradata-Open-Table-Format-for-Apache-Iceberg-and-Delta-Lake-User-Guide/General-Limitations) -- Official Teradata documentation (HIGH confidence)
- [Teradata OTF Performance Guidelines](https://docs.teradata.com/r/Enterprise_IntelliFlex_Lake_VMware/Teradata-Open-Table-Format-for-Apache-Iceberg-and-Delta-Lake-User-Guide/Performance-Guidelines-and-Expectations/Guidelines-to-Improve-Java-OTF-Performance) -- Official Teradata documentation (HIGH confidence)
- [Teradata Open Table Formats Press Release](https://www.teradata.com/press-releases/2024/teradata-embraces-open-table-formats-iceberg) -- Teradata official (HIGH confidence)
- [Apache Iceberg Practical Limitations 2025](https://quesma.com/blog/apache-iceberg-practical-limitations-2025/) -- Quesma blog with documented benchmarks (MEDIUM confidence)
- [Apache Iceberg Production Anti-Patterns 2026](https://iomete.com/resources/blog/apache-iceberg-production-antipatterns-2026) -- IOMETE with detailed failure modes (MEDIUM-HIGH confidence)
- [Iceberg File Explosion Problem](https://www.starburst.io/blog/apache-iceberg-files/) -- Starburst engineering blog (HIGH confidence)
- [Trino Iceberg Planning Stage Performance Issue #26563](https://github.com/trinodb/trino/issues/26563) -- Trino GitHub (HIGH confidence)
- [Snowflake Iceberg Tables Documentation](https://docs.snowflake.com/en/user-guide/tables-iceberg) -- Snowflake official docs (HIGH confidence)
- [Snowflake Iceberg External Write Support GA](https://docs.snowflake.com/en/release-notes/2025/other/2025-10-17-iceberg-external-writes-cld-ga) -- Snowflake official (HIGH confidence)
- [MinIO Maintenance Mode](https://www.infoq.com/news/2025/12/minio-s3-api-alternatives/) -- InfoQ news report (HIGH confidence)
- [Replace MinIO with RustFS in Iceberg -- Issue #14638](https://github.com/apache/iceberg/issues/14638) -- Apache Iceberg GitHub (HIGH confidence)
- [Iceberg + MinIO S3 Signature Issue #13045](https://github.com/apache/iceberg/issues/13045) -- Apache Iceberg GitHub (HIGH confidence)
- [Iceberg Catalogs 2025](https://www.e6data.com/blog/iceberg-catalogs-2025-emerging-catalogs-modern-metadata-management) -- e6data with catalog comparison matrix (MEDIUM confidence)
- [2025 State of Apache Iceberg Ecosystem](https://datalakehousehub.com/blog/2026-02-state-of-the-apache-iceberg-ecosystem/) -- Survey results (MEDIUM confidence)
- [DataStage to PySpark Migration](https://medium.com/@one.step.analytics.on.data/my-first-data-engineering-project-phase-2-migrating-datastage-etl-jobs-to-pyspark-161a8b4e5f18) -- Enterprise case study (MEDIUM confidence)
- [BCBS 239 Data Lineage Compliance](https://www.ovaledge.com/blog/bcbs-239-data-lineage) -- Regulatory guidance (HIGH confidence)
- [Data Lineage in Financial Services](https://www.databahn.ai/blog/strengthening-compliance-and-trust-with-data-lineage-in-financial-services) -- Industry analysis (MEDIUM confidence)
- [Lakehouse Implementation Journey](https://wjaets.com/sites/default/files/fulltext_pdf/WJAETS-2025-0224.pdf) -- Academic paper with schema change statistics (MEDIUM confidence)
- [Iceberg Partitioning and Performance in Trino](https://www.starburst.io/blog/iceberg-partitioning-and-performance-optimizations-in-trino-partitioning/) -- Starburst engineering (HIGH confidence)
- [AWS Iceberg Compaction Best Practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/apache-iceberg-on-aws/best-practices-compaction.html) -- AWS official (HIGH confidence)
- [Enterprise In-Place Migration to Iceberg](https://aws.amazon.com/blogs/big-data/enterprise-scale-in-place-migration-to-apache-iceberg-implementation-guide/) -- AWS Big Data Blog (HIGH confidence)
- [RustFS GitHub](https://github.com/rustfs/rustfs) -- Direct source (HIGH confidence)
- [Teradata FSDM Overview](https://www.teradata.com/industries/financial-services/financial-services-data-model) -- Teradata official (HIGH confidence)

---
*Pitfalls research for: Enterprise Lakehouse Transformation (Financial Services, Teradata to Iceberg)*
*Researched: 2026-03-13*
