# ADR-004: Trino Workload Isolation via Resource Groups

**Status:** Accepted  
**Date:** March 2026  
**Author:** George Chilakos, VP Enterprise Data  
**Reviewers:** Pending — Vinh (manager), Platform Engineering

---

## Context

ADR-002 established Trino as the mandatory query gateway for all Iceberg access.
With a single gateway handling all workload types simultaneously, resource contention
becomes a production risk:

- **ETL pipelines** (Bronze→Silver→Gold transforms) run long, memory-intensive queries
  on large datasets. A nightly Silver rebuild can consume 60–80% of available worker
  memory for several hours.
- **BI queries** (Power BI, Tableau via Cube) are short, interactive, latency-sensitive.
  A 30-second wait is acceptable for a batch job. For a dashboard, it's a user complaint.
- **Soda quality gates** run at the end of each pipeline stage. If they queue behind a
  heavy ETL job, the quality-gate-to-Nessie-merge window grows, delaying downstream
  consumers.
- **AI agent queries** (Borealis, RBC Assist via FastAPI middleware) must return in
  under 2 seconds or the user experience degrades. They should never be starved by
  batch workloads.

Without explicit workload isolation, any of these consumer types can starve the others
by consuming all available Trino worker memory and concurrency slots.

---

## Decision

**Implement Trino resource groups to partition available memory and concurrency across
workload types. Every Trino connection must carry a `source` tag that routes it to the
correct resource group.**

### Resource group allocation

```
Total cluster memory: 100%
│
├── engineering  (60%)
│   ├── etl_pipelines   (40%, 15 concurrent, 4h query timeout)
│   ├── soda_quality    (15%,  5 concurrent, 30m timeout)
│   └── schema_ops      ( 5%,  3 concurrent, 10m timeout)
│
├── bi           (35%)
│   ├── cube_semantic   (20%, 20 concurrent, 5m timeout)
│   ├── power_bi        (10%, 15 concurrent, 10m timeout)
│   └── tableau         ( 5%, 10 concurrent, 10m timeout)
│
└── ai_agents    ( 5%,  5 concurrent,  2m timeout)
```

Memory limits are **soft** — groups can burst past their allocation when the cluster
has spare headroom. Under contention, the scheduler enforces the ratios. This means
a quiet weekend night lets ETL jobs use 90% of memory freely; a busy Monday morning
constrains each group to its budget.

### Routing mechanism

Queries are routed to groups by two signals: the **user** (service account identity)
and the **source** tag on the connection. Source takes precedence over user for BI
tools that connect through a shared service account.

| Source / User | Resource group |
|---|---|
| user: `svc_etl_pipeline`, `svc_airflow`, `svc_spark` | `engineering.etl_pipelines` |
| user: `svc_soda` | `engineering.soda_quality` |
| source: `schema-migration`, `ddl-runner` | `engineering.schema_ops` |
| source: `cube` | `bi.cube_semantic` |
| source: `PowerBI`, `power-bi` | `bi.power_bi` |
| source: `Tableau`, `tableau` | `bi.tableau` |
| user: `svc_borealis`, `svc_rbc_assist`, `svc_fastapi_ai` | `ai_agents` |
| all others | `engineering.etl_pipelines` (safe default) |

### Required source tags in application code

Every Trino connection from application code must use a named constructor from
`etl/src/iceberg_utils/trino.py` that sets the correct source tag:

```python
# ETL pipelines and Airflow DAGs
conn = get_etl_connection(schema="bronze.account")

# Soda quality gates
conn = get_soda_connection(schema="raw.mainframe")

# DDL / schema migration
conn = get_schema_ops_connection()

# AI agent queries (FastAPI middleware)
conn = get_ai_connection(schema="gold")

# Soda branch validation (pre-merge quality gate)
conn = get_nessie_branch_connection("ingest/account-master-20260320")
```

Direct calls to `get_trino_connection()` with no source tag are permitted only in
tests and local development scripts.

---

## Consequences

### What this enables

**BI dashboards stay responsive during heavy ETL.** The nightly Silver rebuild
consumes from the `engineering.etl_pipelines` bucket (40%). Power BI queries go to
`bi.power_bi` (10%). They compete for different memory pools — the rebuild cannot
starve the dashboard.

**AI agent SLA is structurally enforced.** The `ai_agents` group has a 2-minute
query timeout. Any AI-generated query that would run longer is killed automatically.
This prevents runaway AI queries from consuming worker resources — a risk that becomes
significant as AI query volume grows.

**Soda gates complete within predictable windows.** Quality checks are isolated to
`engineering.soda_quality` with a 30-minute timeout. They are not queued behind
14-hour ETL jobs. The Nessie branch merge (which waits on Soda) happens within a
known time window.

**Resource contention is observable.** Trino exposes resource group metrics via its
`system.runtime.queries` and `system.runtime.tasks` views. These feed into the
Prometheus + Grafana observability stack. You can see which group is queued, which
is at concurrency limit, and which is approaching its memory soft limit.

### What this constrains

**Every new service account or BI tool must be explicitly mapped.** If a new consumer
connects with an unrecognised user and no source tag, it falls into
`engineering.etl_pipelines` — the safe default, but possibly wrong. New consumers
must be added to `rules.json` and the named constructor list.

**Timeout limits must be tuned as query patterns evolve.** The 4-hour ETL timeout
and 5-minute BI timeout are initial values. Monitor actual query durations in Grafana
and adjust before enforcing hard limits in production.

---

## Observability

Query the Trino system tables to monitor group utilisation:

```sql
-- See all running queries grouped by resource group
SELECT
    resource_group_id,
    COUNT(*)                              AS running_queries,
    SUM(total_memory_reservation) / 1e9  AS memory_gb,
    MAX(elapsed_time)                     AS longest_query
FROM system.runtime.queries
WHERE state = 'RUNNING'
GROUP BY 1
ORDER BY memory_gb DESC;

-- Queries queued (waiting for a concurrency slot)
SELECT resource_group_id, query_id, queued_time, query
FROM   system.runtime.queries
WHERE  state = 'QUEUED'
ORDER  BY queued_time DESC;
```

Add these as panels in the `pipeline_observability` Grafana dashboard.

---

## Related Documents

- ADR-002: Trino as Mandatory Query Gateway
- `infra/docker/trino/etc/resource-groups/rules.json`
- `infra/docker/trino/etc/resource-groups/resource-groups.properties`
- `etl/src/iceberg_utils/trino.py` — named connection constructors
- `docs/governance/ranger-trino-coverage.md`
