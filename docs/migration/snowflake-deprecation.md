# Snowflake Deprecation Plan

**Status:** Approved for deprecation — pending consumer survey and Iceberg Silver readiness  
**Owner:** VP Enterprise Data  
**Target sunset:** 2028 (aligned with Cloudera decommission)

---

## Why Snowflake Is Being Deprecated, Not Migrated

Snowflake's presence in the RBC data estate (~300 TB) is primarily shadow copies of
Teradata data, loaded historically for performance or cost reasons. It is not a
platform on which material new workloads have been built.

More critically, Snowflake cannot participate in the RBC Lakehouse governance model:

### The Ranger gap — the decisive issue

When Snowflake reads from Nessie-catalogued Iceberg tables, it connects **directly to
Nessie and S3 via the Iceberg REST API**. It never passes through Trino. Apache Ranger
sits inside Trino. Snowflake completely bypasses it.

```
GOVERNED PATH (any Trino consumer):
User → Trino → Ranger policy check → Iceberg/S3
       ↑ column masking, row filtering, audit log

UNGOVERNED PATH (Snowflake direct):
Snowflake → Nessie REST API → S3
            ↑ no Ranger, no column masking, no row filtering, no OpenLineage
```

This is not a configuration problem — it is architectural. Snowflake's Iceberg
integration is designed to read Iceberg tables directly via the REST catalog spec.
It does not pass through Trino, and there is no mechanism to force it to do so.

Consequences:
- **No Ranger policy enforcement** for Snowflake users — column masking and row
  filtering defined in Ranger are silently bypassed
- **No OpenLineage audit events** — Snowflake reads produce no lineage trace,
  creating a gap in the BCBS 239 audit trail
- **No identity passthrough** to the central policy engine — Snowflake users are
  governed by Snowflake's internal RBAC, a completely separate policy system
- **Dual governance regimes** — maintaining consistent access policies across both
  Ranger and Snowflake RBAC is operationally unsustainable

### Snowflake's own RBAC is not a substitute

Snowflake has a mature internal RBAC model. However it is:
- Disconnected from RBC's Active Directory / Kerberos identity model
- Not integrated with Apache Ranger policy definitions
- Not visible to OpenLineage — produces separate audit logs that are not correlated
  with the central BCBS 239 audit store
- Not enforced for data accessed via other engines (Trino, Python, Spark)

Managing a parallel policy system for one platform that holds shadow copies is not
justified. The operational cost exceeds the benefit.

---

## Snowflake's Nessie / REST Catalog Compatibility

For completeness — Snowflake **can** technically connect to Nessie as a REST catalog:

```sql
-- Snowflake catalog integration pointing at Nessie REST API
CREATE CATALOG INTEGRATION nessie_rbc
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  REST_CONFIG = (
    CATALOG_URI = 'http://nessie.lakehouse.rbc.internal:19120/iceberg'
    CATALOG_NAME = 'lakehouse'
  )
  ENABLED = TRUE;
```

And as of July 2025, Snowflake supports write operations to externally managed
Iceberg tables via REST catalogs. So the technical capability exists.

The reason this is not used is governance, not capability. Enabling Snowflake to
read/write your Iceberg tables via Nessie creates an unacceptable Ranger bypass per
ADR-002. The fact that it *can* be done does not mean it *should* be done in an
environment where BCBS 239 compliance requires a complete audit trail.

---

## What Snowflake Holds Today

Before executing deprecation, a consumer survey must confirm the actual use:

| Category | Expected content | Action |
|---|---|---|
| Shadow copies of Teradata data | ~80% of 300 TB | Deprecate — do not migrate |
| Shadow copies of Cloudera data | ~15% of 300 TB | Deprecate — do not migrate |
| Snowflake-native workloads | Unknown — survey required | Migrate to Trino if confirmed |

> ⚠️ **UNRESOLVED**: A formal consumer survey of Snowflake workloads has not been
> done. This must be completed before deprecation notices are issued. Owner: EDW
> domain lead. Required: list of active Snowflake users/roles and their primary
> tables, query frequency, and owning team.

---

## Deprecation Process

### Phase 1: Survey and classify (Q2 2026)

Run query log analysis to identify active Snowflake consumers:

```sql
-- Snowflake query history — active tables in last 90 days
SELECT
    query_text,
    user_name,
    database_name,
    schema_name,
    execution_time,
    COUNT(*) AS query_count
FROM snowflake.account_usage.query_history
WHERE start_time >= DATEADD(day, -90, CURRENT_TIMESTAMP)
  AND query_type = 'SELECT'
GROUP BY 1, 2, 3, 4, 5
ORDER BY query_count DESC;
```

Classify each active consumer:
- **Shadow copy reader** → Consumer migrates to Trino/Iceberg; shadow table deprecated
- **Snowflake-native workload** → Assess migration complexity; create migration ticket

### Phase 2: Migrate consumers (Q3-Q4 2026)

For each active consumer identified in Phase 1:

1. Confirm the equivalent Iceberg Gold/Silver table exists and is validated
2. Update the consumer's connection string to Trino:
   ```
   Before: Snowflake account URL + warehouse
   After:  jdbc:trino://trino.lakehouse.rbc.internal:8080/iceberg/gold
   ```
3. Validate results parity for 30 days
4. Remove Snowflake access for that consumer

### Phase 3: Shadow table cleanup (Q4 2026 - Q2 2027)

As consumers migrate off each Snowflake table:
1. Set table to read-only
2. Communicate 90-day sunset date to all stakeholders
3. Drop table; reclaim storage credits

### Phase 4: Decommission Snowflake account (2028)

Once all consumers are migrated and all tables dropped:
- Terminate Snowflake contract (coordinate with Procurement)
- Recover ~$X CAD annual license cost (TBD based on contract review)
- Archive audit logs per retention policy before account closure

---

## Snowflake vs Trino — Performance Argument

Teams that originally moved to Snowflake did so for performance reasons. The
justification for keeping Snowflake dissolves once Trino on Iceberg is available:

| Capability | Snowflake | Trino on Iceberg |
|---|---|---|
| Columnar storage | ✅ (proprietary) | ✅ (Parquet on S3) |
| Predicate pushdown | ✅ | ✅ |
| Partition pruning | ✅ | ✅ (Iceberg hidden partitions) |
| Time travel | ✅ | ✅ (Iceberg snapshots) |
| Schema evolution | ✅ | ✅ |
| Ranger governance | ❌ bypass | ✅ enforced |
| BCBS 239 lineage | ❌ separate logs | ✅ OpenLineage native |
| Per-query cost | 💰 Snowflake credits | 💰 Compute only (no format tax) |
| Vendor lock-in | High (proprietary format) | None (open Iceberg) |

The performance parity argument for Snowflake is gone. The governance argument
decisively favours deprecation.
