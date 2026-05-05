# 10 — Build plan

Realistic estimate to get the first hub live with the first three
products end-to-end.

| Phase | Duration | Outputs |
| --- | --- | --- |
| **Phase 0** — Design partner selection | 2 weeks | Pick one DMO (suggest WM, given existing relationships) and 2–3 starter products. Validate the `product.yml` schema against their real use cases. |
| **Phase 1** — Framework MVP | 6–8 weeks | `hub-cli` (init, validate, run, promote), `product.yml` schema validator, dbt project generator, GitHub Actions templates, Snowflake role/warehouse pattern, catalog registration hook |
| **Phase 2** — First hub live | 4 weeks | WM hub repo stood up, 3 products promoted to prod, monitoring and cost reporting wired, Hub Steward role formalized |
| **Phase 3** — Portal MVP | 6 weeks | Web portal exposing init / validate / promote / rehydrate; integrates with existing access request system |
| **Phase 4** — Second hub + escape-pattern review | 4 weeks | Second hub onboarded (P&CB), framework v2 incorporates lessons, escape patterns folded into schema |
| **Phase 5** — Federation + cross-hub publishing | 8 weeks | Trino federated read for Teradata views and Hive, cross-hub product subscription, contract enforcement |

## Total to MVP

Phase 0 + 1 + 2: roughly **12–14 weeks** with a team of 4 — one tech
lead, two engineers, one PM. The portal in Phase 3 can run in parallel
with Phase 4.

## What is in Phase 1 in detail

The framework MVP is the critical phase. It must include:

- **`hub-cli`** — init, validate, run, diff, promote (rehydrate
  deferred to Phase 3 portal)
- **Schema validator** — enforces `product.yml` correctness, fails CI
  on missing required fields
- **dbt project generator** — reads `product.yml` + `hub.yml`, emits a
  valid dbt project at compile time
- **GitHub Actions templates** — pr-validate, promote-uat,
  promote-prod, scheduled-runs
- **Snowflake setup** — role hierarchy, warehouse sizing tiers, query
  tag template, RBAC enforcement of Bronze immutability
- **Catalog registration hook** — programmatic API call to register a
  product on prod deploy (target tool TBD)
- **OpenLineage emission** — column-level lineage from dbt manifest

What is *not* in Phase 1:

- Rehydration (Phase 3, requires portal for cost gate)
- Cross-hub publishing (Phase 5)
- Portal (Phase 3)
- Federated read auto-extracts (Phase 5)

## Risk register for the build

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| `product.yml` schema needs many revisions after first DMO contact | High | Medium | Phase 0 explicitly validates schema with one DMO before Phase 1 build starts |
| Framework escape patterns proliferate before being folded in | Medium | High | Phase 4 dedicated to escape pattern review and consolidation |
| Catalog tool choice not finalized in time | Medium | Medium | Build catalog hook as a thin abstraction; specific tool integration is Phase 2 |
| OpenShift runner capacity insufficient | Low | Medium | Coordinate with Helios platform team early; reuse runner pool |
| Snowflake Time Travel cost on rehydrate | Medium | Low | Cost gate in portal; warn-above thresholds; quarterly review of rehydrate costs |
