# Cloudera → Acceldata ODP Migration Planning

**Author:** George Chilakos
**Date:** May 2026
**Status:** Draft for discussion

---

## Current State

| Item | Value |
|---|---|
| Source platform | Cloudera (CDP assumed) |
| Workload mix | 55% Spark, 35% Hive, 10% MapReduce |
| Spark version | 3.3 |
| Hive version | 3.2 |
| Runtime | ODP 3.2 |
| Target | Acceldata Open Data Platform (ODP) |
| Desired timeline | 3 months |

---

## What Acceldata Actually Offers

Acceldata Open Data Platform (ODP) is a 100% open-source, Apache-aligned Hadoop distribution positioned as a direct Cloudera CDP alternative. It includes Spark, Hive, HDFS, Ozone, Ranger, plus modern engines like Trino, Iceberg, and Airflow.

Pulse (their observability product) is a separate, complementary offering.

### The three migration paths

**1. In-place upgrade**
- Upgrade existing cluster, no new infrastructure, no data movement
- Guided runbooks
- Planned 8-hour maintenance window
- Rollback-ready in under 4 hours

**2. Sidecar upgrade**
- Deploy ODP alongside the current cluster
- Parallel deployment with performance benchmarking
- Gradual job migration
- Optional data forking or dual hosting
- Minimal downtime, instant rollback

**3. Forklift upgrade**
- Stand up a new ODP cluster on-prem or in cloud
- Move workloads in phases
- Zero impact on existing cluster during migration
- Ideal for cloud adoption or full platform refresh
- Fast rollback and transition flexibility

The key distinction: **sidecar** = run both in parallel and migrate job by job. **Forklift** = new cluster, often new infrastructure, phased workload move, decommission old.

---

## Path Recommendation by Scenario

| Scenario | Recommended path | Why |
|---|---|---|
| Already on ODP 3.2, want a runtime refresh | **In-place** | Not really a migration — runbook-driven upgrade, 8-hour window |
| On Cloudera CDP, same infrastructure | **Sidecar** | Lowest risk, sequence MR last, validate in parallel |
| On Cloudera CDP, also moving to cloud or new hardware | **Forklift** | Forces the infra decision into the same cutover |

For the stated workload mix on existing infrastructure, **sidecar is the right default**.

---

## Why Sidecar Fits This Workload Mix

- **MapReduce 10% is the schedule risk.** MR jobs are usually legacy code with brittle Hadoop dependencies, Oozie workflows, and custom JARs. Sidecar lets them keep running on the legacy cluster while they're migrated or retired on a separate timeline — they don't sit on the critical path.
- **Hive 3.2 → ODP Hive** is where subtle behavior differences appear (ACID, Tez configs, materialized views, LLAP setups). Sidecar enables parallel validation before cutover.
- **Spark 3.3 jobs are the easiest to move** — wave them through first to build confidence and demonstrate progress.

---

## Wave Plan

| Wave | Workload | Approach | Rationale |
|---|---|---|---|
| 1 | Spark 3.3 jobs (lower risk subset) | Lift and validate on ODP | Quick wins, build confidence |
| 2 | Spark 3.3 jobs (higher risk / complex DAGs) | Lift, performance test, tune | Catch tuning differences early |
| 3 | Hive 3.2 batch jobs | Lift, validate ACID and Tez behavior | Most likely source of subtle bugs |
| 4 | Hive interactive / LLAP | Validate semantic parity | Touches user-facing SLAs |
| 5 | MapReduce | Migrate-or-retire decision per job | Last because highest per-job cost |

---

## Timeline Reality Check

| Path | 3-month feasibility | Notes |
|---|---|---|
| In-place (already on ODP) | **Yes, comfortable** | Single maintenance window, runbook-driven |
| Sidecar from CDP | **Tight but possible** | Requires parallel hardware, dedicated squad, MR scoped to retire-in-place or migrate-last |
| Forklift with new infra | **Aggressive** | Procurement alone can consume a month |

**Realistic enterprise estimate for a full CDP → ODP sidecar:**

| Phase | Duration |
|---|---|
| Discovery, inventory, dependency mapping | 3–4 weeks |
| Lower environment build + parallel run | 4–6 weeks |
| Workload migration in waves | 8–12 weeks |
| Cutover, hypercare, decommission | 4 weeks |
| **Total** | **5–6 months** |

3 months is achievable only if: (a) <500 jobs total, (b) dedicated migration squad, (c) leadership accepts a development freeze during cutover.

The under-4-hour rollback story is the key unlock for compressing the cutover window.

---

## Acceldata ODP vs. Databricks

This is not an apples-to-apples choice. They answer different questions.

| Dimension | Acceldata ODP | Databricks |
|---|---|---|
| Migration type | Exit Cloudera licensing, keep Hadoop runtime | Re-platform to modern lakehouse |
| Code changes | Minimal — recompile and validate | Significant — Hive → Spark SQL on Delta, MR rewrites |
| Infrastructure | On-prem, hybrid, or cloud | Cloud only |
| Timeline | 3–6 months | 18–24 months |
| Cost story | Eliminate Cloudera license, lower TCO fast | Higher transformation cost, modern capability |
| Risk profile | Low — same engines, same code | High — fundamental platform change |
| Strategic upside | Bridge to modernization on your terms | Photon, Delta, Unity Catalog, MLflow, serverless SQL |

**Recommendation for this scenario: Acceldata ODP.**

Reasoning:
- The stated goal appears to be exiting Cloudera, not re-platforming.
- The 3-month target rules out Databricks regardless of merits.
- If analytical workloads will eventually land in the Lumina lakehouse (Iceberg V2, Nessie, Trino, Gravitino, Ranger), ODP is the natural stepping stone — same Iceberg, same Trino, same governance posture. Databricks creates a fork in the road that complicates the Lumina convergence story.

Databricks would only be the right answer if leadership is explicitly funding a re-platform, not a re-license.

---

## Open Questions to Resolve This Week

1. **Source confirmation.** Are we already on Acceldata ODP 3.2, or on Cloudera CDP moving to ODP? The whole plan changes on this answer.
2. **Workload disposition.** Of the Spark / Hive / MR jobs in scope:
   - How many are strategic (keep)?
   - How many are scheduled to retire within 12 months?
   - How many are candidates to refactor into the Lumina lakehouse?
   The in-scope count may be half of the total.
3. **The 3-month deadline.** Where is it coming from? Cloudera contract renewal? If yes, a short-term extension may be cheaper than a rushed migration.
4. **Hardware availability for sidecar.** Is there capacity for a parallel cluster, or does the path force in-place?
5. **MR disposition.** For the 10% MapReduce workload — retire-in-place, lift to Spark, or migrate as-is?

---

## Recommended Next Actions

1. Confirm source platform (CDP vs. already-ODP) and target deployment (on-prem vs. cloud).
2. Run workload disposition exercise before committing to scope.
3. Pressure-test the 3-month deadline against the Cloudera contract dates.
4. If sidecar is the path: secure parallel hardware and define the cutover criteria.
5. Engage Acceldata for a scoped assessment — they offer guidance on strategy selection based on current use cases.
