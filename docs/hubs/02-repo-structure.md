# 02 — Repository structure

One Git repo per hub, owned by the LOB DMO with platform team as
code-owners on framework files. The structure is opinionated — the
framework relies on it.

## Layout

```
wm-hub/                                    # one repo per hub (WM, P&CB, Capital Markets, etc.)
├── README.md
├── CODEOWNERS                             # framework files require platform review
├── .github/
│   └── workflows/
│       ├── pr-validate.yml                # runs on every PR
│       ├── promote-uat.yml                # runs on merge to main
│       ├── promote-prod.yml               # runs on tagged release
│       └── scheduled-runs.yml             # cron for prod product runs
├── hub.yml                                # hub-level config (owner, env, Snowflake account, warehouses)
├── framework/                             # platform-team-owned, locked via CODEOWNERS
│   ├── macros/                            # standard dbt macros (PII masking, audit cols, FSDM joins)
│   ├── tests/                             # custom generic tests (BCBS-239 lineage, OSFI freshness)
│   └── templates/                         # cookiecutter templates for new products
├── products/                              # DMO-owned — one folder per data product
│   ├── client_household_exposure/
│   │   ├── product.yml                    # the single authoring artifact
│   │   ├── silver/
│   │   │   ├── clients_clean.sql
│   │   │   └── positions_clean.sql
│   │   ├── gold/
│   │   │   └── household_exposure.sql
│   │   ├── docs/
│   │   │   ├── README.md                  # business description, methodology
│   │   │   └── lineage.svg                # auto-generated, committed for review
│   │   └── tests/                         # optional product-specific custom tests
│   │       └── test_no_orphan_households.sql
│   ├── advisor_book_summary/
│   └── ...
├── shared/                                # hub-level reusable models and seeds
│   ├── seeds/
│   │   └── product_taxonomy.csv
│   └── models/
│       └── ref_advisor_dim.sql
├── dbt_project.yml                        # generated, do not edit
├── profiles.yml                           # generated, do not edit
└── .hubcli/
    └── lockfile.json                      # framework version pin, ensures reproducibility
```

## What is hand-authored vs generated

| File / folder | Authored by | Notes |
| --- | --- | --- |
| `product.yml` | DMO | The single authoring artifact. Everything else is derived. |
| `silver/*.sql`, `gold/*.sql` | DMO | Plain SQL. No Jinja required for ~90% of products. |
| `docs/README.md` | DMO | Methodology and business context. Required for promotion. |
| `docs/lineage.svg` | Generated | Built from dbt manifest on every CI run. Committed for visual diff in PR review. |
| `dbt_project.yml`, `profiles.yml` | Generated | Framework owns. Regenerated on every CI run from `hub.yml` + `product.yml`. DMOs never edit. |
| `framework/` | Platform team | Locked via CODEOWNERS. Framework upgrades land via platform-team PRs. |
| `hub.yml` | Hub Steward + Platform team | Edited rarely. Defines hub identity and Snowflake binding. |

## Why one repo per hub

Three reasons:

1. **Blast radius.** A bad PR in WM cannot break P&CB's products.
   Repo-level CODEOWNERS, branch protection, and CI all scope to one
   hub.

2. **Ownership clarity.** The repo *is* the hub. The Hub Steward is the
   repo owner. The DMO leads are the senior reviewers. There is no
   ambiguity about who decides.

3. **Independent release cadence.** WM can ship a product change
   without waiting for P&CB's CI to pass. Each hub moves at its own
   pace.

The trade-off is shared models — `shared/` exists for hub-level reuse,
but cross-hub reuse goes through the catalog as a certified product, not
through code sharing. This is intentional.
