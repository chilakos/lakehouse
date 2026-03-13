"""Integration tests for Soda Core quality checks against Spark DataFrames.

Tests that SodaCL check definitions in YAML files correctly detect
quality issues in DataFrames. Validates QUAL-02 requirement.

Requires: soda-core-spark-df installed and Java available for local Spark.
Skips gracefully when dependencies are unavailable.
"""

from __future__ import annotations

import os

import pytest

# Skip entire module if soda-core not importable
soda_scan = pytest.importorskip("soda.scan", reason="soda-core not installed")


@pytest.fixture(scope="session", autouse=True)
def ensure_services():
    """Override integration conftest ensure_services -- quality checks use local Spark only."""
    pass


@pytest.fixture(scope="module")
def local_spark():
    """Create a minimal local SparkSession for quality check testing.

    Does not require external services (Nessie, MinIO).
    Skips if Java/PySpark is not available.
    """
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        pytest.skip("PySpark not installed")

    try:
        spark = (
            SparkSession.builder.appName("quality-check-test")
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
def valid_trades_df(local_spark):
    """Create a valid trades DataFrame from synthetic generators."""
    from src.synthetic.generators import generate_trades

    trades = generate_trades(num_records=100, seed=42)
    return local_spark.createDataFrame(trades)


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
class TestBronzeTradesQualityChecks:
    """Integration tests for Bronze trades quality checks."""

    def test_valid_data_passes_all_critical_checks(self, local_spark, valid_trades_df, bronze_checks_path):
        """All critical checks pass on valid synthetic trade data."""
        from src.quality.scanner import run_soda_checks

        results = run_soda_checks(
            spark_session=local_spark,
            df=valid_trades_df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=["primary_key_not_null", "primary_key_unique", "schema_required_columns"],
        )

        assert results["passed"] is True
        assert len(results["critical_failures"]) == 0
        assert isinstance(results["all_results"], list)
        assert len(results["all_results"]) > 0

    def test_null_trade_id_fails_critical_check(self, local_spark, bronze_checks_path):
        """Injecting null trade_id causes critical check failure."""
        from pyspark.sql import Row

        from src.quality.scanner import run_soda_checks

        # Create data with a null trade_id
        trades_with_null = [
            Row(trade_id=1, trade_date="2026-01-01", symbol="AAPL", side="BUY",
                trade_type="MARKET", quantity=100, price=150.00, notional=15000.00,
                account_id="ACCT-1000", trader_id="TRD-100", exchange="NYSE",
                settlement_date="2026-01-02"),
            Row(trade_id=None, trade_date="2026-01-02", symbol="GOOGL", side="SELL",
                trade_type="LIMIT", quantity=50, price=200.00, notional=10000.00,
                account_id="ACCT-2000", trader_id="TRD-200", exchange="NASDAQ",
                settlement_date="2026-01-03"),
        ]
        df = local_spark.createDataFrame(trades_with_null)

        results = run_soda_checks(
            spark_session=local_spark,
            df=df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=["primary_key_not_null", "primary_key_unique"],
        )

        # Should fail because trade_id has a null
        assert results["passed"] is False
        assert len(results["critical_failures"]) > 0
        critical_names = [r.check_name for r in results["critical_failures"]]
        assert "primary_key_not_null" in critical_names

    def test_negative_price_triggers_advisory_warning(self, local_spark, bronze_checks_path):
        """Injecting negative price triggers advisory check but does not block."""
        from pyspark.sql import Row

        from src.quality.scanner import run_soda_checks

        # Create data with a negative price
        trades_with_neg_price = [
            Row(trade_id=1, trade_date="2026-01-01", symbol="AAPL", side="BUY",
                trade_type="MARKET", quantity=100, price=-50.00, notional=-5000.00,
                account_id="ACCT-1000", trader_id="TRD-100", exchange="NYSE",
                settlement_date="2026-01-02"),
            Row(trade_id=2, trade_date="2026-01-02", symbol="GOOGL", side="SELL",
                trade_type="LIMIT", quantity=50, price=200.00, notional=10000.00,
                account_id="ACCT-2000", trader_id="TRD-200", exchange="NASDAQ",
                settlement_date="2026-01-03"),
        ]
        df = local_spark.createDataFrame(trades_with_neg_price)

        results = run_soda_checks(
            spark_session=local_spark,
            df=df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=["primary_key_not_null", "primary_key_unique", "schema_required_columns"],
        )

        # Advisory check should warn but not block (passed=True since only criticals block)
        assert results["passed"] is True
        # There should be a warning for negative price
        warning_names = [r.check_name for r in results["warnings"]]
        assert "price_non_negative" in warning_names

    def test_result_structure_is_correct(self, local_spark, valid_trades_df, bronze_checks_path):
        """run_soda_checks returns correct structure: passed, critical_failures, warnings."""
        from src.quality.scanner import QualityCheckResult, run_soda_checks

        results = run_soda_checks(
            spark_session=local_spark,
            df=valid_trades_df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=["primary_key_not_null"],
        )

        assert "passed" in results
        assert "critical_failures" in results
        assert "warnings" in results
        assert "all_results" in results
        assert isinstance(results["passed"], bool)
        assert isinstance(results["critical_failures"], list)
        assert isinstance(results["warnings"], list)
        assert isinstance(results["all_results"], list)

        # All results should be QualityCheckResult instances
        for r in results["all_results"]:
            assert isinstance(r, QualityCheckResult)
            assert hasattr(r, "check_name")
            assert hasattr(r, "outcome")
            assert hasattr(r, "is_critical")

    def test_base_pipeline_raises_quality_gate_error(self, local_spark, bronze_checks_path):
        """BasePipeline.execute() raises QualityGateError when critical check fails."""
        from unittest.mock import MagicMock

        from pyspark.sql import Row
        from pyspark.sql.types import (
            DoubleType,
            IntegerType,
            StringType,
            StructField,
            StructType,
        )

        from src.pipelines.base import BasePipeline, PipelineConfig, QualityGateError

        # Create a DataFrame with null trade_id (will fail critical check)
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

        bad_data = [
            (1, "2026-01-01", "AAPL", "BUY", "MARKET", 100, 150.0, 15000.0, "ACCT-1", "TRD-1", "NYSE", "2026-01-02"),
            (None, "2026-01-02", "GOOGL", "SELL", "LIMIT", 50, 200.0, 10000.0, "ACCT-2", "TRD-2", "NASDAQ", "2026-01-03"),
        ]
        bad_df = local_spark.createDataFrame(bad_data, schema=schema)

        # PipelineConfig is frozen, so use a MagicMock config for testing
        mock_config = MagicMock()
        mock_config.name = "test_pipeline"
        mock_config.target_layer.value = "bronze"
        mock_config.target_table = "trades"
        mock_config.target_schema = schema
        mock_config.quality_checks_path = bronze_checks_path
        mock_config.critical_checks = ["primary_key_not_null", "primary_key_unique"]
        mock_config.full_table_name = "lakehouse.bronze.trades"

        # Create a concrete subclass for testing
        class TestPipeline(BasePipeline):
            def extract(self):
                return bad_df

            def transform(self, df):
                return df

        pipeline = TestPipeline(spark=local_spark, config=mock_config)

        with pytest.raises(QualityGateError):
            pipeline.execute()


@pytest.mark.integration
class TestQualityCheckConsistency:
    """Test that quality checks produce consistent results across runs."""

    def test_sequential_runs_produce_same_results(self, local_spark, valid_trades_df, bronze_checks_path):
        """Multiple sequential runs on the same data produce identical outcomes."""
        from src.quality.scanner import run_soda_checks

        critical = ["primary_key_not_null", "primary_key_unique"]

        results_1 = run_soda_checks(
            spark_session=local_spark,
            df=valid_trades_df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=critical,
        )
        results_2 = run_soda_checks(
            spark_session=local_spark,
            df=valid_trades_df,
            checks_yaml_path=bronze_checks_path,
            critical_check_names=critical,
        )

        assert results_1["passed"] == results_2["passed"]
        assert len(results_1["critical_failures"]) == len(results_2["critical_failures"])
        assert len(results_1["warnings"]) == len(results_2["warnings"])
        assert len(results_1["all_results"]) == len(results_2["all_results"])

        # Check names and outcomes should be identical
        names_1 = sorted([(r.check_name, r.outcome) for r in results_1["all_results"]])
        names_2 = sorted([(r.check_name, r.outcome) for r in results_2["all_results"]])
        assert names_1 == names_2
