# Lakehouse Architecture Transformation

## What This Is

A data architecture transformation converting a legacy Teradata/DataStage data warehouse into a modern lakehouse built on Apache Iceberg and Trino. The platform serves a financial services organization with 1.5 PB of data across 300+ sources, supporting both cloud (AWS S3) and on-premises (MinIO S3) consumers with BI and AI semantic layers. This is a feasibility-first approach — keeping Teradata with Open Table Format (OTF) to validate Iceberg/Trino before committing to full migration.

## Core Value

A single, governed copy of data in Iceberg format that every consumer — Teradata, Trino, Snowflake, BI tools, and AI — can access without creating additional copies.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

- [ ] Teradata OTF integration with Iceberg tables on S3/MinIO
- [ ] Trino query engine reading/writing Iceberg tables alongside Teradata
- [ ] Iceberg catalog supporting both cloud (AWS S3) and on-prem (MinIO)
- [ ] Snowflake accessing Iceberg tables via external tables (compute-only role)
- [ ] Python ETL framework replacing DataStage (full retirement)
- [ ] BI semantic layer serving Tableau and Power BI
- [ ] AI semantic layer enabling NL-to-SQL for business users
- [ ] GitHub-based CI/CD pipeline for all ETL and infrastructure code
- [ ] Data model strategy evolving from partial FSDM alignment
- [ ] Support for 250+ internal and 50+ external data sources
- [ ] Hybrid cloud/on-prem consumer access pattern

### Out of Scope

- Full Teradata decommission — this phase validates OTF/Iceberg feasibility first
- Real-time streaming ingestion — batch ETL migration is the priority
- Cloudera retention — being replaced by Iceberg/Trino
- New data model from scratch — evolving from existing FSDM, not rebuilding

## Context

**Current Architecture:**
- **Data Warehouse:** Teradata (1.5 PB), partially aligned to Teradata Financial Services Data Model (FSDM)
- **ETL:** IBM DataStage, primarily pulling from mainframe sources
- **Data Lake:** Cloudera (legacy, being retired)
- **Data Hubs:** Snowflake (contains exported copies from Teradata/Cloudera)
- **BI Consumers:** Tableau and Power BI querying Teradata directly
- **Sources:** 250+ internal, 50+ external — mainframe is the primary upstream system

**Key Problems:**
1. **Data duplication:** Same data copied across Teradata → Cloudera → Snowflake with no single source of truth
2. **Cost & complexity:** Maintaining 4 platforms (Teradata, DataStage, Cloudera, Snowflake) is expensive and fragile
3. **Modernization gap:** Current stack can't serve AI/ML workloads or modern query patterns

**Target Architecture:**
- Teradata with OTF reads/writes Iceberg tables on object storage
- Trino provides open-source query access to the same Iceberg tables
- Snowflake becomes optional compute over Iceberg external tables
- Python ETL replaces all DataStage jobs
- Single copy of data in Iceberg format on S3 (cloud) and MinIO (on-prem)

**Storage:**
- AWS S3 for cloud workloads
- MinIO (S3-compatible) for on-premises workloads
- Both accessible via same Iceberg catalog

## Constraints

- **Timeline:** 6-12 months to show value — phased approach required
- **Data Volume:** 1.5 PB in Teradata — migration strategy must handle scale
- **Regulatory:** Financial services — data governance, lineage, and audit trails are non-negotiable
- **Mainframe Dependency:** Primary source systems are mainframe-based, connectivity must be maintained
- **Team Size:** 40+ data engineers available for parallel workstreams
- **Existing Investments:** Teradata and Snowflake contracts likely still active — architecture must coexist during transition
- **FSDM:** Partially followed today — any model evolution must be backwards-compatible during transition

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep Teradata with OTF as Phase 1 | Validates Iceberg feasibility without big-bang migration risk | — Pending |
| Full DataStage retirement to Python | Modern, testable, CI/CD-friendly ETL | — Pending |
| Iceberg as Open Table Format | Industry standard, multi-engine support (Teradata, Trino, Snowflake) | — Pending |
| AWS S3 + MinIO for hybrid storage | S3 API compatibility enables single Iceberg catalog pattern | — Pending |
| Iceberg catalog choice | SWOT analysis needed — Glue vs Nessie vs HMS vs Polaris | — Pending |
| Data model evolution strategy | SWOT analysis needed — keep FSDM vs evolve vs hybrid | — Pending |
| Snowflake long-term role | SWOT analysis needed — retire vs Iceberg external tables | — Pending |

## SWOT Analyses Required

Leadership needs SWOT documentation for:
1. **Iceberg Catalog Choice** — Glue vs Nessie vs Hive Metastore vs Polaris
2. **Snowflake Strategy** — Retire vs Keep as Iceberg compute vs Maintain as-is
3. **DataStage Migration Approach** — Big-bang vs phased vs parallel-run
4. **Data Model Strategy** — Keep FSDM vs evolve incrementally vs new medallion model
5. **BI Semantic Layer** — Direct Trino/Teradata access vs dedicated semantic layer (dbt, AtScale, Cube)
6. **AI Semantic Layer** — Build vs buy for NL-to-SQL capability

---
*Last updated: 2026-03-13 after initialization*
