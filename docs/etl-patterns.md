# Standardized ETL Patterns

This document defines the standardized ETL patterns for the lakehouse platform.
It is the team onboarding reference for 40+ engineers migrating DataStage jobs
to the Python/PySpark framework. Follow these patterns to ensure consistency
across all pipelines.

---

## 1. Architecture Overview

### Medallion Architecture

All data flows through three layers:

| Layer | Purpose | Namespace | Retention |
|-------|---------|-----------|-----------|
| **Bronze** | Raw-as-is with metadata | `lakehouse.bronze.*` | Full history |
| **Silver** | Cleaned, deduplicated, entity-centric | `lakehouse.silver.*` | Full history |
| **Gold** | Pre-aggregated metrics and curated views | `lakehouse.gold.*` | Full history |

### Data Flow

```
Source Systems --> [Bronze Ingest + Metadata] --> Bronze Tables
                                                    |
                                          [Quality Gate: Critical]
                                                    |
Bronze Tables --> [Dedup + Business Rules] --> Silver Tables
                                                    |
                                          [Quality Gate: Critical]
                                                    |
Silver Tables --> [Aggregation / Curation] --> Gold Tables
```

### Namespace Convention

- Format: `lakehouse.{layer}.{entity}`
- Examples: `lakehouse.bronze.trades`, `lakehouse.silver.positions`, `lakehouse.gold.trading_metrics`
- The `lakehouse` prefix is the Iceberg catalog name (Nessie REST catalog)

### Metadata Columns (Bronze)

Every Bronze table includes three metadata columns:

| Column | Type | Description |
|--------|------|-------------|
| `source_system` | STRING | Identifier for the data source (e.g., "trading_platform") |
| `ingestion_ts` | TIMESTAMP | Timestamp when the record was ingested |
| `batch_id` | STRING | Unique identifier for the ingestion batch |

---

## 2. Creating a New Pipeline

### Step 1: Extend BasePipeline

All pipelines must extend `BasePipeline` from `src.pipelines.base`. This
enforces the extract -> transform -> validate_schema -> quality_check -> write
contract.

```python
from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

class MyBronzePipeline(BasePipeline):
    def __init__(self, spark, source_data, source_system, batch_id):
        self._source_data = source_data
        self._source_system = source_system
        self._batch_id = batch_id

        config = PipelineConfig(
            name="my-data-bronze",
            target_layer=MedallionLayer.BRONZE,
            target_table="my_data",
            target_schema=self._build_bronze_schema(),
            quality_checks_path="src/quality/checks/bronze_my_data.yml",
            critical_checks=["primary_key_not_null", "primary_key_unique"],
        )
        super().__init__(spark=spark, config=config)

    @staticmethod
    def _build_bronze_schema():
        from pyspark.sql.types import (
            StringType, TimestampType, StructField, StructType
        )
        return StructType([
            StructField("id", StringType(), nullable=False),
            StructField("name", StringType(), nullable=True),
            # ... your fields ...
            StructField("source_system", StringType(), nullable=True),
            StructField("ingestion_ts", TimestampType(), nullable=True),
            StructField("batch_id", StringType(), nullable=True),
        ])

    def extract(self):
        # Return raw DataFrame from source
        return self.spark.createDataFrame(self._source_data, self._base_schema())

    def transform(self, df):
        # Bronze: add metadata columns only (no business logic)
        return self.add_metadata_columns(df, self._source_system, self._batch_id)
```

### Step 2: Run the Pipeline

```python
from src.iceberg_utils.catalog import get_spark_session

spark = get_spark_session(enable_lineage=True)
pipeline = MyBronzePipeline(spark, source_data, "my_source", "batch-001")
result = pipeline.execute()
# result = {"rows_written": 1000, "quality": {...}}
```

### Step 3: Add Quality Checks

Create a SodaCL YAML file (see Section 3) and reference it in PipelineConfig.

### Step 4: Create Airflow DAG

Create a DAG file in `etl/dags/` following the patterns in Section 4.

---

## 3. Quality Checks

### SodaCL YAML Format

Quality checks use Soda Core with SodaCL YAML definitions. Each layer has
its own checks file.

```yaml
# src/quality/checks/bronze_my_data.yml
checks for __soda_check_target:
  # --- Critical checks (hard block) ---

  # Primary key must not be null
  - missing_count(id) = 0:
      name: primary_key_not_null

  # Primary key must be unique
  - duplicate_count(id) = 0:
      name: primary_key_unique

  # Schema validation
  - schema:
      name: schema_required_columns
      fail:
        when required column missing:
          [id, name, source_system]

  # --- Advisory checks (soft alert) ---

  # Data completeness
  - missing_percent(name) < 5:
      name: name_completeness
```

### Critical vs Advisory Checks

| Type | Behavior | Use For |
|------|----------|---------|
| **Critical** | Blocks pipeline progression | Schema validation, PK null/unique, referential integrity |
| **Advisory** | Generates warning, pipeline continues | Completeness rates, range validation, outlier detection |

Critical checks are specified in `PipelineConfig.critical_checks` as a list
of check names matching the `name:` field in the YAML.

### Quality Gate Integration

Quality checks run automatically in `BasePipeline.execute()`. Failed critical
checks raise `QualityGateError` and block the pipeline. The quality results
are returned as structured dicts for Grafana dashboard consumption.

```python
# Quality results structure:
{
    "passed": True,
    "critical_failures": [],
    "warnings": [QualityCheckResult(...)],
    "all_results": [QualityCheckResult(...)],
}
```

---

## 4. DAG Patterns

### Hybrid DAG Design

Per locked decision, we use a hybrid DAG pattern:

| DAG Type | Pattern | Example |
|----------|---------|---------|
| **Source-specific** | One DAG per source, Bronze -> Silver | `bronze_silver_trades` |
| **Cross-source Gold** | Separate DAG for aggregation | `gold_trading_metrics` |
| **Maintenance** | Weekly Iceberg maintenance | `iceberg_maintenance` |
| **Quality Report** | Daily quality monitoring | `quality_monitoring_report` |

### DAG Template

```python
from datetime import timedelta
from airflow.sdk import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

default_args = {
    "owner": "data-engineering",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "on_failure_callback": _on_failure_callback,
}

# Include OpenLineage + Iceberg Spark config
_spark_conf = {
    "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
    "spark.sql.catalog.lakehouse": "org.apache.iceberg.spark.SparkCatalog",
    "spark.sql.catalog.lakehouse.type": "rest",
    # ... full config ...
    "spark.extraListeners": "io.openlineage.spark.agent.OpenLineageSparkListener",
    # ... OpenLineage config ...
}

with DAG(
    dag_id="bronze_silver_my_data",
    schedule="0 6 * * *",
    start_date=None,
    catchup=False,
    default_args=default_args,
    tags=["bronze", "silver", "my_data"],
) as dag:
    ingest = SparkSubmitOperator(
        task_id="ingest_bronze",
        application="/opt/airflow/etl_src/pipelines/bronze/my_ingest.py",
        conf=_spark_conf,
        packages=_spark_packages,
    )
    # ... more tasks ...
```

### Retry and Failure Handling

- **Retries:** Minimum 3 with exponential backoff (locked decision)
- **Max retry delay:** 30 minutes
- **Failure callback:** Triggers alerting (PagerDuty, Slack)
- **ExternalTaskSensor:** Gold DAGs wait for Bronze/Silver to complete

### Schedule Conventions

| DAG Type | Schedule | Rationale |
|----------|----------|-----------|
| Bronze/Silver | 06:00 - 07:00 UTC | Early morning, source data available |
| Gold | 08:00 UTC | After Bronze/Silver complete |
| Quality Report | 09:00 UTC | After all pipelines complete |
| Maintenance | Sunday 02:00 UTC | Low-traffic window |

---

## 5. Incremental Loading

### Watermark-Based

For sources without CDC (Change Data Capture), use watermark-based loading:

```python
from src.pipelines.incremental import (
    IncrementalConfig,
    get_last_watermark,
    incremental_extract,
    merge_incremental,
)

# Configure incremental loading
config = IncrementalConfig(
    watermark_column="updated_at",
    merge_keys=["trade_id"],
    target_table="lakehouse.silver.trades",
)

# Get high-water mark from existing Iceberg table
watermark = get_last_watermark(spark, config)

# Extract only records newer than watermark
new_df = incremental_extract(spark, source_df, config, watermark)

# Upsert into Iceberg table (MERGE INTO)
merge_incremental(spark, new_df, config)
```

### CDC (Change Data Capture)

Where available (DB2 logs, Debezium), use CDC for real-time change capture:

1. Debezium captures change events from source database
2. Events land in Kafka topics
3. Spark Structured Streaming reads from Kafka
4. MERGE INTO applies changes to Iceberg tables

### MERGE INTO Pattern

```sql
MERGE INTO lakehouse.silver.trades AS target
USING __incremental_source AS source
ON target.trade_id = source.trade_id
WHEN MATCHED THEN
  UPDATE SET *
WHEN NOT MATCHED THEN
  INSERT *
```

The `merge_incremental()` utility handles this automatically using a temporary
view and Spark SQL.

---

## 6. Mainframe Sources

### Cobrix for COBOL Copybook Parsing

Mainframe flat files use COBOL copybooks to define record layouts. Cobrix
is a Spark data source that reads these natively:

```python
from src.pipelines.bronze.mainframe_ingest import MainframeBronzePipeline

pipeline = MainframeBronzePipeline(
    spark=spark,
    data_path="s3://lakehouse-onprem/mainframe/accounts.dat",
    copybook_path="etl/tests/fixtures/sample_copybook.cpy",
    source_system="mainframe_db2",
    batch_id="batch-mf-001",
)
result = pipeline.execute()
```

### Key Considerations

| Aspect | Approach |
|--------|----------|
| **COBOL copybooks** | Cobrix parses EBCDIC encoding, packed decimal, and record layouts |
| **DB2 z/OS JDBC** | `ibm_db` Python driver for direct mainframe database access |
| **Schema validation** | Overridden -- Cobrix derives schema from copybook at runtime |
| **Testing** | Unit tests use mock data; integration tests need real EBCDIC binary files |
| **Error handling** | Graceful skip when Cobrix JAR unavailable (`CobrixNotAvailableError`) |

### COBOL Copybook Example

```cobol
       01  ACCOUNT-RECORD.
           05  ACCOUNT-ID         PIC X(10).
           05  ACCOUNT-NAME       PIC X(50).
           05  BALANCE             PIC S9(13)V99 COMP-3.
           05  LAST-UPDATE         PIC X(8).
```

---

## 7. Testing

### Unit Test Patterns

Unit tests run without Spark or Docker services. They mock PySpark
dependencies using `unittest.mock`.

```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.mark.unit
class TestMyPipeline:
    def test_transform_adds_metadata(self):
        """Bronze transform adds source_system, ingestion_ts, batch_id."""
        mock_spark = MagicMock()
        pipeline = MyBronzePipeline(
            spark=mock_spark,
            source_data=[],
            source_system="test",
            batch_id="batch-001",
        )
        mock_df = MagicMock()
        result = pipeline.transform(mock_df)
        # Verify withColumn calls for metadata
        assert mock_df.withColumn.called
```

**Key patterns:**
- Use `@pytest.mark.unit` marker
- Mock PySpark at module level: `@patch("src.pipelines.base.lit")`
- Test schemas via StructType assertions (no Spark needed)
- Test classification/filtering logic directly

### Integration Test Patterns

Integration tests require Docker services (Nessie, MinIO, Spark).

```python
import pytest

@pytest.mark.integration
class TestMyPipelineIntegration:
    def test_full_medallion_flow(self, spark_session):
        """End-to-end: Bronze -> Silver -> Gold with real Iceberg tables."""
        # Uses conftest.py spark_session fixture
        pipeline = MyBronzePipeline(spark_session, data, "test", "batch-001")
        result = pipeline.execute()
        assert result["rows_written"] > 0

        # Read back from Iceberg
        df = spark_session.table("lakehouse.bronze.my_data")
        assert df.count() == len(data)
```

### Reconciliation Testing

Use the reconciliation framework to validate migration accuracy:

```python
from src.quality.reconciliation import reconcile_table

result = reconcile_table(
    spark=spark,
    source_df=source_data,
    target_table="lakehouse.bronze.trades",
    key_columns=["trade_id"],
    numeric_columns=["price", "quantity"],
    tolerance=0.001,
)
assert result.row_count_match
assert result.all_checksums_match
```

---

## 8. Job Inventory

### Cataloging DataStage Jobs

Use the job inventory module to catalog existing DataStage jobs for migration
planning:

```python
from src.inventory.catalog import JobInventory
from src.inventory.models import DataStageJob, JobComplexity

# Create a new job entry
job = DataStageJob(
    job_name="DS_TRADES_DAILY",
    job_id="ds-001",
    complexity=JobComplexity.SIMPLE,
    source_systems=["trading_platform"],
    target_tables=["bronze.trades"],
    dependencies=[],
    estimated_effort_hours=8.0,
    has_mainframe_source=False,
    transformation_description="Simple daily trade load",
    schedule="0 6 * * *",
    avg_runtime_minutes=15.0,
    row_volume_estimate=50000,
    migration_status="not_started",
)

# Add to inventory and save
inventory = JobInventory()
inventory.add_job(job)
inventory.save_to_json("inventory.json")
```

### Complexity Classification

The inventory module classifies jobs automatically:

| Complexity | Criteria | Estimated Effort |
|-----------|----------|-----------------|
| **SIMPLE** | Single source, no mainframe, no dependencies | 4-16 hours |
| **MEDIUM** | Multi-source joins, lookups, has dependencies | 16-40 hours |
| **COMPLEX** | Mainframe, COBOL, multi-step, high business logic | 40-120 hours |

```python
# Automatic classification
complexity = inventory.classify_complexity(job)

# Get migration statistics
stats = inventory.get_migration_stats()
# {"total_jobs": 42, "by_complexity": {"simple": 20, "medium": 15, "complex": 7}, ...}
```

### Filtering and Reporting

```python
# Filter by complexity
complex_jobs = inventory.filter_by_complexity(JobComplexity.COMPLEX)

# Filter by source system
mainframe_jobs = inventory.filter_by_source_system("mainframe_db2")

# Filter by migration status
not_started = inventory.filter_by_status("not_started")
```

---

## Quick Reference

### Import Paths

```python
# Pipeline framework
from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig
from src.pipelines.base import SchemaValidationError, QualityGateError

# Bronze pipelines
from src.pipelines.bronze.trades_ingest import TradesBronzePipeline
from src.pipelines.bronze.positions_ingest import PositionsBronzePipeline
from src.pipelines.bronze.mainframe_ingest import MainframeBronzePipeline

# Silver pipelines
from src.pipelines.silver.trades_clean import TradesSilverPipeline
from src.pipelines.silver.positions_clean import PositionsSilverPipeline

# Gold pipelines
from src.pipelines.gold.trading_metrics import TradingMetricsGoldPipeline

# Quality
from src.quality.scanner import run_soda_checks, QualityCheckResult
from src.quality.reconciliation import reconcile_table, ReconciliationResult

# Incremental loading
from src.pipelines.incremental import IncrementalConfig, get_last_watermark, merge_incremental

# Iceberg utilities
from src.iceberg_utils.catalog import get_spark_session, create_namespace
from src.iceberg_utils.maintenance import full_maintenance

# Lineage
from src.lineage.config import get_openlineage_spark_config, OPENLINEAGE_NAMESPACE

# Job inventory
from src.inventory.catalog import JobInventory
from src.inventory.models import DataStageJob, JobComplexity
```

### Financial Precision Rules

- All monetary values use `DecimalType(38, 4)` through aggregation
- Never use `FloatType` or `DoubleType` for financial amounts
- Gold metrics maintain precision through `spark_sum` and `avg`

### Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Table name | snake_case entity | `trades`, `positions`, `trading_metrics` |
| DAG ID | snake_case with layer prefix | `bronze_silver_trades`, `gold_trading_metrics` |
| Pipeline class | PascalCase with Layer suffix | `TradesBronzePipeline`, `TradingMetricsGoldPipeline` |
| Quality checks file | `{layer}_{entity}.yml` | `bronze_trades.yml`, `silver_trades.yml` |
| Test file | `test_{module}.py` | `test_base_pipeline.py`, `test_job_inventory.py` |

---

*Document version: 1.0*
*Last updated: 2026-03-13*
*Maintained by: Data Engineering Team*
