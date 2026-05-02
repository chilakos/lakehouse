# Phase 1 Pilot Plan — Fabric Semantic Models over Snowflake and Trino

| Field | Value |
| --- | --- |
| **Document type** | Pilot plan |
| **Date** | 2026-05-02 |
| **Author** | George Chilakos (VP, Enterprise Data) |
| **Companion to** | ADR-014 (Semantic Plane Architecture) |
| **Target start** | Q3 2026 |
| **Duration** | 12 weeks |
| **Pilot lead** | TBD (proposed: Gautam, Technical Lead, Lakehouse) |

## Purpose

ADR-014 commits RBC to a unified semantic plane based on Fabric semantic models, sitting above both Snowflake and Trino, consumed via Fabric Data Agent. Two architectural assumptions in that ADR are not yet empirically validated at RBC scale:

1. **Fabric semantic models can serve high-concurrency Snowflake-resident workloads** with acceptable latency, either via DirectQuery or via Fabric Mirroring of Snowflake.
2. **Fabric semantic models can serve Trino-fronted on-prem workloads** at acceptable latency and cost, with governance integrated through Purview.

The pilot validates both before broad rollout commits. If either assumption fails materially, ADR-014 is revisited with empirical evidence rather than abandoned on speculation.

## Scope

Two LOB pilots, run in parallel, on representative but non-critical workloads.

### Pilot A — Snowflake-resident workload

**Domain.** A P&CB analytics workload with data already in Snowflake. Specifically, a deposit-product analytics dataset with daily snapshots, customer dimensions, and standard BI metrics (balances, flows, attrition, NIM components).

**Approach.** Build a Fabric semantic model in two parallel configurations:

- **Configuration A1: DirectQuery to Snowflake.** Fabric semantic model issues queries to Snowflake at runtime. Tests Snowflake DirectQuery performance and Snowflake credit consumption.
- **Configuration A2: Fabric Mirroring of Snowflake.** Snowflake data continuously replicated into OneLake; Fabric semantic model reads from OneLake at near-zero latency. Tests mirroring freshness, completeness, and cost.

Both configurations expose the same business definitions. A small number of Power BI reports and a Fabric Data Agent are connected to each, exercised against a benchmark query set.

### Pilot B — Trino-resident on-prem workload

**Domain.** A risk or finance workload sourced from on-prem Iceberg tables accessed through Trino. Specifically, a counterparty-exposure dataset that crosses two LOBs at small scale (a deliberate stress test for the cross-LOB semantic-plane case).

**Approach.** Single configuration:

- **Configuration B1: DirectQuery to Trino.** Fabric semantic model issues queries to Trino, which federates to the appropriate Iceberg tables and any legacy sources still in flight. Tests Trino DirectQuery performance, Ranger policy enforcement through the query path, and Purview lineage capture.

## Success criteria

The pilot produces quantitative evidence on each of the following. Pass thresholds are calibrated to typical RBC BI workload expectations.

| Criterion | Pass threshold | Measurement |
| --- | --- | --- |
| **Query latency (P50)** for typical BI queries | ≤ 3 seconds | Power BI report rendering time, Fabric Data Agent response time |
| **Query latency (P95)** for typical BI queries | ≤ 8 seconds | Same |
| **Concurrency** under realistic load (50 concurrent users) | No degradation beyond P95 threshold | Synthetic load test |
| **Mirroring freshness** (Pilot A2 only) | ≤ 5 minutes lag from Snowflake to OneLake | Timestamp delta on probe records |
| **Governance enforcement** | RLS, CLS, and Purview labels respected end-to-end | Audit test against known-restricted records |
| **Cost (Pilot A1 vs A2)** | Mirroring cheaper than DirectQuery at pilot concurrency | Snowflake credit consumption + Fabric capacity unit consumption |
| **Cost (Pilot B1)** | Within 20% of equivalent direct-Trino BI consumption | Fabric capacity unit consumption + Trino cluster utilization |
| **Data Agent answer accuracy** | ≥ 90% on benchmark NL-to-data question set (curated, 100 questions per pilot) | Manual evaluation against gold answers |
| **Lineage capture** | End-to-end lineage visible in Purview from source Iceberg table to Fabric semantic model to Power BI report | Manual inspection |

A pilot **passes** if it meets all hard thresholds (latency, concurrency, governance) and at least 4 of 5 soft thresholds (mirroring freshness, costs, accuracy, lineage).

A pilot **fails** if any hard threshold is missed materially, or if a fundamental architectural defect is discovered (e.g., DirectQuery to Trino cannot enforce Ranger policies through the query path).

## Out of scope (explicit)

- Migration of existing Cortex Semantic Views to Fabric semantic models. Existing Cortex investments stay where they are. The pilot validates the new architecture, not the migration path.
- The Tier 2 Enterprise Conformance Tier (ADR-016). Pilot B touches a small cross-LOB case but does not implement the full conformance tier.
- Production rollout to LOB BI users. The pilot is run by the Lumina platform team with synthetic and curated workloads. Real LOB user rollout is Phase 2.
- Replacement of any existing BI tool (Tableau, OBIEE). Power BI is used for the pilot because it is the natural Fabric consumption surface; broader BI rationalization is a separate workstream.

## Team and effort

Estimated effort: 4–5 FTE-equivalent for 12 weeks.

| Role | FTE | Responsibility |
| --- | --- | --- |
| Pilot lead | 0.5 | Overall coordination, weekly reporting to Vinh |
| Fabric semantic model engineer | 1.0 | Build the semantic models for both pilots |
| Snowflake engineer | 0.5 | Configure Snowflake side for Pilot A, validate mirroring |
| Trino / lakehouse engineer | 1.0 | Configure Trino DirectQuery path, validate Ranger enforcement |
| Purview / governance engineer | 0.5 | Validate Purview integration and lineage capture |
| Performance engineer | 0.5 | Synthetic load testing, latency benchmarking |
| LOB SME (P&CB and Risk) | 0.5 | Curate benchmark question sets, validate answer accuracy |
| Pilot reporting / writeup | 0.5 | Documentation, results writeup, ADR-014 confirmation memo |

## Deliverables

1. **Pilot results report** — quantitative results against all success criteria, narrative analysis of what worked and what did not.
2. **Architecture confirmation memo** — formal recommendation to either confirm ADR-014 unchanged, amend it based on findings, or revisit if pilot fails.
3. **LOB rollout playbook** — a concrete how-to for subsequent LOBs based on what was learned, including configuration templates, performance tuning notes, and governance setup steps.
4. **Cost model** — empirical cost data for each pilot configuration, used to forecast Phase 2 rollout cost across all LOBs.
5. **Risk register update** — any new risks surfaced during the pilot, with mitigations.

## Decision points and exit criteria

The pilot has three decision gates:

**Week 4 — Architectural feasibility gate.** Can the Fabric semantic model successfully connect, query, and return correct results from both Snowflake (both A1 and A2) and Trino (B1)? If no, escalate immediately to ADR-014 review.

**Week 8 — Performance and governance gate.** Are latency, concurrency, and governance enforcement thresholds being met in early load testing? If no, decide whether to retune, reduce scope, or escalate.

**Week 12 — Final results gate.** All success criteria measured, pilot results report delivered, recommendation made.

## Stakeholder communication

- **Weekly:** Pilot lead status to Vinh, brief written update.
- **Bi-weekly:** Steering group with Vinh, Rex, EDW/EDL/Lakehouse domain leads.
- **Monthly:** Executive readout to broader Lumina governance forum.
- **Final:** Architecture confirmation memo to Vinh and Rex; pilot results presentation to broader D&A leadership.

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Fabric Mirroring of Snowflake not stable at pilot start | Medium | High for Pilot A2 | Hold Pilot A2 until Microsoft GA confirmation; Pilot A1 proceeds independently |
| Trino DirectQuery performance materially worse than expected | Medium | High for the on-prem story | Test Trino query optimization; consider Iceberg materialized views as a fallback |
| Purview lineage capture incomplete at the Fabric-to-Trino boundary | Medium | Medium | Document gaps explicitly; raise with Microsoft; do not block pilot pass on this alone |
| LOB SMEs unavailable for benchmark question curation | Low | Medium | Pre-confirm SME availability before pilot start; have backup SMEs identified |
| Pilot results inconclusive — neither clear pass nor clear fail | Medium | Medium | Pre-define what "inconclusive" looks like and what the next step is (extension vs. scope reduction) |
| Fabric capacity contention with other RBC Fabric workloads | Low | Medium | Provision dedicated Fabric capacity for the pilot |

## Open questions to resolve before pilot start

1. Which P&CB analytics dataset specifically for Pilot A? Recommend confirming with the P&CB CDO before pilot start.
2. Which counterparty-exposure dataset for Pilot B? Recommend confirming with Risk and the FSDM team.
3. Is Fabric Mirroring of Snowflake GA in Canada Central by Q3 2026? Validate with Microsoft account team.
4. Does the existing Trino cluster have headroom for the additional pilot load, or does the pilot need its own Trino capacity?
5. Who is the named pilot lead? Recommended: Gautam, but subject to his other Lakehouse priorities.

## Authorization

This pilot plan is contingent on ADR-014 ratification. Pending Vinh's and Rex's approval of ADR-014, the pilot is provisionally scoped for Q3 2026 start. Final go/no-go and resource commitment decision at the ADR-014 review meeting.
