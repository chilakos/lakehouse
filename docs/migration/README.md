# Migration Overview

This folder documents the strategy and operational playbooks for migrating RBC's
existing data estate to the Lakehouse architecture.

---

## Current State (What We Are Migrating From)

| Platform | Role | Size | Status |
|---|---|---|---|
| Teradata EDW | FSDM Silver base tables + materialized view Gold layer | ~800 TB | Active — migrating |
| Cloudera EDL | Hive external tables + HDFS raw data + shadow copies of Teradata | ~400 TB | Active — migrating + deprecating |
| Snowflake | Cloud DW, shadow copies | ~300 TB | Active — deprecating |
| IBM DataStage | ETL orchestration — 12,000+ jobs | N/A | Active — rewriting to Python |

**Total data under management:** ~1.5 PB across 300+ source systems

---

## Target State (What We Are Migrating To)

| Medallion Layer | Format | Catalog | Query Engine | Governance |
|---|---|---|---|---|
| Bronze | Apache Iceberg V2 | Nessie | Trino | Apache Ranger |
| Silver | Apache Iceberg V2 | Nessie | Trino | Apache Ranger |
| Gold | Apache Iceberg V2 | Nessie | Trino + Cube | Apache Ranger |
| AI Layer | Iceberg (Gold) + Teradata Vector Store | Nessie | Trino / Cube / Bedrock | Apache Ranger |

**Key constraint:** Trino is the mandatory query gateway for all Iceberg access.
No direct S3, OTF bypass, or raw client library reads in production. See ADR-002.

---

## Migration Playbooks

| Document | Covers |
|---|---|
| [teradata-to-iceberg.md](teradata-to-iceberg.md) | Dual-write pattern, type mapping, SCD handling, cutover process |
| [materialized-view-decomposition.md](materialized-view-decomposition.md) | Decomposing Teradata MVs into Gold Iceberg tables and Cube metrics |
| [cloudera-hive-to-iceberg.md](cloudera-hive-to-iceberg.md) | Hive table registration, HDFS data migration, shadow copy deprecation |
| [acceldata-odp-migration-plan.md](acceldata-odp-migration-plan.md) | Cloudera CDP → Acceldata ODP migration plan. Path comparison (in-place / sidecar / forklift), workload mix risk, ODP vs Databricks framing, Cloudera contract-driven timeline. |
| [acceldata-odp-poc-plan.md](acceldata-odp-poc-plan.md) | Zero-cost POC plan for ODP validation before vendor engagement. CDP 7.1.9 SP1 CHF 10 → ODP 3.3.6.x version mapping, Impala and Spark 2.4.8 pre-migration workstreams, GitHub patch-delta inspection. |

---

## Migration Sequencing Principles

1. **Orphan analysis first.** Query logs must confirm activity before any table is
   migrated. Inactive tables are retired, not migrated.

2. **Domain-complete migration.** Migrate all tables in a domain together, never
   cherry-pick individual tables. Cross-domain joins fail silently if source tables
   are on different platforms.

3. **Pilot on Customer 360.** The first full domain migration (Phase 1) is Customer 360
   — well-understood, high-value for Borealis/AI use cases, and has a clear owner.

4. **Shadow copies die, they don't migrate.** Cloudera shadow copies of Teradata data
   are deprecated once the Iceberg Gold layer is live. They are never migrated to Iceberg.

5. **Dual-write before cutover.** No consumer is moved until the Iceberg table has been
   running in shadow mode (dual-write) for a minimum of 30 days with continuous parity
   validation.

6. **Trino gateway from day one.** New Iceberg tables are Trino-only from the moment
   they are registered in Nessie. No exceptions during the migration period.

---

## Phase Gates

| Phase | Exit criteria |
|---|---|
| Phase 0 | Dual-write infrastructure live, Nessie branching validated, orphan analysis complete |
| Phase 1 | Customer 360 domain: all Silver + Gold tables live in Iceberg, all consumers migrated, 60 days zero P1 |
| Phase 2 | 5 additional domains complete, DataStage velocity benchmark established |
| Phase 3 | All active domains migrated, DataStage job count < 1,000 |
| Phase 4 | Teradata read-only, license reduction agreed with Procurement |
| Phase 5 | Teradata decommissioned |

---

## Open Questions

> ⚠️ Direct Teradata consumer survey required before Phase 1. Teams querying Teradata
> outside of OBIEE/Tableau are not catalogued.

> ⚠️ DataStage job velocity estimate required. AI-assisted migration (Claude Code /batch)
> will be benchmarked in Phase 0.

> ⚠️ Procurement engagement required on dual-write storage cost increase during
> transition.
| [snowflake-deprecation.md](snowflake-deprecation.md) | Why Snowflake is deprecated not migrated, the Ranger bypass gap, deprecation process |
| [databricks-architecture-review.md](databricks-architecture-review.md) | Full Databricks/Unity Catalog evaluation — why it is not adopted |
