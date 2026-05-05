# 08 — Governance and enterprise control hooks

The product-definition layer is also where enterprise controls plug
in — without leaking complexity into the DMO's view.

| Control | Hook | DMO experience |
| --- | --- | --- |
| **Classification & PII (PIPEDA)** | `metadata.classification` + `metadata.pii` drive automatic masking macros applied during Silver materialization | Set the flags. Framework enforces. |
| **BCBS-239 lineage** | `metadata.regulatory_tags` drives required lineage capture and end-to-end traceability assertions | Tag the product. Framework asserts lineage completeness in CI. |
| **OSFI B-13 (third-party data risk)** | `sources.access=federated` for Teradata/Hive routes through governed Trino with central audit; copied sources require source classification match | Choose access mode in `product.yml`. Framework refuses mismatched classifications. |
| **Access management** | `publish.consumers` + classification drive RBAC grants in Snowflake automatically; no manual GRANT statements | Declare known consumers. Framework grants. Catalog handles ad-hoc requests. |
| **Data retention** | `metadata.classification` maps to a retention policy applied as a Snowflake table TAG | Implicit. Override available with Hub Steward sign-off. |
| **Cost attribution** | `hub.yml` binds the hub to a Snowflake warehouse and a cost center; every product run carries a query tag with product name + cost center | Visible in monthly hub cost report. No DMO action needed. |
| **Catalog certification** | `publish.certified=true` triggers certification flow on prod deploy; uncertified products are visible only inside the hub | One flag. Framework handles registration. |

## Why this works

The DMO declares intent in `product.yml`. The framework translates
intent into enforcement. The DMO never writes a GRANT statement, never
configures a retention policy, never registers a product in the
catalog manually.

The controls are not optional — they are part of the contract between
the DMO and the platform. CI fails if the controls are not satisfied.
You cannot promote a product to prod with `pii: true` declared but no
masking applied; the framework checks.

This is what makes self-service compatible with regulated environments.
The DMO gets speed. The bank gets compliance. Neither has to compromise.

## What the catalog needs to do

The catalog (whichever tool we land on) needs to support:

- **Programmatic registration** — products register themselves on prod
  deploy via API, not via humans clicking through a UI
- **Certification states** — products move from "internal" to
  "certified" via a deploy event, with provenance to the Git commit
- **Column-level lineage** — required for BCBS-239
- **Tag-based policy** — classification, PII, regulatory tags flow from
  `product.yml` to catalog tags, which downstream tools can read
- **Contract notifications** — when a product declares a breaking
  change, the catalog notifies declared consumers

Catalog tool choice is open — see [`11-open-questions.md`](/lakehouse/hubs/11-open-questions/).
