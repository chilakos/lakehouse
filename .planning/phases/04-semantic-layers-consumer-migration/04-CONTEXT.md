# Phase 4: Semantic Layers and Consumer Migration - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

BI tools (Tableau, Power BI) query the lakehouse through a unified semantic layer with performance parity to direct Teradata queries. NL-to-SQL deployed on curated pilot domains (trading, risk exposure) using BI semantic layer definitions for accuracy. Unified metric definitions serve consistent values across all consumers.

Requirements: BISEM-01, BISEM-02, BISEM-03, BISEM-04, AISEM-01, AISEM-02, AISEM-03

</domain>

<decisions>
## Implementation Decisions

### Semantic Layer Platform
- Platform selection is Claude's discretion — research phase evaluates dbt Semantic Layer vs Cube vs AtScale against the Trino/Iceberg/Nessie stack
- Metric definitions authored as code (YAML/SQL) in the mono-repo, versioned in Git, changes go through PR review
- Data engineers author definitions, business stakeholders review via PR comments/approval
- Security passes through to Trino — Ranger column-masking and row-level filtering enforced at the query layer, no duplicate security logic in the semantic layer
- Pilot domains: trading metrics + risk exposure (two domains to validate cross-domain metric consistency)

### BI Migration Approach
- Phased migration by dashboard — migrate one dashboard/workbook at a time, run old (Teradata direct) and new (lakehouse semantic layer) side-by-side, validate numbers match, then cut over
- BI connector approach is Claude's discretion — depends on the semantic layer platform chosen (Trino JDBC/ODBC direct vs semantic layer API)
- Performance validation: pick 5-10 representative high-traffic dashboards, extract their SQL queries, run against both Teradata and lakehouse, compare latency/throughput
- Performance thresholds are case-by-case: interactive dashboards must match Teradata parity; scheduled reports/extracts can tolerate up to 2-3x slower

### NL-to-SQL Architecture
- Build custom NL-to-SQL using LLM with semantic layer metric definitions as context (not a vendor product)
- LLM selection is Claude's discretion — research evaluates accuracy vs data residency trade-offs for financial services (Claude API vs self-hosted open model)
- Pilot domains: same as BI pilot (trading + risk exposure) — proves AISEM-02 requirement that NL-to-SQL leverages BI semantic definitions
- Accuracy thresholds (AISEM-03): tiered — 90% correct on simple queries (single-domain lookups), 70% correct on complex queries (multi-join analytics)
- NL-to-SQL must use the same metric definitions that serve Tableau/Power BI — business terms resolve to identical calculations

### Metric Governance
- Data engineering owns metric definitions, business reviews and approves via PR process
- Consistency enforcement: single-source architecture (both Tableau and Power BI query the same semantic layer endpoint/views) plus automated cross-tool testing as a safety net
- Metric definitions link to OpenMetadata business glossary (Phase 3) — e.g., 'total_notional' references the glossary definition of 'notional value'. FSDM terms already populated
- Metric changes deploy through standard CI/CD pipeline (PR → dev → staging → prod) — same rigor as ETL code

### Claude's Discretion
- Semantic layer platform selection (dbt Semantic Layer vs Cube vs AtScale vs other)
- BI connector approach (Trino JDBC/ODBC vs semantic layer API)
- LLM selection for NL-to-SQL (Claude API vs self-hosted)
- NL-to-SQL prompt engineering and evaluation framework design
- Risk exposure Gold pipeline design (new pipeline needed for second pilot domain)
- Cross-tool automated testing framework implementation
- Glossary-to-metric linking mechanism

</decisions>

<specifics>
## Specific Ideas

- Trading metrics Gold table already exists (`lakehouse.gold.trading_metrics`) — semantic layer builds on this immediately
- AISEM-02 is the critical integration requirement: NL-to-SQL must resolve business terms to the same calculations as BI dashboards. Same pilot domains prove this end-to-end
- SWOT analyses requested by leadership (PROJECT.md) include BI Semantic Layer and AI Semantic Layer — this phase should produce both
- The 40+ engineer team uses Git-native workflows throughout (Phase 1 decision) — metric authoring must follow the same pattern
- Phased dashboard migration with side-by-side validation mirrors the Phase 2 parallel-run validation approach for ETL — regulated environment demands provable equivalence

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `etl/src/pipelines/gold/trading_metrics.py`: TradingMetricsGoldPipeline — pre-aggregated trading metrics ready for semantic layer consumption
- `etl/src/pipelines/base.py`: BasePipeline ABC with MedallionLayer enum — extend for risk exposure Gold pipeline
- `etl/src/iceberg_utils/catalog.py`: SparkSession factory with Nessie REST catalog — reuse for new Gold pipelines
- `etl/src/iceberg_utils/trino.py`: Trino query utilities — reuse for BI performance benchmarking
- `etl/src/quality/scanner.py`: Soda Core scanner — quality scores feed into metric validation
- `infra/docker/grafana/dashboards/`: Four existing Grafana dashboards — template for BI performance monitoring
- `infra/docker/openmetadata/`: OpenMetadata deployment — integration point for glossary linking

### Established Patterns
- TYPE_CHECKING pattern for lazy PySpark imports — continue for new Gold pipelines
- Decimal type for financial precision — enforce in all semantic layer metric calculations
- REST catalog type for Nessie — all Spark sessions must follow this
- Docker Compose for local dev — extend with semantic layer service
- GitHub Actions CI/CD — extend with metric definition validation and cross-tool tests
- Soda Core for data quality — reuse for metric value reconciliation

### Integration Points
- Trino (JDBC/ODBC): Primary query endpoint for BI tools, already configured with Iceberg catalog
- Nessie REST catalog: All Iceberg table operations, semantic layer reads from this
- Ranger: Column-masking and row-level filtering — semantic layer queries inherit these policies
- OpenMetadata: Business glossary for metric-to-term linking
- Grafana: Existing dashboards, add BI performance monitoring
- Airflow: Orchestrate metric materialization and quality checks
- GitHub Actions: CI/CD for metric definitions alongside ETL code

</code_context>

<deferred>
## Deferred Ideas

- NL-to-SQL for all data domains — REQUIREMENTS.md explicitly scopes to pilot domains; expand incrementally after accuracy is proven
- Self-service SQL workspace for analysts (PLAT-V2-04) — v2 scope
- Real-time metric updates (streaming) — batch-first per REQUIREMENTS.md
- Data contracts between metric producers and consumers (PLAT-V2-03) — v2 scope

</deferred>

---

*Phase: 04-semantic-layers-consumer-migration*
*Context gathered: 2026-03-13*
