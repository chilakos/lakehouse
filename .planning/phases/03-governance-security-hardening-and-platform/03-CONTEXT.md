# Phase 3: Governance, Security Hardening, and Platform - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Production-grade security with column-level and row-level access controls via Apache Ranger, regulatory compliance lineage dashboards (BCBS 239 accuracy/completeness/timeliness), data classification and sensitivity labeling, data catalog for self-service discovery, business glossary accessible to business users, and centralized audit trail capturing all data access across Trino, Teradata, and Snowflake.

Requirements: GOVN-02, GOVN-03, GOVN-04, GOVN-05, SEC-01, SEC-02, SEC-03, SEC-04, PLAT-01, PLAT-03

</domain>

<decisions>
## Implementation Decisions

### Access Control Model
- Apache Ranger for Trino column-level masking and row-level filtering
- Engine-native masking for Teradata (view-based) and Snowflake (dynamic masking policies) to ensure consistent security across all three engines
- Row-level security via business-unit attribute filtering: rows tagged with business_unit column, Ranger policies filter based on user's BU membership from LDAP groups
- Tag-driven data classification with sensitivity levels: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED. Masking rules keyed to tags, not specific columns — scales as new tables are onboarded
- Nested identity mapping: AD groups define team membership → Ranger roles define data access policies. One AD group can map to multiple Ranger roles. Decouples identity management from data policy management
- Existing Phase 1 file-based RBAC (rules.json) replaced by Ranger policies for production

### Regulatory Lineage Dashboards
- Full lineage visualization with data quality overlay: not just WHERE data came from but HOW HEALTHY it was at each transformation step
- BCBS 239 focus on the big three principles: Accuracy (quality scores per node), Completeness (no missing sources in lineage chain), Timeliness (SLA tracking per pipeline)
- Dual format: interactive Grafana dashboards for day-to-day compliance monitoring + scheduled PDF/HTML export for audit evidence archives
- Lineage scope: full instrumented lineage for lakehouse (Trino/Iceberg/Airflow) + manually-registered lineage stubs for legacy systems (Teradata, Snowflake) to show the connection without blocking on legacy instrumentation
- Build on existing Marquez/OpenLineage infrastructure from Phase 2

### Data Catalog & Glossary
- Catalog platform: Claude's discretion — research phase determines best fit (DataHub, OpenMetadata, or other) based on Iceberg/Trino/Airflow ecosystem compatibility
- Business glossary: collaborative wiki-style — business users propose terms, data stewards review and approve. Scales faster than steward-only curation
- Data freshness tracking (PLAT-03): freshness timeline graph + SLA badges per table. Shows update history patterns and committed freshness windows. Traffic-light status (green/yellow/red) for quick glance
- Deep-linked integration between Grafana and catalog: click a table in Grafana → opens catalog page; click lineage in catalog → opens Grafana dashboard. Each tool does what it's good at, connected seamlessly

### Audit Trail Strategy
- Per-engine native audit logging + ETL aggregation: Trino event listener, Teradata DBQL, Snowflake ACCESS_HISTORY → aggregated into common schema for cross-engine reporting
- Full column-level access auditing: user, timestamp, query text, tables accessed, columns accessed, rows returned, data volume scanned, masked vs unmasked access
- Retention: 3 years in searchable hot storage (Elasticsearch or Athena), 7 years total in cold archive (S3 Glacier). Lifecycle tiering for cost management
- Batch daily anomaly reports: daily analysis flagging suspicious patterns (bulk downloads, after-hours access, unusual restricted table access) for security team review. Real-time alerting deferred to future enhancement

### Claude's Discretion
- Data catalog platform selection (DataHub vs OpenMetadata vs other)
- Ranger deployment topology and HA configuration
- Audit log storage technology (Elasticsearch vs S3+Athena vs dedicated audit DB)
- Grafana dashboard layout and panel design for compliance views
- PDF/HTML report generation tooling
- Legacy lineage stub registration approach
- Anomaly detection heuristics for daily audit reports

</decisions>

<specifics>
## Specific Ideas

- Tag-driven classification (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED) is critical for scaling to 300+ sources — column-by-column masking rules won't scale
- BCBS 239 dashboards must be compelling enough for auditors — focus on the big three (accuracy, completeness, timeliness) rather than trying to cover all 11 principles in Phase 3
- Legacy lineage stubs give the "full picture" view without requiring Teradata/Snowflake instrumentation — a practical compromise for Phase 3 timeline
- Business glossary should be populated with terms from the existing FSDM (Financial Services Data Model) as a starting point
- Audit column-level access is essential for PII compliance — need to prove who accessed what specific sensitive columns

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `etl/src/lineage/config.py`: OpenLineage Spark config — already emitting lineage to Marquez. Extend for classification metadata
- `infra/docker/trino/etc/access-control/rules.json`: Phase 1 file-based RBAC rules — reference for role definitions, to be replaced by Ranger policies
- `etl/tests/integration/test_rbac.py`: RBAC rule validation tests — extend to test Ranger policies
- `infra/docker/grafana/dashboards/pipeline_observability.json`: Phase 2 Grafana dashboard — template for compliance dashboards
- `infra/docker/grafana/provisioning/`: Grafana auto-provisioning — reuse pattern for compliance dashboards
- `etl/src/quality/scanner.py`: Soda Core scanner — quality scores can feed into lineage quality overlay
- `etl/src/inventory/catalog.py`: Job inventory module — data for catalog population

### Established Patterns
- Docker Compose for local dev: Extend with Ranger, catalog platform, audit store
- Grafana + Prometheus for observability: Reuse for compliance dashboards
- OpenLineage → Marquez for lineage: Build compliance views on top of existing lineage data
- Airflow DAG pattern: Use for audit log aggregation ETL
- Sensitivity tags map to Ranger tag-based policies (Ranger's native capability)

### Integration Points
- Ranger → Trino: Ranger Trino plugin for policy enforcement
- Ranger → LDAP/AD: Group sync for role mapping
- Marquez API → Grafana: Lineage data for compliance dashboards
- Catalog platform → Marquez: Lineage integration
- Catalog platform → Grafana: Deep-link integration
- Trino event listener → Audit store: Query audit capture
- Audit ETL DAG → Common audit schema: Cross-engine aggregation

</code_context>

<deferred>
## Deferred Ideas

- Real-time anomaly alerting on audit events — batch daily reports for Phase 3, real-time enhancement later
- Full BCBS 239 coverage (all 11 principles) — Phase 3 covers big three, remaining principles in future enhancement
- Nessie branching for schema governance — explore after Ranger is operational
- Data contracts between producer and consumer domains — v2 scope (PLAT-V2-03)

</deferred>

---

*Phase: 03-governance-security-hardening-and-platform*
*Context gathered: 2026-03-13*
