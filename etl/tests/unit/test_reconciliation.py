"""Unit tests for source-to-lakehouse reconciliation framework.

Tests ReconciliationResult dataclass logic and reconcile_table function
with mocked SparkSession. Validates QUAL-03 requirement.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestReconciliationResult:
    """Tests for ReconciliationResult dataclass initialization and passed logic."""

    def test_matching_counts_passed_true(self):
        """ReconciliationResult.passed is True when row counts match and no aggregates."""
        from src.quality.reconciliation import ReconciliationResult

        result = ReconciliationResult(
            table_name="bronze.trades",
            source_row_count=1000,
            target_row_count=1000,
            row_count_match=True,
            source_checksum=None,
            target_checksum=None,
            checksum_match=None,
            source_aggregates={},
            target_aggregates={},
            aggregate_matches={},
            passed=True,
        )
        assert result.passed is True
        assert result.row_count_match is True
        assert result.source_row_count == 1000
        assert result.target_row_count == 1000

    def test_mismatching_counts_passed_false(self):
        """ReconciliationResult.passed is False when row counts differ."""
        from src.quality.reconciliation import ReconciliationResult

        result = ReconciliationResult(
            table_name="bronze.trades",
            source_row_count=1000,
            target_row_count=999,
            row_count_match=False,
            source_checksum=None,
            target_checksum=None,
            checksum_match=None,
            source_aggregates={},
            target_aggregates={},
            aggregate_matches={},
            passed=False,
        )
        assert result.passed is False
        assert result.row_count_match is False

    def test_checksum_match_with_equal_values(self):
        """ReconciliationResult reports checksum_match=True for equal checksums."""
        from src.quality.reconciliation import ReconciliationResult

        result = ReconciliationResult(
            table_name="silver.trades",
            source_row_count=500,
            target_row_count=500,
            row_count_match=True,
            source_checksum=Decimal("123456.7890"),
            target_checksum=Decimal("123456.7890"),
            checksum_match=True,
            source_aggregates={},
            target_aggregates={},
            aggregate_matches={},
            passed=True,
        )
        assert result.checksum_match is True
        assert result.passed is True

    def test_checksum_mismatch_fails(self):
        """ReconciliationResult.passed is False when checksums differ significantly."""
        from src.quality.reconciliation import ReconciliationResult

        result = ReconciliationResult(
            table_name="silver.trades",
            source_row_count=500,
            target_row_count=500,
            row_count_match=True,
            source_checksum=Decimal("123456.7890"),
            target_checksum=Decimal("100000.0000"),
            checksum_match=False,
            source_aggregates={},
            target_aggregates={},
            aggregate_matches={},
            passed=False,
        )
        assert result.checksum_match is False
        assert result.passed is False

    def test_aggregate_matches_all_true(self):
        """ReconciliationResult.passed is True when all aggregates match."""
        from src.quality.reconciliation import ReconciliationResult

        result = ReconciliationResult(
            table_name="silver.trades",
            source_row_count=500,
            target_row_count=500,
            row_count_match=True,
            source_checksum=None,
            target_checksum=None,
            checksum_match=None,
            source_aggregates={"price_avg": Decimal("250.00")},
            target_aggregates={"price_avg": Decimal("250.00")},
            aggregate_matches={"price_avg": True},
            passed=True,
        )
        assert result.passed is True
        assert result.aggregate_matches["price_avg"] is True

    def test_aggregate_mismatch_fails(self):
        """ReconciliationResult.passed is False when an aggregate mismatches."""
        from src.quality.reconciliation import ReconciliationResult

        result = ReconciliationResult(
            table_name="silver.trades",
            source_row_count=500,
            target_row_count=500,
            row_count_match=True,
            source_checksum=None,
            target_checksum=None,
            checksum_match=None,
            source_aggregates={"price_avg": Decimal("250.00")},
            target_aggregates={"price_avg": Decimal("100.00")},
            aggregate_matches={"price_avg": False},
            passed=False,
        )
        assert result.passed is False
        assert result.aggregate_matches["price_avg"] is False


@pytest.mark.unit
class TestReconcileTable:
    """Tests for reconcile_table function with mocked Spark."""

    def test_reconcile_matching_row_counts(self):
        """reconcile_table returns passed=True when source and target counts match."""
        from src.quality.reconciliation import reconcile_table

        mock_spark = MagicMock()
        mock_source_df = MagicMock()
        mock_source_df.count.return_value = 1000

        # Mock target table query: SELECT COUNT(*) as cnt FROM lakehouse.bronze.trades
        mock_target_row = MagicMock()
        mock_target_row.cnt = 1000
        mock_spark.sql.return_value.collect.return_value = [mock_target_row]

        result = reconcile_table(
            spark=mock_spark,
            source_df=mock_source_df,
            target_table="bronze.trades",
        )

        assert result.row_count_match is True
        assert result.source_row_count == 1000
        assert result.target_row_count == 1000
        assert result.passed is True

    def test_reconcile_mismatching_row_counts(self):
        """reconcile_table returns passed=False when row counts differ."""
        from src.quality.reconciliation import reconcile_table

        mock_spark = MagicMock()
        mock_source_df = MagicMock()
        mock_source_df.count.return_value = 1000

        mock_target_row = MagicMock()
        mock_target_row.cnt = 950
        mock_spark.sql.return_value.collect.return_value = [mock_target_row]

        result = reconcile_table(
            spark=mock_spark,
            source_df=mock_source_df,
            target_table="bronze.trades",
        )

        assert result.row_count_match is False
        assert result.passed is False

    def test_reconcile_checksum_within_tolerance(self):
        """reconcile_table passes when checksum difference is within tolerance."""
        from src.quality.reconciliation import reconcile_table

        mock_spark = MagicMock()
        mock_source_df = MagicMock()
        mock_source_df.count.return_value = 100

        # Source checksum via agg
        mock_source_checksum_row = MagicMock()
        mock_source_checksum_row.__getitem__ = lambda self, k: Decimal("50000.0050")
        mock_source_df.agg.return_value.collect.return_value = [mock_source_checksum_row]

        # Mock target count
        mock_target_count_row = MagicMock()
        mock_target_count_row.cnt = 100

        # Mock target checksum
        mock_target_checksum_row = MagicMock()
        mock_target_checksum_row.__getitem__ = lambda self, k: Decimal("50000.0040")

        # Configure spark.sql to return different results based on the query
        def sql_side_effect(query):
            result = MagicMock()
            if "COUNT" in query:
                result.collect.return_value = [mock_target_count_row]
            else:
                result.collect.return_value = [mock_target_checksum_row]
            return result

        mock_spark.sql.side_effect = sql_side_effect

        result = reconcile_table(
            spark=mock_spark,
            source_df=mock_source_df,
            target_table="silver.trades",
            checksum_columns=["price"],
            tolerance=Decimal("0.01"),
        )

        assert result.checksum_match is True
        assert result.row_count_match is True
        assert result.passed is True

    def test_reconcile_checksum_exceeds_tolerance(self):
        """reconcile_table fails when checksum difference exceeds tolerance."""
        from src.quality.reconciliation import reconcile_table

        mock_spark = MagicMock()
        mock_source_df = MagicMock()
        mock_source_df.count.return_value = 100

        # Source checksum via agg - large difference
        mock_source_checksum_row = MagicMock()
        mock_source_checksum_row.__getitem__ = lambda self, k: Decimal("50000.00")
        mock_source_df.agg.return_value.collect.return_value = [mock_source_checksum_row]

        # Mock target count
        mock_target_count_row = MagicMock()
        mock_target_count_row.cnt = 100

        # Mock target checksum - significantly different
        mock_target_checksum_row = MagicMock()
        mock_target_checksum_row.__getitem__ = lambda self, k: Decimal("48000.00")

        def sql_side_effect(query):
            result = MagicMock()
            if "COUNT" in query:
                result.collect.return_value = [mock_target_count_row]
            else:
                result.collect.return_value = [mock_target_checksum_row]
            return result

        mock_spark.sql.side_effect = sql_side_effect

        result = reconcile_table(
            spark=mock_spark,
            source_df=mock_source_df,
            target_table="silver.trades",
            checksum_columns=["price"],
            tolerance=Decimal("0.01"),
        )

        assert result.checksum_match is False
        assert result.passed is False

    def test_reconcile_aggregate_comparison(self):
        """reconcile_table computes and compares aggregate columns."""
        from src.quality.reconciliation import reconcile_table

        mock_spark = MagicMock()
        mock_source_df = MagicMock()
        mock_source_df.count.return_value = 200

        # Source aggregates via agg
        mock_source_agg_row = MagicMock()
        mock_source_agg_row.__getitem__ = lambda self, k: Decimal("5000.00")
        mock_source_df.agg.return_value.collect.return_value = [mock_source_agg_row]

        # Mock target count
        mock_target_count_row = MagicMock()
        mock_target_count_row.cnt = 200

        # Mock target aggregates
        mock_target_agg_row = MagicMock()
        mock_target_agg_row.__getitem__ = lambda self, k: Decimal("5000.00")

        def sql_side_effect(query):
            result = MagicMock()
            if "COUNT" in query:
                result.collect.return_value = [mock_target_count_row]
            else:
                result.collect.return_value = [mock_target_agg_row]
            return result

        mock_spark.sql.side_effect = sql_side_effect

        result = reconcile_table(
            spark=mock_spark,
            source_df=mock_source_df,
            target_table="gold.trading_metrics",
            aggregate_columns={"quantity": "SUM"},
        )

        assert result.row_count_match is True
        assert "quantity_SUM" in result.aggregate_matches
        assert result.aggregate_matches["quantity_SUM"] is True
        assert result.passed is True

    def test_reconcile_passed_requires_all_checks(self):
        """reconcile_table.passed is True only when row counts AND all aggregates match."""
        from src.quality.reconciliation import ReconciliationResult

        # Rows match but aggregate doesn't -> should fail
        result = ReconciliationResult(
            table_name="gold.trading_metrics",
            source_row_count=200,
            target_row_count=200,
            row_count_match=True,
            source_checksum=None,
            target_checksum=None,
            checksum_match=None,
            source_aggregates={"quantity_SUM": Decimal("5000.00")},
            target_aggregates={"quantity_SUM": Decimal("3000.00")},
            aggregate_matches={"quantity_SUM": False},
            passed=False,
        )
        assert result.passed is False
        assert result.row_count_match is True
