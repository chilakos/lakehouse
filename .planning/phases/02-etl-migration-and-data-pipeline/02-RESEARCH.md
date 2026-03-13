# Phase 2: ETL Migration and Data Pipeline - Research

**Researched:** 2026-03-13
**Domain:** ETL pipeline development, workflow orchestration, data quality, data lineage, mainframe migration
**Confidence:** HIGH (core stack), MEDIUM (DQ framework recommendation, mainframe connectivity)

## Summary

Phase 2 transforms the lakehouse from a storage/query platform (Phase 1) into an active data processing system. The core work involves building a Python ETL framework on PySpark + Iceberg that replaces pilot DataStage jobs, implementing medallion architecture (Bronze/Silver/Gold) with quality gates between layers, deploying Apache Airflow 3.x for orchestration, capturing end-to-end lineage via OpenLineage + Marquez, and delivering a pipeline observability dashboard. The existing codebase provides a solid foundation: SparkSession factory with Nessie REST catalog, Iceberg table utilities, synthetic data generators, and Docker Compose infrastructure for local development.

The highest-risk item is mainframe COBOL copybook parsing and DB2 z/OS connectivity in Python -- this must be validated early. The DQ framework decision (Claude's discretion) favors Soda Core for this project given its YAML-based simplicity, native PySpark DataFrame support via `soda-core-spark-df`, and the need for 40+ engineers to onboard quickly. Airflow 3.x (currently 3.1.8) is the target orchestration platform, with the OpenLineage Airflow provider (2.10.x) enabling automatic Spark lineage injection.

**Primary recommendation:** Use Airflow 3.1.x + Soda Core + OpenLineage/Marquez stack. Build an opinionated ETL base class pattern that enforces medallion layer boundaries, schema validation, and quality gates. Validate mainframe connectivity (Cobrix + ibm_db) in the first wave before migrating simpler jobs.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Bronze layer: Raw-as-is with metadata columns (source_system, ingestion_ts, batch_id). No transformation at ingestion -- maximum traceability, no data loss
- Namespace convention: Layer-based namespaces -- lakehouse.bronze.{table}, lakehouse.silver.{table}, lakehouse.gold.{table}
- Silver layer: Cleaned & joined entities -- deduplicate, join related sources, apply business rules. Entity-centric (one table per business entity) without strict Kimball dimensional modeling
- Gold layer: Both pre-aggregated metrics for BI AND curated entity views for specific consumers (regulatory reports, trading desk views)
- Representative mix of 5-10 jobs across complexity levels: 2-3 simple (single source, basic transform), 3-4 medium (multi-source joins, lookups), 1-2 complex (mainframe, COBOL, multi-step)
- Mainframe connectivity: Python needs to replicate COBOL copybook parsing, EBCDIC conversion, and DB2 z/OS JDBC
- Migration validation: Parallel run with comparison -- run both DataStage and Python pipelines simultaneously, compare outputs (row counts, checksums, aggregates)
- Job inventory (ETL-07): Full structured catalog with complexity classification (simple/medium/complex), source systems, dependencies, estimated effort per job
- DAG design: Hybrid -- source-specific DAGs for Bronze-to-Silver, separate Gold DAGs for cross-source aggregations
- Failure handling: Retry then alert -- automatic retries (3x with backoff) on transient failures, alert only after retries exhausted
- Observability dashboard (PLAT-02): Combined ops + data view -- operational metrics (SLA compliance, failure rates, durations) AND data metrics (freshness, quality scores, row counts)
- Incremental loading (ETL-05): CDC where available (DB2 logs, Debezium), fall back to watermark-based for sources without CDC support
- Quality check placement: Gate between layers -- checks run at Bronze-to-Silver and Silver-to-Gold boundaries. Failed checks block promotion to next layer
- Failure behavior: Configurable per check -- critical checks (schema validation, null primary keys) are hard blocks; advisory checks (null rates, outliers) are soft alerts
- OpenLineage integration: Both Airflow plugin (task-level lineage) + Spark agent (column-level detail)

### Claude's Discretion
- DQ framework selection (Great Expectations vs Soda Core vs custom)
- Airflow deployment method and configuration
- Spark job resource allocation and tuning
- OpenLineage backend (Marquez vs other)
- ETL framework base class / abstraction design
- Standardized ETL patterns (ETL-06) structure and documentation format

### Deferred Ideas (OUT OF SCOPE)
- Nessie branching for ETL schema migrations -- explore after basic medallion is operational
- Real-time streaming ingestion (Kafka/Flink) -- explicitly out of scope per REQUIREMENTS.md
- Full DataStage retirement (all 300+ jobs) -- v2 scope, Phase 2 proves the framework with 5-10 pilots
- Data mesh domain ownership model -- v2 scope per REQUIREMENTS.md
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FNDTN-07 | Medallion architecture (Bronze/Silver/Gold) implemented with clear layer boundaries | Namespace convention, metadata columns, quality gates between layers. Existing `create_namespace` and `create_iceberg_table` utilities provide the foundation |
| ETL-01 | Python ETL framework established using PySpark + PyIceberg for Iceberg writes | ETL base class pattern, existing `catalog.py` SparkSession factory, PySpark 3.5 + Iceberg 1.7.1 stack |
| ETL-02 | Pilot ETL migration of 5-10 representative DataStage jobs to Python | Job selection criteria, parallel run validation, complexity classification approach |
| ETL-03 | Mainframe source connectivity validated in Python (COBOL copybook parsing, DB2 z/OS, flat files) | Cobrix for Spark COBOL parsing, ibm_db for DB2 z/OS, coboljsonifier as alternative |
| ETL-04 | Apache Airflow deployed for workflow orchestration with DAG dependency management | Airflow 3.1.x with CeleryExecutor, Docker Compose setup, SparkSubmitOperator patterns |
| ETL-05 | Incremental/delta loading patterns implemented (watermark-based, CDC where available) | Debezium CDC pattern, watermark column tracking, Iceberg merge-on-read for upserts |
| ETL-06 | Standardized ETL patterns documented and reusable across 40+ engineer team | Base class abstraction, cookiecutter templates, documentation format |
| ETL-07 | Full DataStage job inventory cataloged with complexity classification | Structured catalog schema, complexity scoring criteria |
| QUAL-01 | Schema validation enforced on all ingestion pipelines before Iceberg writes | PySpark schema enforcement, StructType validation before DataFrame writes |
| QUAL-02 | Data quality checks (null rates, range validation, uniqueness) integrated into ETL | Soda Core SodaCL checks, configurable hard/soft check behavior |
| QUAL-03 | Source-to-lakehouse reconciliation (row counts, checksums, aggregates) for migrated tables | Reconciliation framework comparing source counts with Iceberg table counts |
| QUAL-04 | Data quality monitoring with alerting for degradation detection | Soda Core scan results + Airflow alerting + Grafana dashboards |
| GOVN-01 | End-to-end data lineage captured via OpenLineage from source to consumption layer | OpenLineage Airflow provider + Spark agent + Marquez backend |
| PLAT-02 | Pipeline observability dashboard with SLA monitoring and failure alerting | Grafana + Airflow StatsD/Prometheus metrics + data quality metrics |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Apache Airflow | 3.1.x (latest 3.1.8) | Workflow orchestration | Industry standard for batch ETL orchestration. Airflow 3.0 released Apr 2025 with Task SDK, DAG versioning, React UI. Stable and production-ready |
| PySpark | 3.5.x (already pinned) | Data processing engine | Already established in project (pyproject.toml pins >=3.5.0,<3.6.0). Iceberg Spark runtime 3.5 already configured |
| Apache Iceberg | 1.7.1 (Spark runtime) | Table format | Already established in project catalog.py. REST catalog via Nessie |
| Soda Core (soda-core-spark-df) | 3.5.6 | Data quality framework | YAML-based SodaCL for checks, native Spark DataFrame support, no separate config file needed for DF scans. Simpler onboarding for 40+ engineers than Great Expectations |
| OpenLineage (openlineage-spark) | latest | Spark lineage agent | Column-level lineage turned on by default. Automatic parent job injection from Airflow |
| apache-airflow-providers-openlineage | 2.10.x | Airflow lineage provider | Native Airflow 3 support. Automatic Spark property injection for parent job tracking |
| Marquez | 0.50.0+ | Lineage backend + UI | Reference OpenLineage backend. Docker deployment. Web UI for lineage visualization. Data Observability dashboard built-in |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Cobrix | 2.9.x | COBOL/EBCDIC Spark data source | Mainframe flat file parsing. Reads COBOL copybooks, handles EBCDIC encoding natively in Spark |
| ibm_db | latest | DB2 z/OS connectivity | Direct Python connection to mainframe DB2. Requires DB2 Connect license |
| coboljsonifier | 1.0.x | Pure Python COBOL parser | Lighter alternative for COBOL copybook parsing outside Spark (testing, validation) |
| apache-airflow-providers-apache-spark | latest | SparkSubmitOperator | Submitting PySpark jobs from Airflow DAGs |
| Grafana | latest | Observability dashboards | Pipeline monitoring, SLA tracking, data quality visualization |
| Prometheus | latest | Metrics collection | Collect Airflow StatsD metrics for Grafana |
| Redis | latest | Airflow message broker | Required for CeleryExecutor in Airflow |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Soda Core | Great Expectations (1.15.x) | GX is more powerful/extensible but heavier setup. Python-first API vs YAML-first. More complex for 40+ engineers to learn. Better for highly customized validation logic |
| Soda Core | AWS Deequ (PyDeequ) | Good for Scala/Spark-native shops but Python wrapper is less mature. Tighter Spark coupling |
| Marquez | DataHub | More feature-rich catalog but heavier. Marquez is focused on lineage which is the Phase 2 need. DataHub better for Phase 3 governance |
| CeleryExecutor | KubernetesExecutor | Better isolation and autoscaling but requires K8s cluster. CeleryExecutor simpler for initial deployment |
| Cobrix | Manual EBCDIC parsing | Cobrix is battle-tested for Spark + COBOL. Manual parsing is error-prone for packed decimal, COMP-3, REDEFINES |

**Installation:**
```bash
# ETL framework dependencies (add to pyproject.toml)
pip install "pyspark>=3.5.0,<3.6.0" "soda-core-spark-df>=3.5.0" "ibm_db>=3.2.0"

# Airflow (separate virtualenv or Docker)
pip install "apache-airflow[celery,postgres,redis]==3.1.8" \
    "apache-airflow-providers-openlineage>=2.10.0" \
    "apache-airflow-providers-apache-spark>=4.0.0"

# Cobrix (added as Spark package, not pip)
# spark.jars.packages: za.co.absa.cobrix:spark-cobol_2.12:2.9.2
```

## Architecture Patterns

### Recommended Project Structure
```
etl/
  src/
    config/
      settings.py              # Existing - extend with Airflow/DQ config
    iceberg_utils/
      catalog.py               # Existing - SparkSession factory
      maintenance.py           # Existing - table maintenance
      trino.py                 # Existing - Trino utilities
    synthetic/
      generators.py            # Existing - test data generators
    pipelines/
      base.py                  # NEW: ETL base class (Bronze/Silver/Gold)
      bronze/
        __init__.py
        trades_ingest.py       # Source-specific Bronze ingestion
        positions_ingest.py
        mainframe_ingest.py    # COBOL/EBCDIC handling
      silver/
        __init__.py
        trades_clean.py        # Entity-level cleaning & dedup
        positions_clean.py
      gold/
        __init__.py
        trading_metrics.py     # Cross-source aggregation
        regulatory_views.py    # Regulatory report views
    quality/
      checks/                  # SodaCL YAML check definitions
        bronze_trades.yml
        silver_trades.yml
        gold_trading_metrics.yml
      scanner.py               # Soda scan runner utility
      reconciliation.py        # Source-to-lakehouse reconciliation
    lineage/
      config.py                # OpenLineage configuration
    inventory/
      catalog.py               # DataStage job inventory
      models.py                # Job metadata models
  dags/
    bronze_trades_dag.py       # Source-specific Bronze->Silver DAGs
    bronze_positions_dag.py
    gold_trading_metrics_dag.py  # Cross-source Gold DAGs
    maintenance_dag.py         # Iceberg table maintenance
    quality_report_dag.py      # Quality monitoring DAG
  tests/
    unit/
    integration/
    quality/                   # DQ check validation tests
```

### Pattern 1: ETL Base Class with Medallion Enforcement

**What:** Abstract base class that enforces medallion layer contracts -- schema validation before writes, quality gates between layers, lineage emission, standardized metadata columns.

**When to use:** Every ETL pipeline in the project. This is the primary abstraction for ETL-06 standardized patterns.

**Example:**
```python
# Source: Project-specific design based on medallion architecture decisions
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.types import StructType


class MedallionLayer(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for a single ETL pipeline."""
    name: str
    source_layer: MedallionLayer | None  # None for Bronze (external source)
    target_layer: MedallionLayer
    target_table: str
    target_schema: "StructType"
    quality_checks_path: str  # Path to SodaCL YAML
    critical_checks: list[str]  # Check names that block promotion
    max_retries: int = 3
    retry_delay_seconds: int = 60


class BasePipeline(ABC):
    """Base class for all ETL pipelines.

    Enforces: schema validation -> transform -> quality gate -> write.
    Subclasses implement extract() and transform() only.
    """

    def __init__(self, spark: "SparkSession", config: PipelineConfig):
        self.spark = spark
        self.config = config

    @abstractmethod
    def extract(self) -> "DataFrame":
        """Extract data from source. Subclass implements."""
        ...

    @abstractmethod
    def transform(self, df: "DataFrame") -> "DataFrame":
        """Transform data. Subclass implements."""
        ...

    def validate_schema(self, df: "DataFrame") -> bool:
        """Validate DataFrame schema matches target_schema."""
        return df.schema == self.config.target_schema

    def run_quality_checks(self, df: "DataFrame") -> dict:
        """Run Soda quality checks. Returns results dict."""
        # Soda scan integration
        ...

    def add_metadata_columns(self, df: "DataFrame") -> "DataFrame":
        """Add source_system, ingestion_ts, batch_id for Bronze layer."""
        ...

    def write(self, df: "DataFrame") -> None:
        """Write to Iceberg table in target namespace."""
        namespace = f"{self.config.target_layer.value}"
        table = self.config.target_table
        full_name = f"lakehouse.{namespace}.{table}"
        df.writeTo(full_name).append()

    def execute(self) -> dict:
        """Full pipeline execution with gates."""
        raw = self.extract()
        transformed = self.transform(raw)

        if not self.validate_schema(transformed):
            raise SchemaValidationError(...)

        qc_results = self.run_quality_checks(transformed)
        if qc_results.get("critical_failures"):
            raise QualityGateError(...)

        self.write(transformed)
        return {"rows_written": transformed.count(), "quality": qc_results}
```

### Pattern 2: Soda Core Quality Gate Integration

**What:** YAML-based quality checks using SodaCL that run between medallion layers, with configurable hard/soft failure behavior.

**When to use:** At every Bronze-to-Silver and Silver-to-Gold boundary.

**Example:**
```yaml
# Source: Soda Core documentation (https://docs.soda.io)
# quality/checks/bronze_trades.yml
checks for bronze.trades:
  # Critical checks (hard block)
  - schema:
      fail:
        when required column missing:
          [trade_id, trade_date, symbol, side, quantity, price]
        when wrong column type:
          trade_id: integer
          price: decimal
  - missing_count(trade_id) = 0:
      name: primary_key_not_null
  - duplicate_count(trade_id) = 0:
      name: primary_key_unique

  # Advisory checks (soft alert)
  - missing_percent(account_id) < 5:
      name: account_id_completeness
  - valid_min(price) >= 0:
      name: price_non_negative
  - valid_min(quantity) > 0:
      name: quantity_positive
```

```python
# Source: Soda Core docs - programmatic scan for Spark DataFrames
from soda.scan import Scan

def run_soda_checks(spark_session, df, checks_yaml_path: str, data_source_name: str = "spark_df"):
    """Run Soda quality checks on a Spark DataFrame."""
    scan = Scan()
    scan.set_scan_definition_name("etl_quality_gate")
    scan.set_data_source_name(data_source_name)
    scan.add_spark_session(spark_session, data_source_name)

    # Register the DataFrame
    scan.add_variables({"table": df.createOrReplaceTempView("__check_target")})
    scan.add_sodacl_yaml_file(checks_yaml_path)

    scan.execute()
    results = scan.get_scan_results()
    return {
        "passed": scan.has_check_fails() is False,
        "critical_failures": [c for c in results if c.outcome == "fail" and c.name in CRITICAL_CHECKS],
        "warnings": [c for c in results if c.outcome == "warn"],
    }
```

### Pattern 3: Airflow DAG with Medallion Layer Orchestration

**What:** Hybrid DAG design with source-specific Bronze-to-Silver DAGs and cross-source Gold DAGs.

**When to use:** All Airflow DAGs in the project follow this pattern.

**Example:**
```python
# Source: Airflow 3.x TaskFlow API + SparkSubmitOperator
from datetime import datetime, timedelta
from airflow.sdk import DAG, task
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

default_args = {
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "on_failure_callback": alert_on_failure,  # Alert after retries exhausted
}

with DAG(
    dag_id="bronze_silver_trades",
    schedule="0 6 * * *",  # Daily at 6 AM
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["bronze", "silver", "trades"],
) as dag:

    ingest_bronze = SparkSubmitOperator(
        task_id="ingest_trades_bronze",
        application="etl/src/pipelines/bronze/trades_ingest.py",
        conn_id="spark_default",
        conf={
            "spark.sql.catalog.lakehouse": "org.apache.iceberg.spark.SparkCatalog",
            "spark.sql.catalog.lakehouse.type": "rest",
            "spark.sql.catalog.lakehouse.uri": "{{ var.value.nessie_iceberg_uri }}",
            "spark.openlineage.transport.type": "http",
            "spark.openlineage.transport.url": "{{ var.value.marquez_url }}",
        },
    )

    quality_gate_bronze = SparkSubmitOperator(
        task_id="quality_check_bronze_trades",
        application="etl/src/quality/scanner.py",
        application_args=["--checks", "quality/checks/bronze_trades.yml", "--table", "bronze.trades"],
        conn_id="spark_default",
    )

    transform_silver = SparkSubmitOperator(
        task_id="transform_trades_silver",
        application="etl/src/pipelines/silver/trades_clean.py",
        conn_id="spark_default",
    )

    quality_gate_silver = SparkSubmitOperator(
        task_id="quality_check_silver_trades",
        application="etl/src/quality/scanner.py",
        application_args=["--checks", "quality/checks/silver_trades.yml", "--table", "silver.trades"],
        conn_id="spark_default",
    )

    ingest_bronze >> quality_gate_bronze >> transform_silver >> quality_gate_silver
```

### Pattern 4: Source-to-Lakehouse Reconciliation

**What:** Automated comparison between source system counts/checksums and Iceberg table counts/checksums after migration.

**When to use:** Every migrated DataStage job must pass reconciliation before being considered validated.

**Example:**
```python
# Source: Project-specific pattern for QUAL-03
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ReconciliationResult:
    table_name: str
    source_row_count: int
    target_row_count: int
    row_count_match: bool
    source_checksum: Decimal | None
    target_checksum: Decimal | None
    checksum_match: bool | None
    source_aggregates: dict
    target_aggregates: dict
    aggregate_matches: dict[str, bool]
    passed: bool


def reconcile_table(
    spark,
    source_query: str,  # SQL to run against source system
    target_table: str,   # Iceberg table name (e.g., "silver.trades")
    checksum_columns: list[str] | None = None,
    aggregate_columns: dict[str, str] | None = None,  # {"column": "SUM|AVG|MIN|MAX"}
) -> ReconciliationResult:
    """Compare source and target data for migration validation."""
    ...
```

### Pattern 5: OpenLineage Configuration

**What:** Dual lineage capture -- Airflow plugin for task-level, Spark agent for column-level.

**When to use:** All pipelines must emit lineage.

**Example:**
```ini
# airflow.cfg or environment variables
[openlineage]
transport = {"type": "http", "url": "http://marquez:5000", "endpoint": "api/v1/lineage"}
namespace = "lakehouse"
spark_inject_parent_job_info = true
spark_inject_transport_info = true
```

```python
# Spark session configuration for OpenLineage agent
# Added to get_spark_session() in catalog.py
builder = builder.config(
    "spark.jars.packages",
    "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1,"
    "io.openlineage:openlineage-spark_2.12:1.25.0"
).config(
    "spark.extraListeners", "io.openlineage.spark.agent.OpenLineageSparkListener"
).config(
    "spark.openlineage.transport.type", "http"
).config(
    "spark.openlineage.transport.url", "http://marquez:5000"
).config(
    "spark.openlineage.transport.endpoint", "api/v1/lineage"
)
# Column-level lineage is enabled by default in OpenLineage Spark agent
```

### Anti-Patterns to Avoid
- **Direct Iceberg writes without schema validation:** Never write to an Iceberg table without first validating the DataFrame schema matches the target. Schema drift causes downstream failures
- **Skipping quality gates for "simple" pipelines:** Every pipeline, even simple ones, must run through quality checks. A "simple" pipeline with a broken source is the most dangerous
- **Monolithic DAGs:** Don't put all Bronze/Silver/Gold steps in one DAG. Source-specific DAGs for Bronze-to-Silver, separate Gold DAGs for cross-source. This allows independent scheduling and failure isolation
- **Hardcoded connection strings in DAG files:** Use Airflow Variables/Connections for all endpoint URLs, credentials
- **Non-deterministic quality checks:** All checks must be deterministic and repeatable. Avoid checks that depend on wall-clock time or external state
- **Ignoring Spark session reuse:** Create one SparkSession per Spark job, not per function call. The existing `get_spark_session()` factory should be the only entry point

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| COBOL copybook parsing | Custom EBCDIC/packed decimal parser | Cobrix (Spark) or coboljsonifier (Python) | COMP-3 packed decimal, REDEFINES, multi-level groups are notoriously tricky. Years of edge cases |
| Data quality checks | Custom validation functions | Soda Core SodaCL | YAML-based, declarative, integrates with Spark DataFrames natively. Built-in check types for common validations |
| Workflow orchestration | Custom scheduler/cron | Apache Airflow | Dependency management, retries, backfill, UI, logging, metrics. Decades of production hardening |
| Data lineage capture | Custom metadata logging | OpenLineage + Marquez | Standard protocol, automatic extraction from Spark/Airflow, column-level lineage, visualization UI |
| Pipeline observability | Custom monitoring scripts | Grafana + Prometheus + Airflow StatsD | Pre-built Airflow dashboards, alerting, time-series storage |
| Schema validation | Custom DataFrame column checks | PySpark StructType comparison + schema enforcement mode | Built into Spark, handles type coercion, nullability, nested types |
| Incremental loading | Custom watermark tracking | Iceberg merge-on-read + watermark patterns | Iceberg supports MERGE INTO for upserts natively. Watermark tracking via Iceberg snapshot metadata |

**Key insight:** The complexity in ETL migration is not in any single component -- it is in the integration of orchestration, quality, lineage, and data processing. Each component has mature open-source solutions. The engineering challenge is wiring them together coherently, which is what the base class pattern provides.

## Common Pitfalls

### Pitfall 1: Airflow 3.x Breaking Changes from 2.x
**What goes wrong:** Teams assume Airflow 2.x patterns work unchanged in Airflow 3.x. Key differences: `logical_date` semantics changed (now equals `run_after` not `data_interval_start`), Flask-AppBuilder auth removed (use SimpleAuthManager), XCom pickling disabled by default, direct metadata DB access no longer works from tasks.
**Why it happens:** Most online tutorials and examples still target Airflow 2.x.
**How to avoid:** Start fresh with Airflow 3.x. Use the official docker-compose.yaml from airflow.apache.org. Run the `ruff` migration checker (`ruff check --select AIR3` on DAG files). Use the TaskFlow API (`@task` decorators) from the start.
**Warning signs:** Import errors referencing `airflow.operators` instead of `airflow.providers`, XCom serialization failures, auth configuration errors.

### Pitfall 2: Soda Core Spark DataFrame Scan Configuration
**What goes wrong:** Treating Soda's Spark DataFrame integration like a SQL data source. For DataFrames, you do NOT need a configuration.yml file -- you pass the SparkSession directly via `scan.add_spark_session()`. Confusing the two paths leads to connection errors.
**Why it happens:** Soda documentation covers both paths and they look similar.
**How to avoid:** For in-pipeline quality gates on DataFrames, use the programmatic scan API only. Reserve configuration.yml for scheduled SQL scans against the catalog.
**Warning signs:** "Connection refused" errors when no JDBC endpoint exists, configuration asking for host/port when scanning DataFrames.

### Pitfall 3: OpenLineage Spark Agent + Nessie REST Catalog Interaction
**What goes wrong:** OpenLineage Spark agent may not correctly resolve table names from REST catalogs if the namespace/dataset naming convention differs from what OpenLineage expects.
**Why it happens:** OpenLineage uses a naming convention based on `namespace:database.table` which must align with the Iceberg catalog's actual namespace structure.
**How to avoid:** Set `spark.openlineage.namespace` explicitly to "lakehouse". Verify lineage events appear in Marquez with correct table references before scaling to all pipelines. Test with one simple pipeline first.
**Warning signs:** Lineage events showing generic table names, missing column-level detail, broken lineage graphs in Marquez UI.

### Pitfall 4: Mainframe COBOL Copybook Complexity
**What goes wrong:** Underestimating the complexity of COBOL copybooks with REDEFINES, OCCURS DEPENDING ON, packed decimal (COMP-3), and nested group structures. A copybook that looks simple can have dozens of edge cases.
**Why it happens:** COBOL data types have no direct equivalent in modern systems. EBCDIC encoding varies by codepage. Packed decimal sign nibbles differ by platform.
**How to avoid:** Start with the simplest mainframe job first. Use Cobrix (Spark-native, battle-tested at ABSA bank). Have sample data files AND expected outputs from DataStage for comparison. Validate byte-by-byte against known good output.
**Warning signs:** Decimal values off by factors of 10/100, garbled text in string fields, incorrect record lengths.

### Pitfall 5: Quality Gate Performance Impact
**What goes wrong:** Running comprehensive quality checks on large DataFrames adds significant time to pipeline execution. Full-table scans for uniqueness checks or aggregation checks can double pipeline runtime.
**Why it happens:** Soda Core translates checks into Spark SQL queries that scan the full dataset.
**How to avoid:** For Bronze layer (high volume), use sampling for advisory checks and full scans only for critical checks. Keep critical check count to under 5 per table. Profile execution time of each check in dev before deploying to prod.
**Warning signs:** Pipeline SLA misses that correlate with quality check execution, Spark jobs with unexpectedly high shuffle.

### Pitfall 6: Parallel Run Validation Precision
**What goes wrong:** Floating-point arithmetic differences between DataStage (running on mainframe/server) and PySpark cause false positives in reconciliation. Aggregated sums differ by tiny amounts due to order-of-operations and precision.
**Why it happens:** DataStage may use different floating-point libraries, rounding modes, or processing order than Spark.
**How to avoid:** Use Decimal types throughout (already established in project). Define acceptable tolerance thresholds for aggregates. Compare at row level first, then aggregates. Document any accepted differences with justification for audit.
**Warning signs:** Row counts match but aggregate checksums differ, differences that appear random but are consistent.

## Code Examples

### Bronze Layer Ingestion with Metadata Columns
```python
# Source: Project-specific pattern based on locked decisions
from pyspark.sql import functions as F
from pyspark.sql import DataFrame


def add_bronze_metadata(df: DataFrame, source_system: str, batch_id: str) -> DataFrame:
    """Add standard Bronze metadata columns per locked decision."""
    return df.withColumns({
        "source_system": F.lit(source_system),
        "ingestion_ts": F.current_timestamp(),
        "batch_id": F.lit(batch_id),
    })
```

### Watermark-Based Incremental Loading
```python
# Source: Iceberg + PySpark pattern for ETL-05
def incremental_extract(
    spark,
    source_table: str,
    watermark_column: str,
    last_watermark_value,
) -> "DataFrame":
    """Extract only new/changed records since last watermark."""
    return spark.read.format("jdbc").options(
        url="jdbc:...",
        dbtable=f"(SELECT * FROM {source_table} WHERE {watermark_column} > '{last_watermark_value}') AS subq",
    ).load()


def get_last_watermark(spark, iceberg_table: str, watermark_column: str):
    """Get the last watermark value from the Iceberg table."""
    result = spark.sql(
        f"SELECT MAX({watermark_column}) as max_wm FROM lakehouse.{iceberg_table}"
    ).collect()
    return result[0]["max_wm"] if result else None
```

### COBOL Copybook Parsing with Cobrix
```python
# Source: Cobrix documentation (https://github.com/AbsaOSS/cobrix)
def read_mainframe_file(spark, copybook_path: str, data_path: str) -> "DataFrame":
    """Read mainframe EBCDIC file using COBOL copybook schema."""
    return spark.read.format("cobol").options(
        copybook=copybook_path,
        encoding="ebcdic",
        is_record_sequence="true",
        schema_retention_policy="collapse_root",
    ).load(data_path)
```

### DataStage Job Inventory Model
```python
# Source: Project-specific pattern for ETL-07
from dataclasses import dataclass
from enum import Enum


class JobComplexity(Enum):
    SIMPLE = "simple"      # Single source, basic transform
    MEDIUM = "medium"      # Multi-source joins, lookups
    COMPLEX = "complex"    # Mainframe, COBOL, multi-step


@dataclass
class DataStageJob:
    job_name: str
    job_id: str
    complexity: JobComplexity
    source_systems: list[str]
    target_tables: list[str]
    dependencies: list[str]  # Other job IDs this depends on
    estimated_effort_hours: float
    has_mainframe_source: bool
    transformation_description: str
    schedule: str
    avg_runtime_minutes: float
    row_volume_estimate: int
    migration_status: str  # "not_started", "in_progress", "migrated", "validated"
    notes: str = ""
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Airflow 2.x with FAB auth | Airflow 3.x with SimpleAuthManager, Task SDK | Apr 2025 | Must use Airflow 3 patterns, not 2.x tutorials |
| Great Expectations 0.x | Great Expectations 1.x (1.15.0) | 2024-2025 | Major API rewrite. Old `0.x` examples don't work |
| Standalone openlineage-airflow package | apache-airflow-providers-openlineage (native) | Airflow 2.7+ | Use the provider package, not standalone |
| Airflow `logical_date` = `data_interval_start` | `logical_date` = `run_after` | Airflow 3.0 | Scheduling semantics changed. Critical for incremental loading |
| XCom pickling | JSON serialization only | Airflow 3.0 | Must ensure all XCom values are JSON-serializable |

**Deprecated/outdated:**
- `openlineage-airflow` standalone package: replaced by `apache-airflow-providers-openlineage`
- Airflow `SubDAGs`: removed in Airflow 3.0, use TaskGroups instead
- Great Expectations `0.x` API: completely different from `1.x`. Do not use `0.x` documentation
- Airflow `contrib.operators`: removed, all moved to provider packages

## Open Questions

1. **Airflow 3 Stability for Production**
   - What we know: Airflow 3.0 released Apr 2025, now at 3.1.8. Active development, major architectural changes from 2.x
   - What's unclear: Whether 3.1.x has matured enough for a regulated financial services environment. Many enterprises still on 2.x
   - Recommendation: Start with 3.1.x since this is a new deployment (no migration from 2.x needed). Pin to specific patch version. If stability issues emerge, 2.11.x is the fallback since OpenLineage provider supports both

2. **DB2 z/OS Licensing for Python ibm_db**
   - What we know: ibm_db driver requires DB2 Connect license for z/OS access. The existing DataStage deployment presumably has this license
   - What's unclear: Whether the existing license covers additional Python clients or needs expansion
   - Recommendation: Validate with infrastructure/licensing team early. This can block mainframe connectivity validation

3. **Soda Core Feature Completeness Without Soda Cloud**
   - What we know: Core open-source Soda Core provides scan execution, SodaCL, and results. Dashboards, anomaly detection, and data contracts require Soda Cloud (paid)
   - What's unclear: Whether open-source features are sufficient for QUAL-04 alerting requirements
   - Recommendation: Use Soda Core OSS for in-pipeline quality gates. Pipe results to Grafana for dashboarding and alerting. This avoids vendor lock-in and keeps the alerting stack unified with Airflow observability

4. **Cobrix Compatibility with Spark 3.5 and Iceberg Runtime**
   - What we know: Cobrix 2.9.x supports Spark 3.x. Project uses Spark 3.5 with Iceberg runtime 1.7.1
   - What's unclear: Whether Cobrix JAR conflicts with Iceberg Spark runtime JARs
   - Recommendation: Test Cobrix + Iceberg in dev environment before committing to mainframe migration pattern. Have coboljsonifier as fallback for pure Python parsing if JAR conflicts arise

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0.0 (already configured) |
| Config file | `etl/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd /home/azureuser/lakehouse/etl && python -m pytest tests/unit/ -x --tb=short` |
| Full suite command | `docker compose -f docker-compose.test.yml up --build --abort-on-container-exit` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FNDTN-07 | Bronze/Silver/Gold namespaces created with correct boundaries | integration | `pytest tests/integration/test_medallion_layers.py -x` | No - Wave 0 |
| ETL-01 | Base pipeline class enforces extract/transform/write contract | unit | `pytest tests/unit/test_base_pipeline.py -x` | No - Wave 0 |
| ETL-02 | Pilot job produces matching output to DataStage | integration | `pytest tests/integration/test_pilot_reconciliation.py -x` | No - Wave 0 |
| ETL-03 | Mainframe file parsed correctly via Cobrix | integration | `pytest tests/integration/test_mainframe_ingest.py -x` | No - Wave 0 |
| ETL-04 | Airflow DAG loads without import errors | unit | `pytest tests/unit/test_dag_integrity.py -x` | No - Wave 0 |
| ETL-05 | Incremental load picks up only new records | integration | `pytest tests/integration/test_incremental_loading.py -x` | No - Wave 0 |
| ETL-06 | ETL patterns documented and base class usable | unit | `pytest tests/unit/test_etl_patterns.py -x` | No - Wave 0 |
| ETL-07 | Job inventory model serializes/deserializes | unit | `pytest tests/unit/test_job_inventory.py -x` | No - Wave 0 |
| QUAL-01 | Schema validation rejects mismatched DataFrame | unit | `pytest tests/unit/test_schema_validation.py -x` | No - Wave 0 |
| QUAL-02 | Soda checks detect null/range/uniqueness violations | integration | `pytest tests/integration/test_quality_checks.py -x` | No - Wave 0 |
| QUAL-03 | Reconciliation detects row count mismatches | unit | `pytest tests/unit/test_reconciliation.py -x` | No - Wave 0 |
| QUAL-04 | Quality alerting triggers on degradation | integration | `pytest tests/integration/test_quality_alerting.py -x` | No - Wave 0 |
| GOVN-01 | OpenLineage events emitted for Spark + Airflow | integration | `pytest tests/integration/test_lineage_capture.py -x` | No - Wave 0 |
| PLAT-02 | Grafana dashboard config is valid JSON/YAML | unit | `pytest tests/unit/test_dashboard_config.py -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd /home/azureuser/lakehouse/etl && python -m pytest tests/unit/ -x --tb=short`
- **Per wave merge:** `docker compose -f docker-compose.test.yml up --build --abort-on-container-exit`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `etl/tests/unit/test_base_pipeline.py` -- covers ETL-01
- [ ] `etl/tests/unit/test_schema_validation.py` -- covers QUAL-01
- [ ] `etl/tests/unit/test_reconciliation.py` -- covers QUAL-03
- [ ] `etl/tests/unit/test_dag_integrity.py` -- covers ETL-04
- [ ] `etl/tests/unit/test_job_inventory.py` -- covers ETL-07
- [ ] `etl/tests/unit/test_etl_patterns.py` -- covers ETL-06
- [ ] `etl/tests/unit/test_dashboard_config.py` -- covers PLAT-02
- [ ] `etl/tests/integration/test_medallion_layers.py` -- covers FNDTN-07
- [ ] `etl/tests/integration/test_quality_checks.py` -- covers QUAL-02
- [ ] `etl/tests/integration/test_lineage_capture.py` -- covers GOVN-01
- [ ] `etl/tests/integration/test_incremental_loading.py` -- covers ETL-05
- [ ] `etl/tests/integration/test_mainframe_ingest.py` -- covers ETL-03
- [ ] `etl/tests/integration/test_pilot_reconciliation.py` -- covers ETL-02
- [ ] `etl/tests/integration/test_quality_alerting.py` -- covers QUAL-04
- [ ] Docker Compose extension for Airflow + Marquez services (extend `docker-compose.test.yml`)
- [ ] `soda-core-spark-df` added to `pyproject.toml` dependencies
- [ ] Cobrix Spark package added to test Spark session configuration

## Sources

### Primary (HIGH confidence)
- [Apache Airflow official docs](https://airflow.apache.org/docs/apache-airflow/stable/) -- Airflow 3.1.8 current stable, Python 3.9-3.12 support, Docker Compose setup, migration from 2.x
- [Apache Airflow Upgrading to 3](https://airflow.apache.org/docs/apache-airflow/stable/installation/upgrading_to_airflow3.html) -- Breaking changes: logical_date semantics, FAB removal, XCom pickling disabled
- [OpenLineage Airflow provider docs](https://airflow.apache.org/docs/apache-airflow-providers-openlineage/stable/guides/user.html) -- Version 2.10.x, spark_inject_parent_job_info, spark_inject_transport_info configuration
- [OpenLineage Spark + Airflow scheduling](https://openlineage.io/docs/integrations/spark/configuration/airflow/) -- Parent job property injection, root parent tracking (v1.31.0+), macro-based dynamic configuration
- [Marquez GitHub](https://github.com/MarquezProject/marquez) -- v0.50.0, Docker deployment, API on port 5000, UI on port 3000
- [great-expectations PyPI](https://pypi.org/project/great-expectations/) -- v1.15.0 (Mar 2026), Python 3.10-3.13, PySpark support
- [soda-core-spark-df PyPI](https://pypi.org/project/soda-core-spark-df/) -- v3.5.6 (Sep 2025), Python 3 compatible
- [Cobrix GitHub](https://github.com/AbsaOSS/cobrix) -- v2.9.2, Spark 3.x COBOL/EBCDIC data source
- [ibm_db PyPI](https://pypi.org/project/ibm-db/) -- Python 3.9-3.14 support, requires DB2 Connect license for z/OS
- Existing project code: `etl/src/iceberg_utils/catalog.py`, `etl/src/config/settings.py`, `etl/pyproject.toml`

### Secondary (MEDIUM confidence)
- [Grafana Airflow monitoring dashboards](https://grafana.com/grafana/dashboards/14448-airflow-monitoring/) -- Pre-built dashboards for DAG metrics, verified with Grafana Labs
- [AWS Prescriptive Guidance EBCDIC conversion](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/convert-and-unpack-ebcdic-data-to-ascii-on-aws-by-using-python.html) -- AWS-verified pattern for EBCDIC conversion
- [Soda Core Spark connection docs](https://docs.soda.io/data-source-reference/connect-spark) -- Programmatic scan API with add_spark_session()
- [Debezium CDC with Spark and Iceberg](https://medium.com/@aalopatin/change-data-capture-cdc-with-debezium-spark-and-iceberg-4472c9a853e2) -- Batch and streaming CDC patterns, verified against Debezium docs
- [Airflow 3.1 Celery + StatsD setup](https://medium.com/@lorenzouriel/airflow-3-1-setup-with-celery-executor-and-statsd-for-monitoring-60b88e9f80e3) -- Production-ready Airflow 3.1 with monitoring

### Tertiary (LOW confidence)
- Soda Core open-source feature completeness for QUAL-04 -- needs validation that OSS alerts (without Soda Cloud) meet requirements
- Cobrix + Iceberg runtime JAR compatibility -- needs integration testing
- Airflow 3.1.x production stability for regulated financial services -- limited production case studies found

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All components verified via official docs and PyPI. Versions confirmed current
- Architecture: HIGH -- Medallion pattern is well-documented. ETL base class design follows established OOP patterns. DAG design follows Airflow best practices
- DQ framework recommendation (Soda Core): MEDIUM -- Clear advantages for this use case (YAML simplicity, Spark DF native support, 40+ engineer onboarding). Open question about OSS feature completeness for alerting
- Mainframe connectivity: MEDIUM -- Cobrix and ibm_db are established tools but JAR compatibility and DB2 licensing need validation
- Pitfalls: HIGH -- Airflow 3 breaking changes verified via official migration docs. Soda/OpenLineage integration patterns verified

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (30 days -- stack is stable, Airflow 3.x is maturing)
