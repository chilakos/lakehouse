"""Unit tests for incremental loading utilities.

Tests watermark-based delta extraction:
- IncrementalConfig dataclass with defaults
- get_last_watermark returns None for empty/missing table
- get_last_watermark returns max value from Iceberg table
- incremental_extract builds filtered query with watermark
- incremental_extract with None watermark does full extract
"""

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestIncrementalConfig:
    """Test IncrementalConfig dataclass defaults and validation."""

    def test_config_has_required_fields(self):
        """IncrementalConfig holds watermark_column, source_table, and tolerance_seconds."""
        from src.pipelines.incremental import IncrementalConfig

        config = IncrementalConfig(
            watermark_column="trade_date",
            source_table="raw_trades",
        )
        assert config.watermark_column == "trade_date"
        assert config.source_table == "raw_trades"

    def test_config_default_tolerance(self):
        """IncrementalConfig defaults tolerance_seconds to 0."""
        from src.pipelines.incremental import IncrementalConfig

        config = IncrementalConfig(
            watermark_column="trade_date",
            source_table="raw_trades",
        )
        assert config.tolerance_seconds == 0

    def test_config_custom_tolerance(self):
        """IncrementalConfig accepts custom tolerance_seconds."""
        from src.pipelines.incremental import IncrementalConfig

        config = IncrementalConfig(
            watermark_column="updated_at",
            source_table="positions",
            tolerance_seconds=300,
        )
        assert config.tolerance_seconds == 300


@pytest.mark.unit
class TestGetLastWatermark:
    """Test get_last_watermark returns correct watermark values."""

    def test_returns_none_when_table_empty(self):
        """get_last_watermark returns None when the target table has no rows."""
        from src.pipelines.incremental import get_last_watermark

        mock_spark = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value=None)
        mock_df = MagicMock()
        mock_df.collect.return_value = [mock_row]
        mock_spark.sql.return_value = mock_df

        result = get_last_watermark(mock_spark, "bronze.trades", "trade_date")
        assert result is None

    def test_returns_max_watermark_value(self):
        """get_last_watermark returns the max value of the watermark column."""
        from datetime import date

        from src.pipelines.incremental import get_last_watermark

        mock_spark = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value=date(2026, 3, 10))
        mock_df = MagicMock()
        mock_df.collect.return_value = [mock_row]
        mock_spark.sql.return_value = mock_df

        result = get_last_watermark(mock_spark, "bronze.trades", "trade_date")
        assert result == date(2026, 3, 10)

    def test_builds_correct_sql_query(self):
        """get_last_watermark runs SELECT MAX({col}) FROM lakehouse.{table}."""
        from src.pipelines.incremental import get_last_watermark

        mock_spark = MagicMock()
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value=None)
        mock_df = MagicMock()
        mock_df.collect.return_value = [mock_row]
        mock_spark.sql.return_value = mock_df

        get_last_watermark(mock_spark, "bronze.trades", "trade_date")
        mock_spark.sql.assert_called_once_with("SELECT MAX(trade_date) AS max_watermark FROM lakehouse.bronze.trades")


@pytest.mark.unit
class TestIncrementalExtract:
    """Test incremental_extract query building."""

    def test_builds_filtered_query_with_watermark(self):
        """incremental_extract adds WHERE clause filtering by watermark > last_watermark."""
        from datetime import date

        from src.pipelines.incremental import incremental_extract

        mock_spark = MagicMock()
        mock_df = MagicMock()
        mock_spark.sql.return_value = mock_df

        incremental_extract(
            mock_spark,
            source_query_template="SELECT * FROM source_db.trades",
            watermark_column="trade_date",
            last_watermark=date(2026, 3, 1),
        )

        # Should add WHERE clause
        call_args = mock_spark.sql.call_args[0][0]
        assert "WHERE" in call_args
        assert "trade_date" in call_args
        assert "2026-03-01" in call_args

    def test_full_extract_when_watermark_is_none(self):
        """incremental_extract does full extract (no WHERE) when last_watermark is None."""
        from src.pipelines.incremental import incremental_extract

        mock_spark = MagicMock()
        mock_df = MagicMock()
        mock_spark.sql.return_value = mock_df

        incremental_extract(
            mock_spark,
            source_query_template="SELECT * FROM source_db.trades",
            watermark_column="trade_date",
            last_watermark=None,
        )

        call_args = mock_spark.sql.call_args[0][0]
        assert "WHERE" not in call_args
        assert call_args == "SELECT * FROM source_db.trades"

    def test_returns_spark_dataframe(self):
        """incremental_extract returns the DataFrame from spark.sql()."""
        from src.pipelines.incremental import incremental_extract

        mock_spark = MagicMock()
        mock_df = MagicMock()
        mock_spark.sql.return_value = mock_df

        result = incremental_extract(
            mock_spark,
            source_query_template="SELECT * FROM source_db.trades",
            watermark_column="trade_date",
            last_watermark=None,
        )

        assert result is mock_df
