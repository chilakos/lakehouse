# ADR-008: Microsoft Fabric OneLake — Wait, Do Not Adopt

**Status:** Accepted (Wait)
**Date:** 2026-03-30
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)
**Raised by:** Platform evaluation — OneLake assessment (March 2026)

---

## Context

Microsoft Fabric OneLake was evaluated as a potential addition to the lakehouse architecture.
The question: does OneLake provide value beyond the existing S3/MinIO + Nessie + Trino stack,
particularly for Power BI consumers?

The current stack follows strong first principles (documented in `docs/FIRST_PRINCIPLES.md`):
- **Principle 1 (Single Copy, Many Readers):** Data written once in Iceberg, read by any engine
- **Principle 3 (Own Your Destiny):** Open formats, open catalogs, no single vendor lock-in
- **Principle 4 (Bring Your Own Compute):** Storage does not dictate compute

---

## Decision

**Do not adopt OneLake as a platform component. Re-evaluate when specific conditions are met.**

---

## Rationale

### 1. Catalog fragmentation is the dealbreaker

OneLake has its own catalog and does NOT integrate with Nessie as an external catalog.
Adopting OneLake would create dual catalogs: Nessie as truth for Trino/open engines, and
OneLake's catalog for Fabric/Power BI. This is exactly the dual-governance problem our
Snowflake SWOT identified as weakness W4 (`docs/swot/data/snowflake-strategy.yml`). It
directly violates Principle 3.

### 2. Iceberg is second-class in Fabric

Fabric's native format is Delta Lake. Iceberg is supported via metadata virtualization
(Iceberg-to-Delta conversion), with known limitations:
- Partition transforms `bucket[N]`, `truncate[W]`, `void` are not supported
- OneLake Table APIs are **read-only** (write support is roadmap)
- Metadata refresh lag between Iceberg source and Delta virtual layer
- No private link support for Iceberg virtualization

This contradicts the Iceberg-everywhere strategy.

### 3. OneLake is cloud-only

OneLake cannot replace MinIO as on-prem storage. The on-prem story is "create shortcuts to
on-prem data" (preview), not "run OneLake on-prem."

### 4. Power BI already works through Cube

Power BI connects via Cube's PostgreSQL wire protocol (port 15432) today. This path provides
metric governance that Direct Lake does not. While Direct Lake offers faster dashboard
refresh (VertiPaq reads Parquet directly), Cube provides consistent metric definitions across
all BI tools.

### 5. OneLake would be additive cost, not replacement

The existing infrastructure (Trino, Nessie, Ranger, MinIO) is still needed for non-Fabric
consumers. OneLake adds cost for the Power BI path only:
- OneLake storage (~$0.023/GB/month)
- Fabric capacity (F32 at ~$2,760/month for 16hr/day)
- Power BI Pro/Premium licenses
- Operational overhead of managing shortcuts and monitoring virtualization health

---

## What OneLake Actually Offers Today (GA vs Roadmap)

| Capability | Status | Notes |
|---|---|---|
| OneLake storage (ADLS Gen2 under the hood) | GA | ~$0.023/GB/month |
| Shortcuts to S3/ADLS/GCS | GA | Zero-copy pointers to external storage |
| Iceberg-to-Delta metadata virtualization | GA | Read-only, partition limitations |
| Direct Lake for Power BI | GA | VertiPaq reads Delta Parquet directly |
| OneLake Table APIs (Iceberg REST) | GA | **Read-only** — write support on roadmap |
| Shortcuts to on-prem data | Preview | Not production-ready |
| OneLake security (ReadWrite controls) | Preview | Not production-ready |
| External catalog integration (Nessie) | Not available | OneLake uses its own catalog only |
| Iceberg native in Direct Lake | Not available | Requires Delta virtualization |

---

## Conditions for Re-Evaluation

Re-evaluate OneLake when **any** of the following conditions are met:

1. **OneLake Table APIs go read-write** and support external catalog delegation (pointing
   to Nessie) — this would eliminate the dual-catalog problem
2. **Direct Lake supports Iceberg natively** without Delta virtualization — aligns with
   the Iceberg-everywhere strategy
3. **Power BI performance through Cube becomes a concrete blocker** — i.e., evidence that
   sub-second dashboard refresh is a hard requirement that Cube pre-aggregations cannot meet
4. **Fabric Iceberg partition support** covers the partition strategies used in the lakehouse

---

## If Power BI Performance Becomes Critical (Contingency)

The integration pattern that best preserves openness:

1. Keep Nessie as the single catalog for all write operations and multi-engine reads
2. Create OneLake shortcuts pointing at Gold-layer Iceberg tables in MinIO/S3 (read-only)
3. Use Direct Lake only for specific dashboards requiring sub-second refresh
4. Keep Cube as the primary BI path for metric governance
5. Do NOT migrate writes or catalog operations to OneLake/Fabric
6. Automate shortcut creation via Fabric REST APIs when new Gold tables appear in Nessie

This gives Direct Lake performance without surrendering catalog control. But it carries
operational cost: managing shortcuts, monitoring virtualization health, running two systems.

---

## Consequences

- No OneLake infrastructure to deploy or maintain
- Power BI continues through Cube's PostgreSQL wire protocol
- No Fabric capacity licensing cost
- Architecture remains fully open-source and vendor-independent
- Must monitor OneLake roadmap for the conditions above (quarterly review)
