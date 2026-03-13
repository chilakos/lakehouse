"""Integration tests for incremental/delta loading with Iceberg tables.

Tests watermark-based extraction and MERGE INTO upserts:
- get_last_watermark returns correct max from an Iceberg table
- incremental_extract returns only new records after watermark
- merge_incremental correctly upserts (updates existing, inserts new)

Validates ETL-05: incremental loading extracts only new records since last watermark.

Requires Docker services: Nessie, MinIO, Spark.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest


@pytest.mark.integration
class TestGetLastWatermarkIntegration:
    """Test get_last_watermark against real Iceberg tables."""

    def test_watermark_returns_none_for_empty_table(self, spark_session):
        """get_last_watermark returns None when Iceberg table has no rows."""
        from src.iceberg_utils.catalog import create_iceberg_table, create_namespace
        from src.pipelines.incremental import get_last_watermark
        from src.synthetic.generators import trades_schema

        ns = f"bronze_wm_{uuid.uuid4().hex[:6]}"
        table = f"trades_{uuid.uuid4().hex[:6]}"
        create_namespace(spark_session, ns)
        create_iceberg_table(
            spark_session, ns, table, trades_schema(),
            f"s3://lakehouse-data/test/{ns}/{table}",
        )

        result = get_last_watermark(spark_session, f"{ns}.{table}", "trade_date")
        assert result is None

    def test_watermark_returns_max_trade_date(self, spark_session):
        """get_last_watermark returns the max trade_date from a populated table."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.pipelines.incremental import get_last_watermark
        from src.synthetic.generators import generate_trades, trades_schema

        ns = f"bronze_wm_{uuid.uuid4().hex[:6]}"
        table = f"trades_{uuid.uuid4().hex[:6]}"
        create_namespace(spark_session, ns)
        schema = trades_schema()
        create_iceberg_table(
            spark_session, ns, table, schema,
            f"s3://lakehouse-data/test/{ns}/{table}",
        )

        trades = generate_trades(50, seed=42)
        write_data(spark_session, ns, table, trades, schema)

        result = get_last_watermark(spark_session, f"{ns}.{table}", "trade_date")
        assert result is not None

        # The max should match the max trade_date from the generated data
        max_date = max(t["trade_date"] for t in trades)
        assert result == max_date, f"Expected watermark {max_date}, got {result}"


@pytest.mark.integration
class TestIncrementalExtractIntegration:
    """Test incremental extraction returns only new records after watermark."""

    def test_incremental_extract_returns_only_new_records(self, spark_session):
        """After writing 50 trades, adding 20 more with later dates, incremental_extract returns only 20."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.pipelines.incremental import get_last_watermark, incremental_extract
        from src.synthetic.generators import generate_trades, trades_schema

        ns = f"bronze_incr_{uuid.uuid4().hex[:6]}"
        table = f"trades_{uuid.uuid4().hex[:6]}"
        create_namespace(spark_session, ns)
        schema = trades_schema()
        create_iceberg_table(
            spark_session, ns, table, schema,
            f"s3://lakehouse-data/test/{ns}/{table}",
        )

        # Write initial batch of 50 trades
        initial_trades = generate_trades(50, seed=42)
        write_data(spark_session, ns, table, initial_trades, schema)

        # Get watermark after initial batch
        watermark = get_last_watermark(spark_session, f"{ns}.{table}", "trade_date")
        assert watermark is not None

        # Generate 20 new trades with dates AFTER the watermark
        new_trades = []
        for i in range(20):
            new_trades.append({
                "trade_id": 1000 + i,
                "trade_date": watermark + timedelta(days=i + 1),
                "symbol": "NEW",
                "side": "BUY",
                "trade_type": "MARKET",
                "quantity": 100,
                "price": Decimal("150.0000"),
                "notional": Decimal("15000.0000"),
                "account_id": f"ACCT-NEW-{i}",
                "trader_id": f"TRD-NEW-{i}",
                "exchange": "NYSE",
                "settlement_date": watermark + timedelta(days=i + 3),
            })
        write_data(spark_session, ns, table, new_trades, schema)

        # Verify total is 70
        total = spark_session.table(f"lakehouse.{ns}.{table}").count()
        assert total == 70

        # Incremental extract should return only the 20 new records
        incremental_df = incremental_extract(
            spark_session,
            source_query_template=f"SELECT * FROM lakehouse.{ns}.{table}",
            watermark_column="trade_date",
            last_watermark=watermark,
        )
        incremental_count = incremental_df.count()
        assert incremental_count == 20, (
            f"Expected 20 incremental records, got {incremental_count}"
        )


@pytest.mark.integration
class TestMergeIncrementalIntegration:
    """Test MERGE INTO upserts for incremental updates."""

    def test_merge_inserts_new_and_updates_existing(self, spark_session):
        """merge_incremental correctly inserts new rows and updates existing ones."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.pipelines.incremental import merge_incremental
        from src.synthetic.generators import trades_schema

        ns = f"bronze_merge_{uuid.uuid4().hex[:6]}"
        table = f"trades_{uuid.uuid4().hex[:6]}"
        full_table = f"lakehouse.{ns}.{table}"
        create_namespace(spark_session, ns)
        schema = trades_schema()
        create_iceberg_table(
            spark_session, ns, table, schema,
            f"s3://lakehouse-data/test/{ns}/{table}",
        )

        # Write 3 initial records
        initial = [
            {
                "trade_id": 1, "trade_date": date(2026, 1, 1),
                "symbol": "AAPL", "side": "BUY", "trade_type": "MARKET",
                "quantity": 100, "price": Decimal("150.0000"),
                "notional": Decimal("15000.0000"), "account_id": "ACCT-1",
                "trader_id": "TRD-1", "exchange": "NYSE",
                "settlement_date": date(2026, 1, 3),
            },
            {
                "trade_id": 2, "trade_date": date(2026, 1, 2),
                "symbol": "GOOGL", "side": "SELL", "trade_type": "LIMIT",
                "quantity": 50, "price": Decimal("200.0000"),
                "notional": Decimal("10000.0000"), "account_id": "ACCT-2",
                "trader_id": "TRD-2", "exchange": "NASDAQ",
                "settlement_date": date(2026, 1, 4),
            },
            {
                "trade_id": 3, "trade_date": date(2026, 1, 3),
                "symbol": "MSFT", "side": "BUY", "trade_type": "MARKET",
                "quantity": 75, "price": Decimal("300.0000"),
                "notional": Decimal("22500.0000"), "account_id": "ACCT-3",
                "trader_id": "TRD-3", "exchange": "NYSE",
                "settlement_date": date(2026, 1, 5),
            },
        ]
        write_data(spark_session, ns, table, initial, schema)

        # Prepare merge data: update trade_id=1 (new price), insert trade_id=4 (new)
        merge_data = [
            {
                "trade_id": 1, "trade_date": date(2026, 1, 1),
                "symbol": "AAPL", "side": "BUY", "trade_type": "MARKET",
                "quantity": 100, "price": Decimal("155.0000"),  # Updated price
                "notional": Decimal("15500.0000"), "account_id": "ACCT-1",
                "trader_id": "TRD-1", "exchange": "NYSE",
                "settlement_date": date(2026, 1, 3),
            },
            {
                "trade_id": 4, "trade_date": date(2026, 1, 4),
                "symbol": "JPM", "side": "BUY", "trade_type": "MARKET",
                "quantity": 200, "price": Decimal("180.0000"),
                "notional": Decimal("36000.0000"), "account_id": "ACCT-4",
                "trader_id": "TRD-4", "exchange": "NYSE",
                "settlement_date": date(2026, 1, 6),
            },
        ]
        merge_df = spark_session.createDataFrame(merge_data, schema)

        merge_incremental(spark_session, full_table, merge_df, "trade_id")

        # Verify results
        result = spark_session.table(full_table)
        assert result.count() == 4, f"Expected 4 rows after merge, got {result.count()}"

        # Verify trade_id=1 was updated (price should be 155.0000)
        updated_row = result.filter("trade_id = 1").collect()[0]
        assert float(updated_row["price"]) == pytest.approx(155.0, abs=0.01), (
            f"Expected price 155.0 for trade_id=1 after update, got {updated_row['price']}"
        )

        # Verify trade_id=4 was inserted
        new_row = result.filter("trade_id = 4").collect()
        assert len(new_row) == 1, "trade_id=4 should have been inserted"
        assert new_row[0]["symbol"] == "JPM"
