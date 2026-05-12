---
title: Session 01 — Opening Bullets
---

# Hub UX Design Session — Opening Bullets

**Author:** Enterprise Data leadership
**Audience:** Hub design partners, DMO leads, Platform Engineering
**Purpose:** Open the design session with a shared frame of what we're solving
**Related:** ADR-013, ADR-014, ADR-015, Data Hub Architecture v2

---

## Frame the session in one line

A DMO walks into the hub with a problem to solve. By the end of the session we should know what they touch — and only what they touch — to get from *"I need Customer X data"* to *"my Gold product is live and certified."*

---

## 1. Sources the DMO pulls from (the inputs)

- DMO sees a **source catalog** inside the hub portal listing every EDL Hive table, EDW Teradata view, and certified Gold product from other hubs they have entitlement to.
- They never write extract code. They pick a source, declare it in `product.yml`, and the platform handles the rest.
- One declarative artifact per product — sources, schedule, tests, owner, sensitivity class — that becomes the contract.

---

## 2. Bronze landing (Helios-driven extract)

- Helios extends from its current ingestion role to **hub-scoped extract jobs** — same scheduling, same git-ops, same observability the team already knows.
- Pattern: `EDL/EDW source → Trino read → Snowpipe/COPY INTO → bronze.<source>_<table>` in the hub's Snowflake account.
- Bronze is **immutable, append-only, schema-enforced** with `source_system`, `ingestion_ts`, `batch_id` metadata columns.
- DMO does not write the Helios job — the platform generates it from `product.yml`. The DMO sees a green check that Bronze landed.
- **Open question for the room:** per-DMO Bronze tables or a shared Bronze pool the hub catalogs by source? Lean is per-product Bronze to keep blast radius small, but it costs storage.

---

## 3. Bronze is the floor — never rehydrated

This is the architectural keystone. If Bronze can be rehydrated from somewhere else, that somewhere else is the real Bronze and we've just moved the problem up one layer.

Three properties must hold together:

1. **Immutable** — once a row lands, it's never updated or deleted. New data is appended with new `ingestion_ts` and `batch_id`. Iceberg V2 row-level deletes are *disabled* on Bronze tables by table property. Hard configuration, not convention.
2. **Append-only with full change capture** — every extract pulls a snapshot or CDC delta and appends. If EDW changes a customer record three times in a day, Bronze has all three versions stamped with `ingestion_ts`.
3. **Iceberg snapshots = free time travel** — every commit creates a snapshot. Query Bronze "as of snapshot 47" or "as of 2026-03-15 14:32 UTC" natively.

Together, these mean **Bronze IS the change history**. No separate change records table — the append-only physics plus Iceberg snapshots ARE the change history.

### The rehydration guarantee is bounded by the extract pattern, not Bronze itself

| Source type | Default pattern | Bronze fidelity | Default snapshot retention |
|---|---|---|---|
| EDW Teradata view | Daily incremental on `updated_ts` | Daily | 90 days hot, 7 years cold |
| EDL Hive table | Daily full snapshot | Daily | 90 days hot, 7 years cold |
| Mainframe CDC | Streaming via Kafka | Per-change | 7 years hot |
| Reference data | Weekly full snapshot | Weekly | 7 years hot |

DMOs override defaults in `product.yml` only with Hub Steward approval.

### Don't "fix" bad data in Bronze

If an upstream system sent garbage, garbage lands in Bronze with a timestamp. The fix is a correction record appended later — never an UPDATE to the original row. This is BCBS 239 Principle 3 (Accuracy and Integrity) territory. The "waste" of append-only is the audit trail. Don't trade it away.

---

## 4. Silver and Gold authoring (dbt under the hood, Helios on top)

- DMO writes **SQL only** — `silver/*.sql` and `gold/*.sql` — referencing Bronze via `{{ source() }}` and other Silver via `{{ ref() }}`.
- They never edit `dbt_project.yml`, `profiles.yml`, or `.github/workflows/`. CODEOWNERS protects the framework.
- `hub-cli` provides the loop: `init`, `validate`, `run`, `promote`, `rehydrate`.
- Helios orchestrates the dbt runs on a schedule declared in `product.yml` — same orchestration plane the team uses for Bronze extracts, so one mental model.
- Tests mandatory at Silver→Gold boundary (uniqueness, not-null on keys, accepted values, freshness). CI fails the promotion if tests fail. **No human override at the dev→UAT line.**
- **Rehydration is a first-class command:** `hub-cli rehydrate gold.household_exposure --as-of 2026-03-15` rebuilds Gold from Bronze at that point in time. This is what makes Bronze-as-immutable a real feature, not a slogan.

---

## 5. Promotion and certification

- Three environments: **dev** (DMO sandbox) → **UAT** (hub UAT account) → **prod** (hub Prod account).
- Promotion is a PR + approval, not a ticket.
  - Dev → UAT: DMO peer review.
  - UAT → Prod: Hub Steward + automated certification check (contract conformance, lineage emitted, governance tags present, quality gates green).
- Certified Gold products **auto-register in the data product registry** — discoverable by other hubs and consumers.

---

## 6. The hosting layer (where Gold gets served)

This is the piece the room should land hardest on. Gold tables in the hub are the production data, but the **consumption surface is platform-controlled, not DMO-controlled**.

Options on the table:

- **Snowflake secure views** in a `hosting.<hub>.<product>` schema, RBAC governed by the platform, DMO grants visible but not edit-able.
- **Fabric mirroring** of Gold for BI consumption via Power BI / Tableau without ETL.
- **Iceberg external volume** so on-prem Trino, Lumina Gateway, and Cortex Analyst can all read the same physical Gold without re-copy.

The DMO **publishes** to the hosting layer through `hub-cli publish` — they do not get to grant access directly. Entitlements route through OPA/Ranger and the existing entitlement service.

This is also where Lumina Gateway picks up the Gold for AI consumption — **one read path for BI, AI, and analyst tools**.

---

## 7. What the platform owns vs what the DMO owns (the wall to defend)

| DMO owns | Platform owns |
|---|---|
| `product.yml`, `silver/*.sql`, `gold/*.sql`, tests, docs | `dbt_project.yml`, `profiles.yml`, CI/CD, Helios job specs |
| Business logic, semantics, SLAs | Snowflake roles, warehouses, grants, hosting layer |
| PR approvals within their product | Hub-level config, framework upgrades, certification |
| Choosing sources to subscribe to | Granting access to the sources |

---

## 8. Questions to put to the team in the session

1. Do we accept **dbt as the engine** but hide it behind `product.yml` + `hub-cli`, or expose dbt directly to advanced DMOs?
   *Lean: hide it. The "thin product layer" is the whole UX story.*
2. **Helios for both** Bronze extract orchestration and Silver/Gold dbt runs — one orchestration plane — or split it?
   *Lean: one plane. Two mental models is the failure mode.*
3. Where does rehydration run — on the DMO's dev warehouse or a platform-owned rehydration warehouse?
   *Cost vs isolation tradeoff.*
4. Do we commit to **Iceberg external volume as the canonical Gold storage** so BI, AI, and on-prem Trino all read the same bytes?
   *This is the ADR-011 thread pulled through to the hub model.*

---

## 9. The success test for the design

- A net-new DMO with SQL skills and zero dbt experience can ship a certified Gold product end-to-end in **under two weeks** with no platform engineer in the loop after onboarding.
- A rerun of any Gold product from any point in time is a **single command**, fully reproducible.
- Every consumption surface (Power BI, Tableau, Lumina Gateway, Cortex Analyst, Trino) reads the same physical Gold — no parallel copies, no drift.
