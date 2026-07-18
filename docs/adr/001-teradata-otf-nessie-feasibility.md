# ADR-001: Teradata OTF + Nessie REST Catalog Feasibility

## Status

DRAFT -- To be updated after Week 1 validation testing.

## Date

2026-03-13

## Context

The lakehouse architecture requires Teradata to query Iceberg tables stored in S3/Pure Storage through the shared Nessie catalog. Teradata's Open Table Format (OTF) feature enables reading external table formats (Iceberg, Delta Lake, Hudi) stored on object storage.

### Current OTF Documentation Gap

Teradata OTF documentation confirms support for the following catalog types:
- **AWS Glue** -- Fully supported
- **Hive Metastore (HMS)** -- Fully supported
- **Databricks Unity Catalog** -- Supported for Delta Lake

**REST catalog (Nessie, Polaris)** is NOT documented in Teradata OTF materials as of this writing. This is the primary risk for our architecture, since we have selected Nessie as the unified Iceberg catalog.

### Requirements

- Teradata must be able to query Iceberg tables created by PySpark and Trino
- Queries must go through the shared Nessie catalog (single source of truth)
- Read-only access from Teradata is acceptable for Phase 1
- Performance must be benchmarked against Trino for equivalent queries

## Decision Options

### Option A: Direct OTF Connection to Nessie REST Catalog

**Approach:** Configure Teradata OTF to connect directly to Nessie's REST catalog endpoint.

**Configuration:**
```sql
CREATE FOREIGN TABLE trades
USING (
    LOCATION ('/s3/lakehouse-data/warehouse/trades')
    STOREDAS ('ICEBERG')
    CATALOG ('REST')
    CATALOG_URI ('https://nessie.company.com:19120/iceberg')
    CATALOG_PREFIX ('main')
)
NO PRIMARY INDEX;
```

**Pros:**
- Simplest architecture -- direct connection, no intermediary
- Minimal latency -- no query translation overhead
- Single catalog endpoint for all engines

**Cons:**
- REST catalog support in OTF is unconfirmed
- May require Teradata engineering engagement or feature request
- Risk of delay if feature is not available in current Teradata version

**Feasibility:** UNKNOWN -- requires testing with live Teradata instance.

### Option B: Trino Query Federation (Fallback)

**Approach:** Teradata connects to Trino via JDBC, and Trino queries the Nessie catalog on Teradata's behalf.

**Architecture:**
```
Teradata -> JDBC -> Trino -> Nessie REST -> Iceberg (S3/Pure Storage)
```

**Configuration:**
```sql
-- Teradata foreign server for Trino
CREATE FOREIGN SERVER trino_lakehouse
USING LINK ('trino')
EXTERNAL SECURITY DEFINER TRUSTED trino_auth
HOST 'trino.company.com'
PORT '8443';

-- Query through federation
SELECT * FROM trino_lakehouse.iceberg.default.trades;
```

**Pros:**
- Proven technology -- Teradata JDBC federation is well-documented
- Trino handles all Iceberg/Nessie complexity
- Works regardless of OTF REST catalog support
- Reuses existing Trino RBAC and security configuration

**Cons:**
- Additional latency from query translation (Teradata SQL -> Trino SQL)
- Additional infrastructure dependency (Trino must be available)
- Potential query pushdown limitations through JDBC
- Double resource usage (query executes on both Teradata and Trino)

**Feasibility:** HIGH -- Teradata JDBC federation is proven.

### Option C: Hive Metastore Shim

**Approach:** Deploy a Hive Metastore compatibility layer in front of Nessie, allowing Teradata OTF to connect using HMS protocol.

**Architecture:**
```
Teradata -> OTF (HMS) -> HMS Shim -> Nessie REST -> Iceberg (S3/Pure Storage)
```

**Pros:**
- Uses Teradata's confirmed HMS support
- Transparent to Teradata -- looks like a standard HMS
- Nessie remains the source of truth

**Cons:**
- Additional component to deploy, monitor, and maintain
- Potential metadata translation issues between HMS and REST catalog
- HMS shim may not support all Nessie features (branching, tagging)
- Increased operational complexity

**Feasibility:** MEDIUM -- HMS shim exists (e.g., Nessie HMS bridge) but adds complexity.

## Recommendation

1. **Test Option A first.** Configure Teradata OTF with REST catalog parameters pointing to Nessie. This is the ideal architecture.

2. **If Option A fails, implement Option B (Trino federation).** This is the locked fallback per project decisions. It adds latency but is proven and maintains the single-catalog architecture.

3. **Option C is a last resort.** Only consider if both A and B have unacceptable limitations.

## Action Items

- [ ] Configure Teradata OTF with REST catalog parameters pointing to Nessie
- [ ] Test direct OTF query: `SELECT * FROM iceberg_table`
- [ ] If REST catalog not supported, test JDBC federation through Trino
- [ ] Benchmark query performance for the selected option
- [ ] Update this ADR status to ACCEPTED with the chosen option

## Consequences

### If Option A (Direct OTF) Works
- Simplest architecture, lowest latency
- All three engines (Trino, Teradata, Snowflake) connect directly to Nessie
- No additional infrastructure components

### If Option B (Trino Federation) Is Required
- Trino becomes a critical path component for Teradata queries
- Must ensure Trino HA for Teradata access patterns
- Query performance will be lower than direct OTF (additional hop)
- RBAC is handled at Trino layer (consistent with other consumers)

## References

- Teradata OTF documentation: Vantage User Guide, Open Table Formats chapter
- Nessie REST catalog specification: https://iceberg.apache.org/spec/#rest-catalog
- Trino JDBC federation: Trino documentation, JDBC connector
- Project Decision Log: .planning/PROJECT.md Key Decisions table
