# ADR-019: Dual-Site Data Hub Hosting — Iceberg on Cloud S3 and On-Prem with Per-Hub Write Affinity

**Status:** Proposed
**Date:** July 2026
**Author:** George Chilakos, VP Enterprise Data
**Reviewers:** Pending — Vinh (manager), Platform Engineering, Lakehouse Tech Lead
**Related:** ADR-003 (Teradata decoupling), ADR-009 (AI Data Hub), ADR-011 (Snowflake Cortex Phase 1), ADR-013 (Ingestion as platform capability), ADR-015 (RBC Data Gateway)

---

## Context

The lakehouse today writes once from the on-prem medallion pipeline (Bronze → Silver → Gold, Iceberg V2 on Pure Storage) and serves cloud consumers from that single copy — Snowflake via external volumes (zero-copy) and Fabric via a Delta copy in Phase 2. As data hubs come online, this single-site model breaks down in two directions:

1. **Cloud-resident consumers need cloud-local data.** Snowflake external volumes over on-prem object storage are not viable at scale; Cortex, Fabric, and Bedrock-hosted AI workloads perform and price acceptably only against S3-resident Iceberg.
2. **Hub write affinity varies.** Some hubs are produced by on-prem pipelines (Teradata-adjacent FSDM domains, mainframe-fed hubs) and need a cloud replica. Others are cloud-native (SaaS-sourced, API-fed, AI-enriched hubs) and need an on-prem replica for Trino consumers, Ranger-governed internal analytics, and residency/DR posture.

We therefore need a **symmetric dual-site hosting pattern**: every published hub exists as Iceberg on both AWS S3 and on-prem Pure Storage, with one site designated as writer per hub and the other as a read replica, synchronized at publish time.

Constraints:

- **No multi-writer Iceberg.** Iceberg has no cross-catalog conflict resolution; active-active writes to the same table from two sites is unsafe by construction.
- **WAP is the publish boundary.** All hub publishes go through write-audit-publish (Soda quality gates, reconciliation) before consumers see data. Replication must key off the WAP commit, not raw writes.
- **The catalog is the source of truth for the current snapshot.** Replicating object storage alone is insufficient — a replica site's catalog must be committed after files land, or readers see torn state.
- **Iceberg metadata embeds absolute file URIs.** Naive bucket replication across differing endpoints/bucket names produces metadata pointing at the wrong site.
- **Egress and bandwidth are material.** Full-medallion replication of a 1.5 PB estate is neither necessary nor affordable; scope must be limited to published hub tables.

---

## Decision

**Each data hub has exactly one designated writer site (on-prem or cloud, declared per hub in a hub registry). The opposite site hosts a read-only Iceberg replica, synchronized per publish: on WAP commit at the writer site, a replication job copies the new snapshot's data and metadata files to the replica site's object store and commits the snapshot into the replica site's catalog. Each site runs its native catalog — Gravitino on-prem, Snowflake Open Catalog (Polaris) in the cloud — bridged by the Iceberg REST protocol; replica tables are registered read-only.**

### Core pattern

```
Writer site (per hub: Pure Storage or S3)                Replica site
┌──────────────────────────────┐
│ Hub pipeline (Python ETL)    │
│   WAP branch → audit → PUBLISH ──┐
└──────────────────────────────┘   │  publish event (Airflow / OpenLineage)
                                   ▼
                        ┌────────────────────────┐
                        │ Hub Replicator          │
                        │ 1. Diff snapshots       │
                        │    (last replicated →   │
                        │     newly published)    │
                        │ 2. Copy delta data +    │
                        │    manifest files       │
                        │ 3. Rewrite metadata     │
                        │    URIs for target site │
                        │ 4. Commit snapshot to   │──▶  replica catalog commit
                        │    replica catalog      │     (readers flip atomically)
                        └────────────────────────┘
```

Properties:

- **Atomic on both sides.** Consumers at the replica site never see a partially copied publish — the replica catalog commit is the last step, mirroring WAP semantics.
- **Incremental.** Only files added since the last replicated snapshot move; snapshot diffing bounds transfer to the publish delta.
- **Snapshot history preserved.** Time travel and rollback work at both sites within the retained snapshot window.
- **Symmetric.** The same replicator runs in both directions; direction is a property of the hub, not the platform.

### Hub registry and write fencing

A hub registry (versioned in the lakehouse repo, enforced in CI and at the catalog) declares per hub: writer site, replica site, replication SLA, and table set. Write fencing is enforced natively per site: Ranger deny-write policies on replicated namespaces on-prem, and read-only principal roles in Polaris RBAC for replicated namespaces in the cloud. Changing a hub's writer site is a controlled promotion (drain publishes → final sync → flip registry → invert read-only flags), which doubles as the DR runbook.

### Catalog topology — heterogeneous by design

- **On-prem: Gravitino metalake.** Trino, governance automation (ADR-007), and the Data Gateway (ADR-015) bind here; Ranger enforces policy at query time.
- **Cloud: Snowflake Open Catalog (Polaris).** Snowflake warehouses and Cortex resolve replicated Iceberg tables natively; Polaris RBAC governs cloud-side access.
- **Iceberg REST is the bridge.** Both catalogs speak the Iceberg REST protocol, so one replicator codepath commits snapshots into either side without engine-specific plumbing.
- **No synchronous cross-site dependency.** Each site's readers resolve tables against their local catalog; a WAN partition degrades replication lag, never availability.
- **Replica registration, not federation.** The replicator commits real snapshots into the replica-site catalog. Gravitino may additionally federate Polaris as a foreign catalog for a single metadata pane of glass, but no query path depends on it.

### Scope

Replication covers **published hub tables (Gold and hub-published Silver marts) and the AI Data Hub serving tier where a hub's consumers span sites**. Bronze and working Silver stay single-site with the writer. (Assumption to confirm — see Open Questions.)

### Implementation

The Hub Replicator is a PyIceberg-based service in the existing ETL framework (consistent with ADR-005: Python, not engine-based copies), triggered by publish events from Airflow, emitting OpenLineage events so replicated tables carry provenance, and monitored in Grafana with per-hub replication-lag SLOs. Transfer path: Pure Storage ↔ S3 over Direct Connect, TLS, object checksums verified before catalog commit.

---

## Alternatives considered

**Bucket-level replication (S3 CRR / Pure Storage object replication).** Rejected as the primary mechanism. It is catalog-unaware: no ordering guarantee that data files land before metadata, no replica catalog commit, and absolute URIs in Iceberg metadata break when endpoints differ. Acceptable only as a bulk-seed accelerator for initial hydration.

**Active-active (both sites writable per hub).** Rejected. Iceberg offers no cross-catalog optimistic concurrency; conflict resolution would have to be invented and audited. Per-hub write affinity delivers the same business outcome (each hub authored where it naturally lives) without split-brain risk.

**Engine-based copy (CTAS / incremental MERGE via Trino or Snowflake).** Rejected. Recomputes rather than copies — burns compute, loses snapshot lineage and history, and creates a second logical table rather than a replica of the same one.

**One catalog technology stretched across both sites** (Gravitino extended to cloud, or Polaris adopted on-prem). Rejected. It couples both sites' availability to the WAN and one deployment, forfeits Snowflake's native Polaris integration on the cloud side, and displaces Gravitino as the on-prem control plane that ADR-007/015 already bind to. Heterogeneous catalogs bridged by Iceberg REST keep each site on its best-fit native stack.

**Vendor-managed replication (e.g., Snowflake-managed Iceberg, OneLake shortcuts).** Rejected as the general mechanism — ties the hub topology to one consumer's platform and doesn't serve the on-prem-replica direction. Individual consumers may still layer their own access patterns (external volumes, shortcuts) over the replica.

---

## Consequences

**Positive**
- Cloud AI/BI consumers (Cortex, Fabric, Bedrock workloads) get S3-local Iceberg; on-prem Trino and Ranger-governed analytics get Pure-Storage-local Iceberg — no cross-site query hops.
- Publish-consistent replicas: replica freshness equals publish cadence, which is the freshness consumers already accept.
- The writer-flip runbook gives every hub a tested DR promotion path.
- Symmetry future-proofs the platform as more hubs go cloud-native during the Cloudera exit.

**Negative / costs**
- A new platform service to build and operate (replicator, hub registry, lag SLOs, alerting).
- Storage is paid twice for replicated tables; egress costs scale with publish deltas — requires per-hub sizing before onboarding large hubs.
- Snapshot retention and maintenance (compaction, expire-snapshots) must be coordinated so the replicator's diff base is never expired at the writer before replication completes.
- Ranger/classification policy parity across sites becomes a hard dependency — extends the ADR-007 governance automation pipeline to dual-site.
- Two catalog technologies means two RBAC models (Ranger vs. Polaris roles) and two operational surfaces; policy-as-code must generate both from one source or they will drift.

---

## Open questions

1. **Scope confirmation:** Gold + published marts only, or do any hubs require full-medallion replication (e.g., for cloud-side reprocessing)?
2. **Residency and PII:** which hubs are cleared for cloud-resident copies under OSFI/data-residency and internal classification rules? Does any hub require masking or column pruning in its cloud replica (a filtered replica variant of this pattern)?
3. **Egress sizing:** projected publish-delta volumes per candidate hub, to validate Direct Connect capacity and cloud egress budget.
4. **Snapshot retention window** at replicas vs. writers, and interaction with maintenance jobs.
5. **Fabric Phase 2:** does the S3 replica retire the Gold→Delta OneLake copy (shortcut over S3 Iceberg instead), simplifying ADR-010/011 plumbing?
