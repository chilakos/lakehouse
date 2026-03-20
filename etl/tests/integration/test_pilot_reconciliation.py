"""Integration tests for pilot pipeline reconciliation.

Validates ETL-02 (pilot migration produces matching output) and QUAL-03
(source-to-lakehouse reconciliation). Proves data accuracy by comparing:
- Row counts between source and Bronze table
- Checksum (sum of notional/market_value) between source and Bronze
- Silver dedup removes duplicates correctly
- No duplicate position_ids per as_of_date in Silver

Requires Docker services: Nessie, MinIO, Spark.
"""

import uuid

import pytest


@pytest.mark.integration
class TestTradesBronzeReconciliation:
    """Reconciliation: synthetic trades -> Bronze pipeline -> Iceberg table."""

    def test_bronze_row_count_matches_source(self, spark_session):
        """Row count of Bronze table matches source count exactly."""
        from src.iceberg_utils.catalog import create_iceberg_table, create_namespace
        from src.pipelines.bronze.trades_ingest import TradesBronzePipeline
        from src.synthetic.generators import generate_trades

        ns = f"bronze_recon_{uuid.uuid4().hex[:6]}"
        table = f"trades_{uuid.uuid4().hex[:6]}"
        create_namespace(spark_session, ns)

        trades = generate_trades(100, seed=42)
        schema = TradesBronzePipeline._build_bronze_schema()
        create_iceberg_table(
            spark_session,
            ns,
            table,
            schema,
            f"s3://lakehouse-data/test/{ns}/{table}",
        )

        pipeline = TradesBronzePipeline(
            spark=spark_session,
            source_data=trades,
            source_system="recon_test",
            batch_id=f"batch-{uuid.uuid4().hex[:6]}",
        )

        df = pipeline.transform(pipeline.extract())
        df.writeTo(f"lakehouse.{ns}.{table}").append()

        result = spark_session.table(f"lakehouse.{ns}.{table}")
        assert result.count() == len(trades), f"Row count mismatch: source={len(trades)}, bronze={result.count()}"

    def test_bronze_notional_checksum_matches_source(self, spark_session):
        """Sum of notional values in Bronze matches source within Decimal precision."""
        from src.iceberg_utils.catalog import create_iceberg_table, create_namespace
        from src.pipelines.bronze.trades_ingest import TradesBronzePipeline
        from src.synthetic.generators import generate_trades

        ns = f"bronze_recon_{uuid.uuid4().hex[:6]}"
        table = f"trades_{uuid.uuid4().hex[:6]}"
        create_namespace(spark_session, ns)

        trades = generate_trades(100, seed=42)
        source_notional_sum = sum(t["notional"] for t in trades)

        schema = TradesBronzePipeline._build_bronze_schema()
        create_iceberg_table(
            spark_session,
            ns,
            table,
            schema,
            f"s3://lakehouse-data/test/{ns}/{table}",
        )

        pipeline = TradesBronzePipeline(
            spark=spark_session,
            source_data=trades,
            source_system="recon_test",
            batch_id=f"batch-{uuid.uuid4().hex[:6]}",
        )
        df = pipeline.transform(pipeline.extract())
        df.writeTo(f"lakehouse.{ns}.{table}").append()

        result = spark_session.table(f"lakehouse.{ns}.{table}")
        bronze_notional_sum = result.agg({"notional": "sum"}).collect()[0][0]

        assert abs(float(source_notional_sum) - float(bronze_notional_sum)) < 0.01, (
            f"Notional checksum mismatch: source={source_notional_sum}, bronze={bronze_notional_sum}"
        )


@pytest.mark.integration
class TestPositionsBronzeSilverReconciliation:
    """Reconciliation: synthetic positions -> Bronze -> Silver pipeline."""

    def test_silver_row_count_lte_bronze(self, spark_session):
        """Silver table has fewer or equal rows to Bronze (dedup removes duplicates)."""
        from src.iceberg_utils.catalog import create_iceberg_table, create_namespace
        from src.pipelines.bronze.positions_ingest import PositionsBronzePipeline
        from src.pipelines.silver.positions_clean import PositionsSilverPipeline
        from src.synthetic.generators import generate_positions

        suffix = uuid.uuid4().hex[:6]
        bronze_ns = f"bronze_pos_{suffix}"
        silver_ns = f"silver_pos_{suffix}"
        table = f"positions_{suffix}"

        create_namespace(spark_session, bronze_ns)
        create_namespace(spark_session, silver_ns)

        positions = generate_positions(50, seed=42)
        bronze_schema = PositionsBronzePipeline._build_bronze_schema()

        create_iceberg_table(
            spark_session,
            bronze_ns,
            table,
            bronze_schema,
            f"s3://lakehouse-data/test/{bronze_ns}/{table}",
        )

        # Ingest same data twice to create duplicates
        for batch_num in range(1, 3):
            pipeline = PositionsBronzePipeline(
                spark=spark_session,
                source_data=positions,
                source_system="recon_test",
                batch_id=f"batch-{batch_num}",
            )
            df = pipeline.transform(pipeline.extract())
            df.writeTo(f"lakehouse.{bronze_ns}.{table}").append()

        bronze_count = spark_session.table(f"lakehouse.{bronze_ns}.{table}").count()
        assert bronze_count == 100  # 50 * 2 batches

        # Silver pipeline reads from Bronze and deduplicates
        silver_pipeline = PositionsSilverPipeline(
            spark=spark_session,
            source_table=f"lakehouse.{bronze_ns}.{table}",
        )
        silver_schema = silver_pipeline.config.target_schema
        create_iceberg_table(
            spark_session,
            silver_ns,
            table,
            silver_schema,
            f"s3://lakehouse-data/test/{silver_ns}/{table}",
        )

        silver_df = silver_pipeline.transform(silver_pipeline.extract())
        silver_df.writeTo(f"lakehouse.{silver_ns}.{table}").append()

        silver_count = spark_session.table(f"lakehouse.{silver_ns}.{table}").count()
        assert silver_count <= bronze_count, f"Silver ({silver_count}) should have <= rows than Bronze ({bronze_count})"
        assert silver_count == 50, f"Silver should have 50 unique positions after dedup, got {silver_count}"

    def test_silver_no_duplicate_position_ids_per_as_of_date(self, spark_session):
        """Silver table has no duplicate position_ids per as_of_date."""
        from src.iceberg_utils.catalog import create_iceberg_table, create_namespace
        from src.pipelines.bronze.positions_ingest import PositionsBronzePipeline
        from src.pipelines.silver.positions_clean import PositionsSilverPipeline
        from src.synthetic.generators import generate_positions

        suffix = uuid.uuid4().hex[:6]
        bronze_ns = f"bronze_nodup_{suffix}"
        silver_ns = f"silver_nodup_{suffix}"
        table = f"positions_{suffix}"

        create_namespace(spark_session, bronze_ns)
        create_namespace(spark_session, silver_ns)

        positions = generate_positions(50, seed=42)
        bronze_schema = PositionsBronzePipeline._build_bronze_schema()

        create_iceberg_table(
            spark_session,
            bronze_ns,
            table,
            bronze_schema,
            f"s3://lakehouse-data/test/{bronze_ns}/{table}",
        )

        # Write twice to simulate duplicate ingestion
        for batch_num in range(1, 3):
            pipeline = PositionsBronzePipeline(
                spark=spark_session,
                source_data=positions,
                source_system="recon_test",
                batch_id=f"batch-{batch_num}",
            )
            df = pipeline.transform(pipeline.extract())
            df.writeTo(f"lakehouse.{bronze_ns}.{table}").append()

        # Silver pipeline
        silver_pipeline = PositionsSilverPipeline(
            spark=spark_session,
            source_table=f"lakehouse.{bronze_ns}.{table}",
        )
        silver_schema = silver_pipeline.config.target_schema
        create_iceberg_table(
            spark_session,
            silver_ns,
            table,
            silver_schema,
            f"s3://lakehouse-data/test/{silver_ns}/{table}",
        )
        silver_df = silver_pipeline.transform(silver_pipeline.extract())
        silver_df.writeTo(f"lakehouse.{silver_ns}.{table}").append()

        # Check for duplicates: count of (position_id, as_of_date) should equal row count
        result = spark_session.table(f"lakehouse.{silver_ns}.{table}")
        total_rows = result.count()
        distinct_keys = result.select("position_id", "as_of_date").distinct().count()

        assert total_rows == distinct_keys, (
            f"Duplicate position_id+as_of_date found: {total_rows} rows but {distinct_keys} distinct keys"
        )
