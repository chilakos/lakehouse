# Databricks Architecture Review

**Purpose:** Evaluate Databricks / Unity Catalog as a potential component of or
alternative to the RBC Lakehouse architecture.  
**Conclusion:** Not recommended for adoption. Databricks creates the same Ranger
governance gap as Snowflake, introduces a competing catalog to Nessie, and adds
significant proprietary lock-in risk incompatible with RBC's open stack strategy.

---

## What Databricks Is

Databricks is a commercial data and AI platform built primarily on Apache Spark.
Its governance layer is **Unity Catalog** — a proprietary (though open-sourced in
2024) metadata catalog that manages Iceberg, Delta Lake, and other table formats.

As of June 2025, Unity Catalog adds full support for Apache Iceberg tables,
including native support for the Apache Iceberg REST Catalog APIs, meaning
it can function as an alternative to Nessie for Iceberg table management. The key
difference: Unity Catalog is a Databricks-controlled product, not an independent
open-source catalog like Nessie.

---

## Technical Compatibility with RBC's Stack

### Databricks + Nessie: Competing catalogs, not complementary

Nessie and Unity Catalog are both Iceberg REST catalog implementations. They serve
the same role — managing table metadata — and cannot be used together on the same
tables without significant complexity.

If Databricks were adopted at RBC, you would face a choice:
- **Databricks uses Nessie** → possible technically (Databricks Spark can connect to
  a Nessie REST endpoint), but Unity Catalog governance features are not applied
  (Databricks would want you on Unity Catalog)
- **Databricks uses Unity Catalog** → Nessie is sidelined; Trino must connect to
  Unity Catalog instead of Nessie; the migration tooling built around Nessie branching
  is lost
- **Two catalogs in parallel** → unsustainable operationally; table ownership becomes
  ambiguous; lineage gaps guaranteed

RBC has already committed to Nessie as the catalog layer (ADR-001). Adopting Databricks
would require re-evaluating that decision and absorbing significant migration cost.

### Databricks + Apache Ranger: The same governance gap as Snowflake

This is the decisive issue. When Databricks Spark or Databricks SQL reads from your
Iceberg tables, it uses Unity Catalog's credential vending to access S3 directly — it
does not route through Trino. Ranger is not in the path.

```
GOVERNED PATH (Trino):
Any user → Trino → Ranger policy check → Iceberg/S3

UNGOVERNED PATH (Databricks):
Databricks Spark/SQL → Unity Catalog REST API → S3 (credential vended)
                        ↑ Ranger not involved, no column masking, no row filter,
                          no OpenLineage events visible to BCBS 239 audit store
```

Databricks has its own fine-grained access control within Unity Catalog — row-level
filtering, column masking, attribute-based policies. These are real capabilities.
But they are enforced by Unity Catalog, not by Apache Ranger, and they produce audit
logs in the Databricks platform, not in OpenLineage / Solr.

The result is the same dual governance problem as Snowflake:
- Two parallel policy systems (Ranger + Unity Catalog RBAC) that must be kept in sync
- Two separate audit stores that must be correlated for BCBS 239 compliance
- Databricks users have a different governance experience than Trino users on the
  same underlying data
- Column masking and row filtering defined in Ranger are not applied to Databricks
  queries

### The only governed Databricks path: Trino federation

There is one way to use Databricks capabilities while keeping Ranger in the governance
chain: route Databricks queries **through Trino** using the Trino connector for
Databricks or by having Databricks Spark query via Trino JDBC. This is technically
possible but operationally awkward — it negates most of the performance advantages
Databricks claims and is not how Databricks is designed to be used.

---

## The Catalog War Context

Understanding why Databricks is aggressive on Iceberg / Unity Catalog requires
understanding the competitive dynamics. The industry is converging on Iceberg as
the open table format, and Databricks recognizes that if Iceberg wins the format war,
their value-add must shift to the catalog and governance layer.

Hence: Unity Catalog, Managed Iceberg tables, REST catalog API support,
Lakehouse Federation — all announced or generally available in 2025. Databricks is
trying to become the de facto catalog layer for the industry's Iceberg data,
replacing Nessie, Polaris, and Glue with a single (proprietary) alternative.

Relevant context: Snowflake announced plans to merge Nessie with Polaris Catalog
to reduce catalog sprawl. This Polaris/Nessie convergence is the open-source
alternative to Databricks Unity Catalog. RBC's Nessie choice positions it on the
open, vendor-neutral side of this divide.

---

## Databricks Strengths — Where It Actually Excels

This review should be honest. Databricks does certain things very well:

**Apache Spark at scale:** Databricks is the best commercial Spark environment.
For heavy ML training, large-scale feature engineering, or Spark-native workloads,
it is genuinely superior to running open-source Spark on Kubernetes.

**MLflow and model tracking:** Native integration with MLflow for experiment tracking,
model registry, and model serving. If RBC builds significant ML model training
pipelines, this is a real capability gap in the open stack.

**Mosaic AI and vector search:** Databricks has strong AI/ML capabilities —
vector search, model serving, AI functions. These are ahead of the open stack.

**Delta Live Tables:** Streaming/incremental pipeline management with automatic
dependency resolution. Roughly equivalent to the Python + Airflow stack, but more
opinionated and managed.

**Photon engine:** Databricks' vectorized execution engine delivers genuine
query performance improvements over open-source Spark.

None of these capabilities justify adopting Databricks as a core platform component
for RBC's data lakehouse given the governance constraints. However, they are relevant
if RBC ever evaluates a dedicated ML platform separate from the EDL/EDW lakehouse.

---

## Comparison: Nessie vs Unity Catalog

| Capability | Nessie (RBC choice) | Unity Catalog (Databricks) |
|---|---|---|
| Iceberg REST catalog | ✅ Native | ✅ Native |
| Git-like branching | ✅ Core feature | ❌ Not available |
| Multi-table transactions | ✅ Yes | ❌ No |
| Apache Ranger integration | ✅ Via Trino | ❌ Own RBAC only |
| OpenLineage native | ✅ Via Trino | ❌ Databricks lineage only |
| Self-hosted / on-prem | ✅ Yes | ⚠️ Managed cloud preferred |
| Open source license | ✅ Apache 2.0 | ⚠️ OSS but Databricks-controlled |
| Vendor lock-in risk | None | High (commercial product) |
| Column/row security | Via Ranger/Trino | Via Unity Catalog RBAC |
| BCBS 239 audit trail | ✅ OpenLineage → Solr | ❌ Separate Databricks audit |
| Migration branch strategy | ✅ Core use case | ❌ Not supported |
| Delta Lake support | ❌ Iceberg only | ✅ Native |
| Cost | Open source + infra | Per-DBU compute pricing |

For RBC's specific requirements — BCBS 239, Ranger as single policy enforcement
point, Nessie branching for migration safety, no vendor lock-in — Nessie is clearly
the right choice. Unity Catalog would require replacing or duplicating every
governance component in the stack.

---

## Decision

**Databricks is not adopted as a component of the RBC Lakehouse architecture.**

The rationale:
1. Creates the same Ranger governance gap as Snowflake (ADR-002 violation)
2. Unity Catalog directly competes with Nessie — adopting both is unsustainable
3. Incompatible with BCBS 239 requirement for a unified OpenLineage audit trail
4. Significant proprietary lock-in risk incompatible with RBC's open stack strategy
5. The Spark-specific capabilities Databricks offers (ML, Photon) are not required
   for the core EDL/EDW workload that this lakehouse serves

This decision does not preclude evaluating Databricks for a separate ML platform
use case (model training, feature engineering) where the governance constraints
apply differently and the Spark performance benefits are more compelling.

---

## Future Watch Items

The industry is moving fast in this space. These developments warrant monitoring:

> 📌 **Polaris + Nessie merger**: Dremio has announced plans to merge Nessie into
> Apache Polaris (Snowflake's open-source catalog). If this materialises, Nessie's
> community and governance features may be subsumed into a larger, more
> widely-supported project. RBC should monitor whether migration from Nessie to
> Polaris becomes advisable (likely a catalog-to-catalog migration with no data
> movement required).

> 📌 **Unity Catalog Apache Ranger integration**: Databricks has not announced a
> Ranger plugin. If one emerges and is production-grade, it would change the
> governance gap analysis significantly. Monitor the Apache Ranger project tracker.

> 📌 **Trino + Unity Catalog connector**: Trino has a connector for reading Delta
> tables. If it adds full Unity Catalog governance passthrough (Trino calls Unity
> Catalog for authorization instead of Ranger), this could enable a governed
> Databricks integration. Currently not available.

---

## Related Documents

- ADR-002: Trino as Mandatory Query Gateway
- ADR-003: Teradata Decoupling Strategy
- `docs/migration/snowflake-deprecation.md`
- `docs/governance/ranger-trino-coverage.md`
- `docs/swot/nessie-catalog-swot.md` (existing)
