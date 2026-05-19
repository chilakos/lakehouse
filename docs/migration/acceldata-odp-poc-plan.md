# ODP POC Plan — CDP 7.1.9 SP1 CHF 10 → ODP 3.3.6.x

**Owner:** George Chilakos
**Goal:** Validate Acceldata ODP as a viable Cloudera exit target before engaging vendor sales. Generate evidence-based answers and procurement leverage.
**Time budget:** 4–6 engineer-days
**Cost:** $0 (no licenses, no sales engagement)

---

## Source State (Confirmed)

| Component | Current version | Notes |
|---|---|---|
| Distribution | CDP Private Cloud Base 7.1.9 SP1 CHF 10 (Runtime 7.1.9.1054-4) | Well-patched recent CDP build |
| Apache Hadoop / YARN / HDFS | 3.1.1 | |
| Apache HBase | 2.4.17 | |
| Apache Hive | 3.1.3000 (= 3.1.3 with Cloudera build tag) | |
| Apache Iceberg | 1.3.0 | **Strategic asset — already in place** |
| Apache Impala | 4.0.0 | **Not in ODP — migration workstream required** |
| Apache Kafka | 3.4.1 | |
| Apache Knox | 1.3.0 | |
| Apache Livy | 0.7.2 | |
| Apache MapReduce | 3.1.1 | |
| Apache Oozie | 5.1.0 | |
| Apache Ranger | 2.4.0 | **Exact match with ODP target** |
| Apache Spark 2.x | 2.4.8 | **Deprecated — pre-migration uplift workstream required** |
| Apache Spark 3.x | 3.3 (CDS build 3.3.7191000.3-1) | |
| Apache Sqoop | 1.4.7 | Apache Sqoop is deprecated upstream; plan exit |
| Apache Tez | 0.9.1 | |
| Apache ZooKeeper | 3.8.1 | |

---

## Target State

| Item | Target | Fallback |
|---|---|---|
| ODP release | 3.3.6.4-1 (current GA, May 2026) | 3.3.6.3-1 (if 3.3.6.4-1 not on public mirror) |
| Spark 3 | 3.3.3 (matches current Spark 3.3) | — |
| Hive | 3.1.x (matches current 3.1.3) | — |
| Hadoop / YARN / HDFS | 3.3.x | — |
| HBase | 2.5.x | — |
| Ranger | 2.4.x | — |
| OS | RHEL 9 | Ubuntu 22 |
| JDK | 17 | — |
| Python | 3.x | — |
| Management plane | Apache Ambari (Acceldata fork) | — |

**Decision rationale:** Spark 3.3 → 3.3.3 is same-minor; ODP supports Spark 3.3.3 / 3.5.1 / 3.5.5 / 4.1.1 simultaneously so we can do platform migration first and Spark major uplift as a separate later wave. Hive 3.1.3 → 3.1.x is essentially same-version. Ranger 2.4.0 → 2.4.x is exact — policy round-trip should be clean.

---

## Source → Target Version Map

| Component | CDP 7.1.9 SP1 | ODP 3.3.6.x | Δ | Migration risk |
|---|---|---|---|---|
| Hadoop / HDFS / YARN | 3.1.1 | 3.3.x | Minor version jump | **Medium** — YARN scheduler configs, capacity scheduler evolution, HDFS RBF improvements |
| Hive | 3.1.3 | 3.1.x | Same minor | **Low** — ACID and metastore should be clean |
| Spark 3.x | 3.3 (CDS) | 3.3.3 (Apache) | Same minor, CDS → Apache | **Low** — code change near-zero; CDS-specific connectors (spark-warehouse-connector) are the watch area |
| Spark 2.x | 2.4.8 | **Not supported** | Major | **Workstream** — must move to Spark 3 first, regardless of platform |
| MapReduce | 3.1.1 | 3.3.x | Minor uplift | **Medium** — MR1 API stable, same lineage as Hadoop |
| HBase | 2.4.17 | 2.5.x | Minor uplift | **Low** |
| Kafka | 3.4.1 | 3.x (Kafka3 in ODP) | Same major | **Low** |
| Tez | 0.9.1 | 0.9.x | Same | **Low** |
| Ranger | 2.4.0 | 2.4.x | Exact match | **Low** — policy export/import should round-trip |
| Oozie | 5.1.0 | 5.x | Same major | **Low** |
| Sqoop | 1.4.7 | 1.4.x | Same | **Low** — but Apache Sqoop deprecated; plan exit |
| Livy | 0.7.2 | 0.7.x (Livy3 in ODP) | Same | **Low** |
| Knox | 1.3.0 | Knox in ODP | — | **Low** |
| ZooKeeper | 3.8.1 | 3.x | Same major | **Low** |
| Iceberg | 1.3.0 | Iceberg native | — | **Low** — strong asset for Lumina convergence |
| Impala | 4.0.0 | **Not in ODP** | Discontinued | **Workstream** — migrate to Trino or Hive LLAP |
| **JDK** | 8 / 11 | **17** | Major uplift | **Medium-High** — all custom JARs / UDFs / connectors must recompile and be tested |
| **Python** | 2 or 3 | **3.x** | Possible major | **Low-Medium** — depends on PySpark UDF inventory |
| **OS** | RHEL 7 / 8 | RHEL 8/9 or Ubuntu 20/22 | Possible OS uplift | **Medium** — full OS migration if currently on RHEL 7 |

---

## Two Pre-Migration Workstreams (Must Scope Before Committing to a Timeline)

These are **not optional** and they are **not part of the ODP migration itself**. They are prerequisites that determine whether 3 months is feasible.

### Workstream A: Impala 4.0.0 Decommissioning / Migration

**Why it matters:** ODP does not ship Impala. If we have Impala in production at any meaningful volume, it must be migrated *before or during* the ODP cut-over, otherwise those workloads break.

**Scope-defining questions:**
1. How many distinct Impala workloads are in production today?
2. How many users / dashboards / BI tools query Impala directly?
3. What's the total Impala query volume vs. Hive vs. Spark SQL?
4. Are there workloads with Impala-specific SQL features (e.g., COMPUTE STATS, INVALIDATE METADATA workflows, Impala-specific UDFs)?

**Migration target options:**

| Option | Pros | Cons |
|---|---|---|
| **Trino** (native in ODP) | Modern, fast, federation across multiple sources, aligns with Lumina | Different SQL dialect, requires query rewrites |
| **Hive LLAP** | Closer Impala-replacement, same SQL dialect as existing Hive | Older tech, less aligned with future direction |
| **Retire** | Best option for low-value workloads | Requires business-side workload review |

**Effort estimate:** If Impala is <10% of analytical workload → 2–4 weeks scoped effort. If 10–30% → 6–10 weeks. If >30% → this is the project, not the ODP migration.

**Decision needed before POC:** Get an Impala usage inventory. This is the single biggest unknown.

### Workstream B: Spark 2.4.8 → Spark 3 Uplift

**Why it matters:** Anything still on Spark 2.x must move to Spark 3 before ODP, regardless of platform direction. This is true even if we stay on Cloudera.

**Scope-defining questions:**
1. How many Spark 2.4.8 jobs are in production?
2. Are they Scala, Java, or PySpark?
3. Any dependencies on Spark 2.x-specific APIs (RDD-heavy code, Spark 2 ML pipelines)?

**Effort estimate:** Per-job rewrite cost is usually small (Spark 2 → 3 is mostly clean for DataFrame API code). Bulk is in regression testing.

**Decision needed before POC:** Get a Spark 2 vs Spark 3 inventory. If <50 Spark 2 jobs, this is a 3–4 week sprint. If 200+, scope it as a parallel project.

---

## GitHub Repos for POC

### Public binary mirror (no auth required, confirmed accessible)

| Resource | URL |
|---|---|
| Mirror index (RHEL 9, ODP 3.3.6.3-1) | `https://mirror.odp.acceldata.dev/v2/odp/python3/jdk17/3.3.6.3-1/releases/rhel9/` |
| Mirror index (RHEL 9, ODP 3.3.6.4-1) | `https://mirror.odp.acceldata.dev/v2/odp/python3/jdk17/3.3.6.4-1/releases/rhel9/` (verify accessibility) |
| Stack tarball path | `https://mirror.odp.acceldata.dev/v2/odp/python3/jdk17/3.3.6.3-1/tarballs/rhel9/` |
| Repo file for yum/dnf | `https://mirror.odp.acceldata.dev/v2/odp/python3/jdk17/3.3.6.3-1/repofiles/rhel9/ambari-odp-1.repo` |

### Acceldata GitHub source forks (for patch-delta inspection)

These are the public Apache project forks Acceldata maintains. **Inspect the diff between these and upstream Apache to understand what value-add the distribution provides.** This is also our procurement leverage — knowing what's in the diff is knowing what we'd have to do ourselves if we walk away from the vendor.

| Component | Repo | Priority for POC |
|---|---|---|
| Hadoop | `https://github.com/acceldata-io/hadoop` | **High** — core runtime, big delta from our 3.1.1 |
| Spark 3 | `https://github.com/acceldata-io/spark3` | **High** — 55% of our workloads |
| Ranger | `https://github.com/acceldata-io/ranger` | **High** — critical for policy migration; exact version match |
| Kafka | `https://github.com/acceldata-io/kafka` | **Medium** — only if Kafka in scope |
| Airflow | `https://github.com/acceldata-io/airflow` | **Medium** — relevant if standardizing on Airflow for orchestration |
| spark-rapids | `https://github.com/acceldata-io/spark-rapids` | **Low** — only if GPU workloads in scope |
| Phoenix | `https://github.com/acceldata-io/phoenix` | **Low** — only if HBase + Phoenix used today |
| Delta | `https://github.com/acceldata-io/delta` | **Skip** — we're standardizing on Iceberg |
| ClickHouse | `https://github.com/acceldata-io/ClickHouse` | **Skip** — not in current scope |
| Celeborn | `https://github.com/acceldata-io/celeborn` | **Optional** — shuffle service, evaluate only if Spark perf is a POC criterion |

Full Acceldata org page: `https://github.com/acceldata-io` (116 repos total)

### Patch-delta inspection commands

```bash
# Clone Acceldata's Spark fork
git clone https://github.com/acceldata-io/spark3.git
cd spark3

# Add upstream Apache Spark as a remote
git remote add apache https://github.com/apache/spark.git
git fetch apache --tags

# List patches against the Apache Spark 3.3.3 tag
git log --oneline v3.3.3..HEAD | head -50

# See full diff against upstream
git diff v3.3.3..HEAD --stat | tail -20

# Count files changed
git diff --stat v3.3.3..HEAD | tail -1
```

Do the same for `acceldata-io/hadoop` (compare against Apache `release-3.3.x`) and `acceldata-io/ranger` (compare against Apache `release-ranger-2.4.0`). **The size and nature of these diffs is the single most informative artifact for the procurement conversation.**

---

## Phase 1: Inspect (1–2 hours)

**Goal:** Confirm public-mirror access and understand patch delta against upstream Apache.

### Tasks
1. Browse `https://mirror.odp.acceldata.dev/v2/odp/python3/jdk17/3.3.6.3-1/releases/rhel9/` and confirm no auth required.
2. Pull the stack tarball:
   ```bash
   curl -O https://mirror.odp.acceldata.dev/v2/odp/python3/jdk17/3.3.6.3-1/tarballs/rhel9/ODP-3.3.6.3-1.tar.gz
   tar -tzf ODP-3.3.6.3-1.tar.gz | head -100
   ```
3. Clone `acceldata-io/spark3`, `acceldata-io/hadoop`, `acceldata-io/ranger`. Run the upstream-diff commands above.
4. Capture: lines-of-code changed, files changed, commit message patterns (CVE, perf, integration glue, packaging only).

### Success criteria
- Tarball downloads without auth.
- Spark3 patch delta against `v3.3.3` is non-trivial but readable (not 100k LOC of unexplained changes).
- Patches look like CVE backports, performance fixes, integration glue — not proprietary algorithm replacements.

### Smells to watch for
- Auth wall on tarball download → public access claim is weaker than advertised.
- Patch delta is just packaging metadata → low value-add; pure-Apache build alternative is credible.
- Patch delta is huge and undocumented → high lock-in; harder to leave Acceldata than to leave Cloudera.

---

## Phase 2: Single-Node Install (half day to one day)

**Goal:** Prove the install works and the management plane is usable.

### Hardware
- 1 VM: RHEL 9, 16 GB RAM, 4 vCPU, 100 GB disk
- Outbound network to `mirror.odp.acceldata.dev`

### Steps
1. Install JDK 17 and Python 3.
2. Configure repo file from the URL above.
3. Install Ambari server + agent.
4. Use Ambari to deploy: HDFS, YARN, Hive, Spark3 (pin to 3.3.3), ZooKeeper, Ranger.
5. Validate services start cleanly.

### Validation tests
| Test | Pass criteria |
|---|---|
| HDFS write/read | Put a file, get it back, checksums match |
| Hive create table + ACID insert + select | INSERT works on managed table |
| Spark `pi` example | Runs and exits 0 |
| PySpark hello world under Python 3 | Runs |
| Ranger DENY policy on Hive table | Actually blocks unauthorized user |
| Ambari UI | All services green, logs accessible |

### Success criteria
- All six tests pass.
- Install completed in <1 day.
- No undocumented manual steps.

---

## Phase 3: Workload Compatibility Smoke Test (2 days)

**Goal:** Run a representative slice of real workloads on ODP unchanged.

### Workload selection: 5 jobs biased to find problems
- 2 Spark 3 jobs (one simple ETL, one with complex joins / heavy SQL)
- 2 Hive jobs (one batch, one with ACID writes or materialized views)
- 1 MapReduce job (the legacy class we're most worried about)

**Note:** Do NOT include Impala workloads in Phase 3 — they're scoped to Workstream A and require their own migration path before they'd run on ODP.

**Anonymize data** before copying to POC VM.

### Tests per job
1. Compile / package on JDK 17 — does it build?
2. Submit to ODP cluster — does it run?
3. Compare output to CDP production output — bitwise identical or explained differences only?
4. Compare runtime — within 20% of current?
5. Note every config tweak required — this is the migration backlog seed.

### Success criteria
- 5 out of 5 jobs run.
- Required code changes are minor (recompile, dependency bumps) — no architectural rewrites.
- Performance within 20% of CDP baseline.

### Smells to watch for
- "Simple" job needs significant rework → rework estate is much larger than estimated.
- Hive ACID semantics shift → 35% of workload is at risk.
- MR job fails outright → confirms MR-is-schedule-risk thesis.
- Spark regressions >20% → pressure-test the vectorized execution marketing claim.

---

## Phase 4: Pre-Migration Workstream Sizing (1 day, parallel to Phase 3)

**Goal:** Get hard numbers on Impala and Spark 2 estate so we can decide if 3 months is feasible.

### Tasks
1. Pull Impala query log from CDP. Count: distinct queries, distinct users, dashboards/tools that connect.
2. Pull Spark 2.4.8 job inventory. Count: jobs by team, by criticality, by language.
3. Classify both inventories: keep / refactor / retire.
4. Estimate effort per category.

### Output
A table with rows = workload, columns = (current platform, target, effort estimate, owner). This is what we take into the Vinh/Martin conversation.

---

## What This POC Answers

After 4–6 engineer-days we will have evidence-based answers to:

1. **Does ODP install cleanly from public artifacts?** → open-source-credibility question.
2. **Do our Spark 3.3 / Hive 3.1.3 / Hadoop 3.1 workloads run with minimal change?** → migration-risk question.
3. **What's the patch delta vs. pure Apache?** → "could we just build it ourselves" question and procurement leverage.
4. **What does the Impala + Spark 2 estate actually look like?** → is 3 months feasible at all.
5. **Where are the rough edges?** → with evidence, not opinion.

---

## What This POC Does NOT Answer

- Multi-tenancy at scale (need 5+ node cluster, real concurrent users).
- Pulse observability (separately licensed).
- Proprietary vectorized Spark execution claim (confirm whether in open binaries or commercial add-on).
- Support response quality and SLA adherence.
- Real Ranger policy migration from CDP at production scale.
- Kerberos / Active Directory integration at RBC complexity.
- Ozone vs. HDFS at scale.

These belong in a paid POC with Acceldata SAs after vendor engagement.

---

## Decision Gates After POC

| If POC shows... | Then... |
|---|---|
| Clean install + 5/5 jobs run + small patch delta + Impala scope <10% | Proceed to vendor engagement with strong leverage. 3 months realistic with discipline. |
| Clean install + 5/5 jobs run + large patch delta + Impala scope <10% | Proceed to vendor engagement. ODP is doing real engineering work; weaker pure-Apache alternative argument. 3 months still possible. |
| Clean install + Impala scope 10–30% | Re-baseline timeline to 5–6 months. Impala migration is its own project. |
| Clean install + Impala scope >30% | Stop. Impala migration is the project, ODP is secondary. Rescope entirely. |
| Install issues or job failures | Pause. Either deeper paid POC needed, or ODP isn't as plug-and-play as marketed. |
| Spark perf significantly better than CDP | Worth standalone perf POC and a separate value conversation. |

---

## Engineering Effort

| Phase | Effort |
|---|---|
| Phase 1: Inspect | 0.5 day, 1 engineer |
| Phase 2: Single-node install | 1 day, 1 engineer |
| Phase 3: Workload smoke test | 2 days, 1 engineer + light app team support |
| Phase 4: Impala + Spark 2 inventory | 1 day, 1 engineer + light app team support |
| Findings write-up | 0.5–1 day |
| **Total** | **5–6 engineer-days** |

---

## Open Questions Before Starting

1. Who is the platform engineer assigned?
2. VM environment — RBC cloud sandbox, personal lab, or shared dev?
3. Which 5 production jobs do we pull as the workload sample?
4. InfoSec sign-off needed for sandbox download of open-source binaries?
5. Allowed to pull production code into POC env, or do we need synthetic equivalents?
6. **Impala usage inventory — who owns this and how fast can we get it?**
7. **Spark 2.4.8 inventory — who owns this and how fast can we get it?**

---

## Summary for the Exec Conversation

Going into a planning meeting with Vinh, the headline:

> "Source is CDP 7.1.9 SP1 CHF 10. Target is Acceldata ODP 3.3.6.x. The runtime mapping is clean — Spark 3.3 → 3.3.3, Hive 3.1.3 → 3.1.x, Ranger 2.4.0 → 2.4.x. **The two unknowns that determine timeline are Impala (not in ODP) and Spark 2.4.8 (must uplift first). We need usage inventory on both before committing to 3 months.** Free POC from public artifacts validates the technical path in 5–6 engineer-days, generates procurement leverage, and gives us hard numbers before any vendor conversation."
