# 07 — CI/CD pattern

The hub pipeline mirrors the Helios pattern (GitHub Actions,
self-hosted runners on OpenShift) so platform engineering is not
learning a second model. The product-definition layer adds three
things on top: schema validation, lineage diffing, and a promotion
gate.

## Promotion stages

| Stage | Trigger | Approvers | What runs |
| --- | --- | --- | --- |
| **Dev** | Push to feature branch | None | Compile, test, lineage, sample data only |
| **UAT** | Merge to `main` | Peer in same DMO (CODEOWNERS) | Full run against UAT data, masked PII, lineage published to UAT catalog |
| **Prod** | Tagged release | Hub Steward; + Enterprise Data if `certified` or `cross-hub` | Production run, lineage to prod catalog, certified product registration, scheduled job activated |

## PR validate workflow

Excerpt from `.github/workflows/pr-validate.yml`:

```yaml
on: [pull_request]
jobs:
  validate:
    runs-on: [self-hosted, openshift, hub-runner]
    steps:
      - uses: actions/checkout@v4
      - name: Lint product.yml schema
        run: hub-cli lint products/${{ matrix.product }}
      - name: Compile dbt project
        run: hub-cli compile products/${{ matrix.product }}
      - name: Run tests in dev Snowflake schema
        run: hub-cli test products/${{ matrix.product }} --target dev
      - name: Generate lineage diff
        run: hub-cli lineage diff products/${{ matrix.product }}
      - name: Classification & PII enforcement check
        run: hub-cli policy products/${{ matrix.product }}
      - name: Naming convention check
        run: hub-cli naming products/${{ matrix.product }}
      - name: Cost estimate
        run: hub-cli cost-estimate products/${{ matrix.product }} --warn-above 50CAD/run
```

## Rehydration job

Rehydration is a parameterized version of the standard run, executed
as a one-shot Kubernetes job rather than a scheduled run. The
framework wraps Snowflake Time Travel calls so the SQL the DMO wrote
does not need to be aware of `as_of_date`.

```
# Conceptual pseudo-flow inside the framework
for date in date_range(as_of, through):
    set_session_query_tag(f"rehydrate:{product}:{date}")
    set_bronze_time_travel_pin(date)            # AT(TIMESTAMP => '...')
    dbt run --select silver.* gold.* --vars '{business_date: date}'
    emit_lineage_event(product, date, regenerated=true)
write_audit_record(product, as_of, through, git_sha, approver)
```

## Why the same pattern as Helios matters

1. **One operating model for the platform team.** They already run
   GitHub Actions on OpenShift for Helios. Same secrets management,
   same monitoring, same on-call rotation, same incident response
   runbooks.

2. **Audit trail is the same.** OSFI auditors get a complete picture
   from one control plane: who deployed what, when, with which
   approval, against which data, with which result. They do not need
   a Snowflake login to reconstruct it.

3. **Cost model is the same.** Compute on OpenShift is already
   chargeable to the hub's cost center. Snowflake compute is tagged
   with the hub and product via the query tag. Monthly hub cost
   reports reconcile both.

4. **Exit cost is bounded.** If the hub compute target ever changes
   (Iceberg-on-Trino, Fabric, Databricks for an LOB that wants it),
   the dbt adapter changes and the SQL dialect changes. The CI/CD,
   the authoring experience, the governance integration — all carry
   over.

## Why we are not running dbt inside Snowflake

Snowflake offers a dbt-native authoring experience (Workspaces / dbt
Projects on Snowflake). We are deliberately not using it for the hub
program. Three reasons:

1. **Vendor coupling at the authoring layer.** It binds the
   experience to Snowflake's UI and Snowflake's view of how dbt
   should work. This throws away dbt's portability — exactly the
   property that makes dbt a good choice in the first place.

2. **CI/CD fragmentation.** It would put hub deploys in Snowflake's
   control plane and Helios deploys in our own. Two operating
   models for the platform team, two audit trails, two failure
   modes. Exactly the spaghetti pattern we are trying to escape.

3. **Governance escapes the enterprise plane.** Lineage, run logs,
   audit, and observability would live inside Snowflake, requiring
   reverse-engineered exports to satisfy BCBS-239 and OSFI B-13.
   Running on our own infrastructure keeps the control plane ours.

dbt Core, on our runners, against Snowflake — same authoring
experience, none of the lock-in.
