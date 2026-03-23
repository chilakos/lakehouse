# ADR-005: Use Trino + Python for Compute — No Apache Spark

**Status:** Accepted  
**Date:** 2026-03-23  
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)  
**Raised by:** Data Pillar review — CDO / Data Office (March 23, 2026)

---

## Context

During the Data Pillar review (March 23, 2026), stakeholders raised the absence of Apache Spark
in the EDL 2.0 / Lakehouse architecture. Most enterprise lakehouse reference architectures
(Databricks, Cloudera) assume Spark as the primary compute engine. This ADR documents why
Spark was deliberately excluded from the initial design and what that means for future workloads.

The current Lakehouse stack is:
- **Storage format:** Apache Iceberg V2
- **Catalog:** Nessie (git-like branching for table versions)
- **Query engine:** Trino (primary)
- **Transformations:** Python (not PySpark)
- **Orchestration:** Apache Airflow
- **Quality:** Soda Core
- **Lineage:** OpenLineage + Marquez

---

## Decision

**We will use Trino as the primary query engine and Python for ETL transformations.
Apache Spark will not be included in phase one of the Lakehouse build.**

---

## Rationale

### 1. Iceberg is compute-engine agnostic
Apache Iceberg V2 natively supports multiple compute engines — Trino, Spark, Flink, Dremio,
and others — all reading and writing the same table format. Choosing Trino for phase one does
not lock us out of Spark later. We can add Spark as a second compute engine without changing
the storage layer or re-platforming.

### 2. Trino eliminates cluster overhead
Trino queries Iceberg tables directly via the Nessie catalog. There is no persistent cluster
to manage, no YARN resource negotiation, no Spark context spin-up time. For interactive
queries and scheduled ETL jobs at our current scale, Trino's query-per-request model is
operationally simpler and more cost-effective.

### 3. Python over PySpark for transformations
RBC's existing engineering skills are centred on Python, not Scala or PySpark. Our
DataStage → Python migration (12,000+ jobs) is already producing Python-native pipelines.
Introducing PySpark would require a para
