# ADR-003: Teradata Decoupling Strategy — Dual-Write Migration to Iceberg

**Status:** Accepted  
**Date:** March 2026  
**Author:** George Chilakos, VP Enterprise Data  
**Reviewers:** Pending — Vinh (manager), EDW Domain Lead, Platform Engineering

---

## Context

RBC's current EDW runs on Teradata (~800 TB), with data organized according to the
Financial Services Data Model (FSDM). The Lakehouse target state replaces this with
Apache Iceberg V2 tables governed by Nessie, queryable via Trino.

The Teradata estate contains:
- **FSDM-conformed base tables** — the current "Silver" equivalent
- **Materialized views** — pre-computed aggregations serving BI tools (OBIEE, Tableau)
  and DataStage jobs; the current "Gold" equivalent
- **No stored procedures** — business logic lives in DataStage ETL jobs, simplifying migration

The migration must be executed without a big-bang cutover. RBC cannot take a planned
outage on the EDW. The migration must be:
- Reversible at any stage
- Validated before consumers are moved
- Incremental — table by table, domain by domain

---

## Decision

**The dual-write shadow table pattern is the chosen strategy for decoupling Teradata.**

### Core pattern

For each Teradata table being migrated:

1. **Shadow phase**: Python ETL pipeline writes to both Teradata (existing) and Iceberg
   (new) simultaneously. Nessie catalogs the Iceberg table immediately. No consumers
   move. Parity is validated continuously.

2. **Consumer migration phase**: Read consumers (Tableau, Power BI, Trino ad-hoc,
   Borealis) are redirected to the Iceberg table one at a time. Producers still write
   to both. Each consumer is validated before the next is moved.

3. **Cutover phase**: Once all consumers are confirmed on Iceberg, dual-write is dropped.
   Teradata becomes read-only for that table. A defined sunset date is set.

4. **Decommission**: Teradata table is dropped. Disk reclaimed. Teradata license cost
   reduced.

### Nessie branching for safe cutover

Nessie's Git-like branching model provides a rollback mechanism that traditional
migrations lack:

```
main branch         → production consumers read from here
migration/silver-X  → new Iceberg table written here during shadow phase
                      consumers validated against this branch
                      merged to main only when parity confirmed
```

If validation fails, the branch is abandoned. No production impact.

### Sequencing — what migrates first

Migration priority is determined by:

1. **Consumer overlap with OBIEE→Power BI migration** — tables feeding reports already
   scheduled for migration get their underlying Iceberg table created first
2. **DataStage job complexity** — simpler jobs (single-source extracts) migrate before
   complex multi-source jobs
3. **Query frequency** — tables with >90-day query inactivity in Teradata logs are
   candidates for retirement, not migration (see below)
4. **Domain isolation** — migrate complete domains (e.g. all of Customer 360) rather
   than cherry-picking tables, to avoid cross-domain join failures

### Orphan analysis — retire before migrating

Before migrating any table, a query log analysis must confirm it has been accessed
in the last 90 days. Experience from similar migrations indicates 20-35% of tables
in a long-running EDW are orphaned artefacts.

```sql
-- Run against Teradata query log (DBQL)
SELECT TableName, MAX(CollectTimeStamp) AS last_accessed
FROM DBC.DBQLObjTbl
WHERE DatabaseName = 'PROD_SILVER'
GROUP BY TableName
HAVING MAX(CollectTimeStamp) < CURRENT_DATE - 90
ORDER BY last_accessed;
```

Tables with no activity in 90 days → **retirement candidate**, not migration.
Tables with no activity in 180 days → **retire, do not migrate**.

---

## Materialized Views → Gold Layer

Teradata materialized views are the current Gold layer equivalent. They do not migrate
as-is — they are **decomposed** into their constituent parts.

### Mapping

| Materialized view type | Target |
|---|---|
| Heavy aggregate (SUM, COUNT, GROUP BY) | Physical Gold Iceberg table |
| Thin semantic (calculated ratio, derived KPI) | Cube YAML metric definition |
| Point-in-time snapshot (end-of-day, month-end) | Gold Iceberg table with `snapshot_date` partition |
| Cross-domain join materializing FSDM relationships | Decomposed: source tables to Silver Iceberg, join logic to Python pipeline |

See `docs/migration/materialized-view-decomposition.md` for the full decomposition
methodology.

### The join complexity problem

Teradata materialized views with large numbers of table joins (100+) are not monolithic
objects to be translated — they are **encoded business processes**. The correct approach
is to decompose them into a dependency graph:

```
Complex MV (N table joins)
    → dependency analysis
    → identify Silver-level source tables (already in Iceberg Silver)
    → identify lookup/reference tables (become Silver dimension tables)
    → identify intermediate aggregations (become intermediate Gold tables)
    → the final aggregation is the actual Gold table
```

Most join complexity dissolves once Silver is clean and normalized, because the joins
exist precisely to compensate for the fragmentation that Silver eliminates.

### AI-assisted migration

Given the volume (12,000 DataStage jobs, hundreds of materialized views), manual
rewriting is not feasible within a reasonable timeline. Claude Code batch processing
(`/batch` mode) will be used to:
- Parse Teradata DDL and DataStage job XML
- Generate equivalent Python pipeline code
- Generate Trino SQL equivalents for materialized view logic
- Flag cases requiring human review (non-standard Teradata types, business logic ambiguity)

Human review is mandatory for all AI-generated migrations before promotion to staging.

---

## Teradata-Specific Technical Considerations

### Data type mapping

| Teradata type | Iceberg equivalent | Notes |
|---|---|---|
| `BYTEINT` | `int` | Upcast — no precision loss |
| `SMALLINT` | `int` | Upcast |
| `INTEGER` | `int` | Direct |
| `BIGINT` | `long` | Direct |
| `DECIMAL(p,s)` | `decimal(p,s)` | Iceberg supports up to (38,18) |
| `FLOAT` / `REAL` | `double` | Direct |
| `CHAR(n)` / `VARCHAR(n)` | `string` | Trailing space handling required |
| `DATE` | `date` | Direct — Teradata DATE is ISO |
| `TIME` | `time` | Direct |
| `TIMESTAMP` | `timestamp` | Timezone handling: Teradata is session-TZ; Iceberg prefers UTC |
| `PERIOD(DATE)` | No direct equivalent | Decompose to `start_date` + `end_date` columns |
| `VARBYTE` / `BYTE` | `binary` | Direct |
| COMP-3 packed decimal | Decode in Bronze Python pipeline before Silver | See Bronze layer ETL patterns |

### Slowly changing dimensions

If Silver tables use Type 2 SCD patterns (effective/expiry dates), the Iceberg
equivalent uses `MERGE INTO` with row-level updates (Iceberg V2 required):

```sql
MERGE INTO iceberg.silver.customer_dim AS target
USING staging AS source
ON target.customer_key = source.customer_key
   AND target.is_current = TRUE
WHEN MATCHED AND source.has_changes = TRUE THEN
  UPDATE SET is_current = FALSE, expiry_date = source.effective_date
WHEN NOT MATCHED THEN
  INSERT (customer_key, ..., effective_date, expiry_date, is_current)
  VALUES (source.customer_key, ..., source.effective_date, DATE '9999-12-31', TRUE);
```

### Timestamp and timezone

Teradata timestamps are session-timezone dependent. All Iceberg timestamps must be
normalized to UTC at the Silver layer. The Python ETL pipeline is responsible for
this conversion — it is not assumed to be correct in the Bronze layer.

---

## Timeline and Phases

This is a multi-year programme. The DataStage → Python migration is the long pole,
not the data migration.

| Phase | Scope | Target |
|---|---|---|
| **Phase 0** (now) | Dual-write infrastructure, Nessie branching workflows, orphan analysis | Q2 2026 |
| **Phase 1** | Pilot domain — Customer 360 (Silver + Gold) | Q3-Q4 2026 |
| **Phase 2** | Expand to 5 high-priority domains | 2027 |
| **Phase 3** | Remaining active domains, DataStage job migration | 2027-2028 |
| **Phase 4** | Teradata becomes read-only, license reduction begins | 2028 |
| **Phase 5** | Teradata sunset | 2029 (TBD based on Phase 3 completion) |

These are directional. Each phase gate requires:
- Full consumer validation on Iceberg
- Zero P1 incidents attributable to the migration in the prior 60 days
- Sign-off from Vinh and the relevant domain lead

---

## Stakeholder Risks

> ⚠️ **UNRESOLVED**: Some teams have built analytical processes directly on Teradata
> materialized views outside of OBIEE/Tableau. These are not catalogued. A survey of
> direct Teradata consumers is required before Phase 1 begins.

> ⚠️ **UNRESOLVED**: Teradata license cost reduction requires engagement with
> Procurement. The dual-write period will briefly *increase* Teradata storage before
> it decreases. Procurement needs to know this is temporary.

> ⚠️ **UNRESOLVED**: DataStage job migration velocity depends on headcount and AI
> tooling adoption. A formal estimate is required once Phase 0 infrastructure is live.

---

## Related Documents

- ADR-001: Teradata OTF + Nessie Feasibility
- ADR-002: Trino as Mandatory Query Gateway
- `docs/migration/teradata-to-iceberg.md`
- `docs/migration/materialized-view-decomposition.md`
- `docs/etl-patterns.md`
