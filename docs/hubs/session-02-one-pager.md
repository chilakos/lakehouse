---
title: Session 02 — One-Pager Handout
---

# Lumina Hub — How a DMO Ships a Data Product

**One page. Read in 90 seconds.**

---

## The promise

You declare what you want. The platform handles how. Bronze is the immutable floor. Silver and Gold are always rebuildable from Bronze. One read path for BI, AI, and analysts.

---

## What you touch

```
your-product/
├── product.yml          ← sources, schedule, owner, tests, sensitivity
├── silver/*.sql         ← clean + conform
├── gold/*.sql           ← business product
└── README.md            ← what this is, who uses it
```

**That's it.** You never edit `dbt_project.yml`, `profiles.yml`, CI workflows, or Helios job specs. CODEOWNERS keeps you out of the framework, by design.

---

## The authoring loop

| # | Command | What happens |
|---|---|---|
| 1 | `hub-cli init <product-name>` | Scaffolds the folder structure |
| 2 | Write `product.yml` + SQL | Declare sources, write business logic |
| 3 | `hub-cli validate` | Runs tests locally against dev Snowflake |
| 4 | Open PR | DMO peer review |
| 5 | `hub-cli promote --to uat` | Merged PR triggers UAT deployment |
| 6 | `hub-cli promote --to prod` | Hub Steward + cert check → live |
| 7 | `hub-cli rehydrate --as-of <date>` | Rebuild any product, any point in time |

---

## The data flow

```
┌─────────────────────┐    ┌─────────────────────┐
│   EDL Hive tables   │    │  EDW Teradata views │
└──────────┬──────────┘    └──────────┬──────────┘
           │                          │
           └─────────────┬────────────┘
                         │ Helios scheduled extract
                         ▼
              ┌─────────────────────┐
              │  BRONZE  (Iceberg)  │  immutable, append-only
              │  per-source tables  │  Iceberg snapshots = history
              └──────────┬──────────┘
                         │ your silver/*.sql (dbt under the hood)
                         ▼
              ┌─────────────────────┐
              │       SILVER        │  cleansed, conformed
              └──────────┬──────────┘
                         │ your gold/*.sql
                         ▼
              ┌─────────────────────┐
              │        GOLD         │  certified product
              └──────────┬──────────┘
                         │ hub-cli publish
                         ▼
              ┌─────────────────────┐
              │   HOSTING LAYER     │  platform-owned consumption
              │  (one read path)    │  BI · AI · Trino · Cortex
              └─────────────────────┘
```

---

## The rules that don't bend

1. **Bronze is immutable.** No updates. No deletes. Corrections are new rows with a later timestamp.
2. **Silver and Gold are derivable from Bronze.** Rehydration is one command.
3. **Tests are mandatory.** Uniqueness, not-null on keys, freshness. CI blocks promotion if they fail.
4. **You publish to the hosting layer. You don't grant access.** Entitlements route through OPA/Ranger.
5. **One physical Gold table per product.** BI, AI, and Trino read the same bytes. No copies, no drift.

---

## Who owns what

| You (DMO) | Platform |
|---|---|
| `product.yml`, SQL, tests, docs | dbt config, CI/CD, Helios jobs |
| Business logic and SLAs | Snowflake roles, warehouses, grants |
| Product-level PR approvals | Hub config, framework, certification |
| Choosing sources | Granting access to those sources |

---

## The success test

**Two weeks. SQL skills only. No dbt experience required. No platform engineer in the loop after onboarding.**

If you can't ship a certified product end-to-end inside that envelope, the design has failed. Tell us.

---

## Help

- `hub-cli --help` for commands
- `<hub-support-channel>` in Slack
- Hub Steward office hours: Wednesdays 2–3pm
- Docs: `docs.lumina.<company>.com/hubs`
