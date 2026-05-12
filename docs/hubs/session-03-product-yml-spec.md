---
title: Session 03 — product.yml Spec
---

# `product.yml` — Schema and Worked Example

**Author:** Enterprise Data leadership
**Status:** Draft for design session review
**Purpose:** The single declarative artifact a DMO authors per data product. Everything else (Helios jobs, dbt project files, CI workflows, registry entries) is generated from this.

---

## Design principle

`product.yml` is the **only** config file a DMO writes by hand. If they need to touch anything in `framework/`, `.github/workflows/`, `dbt_project.yml`, or `profiles.yml` to ship a product, the design has failed.

One file = one contract = one data product.

---

## Full schema

```yaml
# ─────────────────────────────────────────────────────────────
# 1. IDENTITY — who is this and who owns it
# ─────────────────────────────────────────────────────────────
apiVersion: lumina/v1
kind: DataProduct
metadata:
  name: client_household_exposure          # snake_case, unique per hub
  hub: wm                                  # wm | pcb | cm | ins | risk
  version: 1.0.0                           # semver; bump on breaking change
  description: >
    Total exposure per client household across all WM products,
    refreshed daily. Used by relationship managers and credit risk.
  tags:
    - household
    - exposure
    - credit-risk
  classification: confidential             # public | internal | confidential | restricted

owner:
  team: <dmo-team>                   # maps to GitHub team + AD group
  primary: jane.doe@example.com
  secondary: john.smith@example.com
  slack: "<dmo-slack-channel>"

# ─────────────────────────────────────────────────────────────
# 2. SOURCES — what this product pulls from
# ─────────────────────────────────────────────────────────────
sources:
  - name: edw_client_master
    type: edw_teradata                     # edw_teradata | edl_hive | hub_gold
    object: prod_edw.clients.client_master_v
    extract_pattern: incremental           # incremental | full_snapshot | cdc
    watermark_column: updated_ts
    schedule: "0 2 * * *"                  # cron, UTC; daily 2am
    bronze_table: bronze.edw_client_master # auto-generated if omitted
    retention:
      hot_days: 90
      cold_years: 7

  - name: edl_positions
    type: edl_hive
    object: edl_prod.wm.positions
    extract_pattern: full_snapshot
    schedule: "0 3 * * *"
    bronze_table: bronze.edl_positions
    retention:
      hot_days: 90
      cold_years: 7

  - name: pcb_household_dim                # cross-hub consumption of certified Gold
    type: hub_gold
    hub: pcb
    object: gold.household_dim
    extract_pattern: full_snapshot
    schedule: "0 4 * * *"
    bronze_table: bronze.pcb_household_dim

# ─────────────────────────────────────────────────────────────
# 3. BUILD — the Silver and Gold models the DMO writes
# ─────────────────────────────────────────────────────────────
build:
  silver:
    schedule: "0 5 * * *"                  # runs after all bronze extracts settle
    models:
      - name: clients_clean
        description: Deduped, type-normalized client records
        tests:
          - unique: client_id
          - not_null: [client_id, updated_ts]
      - name: positions_clean
        description: Position records joined to client_id
        tests:
          - not_null: [client_id, position_id, market_value]
          - relationships:
              to: clients_clean
              field: client_id

  gold:
    schedule: "0 6 * * *"                  # runs after silver
    models:
      - name: household_exposure
        description: One row per household with total exposure across products
        grain: one row per household_id per as_of_date
        tests:
          - unique: [household_id, as_of_date]
          - not_null: [household_id, total_exposure, as_of_date]
          - accepted_range:
              column: total_exposure
              min: 0
          - freshness:
              column: as_of_date
              warn_after: 25h
              error_after: 49h

# ─────────────────────────────────────────────────────────────
# 4. PUBLISH — how this product is served to consumers
# ─────────────────────────────────────────────────────────────
publish:
  hosting:
    snowflake_secure_view: true            # creates hosting.wm.household_exposure
    fabric_mirror: true                    # mirrors Gold to Fabric for Power BI
    iceberg_external_volume: true          # exposes to on-prem Trino + Cortex + Lumina Gateway
  consumers:                               # declarative entitlements (Hub Steward approves)
    - team: <rm-team>
      access: read
    - team: <risk-analytics-team>
      access: read
    - service: lumina-gateway
      access: read
      purpose: ai-agent-consumption

# ─────────────────────────────────────────────────────────────
# 5. GOVERNANCE — what compliance needs to know
# ─────────────────────────────────────────────────────────────
governance:
  data_domain: wealth-management
  regulatory_scope:
    - BCBS-239
    - OSFI-B-13
  pii: false
  contains_columns:
    - name: client_id
      classification: confidential
      masking: none
    - name: total_exposure
      classification: confidential
      masking: role-based
  retention_policy: 7-years                # tied to regulatory scope
  glossary_terms:
    - household
    - exposure
    - relationship_manager

# ─────────────────────────────────────────────────────────────
# 6. SLA — what we promise consumers
# ─────────────────────────────────────────────────────────────
sla:
  freshness: 24h                           # Gold no older than X
  availability: 99.5
  quality_score_min: 95                    # composite Soda score
  incident_response:
    p1: 2h
    p2: 8h
    p3: 2bd
```

---

## Field-by-field notes

### `metadata`
- `name` must be unique within the hub. `<hub>.<name>` is the global identifier.
- `version` follows semver. Breaking change = major bump = new hosting view alongside the old, with a deprecation window.
- `classification` drives default masking, retention, and access patterns. Lying here is a governance event.

### `owner`
- `team` maps to a GitHub team **and** an AD group. Both must exist before the product can be created. `hub-cli init` checks.
- Primary and secondary are humans, not aliases. Pager rotates between them.

### `sources`
- Three source types only: **`edw_teradata`** (read from EDW via Trino), **`edl_hive`** (read from EDL via Trino), **`hub_gold`** (read from another hub's certified Gold via the hosting layer).
- `extract_pattern` is the rehydration-fidelity knob:
  - `incremental` — watermarked. Captures changes between runs. Good for systems with reliable `updated_ts`.
  - `full_snapshot` — full table copy each run. Highest cost, simplest correctness.
  - `cdc` — streaming via Kafka. Per-change fidelity. Requires source-side CDC capability.
- `retention` defaults come from the hub. Override only with Hub Steward approval.

### `build`
- Silver and Gold schedules are declared, not coded. Helios generates the orchestration.
- Tests are first-class. CI blocks promotion if any test fails. No exceptions at the dev→UAT line.
- Test types supported: `unique`, `not_null`, `relationships`, `accepted_values`, `accepted_range`, `freshness`, `custom` (points to a SQL file).

### `publish`
- The DMO declares **what surfaces** the product is published to. They do **not** grant access.
- `consumers` is the entitlement request. Hub Steward approves the request, OPA/Ranger enforces.
- One physical Gold table. Multiple read paths. No copies.

### `governance`
- Required fields. Empty `regulatory_scope` is allowed but flagged in the certification check.
- `pii: true` triggers additional masking and access review on every PR.
- `glossary_terms` link to the enterprise business glossary; certification fails if a term doesn't exist.

### `sla`
- Concrete numbers, not adjectives. "Best effort" is not an SLA.
- Quality score is composite from Soda tests run at Silver→Gold boundary.
- Incident response tier maps to PagerDuty rotation defined per `owner.team`.

---

## What `hub-cli` generates from this file

When the DMO runs `hub-cli validate` or opens a PR, the platform generates:

1. **Helios extract jobs** — one per source, scheduled per `sources[].schedule`.
2. **dbt project structure** — `dbt_project.yml`, `profiles.yml`, sources file, schema tests.
3. **CI workflow** — `.github/workflows/<product>-ci.yml` runs validate + tests on every PR.
4. **Snowflake DDL** — Bronze tables with Iceberg properties (immutable, snapshot retention), Silver/Gold schemas, hosting layer views.
5. **OPA policies** — entitlement rules from `publish.consumers`.
6. **Catalog registration** — Purview entry, glossary linkage, lineage stubs.
7. **PagerDuty rotation** — from `owner` + `sla.incident_response`.

The DMO sees none of this. They see the product working.

---

## What changes break the contract (and require version bump)

- Removing or renaming a Gold column → **major**
- Changing a Gold column type → **major**
- Changing the grain of a Gold table → **major**
- Tightening an SLA → **minor** (consumers benefit)
- Adding a Gold column → **minor**
- Adding a new source for an existing Silver/Gold → **minor**
- Loosening an SLA → **patch with notification to consumers**
- Internal Silver refactor with no Gold change → **patch**

---

## Open design questions for the session

1. Should `sources[].extract_pattern` be DMO-settable or platform-defaulted per source type? *Lean: platform-default with override-on-approval.*
2. Should we allow inline SQL in `tests` for `custom` types, or force them to a `tests/*.sql` file? *Lean: separate files. Inline gets messy fast.*
3. Versioning: do we keep the old hosting view alive on major bumps, and for how long? *Lean: 90 days deprecation window, configurable per consumer.*
4. Cross-hub consumption (`type: hub_gold`) — does it always go through the hosting layer, or can it read the source hub's Gold directly via Iceberg external volume? *This is an ADR-011 follow-on question.*
