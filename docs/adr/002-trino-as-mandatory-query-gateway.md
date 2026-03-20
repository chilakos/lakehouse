# ADR-002: Trino as the Mandatory Query Gateway for All Iceberg Access

**Status:** Accepted  
**Date:** March 2026  
**Author:** George Chilakos, VP Enterprise Data  
**Reviewers:** Pending — Vinh (manager), Platform Engineering

---

## Context

The RBC Lakehouse uses Apache Iceberg V2 as its single open table format, with data
physically stored in S3/MinIO and catalogued via Apache Nessie. Multiple compute engines
are capable of reading Iceberg tables directly — including Trino, Teradata OTF, Apache
Spark, and raw client libraries (PyArrow, boto3, DuckDB).

Without an explicit architectural decision, different teams and pipelines could read
Iceberg data through different paths, creating:

- **Ungoverned access**: Paths that bypass Apache Ranger entirely, producing no audit trail
- **BCBS 239 gaps**: Incomplete lineage if some reads are invisible to OpenLineage
- **Inconsistent policy enforcement**: Row/column masking policies enforced for some
  consumers but not others
- **Dual audit trail complexity**: Ranger logs + Teradata-native logs exist independently,
  requiring correlation for compliance reporting

This is especially acute during the Teradata migration period, when data exists in both
Teradata (internal tables) and Iceberg simultaneously.

---

## Decision

**Trino is the mandatory and sole query gateway for all access to Iceberg tables in the
RBC Lakehouse.**

No pipeline, tool, user, or service account may read from or write to Iceberg tables
by any path other than Trino, except where explicitly approved via the exception process
below.

This applies to:
- All Bronze, Silver, and Gold Iceberg tables
- All Nessie catalog namespaces (`lakehouse.bronze.*`, `lakehouse.silver.*`, `lakehouse.gold.*`)
- All environments: development, staging, and production

---

## Consequences

### What this enables

**Single enforcement point for Apache Ranger.** All access decisions — allow/deny,
column masking, row filtering — are evaluated by the Ranger-Trino plugin at one place.
A user or service account either has a Ranger policy granting access or they don't.
There are no side doors.

**Continuous BCBS 239 audit trail.** Every query that reads or writes Iceberg data
produces an OpenLineage event via the Trino-OpenLineage integration. Lineage is complete
and unbroken from ingestion (Bronze) through consumption (Gold → BI / AI agents).

**Consistent identity passthrough.** Trino propagates the authenticated user identity
to Ranger for every query. This means service accounts, human analysts, and AI agents
(Borealis, RBC Assist) are all governed by the same policy engine with the same identity
model.

**Simplified policy management.** The data governance team defines policies once in the
Ranger Admin UI. Those policies apply to every consumer automatically — no per-tool
configuration, no per-pipeline grants to maintain.

### What this constrains

**Python ETL pipelines** must use the Trino JDBC connector or the Trino Python client
(`trino-python-client`) to write to Iceberg. Direct PyArrow or Iceberg REST writes are
not permitted in production.

**Spark jobs** (if used for heavy ingestion) must register tables via the Nessie catalog
and validate that Ranger policies exist before any job is promoted to production.

**Teradata OTF** — if/when Teradata OTF to Nessie REST catalog integration is confirmed
(see ADR-001), Teradata may read Iceberg tables for federated queries. This is permitted
only if Teradata's access is itself governed by a Ranger policy applied at the Trino
boundary. Teradata OTF direct reads that bypass Trino are not permitted.

**AI agents (Borealis, RBC Assist)** must access Gold data via the Cube SQL API
(Postgres wire protocol over Trino), not by querying Iceberg or Trino directly. The
Cube layer acts as the additional trust boundary for AI consumption (see the AI semantic
layer architecture).

### Exception process

Teams requiring a non-Trino read path must:
1. Raise a formal exception with the Enterprise Data governance team
2. Demonstrate that the alternative path has equivalent Ranger policy enforcement
3. Obtain sign-off from the VP Enterprise Data and the CISO data governance liaison
4. Accept that non-Trino paths will not be covered by the central BCBS 239 audit trail

---

## Alternatives Considered

**Per-tool Ranger plugins (Spark, Hive, etc.)** — Ranger supports plugins for many
engines. The problem is operational: each plugin requires separate configuration,
separate policy definitions, and separate audit infrastructure. At RBC scale (300+
sources, 1.5 PB) this becomes unmanageable. Single gateway is operationally superior.

**S3 bucket policies + IAM** — Provides access control at the storage layer but has
no awareness of table/column/row structure. Cannot enforce row-level filtering or
column masking. Does not produce queryable lineage events. Insufficient for BCBS 239.

**Nessie access control** — Nessie provides catalog-level access control (branch
permissions, namespace permissions) but not table/column/row level. Complements Ranger
but does not replace it.

---

## Open Questions

> ⚠️ **UNRESOLVED**: If Teradata OTF achieves confirmed Nessie REST catalog support
> (ADR-001), does the OTF read path go through Trino or directly to Nessie? If direct,
> this creates a Ranger gap. Resolution required before OTF is enabled in production.

> ⚠️ **UNRESOLVED**: Dual audit trail — Ranger audit logs (Solr) and Teradata query
> logs exist independently during the transition period. A process to correlate these
> for BCBS 239 reporting has not been defined. Owner: governance team.

---

## Related Documents

- ADR-001: Teradata OTF + Nessie Feasibility
- ADR-003: Teradata Decoupling Strategy
- `docs/governance/ranger-trino-coverage.md`
- `docs/migration/teradata-to-iceberg.md`
