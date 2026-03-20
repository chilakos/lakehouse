# Teradata to Iceberg Migration Playbook

**Scope:** Migrating Teradata FSDM Silver base tables and materialized view Gold layer
to Apache Iceberg V2 via dual-write shadow table pattern.

---

## The Dual-Write Pattern

### How it works

```
                    ┌─────────────────┐
Source System  ───► │  Python ETL      │
                    │  (BasePipeline)  │
                    └────────┬────────┘
                             │ dual-write
                    ┌────────┴────────────────────────┐
                    │                                  │
                    ▼                                  ▼
           ┌──────────────┐                  ┌──────────────────┐
           │  Teradata     │                  │  Iceberg (Nessie) │
           │  PROD_SILVER  │                  │  silver.accounts  │
           │  (existing)   │                  │  (new, shadow)    │
           └──────────────┘                  └──────────────────┘
                    │                                  │
           existing consumers               validation only
           still read here                 (no consumers yet)
```

During the shadow phase, both tables receive every write. The Iceberg table is
registered in Nessie on a `migration/<table-name>` branch. No production consumers
read from it yet.

### Python dual-write implementation

```python
class DualWritePipeline(BasePipeline):
    """
    Extends BasePipeline to write to both Teradata and Iceberg
    during the shadow migration phase.
    """

    def __init__(self, table_name: str, shadow_mode: bool = True):
        super().__init__(table_name)
        self.shadow_mode = shadow_mode
        self.iceberg_table = f"lakehouse.silver.{table_name}"
        self.nessie_branch = f"migration/{table_name}"

    def write(self, df: DataFrame) -> None:
        # Always write to Teradata (existing path)
        self._write_teradata(df)

        # Write to Iceberg if in shadow mode
        if self.shadow_mode:
            self._write_iceberg_shadow(df)

    def _write_iceberg_shadow(self, df: DataFrame) -> None:
        (df.write
           .format("iceberg")
           .option("catalog", "nessie")
           .option("ref", self.nessie_branch)
           .mode("append")
           .saveAsTable(self.iceberg_table))

    def validate_parity(self) -> ParityReport:
        """
        Compare row counts and key metrics between Teradata and Iceberg.
        Must pass before consumer migration begins.
        """
        td_count = self._count_teradata()
        ic_count = self._count_iceberg()
        td_checksum = self._checksum_teradata()
        ic_checksum = self._checksum_iceberg()

        return ParityReport(
            table=self.table_name,
            teradata_rows=td_count,
            iceberg_rows=ic_count,
            row_delta=td_count - ic_count,
            checksum_match=td_checksum == ic_checksum,
            parity_passed=abs(td_count - ic_count) == 0
                          and td_checksum == ic_checksum
        )
```

---

## Phase 1: Shadow Mode (Minimum 30 Days)

### Setup checklist

- [ ] Orphan analysis complete — table confirmed active in last 90 days
- [ ] Nessie branch created: `migration/<table-name>`
- [ ] Iceberg table schema created with correct type mappings (see below)
- [ ] DualWritePipeline deployed and writing to both targets
- [ ] Soda Core parity check running daily — alerts on row delta > 0
- [ ] OpenLineage events confirmed for Iceberg writes

### Parity validation (daily, automated)

```yaml
# soda/migration/parity_accounts.yml
checks for silver_accounts_parity:
  - row_count:
      name: "Iceberg row count matches Teradata"
      fail: when iceberg_count != teradata_count
  - duplicate_count(account_id):
      name: "No duplicates introduced in Iceberg"
      fail: when > 0
  - freshness(silver_ts):
      name: "Iceberg table updated within 6 hours"
      warn: when > 4h
      fail: when > 6h
```

### Promotion criteria (before consumer migration)

- [ ] 30+ days of continuous dual-write with zero parity failures
- [ ] Soda parity checks passing 100% over the last 30 days
- [ ] Schema validation: all columns present, all types match specification
- [ ] No P1 incidents attributable to the dual-write pipeline

---

## Phase 2: Consumer Migration

### Consumer migration order

Move consumers in this order — lowest risk first:

1. **Ad-hoc Trino queries** (developers, analysts) — point at Iceberg catalog, validate
2. **Power BI / Fabric reports** — change data source connection string
3. **Tableau workbooks** — update connection to Trino endpoint
4. **Scheduled DataStage jobs reading the table** — update job source
5. **Borealis / RBC Assist** — update semantic layer configuration
6. **AI agents** — update Cube YAML catalog reference

### Connection string migration (consumer change)

```
# Before (Teradata JDBC)
jdbc:teradata://rbc-prod-td/database=PROD_SILVER

# After (Trino on Iceberg)
jdbc:trino://trino.lakehouse.rbc.internal:8080/iceberg/silver
```

For Tableau: update the data source from the Teradata connector to the Trino connector.
Schema and table names remain identical — `silver.accounts` in both cases.

---

## Phase 3: Cutover and Teradata Decommission

### Cutover checklist

- [ ] All consumers confirmed on Iceberg (zero Teradata reads in query log for 14 days)
- [ ] Dual-write disabled — Iceberg is now the sole write target
- [ ] Nessie branch `migration/<table-name>` merged to `main`
- [ ] Teradata table set to read-only (no further writes)
- [ ] Sunset date communicated to all stakeholders (minimum 90 days notice)
- [ ] Teradata table dropped after sunset date
- [ ] Storage reclaimed, license cost reduction logged

---

## Type Mapping Reference

| Teradata type | Iceberg equivalent | Notes |
|---|---|---|
| `BYTEINT` | `int` | Upcast — no precision loss |
| `SMALLINT` | `int` | Upcast |
| `INTEGER` | `int` | Direct |
| `BIGINT` | `long` | Direct |
| `DECIMAL(p,s)` | `decimal(p,s)` | Iceberg max: (38,18) |
| `FLOAT` / `REAL` | `double` | Direct |
| `NUMBER` | `decimal(38,18)` | Use max precision |
| `CHAR(n)` | `string` | Strip trailing spaces in Python before write |
| `VARCHAR(n)` | `string` | Direct |
| `DATE` | `date` | Direct — Teradata DATE is ISO |
| `TIME` | `time` | Direct |
| `TIMESTAMP` | `timestamptz` | Normalize to UTC in Python before write |
| `TIMESTAMP WITH TIME ZONE` | `timestamptz` | Direct |
| `PERIOD(DATE)` | Two `date` columns: `valid_from`, `valid_to` | Decompose — no Iceberg equivalent |
| `PERIOD(TIMESTAMP)` | Two `timestamptz` columns | Decompose |
| `VARBYTE` / `BYTE` | `binary` | Direct |
| `JSON` | `string` | Store as string; parse at query time |
| `CLOB` | `string` | Direct — Iceberg strings are unlimited length |

### Timestamp normalization

Teradata timestamps are session-timezone dependent. All timestamps must be
normalized to UTC before writing to Iceberg Silver:

```python
from datetime import timezone

def normalize_timestamp(ts, source_tz="America/Toronto"):
    """Normalize Teradata session-TZ timestamp to UTC for Iceberg."""
    if ts is None:
        return None
    import pytz
    local_tz = pytz.timezone(source_tz)
    if ts.tzinfo is None:
        ts = local_tz.localize(ts)
    return ts.astimezone(timezone.utc)
```

### Trailing space handling

Teradata `CHAR(n)` columns are space-padded to fixed length. Strip before writing:

```python
def clean_char_columns(df: DataFrame, char_cols: list) -> DataFrame:
    """Strip trailing spaces from CHAR columns before Iceberg write."""
    for col in char_cols:
        df[col] = df[col].str.rstrip()
    return df
```

---

## Slowly Changing Dimensions

Type 2 SCD tables in Teradata use `effective_date` / `expiry_date` / `is_current`
columns. The Iceberg equivalent uses Iceberg V2 row-level deletes + `MERGE INTO`:

```sql
-- Type 2 SCD merge pattern in Trino
MERGE INTO iceberg.silver.customer_dim AS target
USING (
    SELECT * FROM staging.customer_updates
) AS source
ON target.customer_key = source.customer_key
   AND target.is_current = TRUE
WHEN MATCHED
     AND (target.party_nm != source.party_nm
          OR target.risk_tier != source.risk_tier)
THEN UPDATE SET
    is_current    = FALSE,
    expiry_date   = source.effective_date
WHEN NOT MATCHED THEN INSERT (
    customer_key, party_nm, risk_tier,
    effective_date, expiry_date, is_current
) VALUES (
    source.customer_key, source.party_nm, source.risk_tier,
    source.effective_date, DATE '9999-12-31', TRUE
);
```

---

## Rollback Procedure

If a consumer migration fails after cutover:

1. Re-enable dual-write to Teradata immediately
2. Redirect consumer back to Teradata connection string
3. Root-cause the failure — document in incident log
4. Do not re-attempt consumer migration until root cause is resolved and parity
   is re-validated for 14 days

The Nessie branch is never deleted until the Teradata table is decommissioned.
If rollback is required before branch merge, simply abandon the branch — main
is unaffected.
