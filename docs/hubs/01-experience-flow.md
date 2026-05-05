# 01 — Experience flow

A walkthrough of the DMO experience using a concrete example: Jane, a
WM DMO analyst, is building a Gold product called
`client_household_exposure`.

## Day 1 — Discover and scaffold

1. Jane opens the hub portal and searches the catalog for sources she
   needs (Bronze tables landed by Helios, Teradata views via federated
   read, Hive tables in the EDL, EDLH conformed dimensions).
2. Confirms entitlements. Requests access where missing — flows through
   the existing access request pipeline, not a new one.
3. Clicks **New Data Product**. Portal prompts for: name, domain, owner,
   classification, refresh cadence, business description.
4. Portal scaffolds a folder in the WM hub repo with `product.yml`,
   empty `silver/` and `gold/` folders, README, and a CODEOWNERS entry.
   Branch is created from `main`.

## Day 2–5 — Author

5. Jane prototypes SQL in a Snowflake worksheet against Bronze and
   EDLH sources. Validates results visually.
6. Pastes finished queries into:
   - `silver/clients_clean.sql`
   - `silver/positions_clean.sql`
   - `gold/household_exposure.sql`
7. Edits `product.yml`: declares sources with version pins, declares
   tests (uniqueness on `household_id`, not-null on FK columns,
   freshness ≤ 24h, referential integrity to the customer dimension),
   declares the Gold schema.

## Day 6 — Validate

8. Runs `hub validate client_household_exposure` from the portal or
   laptop CLI.
9. Framework executes dbt against Jane's dev Snowflake schema, runs all
   tests, generates a lineage diagram, posts row counts and test
   results back.
10. Failures point at the offending model and rule. Jane fixes SQL,
    reruns.

## Day 7 — Promote to UAT

11. Jane opens a PR (or clicks **Promote** in the portal, which opens
    the PR for her).
12. CI runs: SQL lint, dbt compile, tests in dev, lineage diff,
    classification check, naming-convention check.
13. A designated peer in the same DMO reviews the SQL and approves.
    CODEOWNERS auto-routes.
14. Merge triggers UAT deploy. The product runs in UAT against a UAT
    Snowflake schema with masked data.

## Day 8 — Promote to Prod

15. UAT results validated by Jane and a peer. Click **Promote to Prod**.
16. Approval gate: Hub Steward sign-off (one click). For products
    classified as regulatory or "reused by other hubs", a second
    approval from Enterprise Data is required.
17. Framework deploys to Prod. Product runs on its declared schedule.
    Lineage flows to the catalog. Gold table is registered as a
    certified data product.

## Six months later — Rebuild and rehydrate

18. Methodology change: household rollup logic is updated. Jane edits
    `silver/clients_clean.sql`, opens a PR, ships the same way.
19. To rebuild historical values:
    ```
    hub rehydrate client_household_exposure \
      --as-of 2026-03-15 \
      --through 2026-05-02 \
      --reason "Methodology update RFI-2026-1142"
    ```
20. Framework parameterizes the load_ts cutoff against Bronze using
    Snowflake Time Travel, runs Silver and Gold for each day in the
    window, and writes results to the Gold table with a regeneration
    tag. The new methodology applied to historical data is
    audit-traceable to the Git commit that introduced it.

See [`05-rehydration.md`](./05-rehydration.md) for the rehydration
mechanic in detail.

## What is *not* in this flow

- No Jinja editing
- No `dbt_project.yml` or `profiles.yml` management
- No manual Snowflake GRANT statements
- No manual catalog registration
- No separate dbt CLI commands from a terminal (unless the user is in
  the analytics-engineer tier and prefers it)

The framework absorbs all of these.
