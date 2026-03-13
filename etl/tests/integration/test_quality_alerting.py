"""Integration tests for quality check alerting structure.

Validates that quality check results are structured for downstream alerting
(Grafana/monitoring integration). Validates QUAL-04 requirement at the data
layer; dashboard integration is in Plan 05.

Requires: soda-core-spark-df installed and Java available for local Spark.
Skips gracefully when dependencies are unavailable.
"""

from __future__ import annotations

import json
import os

import pytest

# Skip entire module if soda-core not importable
soda_scan = pytest.importorskip("soda.scan", reason="soda-core not installed")


@pytest.fixture(scope="session", autouse=True)
def ensure_services():
    """Override integration conftest ensure_services -- alerting tests use local Spark only."""
    pass


@pytest.fixture(scope="module")
def local_spark():
    """Create a minimal local SparkSession for alerting tests."""
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        pytest.skip("PySpark not installed")

    try:
        spark = (
            SparkSession.builder.appName("quality-alerting-test")
            .master("local[1]")
            .config("spark.ui.enabled", "false")
            .config("spark.driver.memory", "512m")
            .config("spark.sql.shuffle.partitions", "2")
            .getOrCreate()
        )
    except Exception as e:
        pytest.skip(f"Cannot create local SparkSession: {e}")

    yield spark
    spark.stop()


@pytest.fixture
def bronze_checks_path():
    """Path to Bronze trades SodaCL check file."""
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "src",
        "quality",
        "checks",
        "bronze_trades.yml",
    )
    return os.path.abspath(path)


@pytest.mark.integration
class TestQualityCheckAlertingStructure:
    """Tests that quality check results have the right structure for alerting."""

    def test_quality_check_result_has_required_fields(self):
        """QualityCheckResult has check_name, outcome, metric_value, is_critical fields."""
        from src.quality.scanner import QualityCheckResult

        result = QualityCheckResult(
            check_name="primary_key_not_null",
            outcome="pass",
            metric_value=0,
            threshold="= 0",
            is_critical=True,
        )

        assert hasattr(result, "check_name")
        assert hasattr(result, "outcome")
        assert hasattr(result, "metric_value")
        assert hasattr(result, "threshold")
        assert hasattr(result, "is_critical")

    def test_quality_check_result_serializable_to_json(self):
        """QualityCheckResult can be serialized to JSON for Grafana/alerting."""
        from src.quality.scanner import QualityCheckResult

        result = QualityCheckResult(
            check_name="primary_key_not_null",
            outcome="fail",
            metric_value=3,
            threshold="= 0",
            is_critical=True,
        )

        json_str = result.to_json()
        assert isinstance(json_str, str)

        parsed = json.loads(json_str)
        assert parsed["check_name"] == "primary_key_not_null"
        assert parsed["outcome"] == "fail"
        assert parsed["metric_value"] == 3
        assert parsed["threshold"] == "= 0"
        assert parsed["is_critical"] is True

    def test_quality_check_result_to_dict(self):
        """QualityCheckResult.to_dict() returns a dictionary."""
        from src.quality.scanner import QualityCheckResult

        result = QualityCheckResult(
            check_name="price_non_negative",
            outcome="warn",
            metric_value=-5.0,
            threshold=">= 0",
            is_critical=False,
        )

        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["check_name"] == "price_non_negative"
        assert d["outcome"] == "warn"
        assert d["is_critical"] is False

    def test_failed_critical_check_produces_alertable_result(self, local_spark, bronze_checks_path):
        """A failed critical check produces a result that can be serialized for alerting."""
        from pyspark.sql.types import (
            DoubleType,
            IntegerType,
            StringType,
            StructField,
            StructType,
        )

        from src.quality.scanner import run_soda_checks

        # Explicit schema needed because null trade_id prevents type inference
        schema = StructType([
            StructField("trade_id", IntegerType(), True),
            StructField("trade_date", StringType(), True),
            StructField("symbol", StringType(), True),
            StructField("side", StringType(), True),
            StructField("trade_type", StringType(), True),
            StructField("quantity", IntegerType(), True),
            StructField("price", DoubleType(), True),
            StructField("notional", DoubleType(), True),
            StructField("account_id", StringType(), True),
            StructField("trader_id", StringType(), True),
            StructField("exchange", StringType(), True),
            StructField("settlement_date", StringType(), True),
        ])

        # Create data with null trade_id to trigger critical failure
        bad_data = [
            (None, "2026-01-01", "AAPL", "BUY", "MARKET", 100, 150.0, 15000.0,
             "ACCT-1000", "TRD-100", "NYSE", "2026-01-02"),
        ]
        df = local_spark.createDataFrame(bad_data, schema=schema)

        results = run_soda_checks(
            spark_session=local_spark,
            df=df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=["primary_key_not_null", "primary_key_unique"],
        )

        assert len(results["critical_failures"]) > 0

        # Each critical failure should be serializable to JSON
        for failure in results["critical_failures"]:
            json_str = failure.to_json()
            parsed = json.loads(json_str)
            assert "check_name" in parsed
            assert "outcome" in parsed
            assert parsed["is_critical"] is True

    def test_all_results_serializable_to_json_batch(self, local_spark, bronze_checks_path):
        """All check results from a scan can be batch-serialized for alerting."""
        from src.synthetic.generators import generate_trades

        from src.quality.scanner import run_soda_checks

        trades = generate_trades(num_records=50, seed=99)
        df = local_spark.createDataFrame(trades)

        results = run_soda_checks(
            spark_session=local_spark,
            df=df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=["primary_key_not_null"],
        )

        # Batch serialize all results
        batch_json = json.dumps(
            [r.to_dict() for r in results["all_results"]],
            default=str,
        )
        assert isinstance(batch_json, str)

        parsed_batch = json.loads(batch_json)
        assert isinstance(parsed_batch, list)
        assert len(parsed_batch) > 0

        # Each entry should have alerting-relevant fields
        for entry in parsed_batch:
            assert "check_name" in entry
            assert "outcome" in entry
            assert "is_critical" in entry

    def test_sequential_runs_produce_comparable_results(self, local_spark, bronze_checks_path):
        """Multiple sequential runs produce comparable results (no flaky checks)."""
        from src.synthetic.generators import generate_trades

        from src.quality.scanner import run_soda_checks

        trades = generate_trades(num_records=50, seed=42)
        df = local_spark.createDataFrame(trades)
        critical = ["primary_key_not_null", "primary_key_unique"]

        results_a = run_soda_checks(
            spark_session=local_spark,
            df=df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=critical,
        )
        results_b = run_soda_checks(
            spark_session=local_spark,
            df=df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=critical,
        )

        # Both runs should have the same pass/fail status
        assert results_a["passed"] == results_b["passed"]

        # Same number of results
        assert len(results_a["all_results"]) == len(results_b["all_results"])

        # Same outcomes for same checks
        outcomes_a = {r.check_name: r.outcome for r in results_a["all_results"]}
        outcomes_b = {r.check_name: r.outcome for r in results_b["all_results"]}
        assert outcomes_a == outcomes_b
