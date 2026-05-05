# 06 — CLI and portal

DMOs use a small CLI (or its web-portal equivalent) for the entire
authoring loop. The command set is deliberately narrow.

## CLI commands

| Command | What it does | Where it runs |
| --- | --- | --- |
| `hub init <product-name>` | Bootstraps a new product from the template. Prompts interactively for metadata, scaffolds the folder, opens the branch. | Local or portal |
| `hub validate <product>` | Compiles dbt against dev Snowflake schema, runs all tests, generates lineage SVG, prints row counts and test results. | Local or portal |
| `hub run <product>` | Executes the product end-to-end (Silver → Gold) in dev. Used for iteration before opening a PR. | Local or portal |
| `hub diff <product>` | Shows what changes between current branch and main: schema diffs, test diffs, lineage diffs, sample row deltas. | Local or portal |
| `hub promote <product> --to <env>` | Opens the PR with the right reviewers and approvals. Wraps the Git/PR ceremony. | Local or portal |
| `hub rehydrate <product> --as-of <date> --through <date>` | Rebuilds Gold over a historical window from Bronze. Uses Snowflake Time Travel for source pinning. | Portal only (cost gate) |
| `hub deprecate <product> --replace-with <other>` | Initiates the contract deprecation flow. Notifies declared consumers. Sets retirement date. | Portal only |
| `hub catalog publish <product>` | Forces a re-publish to the catalog. Usually automatic on prod deploy; this is the manual override. | Local or portal |

## Why both a CLI and a portal

The CLI is for analytics-engineer-tier users who already work in a
terminal. The portal exposes the same commands as buttons and forms
for DMO-tier users who don't. Both call the same backend API.

There is no command in the CLI that is not also in the portal — and
vice versa — except `hub rehydrate`, which is portal-only because of
the cost approval gate.

## Portal navigation

```
Home
├── My Products              (products this user owns or contributes to)
├── Sources                  (unified Teradata / Hive / EDLH browser)
├── Catalog                  (all certified products across all hubs)
├── Approvals                (queue for Hub Stewards and Enterprise approvers)
├── Cost                     (per-product, per-hub usage and forecast)
└── Help
    ├── Templates
    ├── Framework changelog
    └── Submit feedback
```

## Authentication and identity

- All CLI calls use the user's RBC SSO identity (token cached locally,
  refreshed via the existing identity provider)
- Portal uses the same SSO
- Snowflake access is via the user's role mapped from AD group; the
  framework never embeds credentials in the product or the repo
- Service principals for scheduled runs and extracts are managed by
  the platform team, rotated on the standard schedule
