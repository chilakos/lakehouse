# Materialized View Decomposition — Teradata to Gold Iceberg

**Scope:** Methodology for decomposing Teradata materialized views (the current Gold
layer) into Gold Iceberg tables and Cube YAML metric definitions.

---

## Why Views Can't Be Directly Translated

A Teradata materialized view with hundreds of table joins is not a database object —
it is an **encoded business process**. The join complexity exists for two reasons:

1. **FSDM relationship encoding** — joins traverse the FSDM entity model to assemble
   a business-meaningful record from normalized base tables
2. **Legacy compensation** — joins compensate for data fragmentation that predates
   the FSDM, resolving inconsistencies that Silver (once clean) should eliminate

Once Silver Iceberg tables are clean, normalized, and FSDM-compliant, most of the
join complexity in existing Gold views dissolves. The migration is therefore not
a translation exercise — it is a **re-derivation** using the clean Silver layer
as the new foundation.

---

## Decomposition Methodology

### Step 1: Dependency graph extraction

Extract all table references from the materialized view DDL:

```python
import re
import networkx as nx

def extract_dependencies(view_ddl: str) -> dict:
    """
    Parse a Teradata materialized view DDL and extract table dependencies.
    Returns a dict of {table_name: [column_list]} for each referenced table.
    """
    # Extract FROM and JOIN clauses
    pattern = r'\b(?:FROM|JOIN)\s+(\w+\.\w+|\w+)\s+(?:AS\s+)?(\w+)?'
    matches = re.findall(pattern, view_ddl, re.IGNORECASE)

    dependencies = {}
    for table_ref, alias in matches:
        dependencies[table_ref] = {
            'alias': alias,
            'layer': classify_table(table_ref)
        }
    return dependencies

def classify_table(table_name: str) -> str:
    """Classify a Teradata table into Silver/reference/intermediate/unknown."""
    silver_prefixes = ['FSDM_', 'F_', 'D_', 'PROD_SILVER']
    ref_prefixes = ['REF_', 'LKP_', 'CODE_']

    if any(table_name.upper().startswith(p) for p in silver_prefixes):
        return 'silver'
    elif any(table_name.upper().startswith(p) for p in ref_prefixes):
        return 'reference'
    else:
        return 'unknown'
```

### Step 2: Classify each dependency

For each table referenced in the view, classify it:

| Classification | Description | Target in lakehouse |
|---|---|---|
| `silver` | FSDM-conformed base table | Already exists (or will exist) as Iceberg Silver |
| `reference` | Code/lookup table | Iceberg Silver dimension table |
| `intermediate` | Derived table used only within this view | Intermediate Gold Iceberg table |
| `unknown` | Cannot be classified automatically | **Requires human review** |

### Step 3: Identify the aggregation pattern

Once source tables are classified, identify what the view is actually doing:

```python
def classify_view_type(view_ddl: str) -> str:
    """
    Classify the primary aggregation pattern of the view.
    """
    ddl_upper = view_ddl.upper()

    if re.search(r'\bGROUP BY\b', ddl_upper):
        if re.search(r'\b(SUM|COUNT|AVG|MIN|MAX)\s*\(', ddl_upper):
            return 'aggregate'  # → Physical Gold Iceberg table
    if re.search(r'\bPARTITION BY\b', ddl_upper):
        return 'window'        # → Physical Gold Iceberg table
    if re.search(r'\bWHERE.*SNAPSHOT|AS_OF|PERIOD\b', ddl_upper):
        return 'snapshot'      # → Gold table with snapshot_date partition
    if not re.search(r'\bGROUP BY\b', ddl_upper):
        return 'semantic'      # → Cube YAML definition (no physical table needed)

    return 'unknown'           # Requires human review
```

### Step 4: Map to target

| View type | Target | Rationale |
|---|---|---|
| `aggregate` | Physical Gold Iceberg table | Expensive to compute on the fly; BI tools need pre-computed |
| `window` | Physical Gold Iceberg table | Window functions over large datasets need materialization |
| `snapshot` | Gold Iceberg table with `snapshot_date` partition | Point-in-time semantics require physical storage |
| `semantic` | Cube YAML metric definition | Thin calculation with no heavy aggregation; Cube computes at query time |
| `unknown` | **Human review required** | Cannot be safely auto-classified |

---

## Aggregate Views → Gold Iceberg Tables

### Pattern

```python
# Python pipeline for a Gold aggregate table
# (replaces Teradata materialized view MV_CUSTOMER_360)

class Customer360GoldPipeline(BasePipeline):

    def run(self) -> None:
        # Read from Silver Iceberg (via Trino)
        silver = self.trino.sql("""
            SELECT
                a.party_id,
                a.party_nm,
                a.risk_tier,
                a.acct_bal_amt,
                t.ytd_tx_count,
                t.avg_monthly_vol,
                p.portfolio_count,
                r.relationship_score
            FROM iceberg.silver.accounts      a
            JOIN iceberg.silver.transactions_ytd t ON a.party_id = t.party_id
            JOIN iceberg.silver.portfolios     p ON a.party_id = p.party_id
            JOIN iceberg.silver.relationships  r ON a.party_id = r.party_id
        """)

        # Apply business logic (previously in Teradata MV SQL)
        gold = silver.withColumn(
            "risk_tier",
            when(col("acct_bal_amt") > 500000, "HIGH_NET_WORTH")
            .when(col("acct_bal_amt") > 100000, "AFFLUENT")
            .otherwise("RETAIL")
        )

        # Write to Gold Iceberg
        self.write_gold(gold, "lakehouse.gold.customer_360")

    def write_gold(self, df, table: str) -> None:
        (df.write
           .format("iceberg")
           .option("catalog", "nessie")
           .mode("overwrite")
           .option("overwrite-mode", "dynamic")
           .saveAsTable(table))
```

---

## Semantic Views → Cube YAML

Views that are purely calculated measures with no GROUP BY — ratios, weighted averages,
derived KPIs — belong in Cube, not in a physical Iceberg table.

### Example: Teradata view → Cube YAML

**Teradata view (before):**
```sql
CREATE VIEW MV_BALANCE_UTILIZATION AS
SELECT
    a.party_id,
    a.acct_bal_amt,
    l.credit_limit,
    CAST(a.acct_bal_amt AS FLOAT) / NULLIF(l.credit_limit, 0) AS balance_utilization_pct,
    CASE
        WHEN a.acct_bal_amt / NULLIF(l.credit_limit, 0) > 0.8 THEN 'HIGH_UTILIZATION'
        ELSE 'NORMAL'
    END AS utilization_band
FROM FSDM_ACCOUNT a
JOIN FSDM_CREDIT_LIMIT l ON a.party_id = l.party_id;
```

**Cube YAML (after):**
```yaml
cubes:
  - name: account_utilization
    sql: >
      SELECT a.party_id, a.acct_bal_amt, l.credit_limit
      FROM iceberg.gold.customer_360 a
      JOIN iceberg.silver.credit_limits l ON a.party_id = l.party_id

    measures:
      - name: balance_utilization_pct
        sql: "CAST({acct_bal_amt} AS DOUBLE) / NULLIF({credit_limit}, 0)"
        type: number
        format: percent
        description: "Balance as % of credit limit"

    dimensions:
      - name: utilization_band
        sql: >
          CASE
            WHEN CAST({acct_bal_amt} AS DOUBLE) / NULLIF({credit_limit}, 0) > 0.8
            THEN 'HIGH_UTILIZATION'
            ELSE 'NORMAL'
          END
        type: string
```

The Cube definition is computed at query time from Gold Iceberg tables. No physical
Gold table is needed. The metric is available to BI tools, Borealis, and AI agents
identically — and stays in sync automatically as the underlying Silver/Gold tables
update.

---

## Snapshot Views → Partitioned Gold Tables

End-of-day, month-end, and quarter-end snapshots are physical tables in Iceberg with
a `snapshot_date` partition column:

```python
class EodBalanceSnapshotPipeline(BasePipeline):
    """
    Replaces Teradata MV_EOD_BALANCES.
    Writes a partition per snapshot_date to Gold Iceberg.
    """

    def run(self, snapshot_date: date) -> None:
        eod = self.trino.sql(f"""
            SELECT
                party_id,
                acct_bal_amt,
                DATE '{snapshot_date}' AS snapshot_date
            FROM iceberg.silver.accounts
            WHERE silver_ts <= TIMESTAMP '{snapshot_date} 23:59:59'
        """)

        (eod.write
            .format("iceberg")
            .option("catalog", "nessie")
            .partitionBy("snapshot_date")
            .mode("overwrite")
            .option("overwrite-mode", "dynamic")
            .saveAsTable("lakehouse.gold.eod_balances"))
```

Note: Iceberg V2 time travel can serve *some* point-in-time queries without explicit
snapshot tables. However, time travel has a retention window (typically 7-30 days).
For regulatory snapshots (month-end, quarter-end) that must be retained for years,
explicit snapshot partitions are required.

---

## AI-Assisted Migration at Scale

Given hundreds of materialized views, the decomposition process is AI-assisted via
Claude Code:

### Input to Claude Code (`/batch` mode)
```
For each view in /migrations/views/pending/:
  1. Parse DDL — extract table references, join conditions, aggregation logic
  2. Classify all referenced tables (silver/reference/intermediate/unknown)
  3. Classify the view type (aggregate/semantic/snapshot/unknown)
  4. If aggregate or snapshot: generate Python Gold pipeline
  5. If semantic: generate Cube YAML definition
  6. If unknown: flag for human review with context summary
  7. Write output to /migrations/views/generated/<view_name>/
     - pipeline.py (if aggregate/snapshot)
     - cube.yaml (if semantic)
     - review_required.md (if unknown)
```

### Human review gates

All AI-generated migrations require human review before staging:
- [ ] Type mappings verified against Teradata DDL
- [ ] Business logic reviewed by domain SME
- [ ] Parity test written and passing against Teradata source
- [ ] Soda Core quality check added to pipeline

---

## Orphan View Retirement

Before migrating any view, confirm it is active:

```sql
-- Identify inactive views (Teradata DBQL)
SELECT ObjectName, MAX(CollectTimeStamp) AS last_queried
FROM DBC.DBQLObjTbl
WHERE DatabaseName = 'PROD_GOLD'
  AND ObjectType = 'View'
GROUP BY ObjectName
HAVING MAX(CollectTimeStamp) < CURRENT_DATE - 90
ORDER BY last_queried;
```

Views with no activity in:
- **90 days** → Migration candidate review: confirm with domain owner before migrating
- **180 days** → Retire without migration; document reason
- **365 days** → Retire immediately; no domain owner consultation required

Expectation based on industry precedent: **20-35% of views will be retired**, not
migrated. This meaningfully reduces the actual migration workload.
