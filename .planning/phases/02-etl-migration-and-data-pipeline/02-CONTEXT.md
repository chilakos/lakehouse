# Phase 2: ETL Migration and Data Pipeline - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Python ETL framework replaces DataStage pilot jobs. Medallion architecture (Bronze/Silver/Gold) implemented with Iceberg tables on Nessie catalog. Data quality enforced on every pipeline. End-to-end lineage captured via OpenLineage. Airflow orchestrates all workflows. Pipeline observability dashboard operational. DataStage job inventory cataloged with complexity classification.

Requirements: FNDTN-07, ETL-01 through ETL-07, QUAL-01 through QUAL-04, GOVN-01, PLAT-02

</domain>

<decisions>
## Implementation Decisions

### Medallion Architecture
- Bronze layer: Raw-as-is with metadata columns (source_system, ingestion_ts, batch_id). No transformation at ingestion — maximum traceability, no data loss
- Namespace convention: Layer-based namespaces — lakehouse.bronze.{table}, lakehouse.silver.{table}, lakehouse.gold.{table}
- Silver layer: Cleaned & joined entities — deduplicate, join related sources, apply business rules. Entity-centric (one table per business entity) without strict Kimball dimensional modeling
- Gold layer: Both pre-aggregated metrics for BI AND curated entity views for specific consumers (regulatory reports, trading desk views)

### DataStage Pilot Selection
- Representative mix of 5-10 jobs across complexity levels: 2-3 simple (single source, basic transform), 3-4 medium (multi-source joins, lookups), 1-2 complex (mainframe, COBOL, multi-step)
- Mainframe connectivity: DataStage handles it today — Python needs to replicate COBOL copybook parsing, EBCDIC conversion, and DB2 z/OS JDBC. Known hard problem, high-risk area
- Migration validation: Parallel run with comparison — run both DataStage and Python pipelines simultaneously, compare outputs (row counts, checksums, aggregates). Gold standard validation
- Job inventory (ETL-07): Full structured catalog with complexity classification (simple/medium/complex), source systems, dependencies, estimated effort per job. Needed for planning full v2 migration

### Orchestration & Observability
- DAG design: Hybrid — source-specific DAGs for Bronze→Silver, separate Gold DAGs for cross-source aggregations. Balances ownership with cross-cutting concerns
- Failure handling: Retry then alert — automatic retries (3x with backoff) on transient failures, alert only after retries exhausted. Reduces noise from temporary issues
- Observability dashboard (PLAT-02): Combined ops + data view — operational metrics (SLA compliance, failure rates, durations) AND data metrics (freshness, quality scores, row counts)
- Incremental loading (ETL-05): CDC where available (DB2 logs, Debezium), fall back to watermark-based for sources without CDC support. Catches updates/deletes where possible

### Data Quality & Lineage
- Quality check placement: Gate between layers — checks run at Bronze→Silver and Silver→Gold boundaries. Failed checks block promotion to next layer
- Failure behavior: Configurable per check — critical checks (schema validation, null primary keys) are hard blocks; advisory checks (null rates, outliers) are soft alerts
- DQ framework: Claude's discretion — research phase determines best fit (Great Expectations, Soda Core, or custom) based on PySpark + Iceberg + Airflow ecosystem compatibility
- OpenLineage integration: Both Airflow plugin (task-level lineage) + Spark agent (column-level detail). Most complete lineage picture for GOVN-01 source-to-consumption requirement

### Claude's Discretion
- DQ framework selection (Great Expectations vs Soda Core vs custom)
- Airflow deployment method and configuration
- Spark job resource allocation and tuning
- OpenLineage backend (Marquez vs other)
- ETL framework base class / abstraction design
- Standardized ETL patterns (ETL-06) structure and documentation format

</decisions>

<specifics>
## Specific Ideas

- Parallel run validation is critical — this is a regulated financial services environment, so data accuracy must be provably equivalent before DataStage retirement
- Mainframe COBOL copybook parsing is the highest-risk technical challenge — validate early in the phase
- The 40+ engineer team needs standardized, reusable ETL patterns (ETL-06) they can onboard to quickly — framework must be opinionated enough to enforce consistency
- OpenLineage lineage must be end-to-end (source to consumption layer) for GOVN-01 — partial lineage won't satisfy regulatory requirements
- Job inventory serves dual purpose: Phase 2 pilot selection AND Phase v2 full migration planning

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `etl/src/iceberg_utils/catalog.py`: SparkSession factory with Nessie REST catalog config — reuse for all Bronze/Silver/Gold writes
- `etl/src/iceberg_utils/maintenance.py`: Iceberg table maintenance (compaction, snapshot expiration) — schedule via Airflow
- `etl/src/iceberg_utils/trino.py`: Trino query utilities — reuse for Gold layer validation and cross-engine consistency checks
- `etl/src/synthetic/generators.py`: Financial data generators (trades, positions, risk metrics) — extend for integration testing
- `etl/src/config/settings.py`: Environment-aware Settings dataclass — extend with Airflow and DQ config

### Established Patterns
- TYPE_CHECKING pattern for lazy PySpark imports (catalog.py) — continue for all Spark-dependent modules
- Isolated random.Random(seed) for deterministic test data — maintain for reproducible pipeline tests
- REST catalog type for Nessie (not Nessie-specific) — all new Spark sessions must follow this
- Decimal type for financial precision — enforce in all Bronze→Silver→Gold transforms

### Integration Points
- Nessie REST catalog: All Iceberg table operations go through Nessie REST endpoint
- Docker Compose: Local dev environment for Spark/Nessie/MinIO/Trino — extend with Airflow
- GitHub Actions CI/CD: Existing test/deploy workflows — add DAG validation and quality checks
- Terraform modules: Infrastructure for Nessie/Trino/S3 — add Airflow infrastructure

</code_context>

<deferred>
## Deferred Ideas

- Nessie branching for ETL schema migrations — explore after basic medallion is operational
- Real-time streaming ingestion (Kafka/Flink) — explicitly out of scope per REQUIREMENTS.md
- Full DataStage retirement (all 300+ jobs) — v2 scope, Phase 2 proves the framework with 5-10 pilots
- Data mesh domain ownership model — v2 scope per REQUIREMENTS.md

</deferred>

---

*Phase: 02-etl-migration-and-data-pipeline*
*Context gathered: 2026-03-13*
