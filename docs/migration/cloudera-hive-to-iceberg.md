# Cloudera Hive to Iceberg Migration Playbook

**Scope:** Migrating Cloudera EDL Hive tables and HDFS data to Iceberg, and
deprecating all shadow copies of Teradata data running on Cloudera.

---

## The Three Problems in Cloudera

Cloudera's situation involves three distinct problems that require different approaches:

```
Cloudera EDL (~400 TB total)
│
├── 1. Hive external tables → HDFS (Parquet/ORC)
│      These have legitimate data that needs to migrate to Iceberg Bronze/Silver
│
├── 2. Shadow copies of Teradata data
│      These are COPY ⚡ — duplicated data with no single source of truth
│      DO NOT MIGRATE — DEPRECATE
│
└── 3. Cloudera-native pipelines writing to HDFS
       Spark/DataStage jobs writing to Hive tables
       Re-target to Iceberg via Nessie
```

---

## Problem 1: Hive External Tables → Iceberg Bronze

### The fast path — in-place registration

Hive external tables store data as Parquet or ORC files in HDFS. Apache Iceberg can
read these files natively. The fast path is to **register the existing files as an
Iceberg table in Nessie without moving any data**:

```python
# Step 1: Register existing Parquet files as an Iceberg table
# This creates Iceberg metadata pointing at the existing HDFS files
# No data movement required

from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.nessie.catalog-impl",
            "org.apache.iceberg.nessie.NessieCatalog") \
    .config("spark.sql.catalog.nessie.uri",
            "http://nessie.lakehouse.svc.cluster.local:19120/api/v1") \
    .config("spark.sql.catalog.nessie.ref", "migration/hive-bronze") \
    .getOrCreate()

# Register the Hive table as an Iceberg table
spark.sql("""
    CALL nessie.system.register_table(
        table => 'nessie.bronze.cloudera_transactions',
        metadata_file => 'hdfs://namenode/user/hive/warehouse/transactions/'
    )
""")
```

This creates an Iceberg table entry in Nessie pointing at the existing HDFS Parquet
files. The data is immediately queryable via Trino with Ranger policies applied —
without moving a single byte.

### The proper path — full conversion to Iceberg V2

In-place registration keeps the data in HDFS/ORC/Parquet format. For production use,
a full conversion to Iceberg V2 format is required (enables ACID, time travel, schema
evolution, row-level deletes):

```python
# Convert Hive Parquet table to native Iceberg V2 format
# This rewrites the data files into Iceberg format on S3/MinIO

spark.sql("""
    CREATE TABLE nessie.bronze.transactions
    USING iceberg
    TBLPROPERTIES (
        'format-version' = '2',
        'write.target-file-size-bytes' = '134217728'
    )
    AS SELECT * FROM hive.default.transactions
""")

# Validate row count
hive_count = spark.sql("SELECT COUNT(*) FROM hive.default.transactions").collect()[0][0]
iceberg_count = spark.sql("SELECT COUNT(*) FROM nessie.bronze.transactions").collect()[0][0]
assert hive_count == iceberg_count, f"Row count mismatch: {hive_count} vs {iceberg_count}"
```

### When to use each path

| Scenario | Approach |
|---|---|
| Table is large (>1 TB), data is current, conversion would take days | In-place registration first, schedule full conversion |
| Table is < 100 GB | Full V2 conversion directly |
| Table is ORC format | Full conversion required (Iceberg V2 prefers Parquet) |
| Table will be retired within 6 months | In-place registration only; skip full conversion |

---

## Problem 2: Shadow Copies — Deprecate, Do Not Migrate

Shadow copies of Teradata data on Cloudera exist because at some point, a team needed
better performance or lower cost for a specific workload and extracted a copy of
Teradata data to HDFS. These copies are now stale, ungoverned, and violate the
single source of truth principle.

**These tables must not be migrated to Iceberg. They must be deprecated.**

### Why deprecation, not migration

- The authoritative source is Teradata (being migrated to Iceberg Silver via dual-write)
- Creating an Iceberg copy of a Teradata copy creates a third copy of the same data
- Trino on Iceberg Gold/Silver will be faster for analytical queries than the old
  Cloudera Hive tables, removing the original performance justification

### Deprecation process

```
Step 1: Identify shadow copies
        Compare Cloudera Hive table names/schemas against Teradata FSDM table inventory
        Look for: identical column names, similar data volumes, no Cloudera-native source

Step 2: Find and notify consumers
        Query Hive query logs for tables in question (last 90 days)
        Identify teams/jobs reading these tables
        Notify: "This table is a shadow copy of [Teradata source]. The authoritative
        data will be available via Trino at iceberg.silver.[table_name] by [date].
        This Hive table will be deprecated on [date + 90 days]."

Step 3: Validate the Iceberg alternative exists
        Do not deprecate until the Teradata dual-write to Iceberg is live and validated
        Consumers must have a working alternative before the shadow is removed

Step 4: Set read-only, then drop
        Set Hive table to read-only 30 days before drop date
        Drop table and delete HDFS files after sunset date
```

### Stakeholder communication template

```
Subject: [ACTION REQUIRED] Cloudera Hive table [table_name] deprecation — [date]

The Hive table [database].[table_name] on Cloudera is a shadow copy of
[TERADATA_TABLE] and will be deprecated on [date].

The authoritative data is now available at:
  Trino endpoint: trino.lakehouse.rbc.internal:8080
  Table: iceberg.silver.[table_name]
  Access: Request via the data access portal (Ranger policy)

The Iceberg table has been in production since [date], with validated parity
against the Teradata source.

Please update your workloads before [date]. After this date, the Hive table
will be set to read-only. It will be permanently deleted on [date + 30 days].

Questions: contact the Enterprise Data team.
```

> ⚠️ **Executive air cover required before mass deprecation.** Some teams treat shadow
> copies as "their" data and will push back. This conversation needs to happen at the
> VP level (Vinh) before deprecation notices go out. The architectural argument:
> Trino on Iceberg is faster and cheaper than Cloudera Hive for analytical workloads.

---

## Problem 3: Cloudera-Native Pipelines → Iceberg

Spark and DataStage jobs that currently write to HDFS/Hive need to be redirected
to write to Iceberg via Nessie. The data model stays the same — only the destination
changes.

### Spark pipeline re-targeting

```python
# Before: writing to Hive/HDFS
df.write \
  .format("parquet") \
  .mode("append") \
  .saveAsTable("hive.default.transactions")

# After: writing to Iceberg via Nessie
df.write \
  .format("iceberg") \
  .option("catalog", "nessie") \
  .mode("append") \
  .saveAsTable("nessie.bronze.transactions")
```

This is a single-line change for most Spark jobs. The schema, partitioning, and
data model are unchanged. The destination is different.

### DataStage re-targeting

DataStage jobs writing to Hive use the JDBC Hive connector. Re-targeting to Iceberg
requires updating the JDBC connection to Trino:

```
Before: JDBC URL = jdbc:hive2://cloudera-master:10000/default
After:  JDBC URL = jdbc:trino://trino.lakehouse.rbc.internal:8080/iceberg/bronze
```

This is part of the broader DataStage → Python migration. In the interim, DataStage
can write to Iceberg via Trino JDBC while the Python rewrite is underway.

---

## Migration Sequencing

Cloudera migration runs in parallel with Teradata migration, not sequentially:

```
Q2 2026: Shadow copy inventory complete
         Consumer notification sent for top 20 shadow copies

Q3 2026: Top 20 shadow copies deprecated (Iceberg Silver live for those tables)
         Hive external tables: in-place registration for all active tables

Q4 2026: Full Iceberg V2 conversion for priority tables
         Cloudera-native pipeline re-targeting begins

2027:    Remaining shadow copies deprecated as Iceberg Silver layer matures
         Cloudera storage footprint shrinking quarter-over-quarter

2028:    Cloudera decommissioned
```

---

## Validation Checklist (per table)

- [ ] Hive table type confirmed (external/managed/shadow copy)
- [ ] Consumer query log checked — active in last 90 days
- [ ] Row count parity validated between Hive and Iceberg
- [ ] Schema parity validated (all columns, correct types)
- [ ] Ranger policy created for Iceberg table (Trino gateway)
- [ ] OpenLineage events confirmed for Iceberg table
- [ ] Consumer notifications sent (if shadow copy deprecation)
- [ ] Hive table sunset date set and communicated
