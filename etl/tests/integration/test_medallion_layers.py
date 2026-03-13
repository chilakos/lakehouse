"""Integration tests for medallion layer (Bronze -> Silver -> Gold) pipeline flow.

Tests end-to-end data flow through Iceberg tables in correct namespaces.
Requires Docker services: Nessie, MinIO, Spark.

Uses @pytest.mark.integration marker -- skipped when services unavailable.
"""

import uuid

import pytest


@pytest.mark.integration
class TestMedallionBronzeLayer:
    """Test Bronze layer pipeline behavior with real Spark/Iceberg."""

    def test_bronze_trades_adds_metadata_columns(self, spark_session):
        """Bronze trades pipeline adds source_system, ingestion_ts, batch_id columns."""
        from src.synthetic.generators import generate_trades
        from src.pipelines.bronze.trades_ingest import TradesBronzePipeline

        batch_id = f"test-{uuid.uuid4().hex[:8]}"
        trades = generate_trades(5, seed=42)

        pipeline = TradesBronzePipeline(
            spark=spark_session,
            source_data=trades,
            source_system="test_system",
            batch_id=batch_id,
        )

        df = pipeline.extract()
        transformed = pipeline.transform(df)

        col_names = [f.name for f in transformed.schema.fields]
        assert "source_system" in col_names
        assert "ingestion_ts" in col_names
        assert "batch_id" in col_names

    def test_bronze_trades_preserves_original_fields(self, spark_session):
        """Bronze trades pipeline preserves all original trade fields without transformation."""
        from src.synthetic.generators import generate_trades
        from src.pipelines.bronze.trades_ingest import TradesBronzePipeline

        trades = generate_trades(3, seed=42)
        pipeline = TradesBronzePipeline(
            spark=spark_session,
            source_data=trades,
            source_system="test_system",
            batch_id="test-batch",
        )

        df = pipeline.extract()
        transformed = pipeline.transform(df)

        # Original trade fields should all be present
        original_fields = [
            "trade_id", "trade_date", "symbol", "side", "trade_type",
            "quantity", "price", "notional", "account_id", "trader_id",
            "exchange", "settlement_date",
        ]
        col_names = [f.name for f in transformed.schema.fields]
        for field_name in original_fields:
            assert field_name in col_names, f"Missing original field: {field_name}"


@pytest.mark.integration
class TestMedallionSilverLayer:
    """Test Silver layer pipeline behavior with real Spark/Iceberg."""

    def test_silver_trades_deduplicates_by_trade_id(self, spark_session):
        """Silver trades pipeline deduplicates by trade_id, keeping latest ingestion."""
        from src.pipelines.silver.trades_clean import TradesSilverPipeline
        from src.pipelines.bronze.trades_ingest import TradesBronzePipeline
        from src.synthetic.generators import generate_trades
        from src.iceberg_utils.catalog import create_namespace, create_iceberg_table

        ns = f"bronze_dedup_{uuid.uuid4().hex[:6]}"
        create_namespace(spark_session, ns)

        # Ingest same trades twice (creates duplicates by trade_id)
        trades = generate_trades(5, seed=42)
        schema = TradesBronzePipeline._build_bronze_schema()

        table_name = f"trades_{uuid.uuid4().hex[:6]}"
        create_iceberg_table(
            spark_session, ns, table_name, schema,
            f"s3://lakehouse-data/test/{ns}/{table_name}",
        )

        # Write same data twice to simulate duplicate ingestion
        pipeline = TradesBronzePipeline(
            spark=spark_session, source_data=trades,
            source_system="test", batch_id="batch-1",
        )
        df1 = pipeline.transform(pipeline.extract())
        df1.writeTo(f"lakehouse.{ns}.{table_name}").append()

        pipeline2 = TradesBronzePipeline(
            spark=spark_session, source_data=trades,
            source_system="test", batch_id="batch-2",
        )
        df2 = pipeline2.transform(pipeline2.extract())
        df2.writeTo(f"lakehouse.{ns}.{table_name}").append()

        # Now test silver dedup reads from that table
        silver = TradesSilverPipeline(
            spark=spark_session,
            source_table=f"lakehouse.{ns}.{table_name}",
        )
        raw = silver.extract()
        assert raw.count() == 10  # 5 trades * 2 batches

        cleaned = silver.transform(raw)
        assert cleaned.count() == 5  # Deduplicated to 5 unique trade_ids


@pytest.mark.integration
class TestMedallionGoldLayer:
    """Test Gold layer pipeline behavior with real Spark/Iceberg."""

    def test_gold_trading_metrics_produces_aggregates(self, spark_session):
        """Gold trading metrics pipeline produces aggregated metrics per symbol/side."""
        from pyspark.sql.types import (
            DateType, DecimalType, IntegerType, StringType,
            StructField, StructType,
        )
        from src.pipelines.gold.trading_metrics import TradingMetricsGoldPipeline

        # Create a simple Silver-like DataFrame directly
        silver_schema = StructType([
            StructField("trade_id", IntegerType(), nullable=False),
            StructField("trade_date", DateType(), nullable=False),
            StructField("symbol", StringType(), nullable=False),
            StructField("side", StringType(), nullable=False),
            StructField("trade_type", StringType(), nullable=False),
            StructField("quantity", IntegerType(), nullable=False),
            StructField("price", DecimalType(18, 4), nullable=False),
            StructField("notional", DecimalType(18, 4), nullable=False),
            StructField("account_id", StringType(), nullable=False),
            StructField("trader_id", StringType(), nullable=False),
            StructField("exchange", StringType(), nullable=False),
            StructField("settlement_date", DateType(), nullable=False),
        ])

        from datetime import date
        from decimal import Decimal

        data = [
            (1, date(2024, 1, 1), "AAPL", "BUY", "MARKET", 100,
             Decimal("150.0000"), Decimal("15000.0000"), "ACCT-1", "TRD-1", "NYSE", date(2024, 1, 2)),
            (2, date(2024, 1, 1), "AAPL", "BUY", "LIMIT", 200,
             Decimal("151.0000"), Decimal("30200.0000"), "ACCT-2", "TRD-2", "NYSE", date(2024, 1, 2)),
            (3, date(2024, 1, 1), "AAPL", "SELL", "MARKET", 50,
             Decimal("152.0000"), Decimal("7600.0000"), "ACCT-1", "TRD-1", "NYSE", date(2024, 1, 2)),
        ]

        silver_df = spark_session.createDataFrame(data, silver_schema)

        pipeline = TradingMetricsGoldPipeline(spark=spark_session)
        result = pipeline.transform(silver_df)

        rows = result.collect()
        # Should have 2 groups: AAPL/BUY and AAPL/SELL
        assert len(rows) == 2

        # Check AAPL BUY aggregate
        buy_rows = [r for r in rows if r["side"] == "BUY"]
        assert len(buy_rows) == 1
        assert buy_rows[0]["trade_count"] == 2
        assert float(buy_rows[0]["total_notional"]) == pytest.approx(45200.0, abs=1.0)

        # Check AAPL SELL aggregate
        sell_rows = [r for r in rows if r["side"] == "SELL"]
        assert len(sell_rows) == 1
        assert sell_rows[0]["trade_count"] == 1


@pytest.mark.integration
class TestMedallionEndToEnd:
    """Test full Bronze -> Silver -> Gold flow with Iceberg tables."""

    def test_full_medallion_flow(self, spark_session):
        """Synthetic data flows Bronze -> Silver -> Gold, all in Iceberg tables."""
        from src.synthetic.generators import generate_trades
        from src.pipelines.bronze.trades_ingest import TradesBronzePipeline
        from src.pipelines.silver.trades_clean import TradesSilverPipeline
        from src.pipelines.gold.trading_metrics import TradingMetricsGoldPipeline
        from src.iceberg_utils.catalog import create_namespace, create_iceberg_table

        suffix = uuid.uuid4().hex[:6]

        # Create namespaces following lakehouse.{layer} convention
        for layer in ["bronze", "silver", "gold"]:
            create_namespace(spark_session, f"{layer}_{suffix}")

        # -- Bronze --
        trades = generate_trades(20, seed=42)
        bronze_pipeline = TradesBronzePipeline(
            spark=spark_session, source_data=trades,
            source_system="e2e_test", batch_id=f"batch-{suffix}",
        )
        bronze_schema = TradesBronzePipeline._build_bronze_schema()
        bronze_table = f"trades_{suffix}"
        create_iceberg_table(
            spark_session, f"bronze_{suffix}", bronze_table, bronze_schema,
            f"s3://lakehouse-data/test/bronze_{suffix}/{bronze_table}",
        )
        bronze_df = bronze_pipeline.transform(bronze_pipeline.extract())
        bronze_df.writeTo(f"lakehouse.bronze_{suffix}.{bronze_table}").append()

        bronze_result = spark_session.table(f"lakehouse.bronze_{suffix}.{bronze_table}")
        assert bronze_result.count() == 20
        bronze_cols = [f.name for f in bronze_result.schema.fields]
        assert "source_system" in bronze_cols
        assert "ingestion_ts" in bronze_cols
        assert "batch_id" in bronze_cols

        # -- Silver --
        silver_pipeline = TradesSilverPipeline(
            spark=spark_session,
            source_table=f"lakehouse.bronze_{suffix}.{bronze_table}",
        )
        silver_schema = silver_pipeline.config.target_schema
        silver_table = f"trades_{suffix}"
        create_iceberg_table(
            spark_session, f"silver_{suffix}", silver_table, silver_schema,
            f"s3://lakehouse-data/test/silver_{suffix}/{silver_table}",
        )
        silver_df = silver_pipeline.transform(silver_pipeline.extract())
        silver_df.writeTo(f"lakehouse.silver_{suffix}.{silver_table}").append()

        silver_result = spark_session.table(f"lakehouse.silver_{suffix}.{silver_table}")
        # Deduped -- should be <= 20 (equal if all trade_ids unique, which they are with sequential IDs)
        assert silver_result.count() == 20
        # Silver should NOT have metadata columns
        silver_cols = [f.name for f in silver_result.schema.fields]
        assert "source_system" not in silver_cols
        assert "ingestion_ts" not in silver_cols
        assert "batch_id" not in silver_cols

        # -- Gold --
        gold_pipeline = TradingMetricsGoldPipeline(
            spark=spark_session,
            source_table=f"lakehouse.silver_{suffix}.{silver_table}",
        )
        gold_schema = gold_pipeline.config.target_schema
        gold_table = f"trading_metrics_{suffix}"
        create_iceberg_table(
            spark_session, f"gold_{suffix}", gold_table, gold_schema,
            f"s3://lakehouse-data/test/gold_{suffix}/{gold_table}",
        )
        gold_df = gold_pipeline.transform(gold_pipeline.extract())
        gold_df.writeTo(f"lakehouse.gold_{suffix}.{gold_table}").append()

        gold_result = spark_session.table(f"lakehouse.gold_{suffix}.{gold_table}")
        assert gold_result.count() > 0

        # Gold should have aggregated columns
        gold_cols = [f.name for f in gold_result.schema.fields]
        assert "symbol" in gold_cols
        assert "side" in gold_cols
        assert "total_notional" in gold_cols
        assert "trade_count" in gold_cols
        assert "avg_price" in gold_cols

    def test_namespaces_follow_convention(self, spark_session):
        """All three namespaces follow lakehouse.{layer}.{table} convention."""
        from src.iceberg_utils.catalog import create_namespace

        suffix = uuid.uuid4().hex[:6]
        for layer in ["bronze", "silver", "gold"]:
            ns = f"{layer}_{suffix}"
            create_namespace(spark_session, ns)
            # Verify namespace exists by querying it
            result = spark_session.sql(f"SHOW NAMESPACES IN lakehouse LIKE '{ns}'")
            assert result.count() >= 1, f"Namespace lakehouse.{ns} not found"
