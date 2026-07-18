# ADR-008: Microsoft Fabric OneLake — Shortcuts and XTable Not Adopted

**Status:** Superseded (see ADR-010)
**Date:** 2026-03-30
**Updated:** 2026-04-01
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)
**Raised by:** Platform evaluation — OneLake assessment (March 2026)

---

## Update (2026-04-01)

This ADR has been superseded by **ADR-010: Fabric Import Semantic Model as BI and AI Surface Layer**.

The original "Wait, Do Not Adopt" decision was correct for OneLake shortcuts and XTable
metadata virtualization — that position stands and is carried forward in ADR-010.

However, a separate evaluation concluded that **Microsoft Fabric's semantic layer in Import
mode** is the right BI and AI surface for Gold-layer consumption, specifically *without*
OneLake shortcuts. ADR-010 documents that decision in full.

**Summary of what changed:**
- OneLake shortcuts → S3/on-prem: ❌ Not adopted (this ADR stands)
- XTable Iceberg-to-Delta virtualization: ❌ Not adopted (this ADR stands)
- Direct Lake on shortcutted data: ❌ Not adopted (this ADR stands)
- Fabric Import semantic model (Delta copy of Gold): ✅ Adopted via ADR-010
- Fabric Data Agent → Azure AI Foundry → RBC Assist: ✅ Adopted via ADR-010

---

## Original Decision (2026-03-30)

**Do not adopt OneLake as a platform component via shortcuts or metadata virtualization.
Re-evaluate when specific conditions are met.**

---

## Original Rationale

### 1. Catalog fragmentation is the dealbreaker

OneLake has its own catalog and does NOT integrate with Nessie as an external catalog.
Adopting OneLake would create dual catalogs: Nessie as truth for Trino/open engines, and
OneLake's catalog for Fabric/Power BI. This is exactly the dual-governance problem our
Snowflake SWOT identified as weakness W4 (`docs/swot/data/snowflake-strategy.yml`). It
directly violates Principle 3.

### 2. Iceberg is second-class in Fabric via shortcuts

Fabric's native format is Delta Lake. Iceberg is supported via metadata virtualization
(Iceberg-to-Delta conversion via Apache XTable), with known limitations:
- Partition transforms `bucket[N]`, `truncate[W]`, `void` are not supported
- OneLake Table APIs are **read-only** (write support is roadmap)
- Metadata refresh lag between Iceberg source and Delta virtual layer
- RLS on shortcutted tables causes 403 errors across workspace boundaries
- Absolute path references in Iceberg metadata break if tables are moved

### 3. OneLake is cloud-only

OneLake cannot replace Pure Storage as on-prem storage. The on-prem story is "create shortcuts to
on-prem data via an On-Premises Data Gateway (OPDG)" — a Windows agent that must be
installed, patched, and monitored. This adds operational overhead without eliminating
the data copy problem.

### 4. S3-compatible shortcut auth is key/secret only

On-prem S3-compatible shortcuts only support key/secret authentication — no IAM delegation,
no Entra service principal. For RBC's OSFI B-13 posture this is a governance gap.

### 5. OneLake would be additive cost, not replacement

The existing infrastructure (Trino, Nessie, Ranger, Pure Storage) is still needed for non-Fabric
consumers. OneLake adds cost for the Power BI path only.

---

## Conditions for Re-Evaluation of Shortcuts

Re-evaluate OneLake shortcuts when **any** of the following conditions are met:

1. **OneLake Table APIs go read-write** and support external catalog delegation pointing
   to Nessie — this would eliminate the dual-catalog problem
2. **Direct Lake supports Iceberg natively** without Delta virtualization
3. **RLS works cleanly across OneLake-to-OneLake shortcut paths** without 403 errors
4. **S3-compatible shortcuts support Entra/IAM auth** instead of static key/secret

---

## Consequences

- No OneLake shortcuts deployed
- No XTable metadata virtualization in the critical path
- No OPDG Windows agents to manage
- Nessie remains the single catalog for all write operations and multi-engine reads
- See ADR-010 for how Fabric BI/AI consumption is achieved without shortcuts
