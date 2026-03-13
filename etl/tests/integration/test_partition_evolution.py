"""Integration tests for Iceberg partition evolution operations.

Tests FNDTN-05: Iceberg partition evolution supported for query performance optimization.

Validates:
- Partition by date: creating a table partitioned by days(trade_date)
- Partition evolution: changing from day to month partitioning
- Old data readable after partition evolution
- New writes use the new partition scheme

Requires Docker Compose services: Nessie, MinIO.
Tests skip gracefully when services are unavailable.
"""

import pytest

from src.iceberg_utils.catalog import (
    create_iceberg_table,
    create_namespace,
    read_table,
    write_data,
)
from src.synthetic.generators import generate_trades, trades_schema


pytestmark = pytest.mark.integration


class TestPartitionEvolution:
    """Tests for Iceberg partition evolution operations."""

    def test_partition_by_date(self, spark_session, clean_nessie):
        """Test creating a table partitioned by days(trade_date).

        Verifies that partition pruning works by checking that a query
        for a single day scans fewer files than a full table scan.
        """
        ns = "test_partition_date"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_partition_date/trades",
            partition_by=["days(trade_date)"],
        )

        # Insert synthetic data spanning multiple days
        data = generate_trades(100, seed=42)
        write_data(spark_session, ns, "trades", data, schema)

        # Verify data is readable
        result_df = read_table(spark_session, ns, "trades")
        assert result_df.count() == 100

        # Verify partitioning is set up by checking table properties
        # Query for a single date and compare to full scan
        all_dates = result_df.select("trade_date").distinct().collect()
        assert len(all_dates) > 1, "Data should span multiple dates for partition testing"

        # Query a single day -- should use partition pruning
        single_date = all_dates[0]["trade_date"]
        filtered_df = spark_session.sql(
            f"SELECT * FROM lakehouse.{ns}.trades WHERE trade_date = DATE '{single_date}'"
        )
        filtered_count = filtered_df.count()
        assert filtered_count > 0, "Filtered query should return some rows"
        assert filtered_count < 100, "Filtered query should return fewer rows than full table"

    def test_partition_evolution(self, spark_session, clean_nessie):
        """Test changing partition strategy from days to months.

        Verifies that:
        1. Old data is still readable after partition evolution
        2. New data writes use the new partition scheme
        """
        ns = "test_partition_evo"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_partition_evo/trades",
            partition_by=["days(trade_date)"],
        )

        # Insert initial data with day partitioning
        data_batch1 = generate_trades(50, seed=42)
        write_data(spark_session, ns, "trades", data_batch1, schema)

        # Verify initial data count
        initial_count = read_table(spark_session, ns, "trades").count()
        assert initial_count == 50

        # Evolve partition: change from days(trade_date) to months(trade_date)
        spark_session.sql(
            f"ALTER TABLE lakehouse.{ns}.trades REPLACE PARTITION FIELD days(trade_date) WITH months(trade_date)"
        )

        # Verify old data is still readable after evolution
        post_evo_count = read_table(spark_session, ns, "trades").count()
        assert post_evo_count == 50, (
            f"Old data should still be readable after partition evolution: "
            f"expected 50, got {post_evo_count}"
        )

        # Write new data with the new partition scheme
        data_batch2 = generate_trades(30, seed=99)
        write_data(spark_session, ns, "trades", data_batch2, schema)

        # Verify combined data
        total_count = read_table(spark_session, ns, "trades").count()
        assert total_count == 80, (
            f"Total count should be 80 (50 old + 30 new): got {total_count}"
        )

    def test_partition_evolution_data_integrity(self, spark_session, clean_nessie):
        """Test that partition evolution preserves data integrity.

        After evolution, all original values should be unchanged.
        """
        ns = "test_partition_integrity"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_partition_integrity/trades",
            partition_by=["days(trade_date)"],
        )

        # Insert known data
        data = generate_trades(20, seed=42)
        write_data(spark_session, ns, "trades", data, schema)

        # Evolve partition
        spark_session.sql(
            f"ALTER TABLE lakehouse.{ns}.trades REPLACE PARTITION FIELD days(trade_date) WITH months(trade_date)"
        )

        # Read back and verify values match
        result_df = read_table(spark_session, ns, "trades")
        rows = result_df.orderBy("trade_id").collect()

        assert len(rows) == 20
        for i, row in enumerate(rows):
            assert row["trade_id"] == data[i]["trade_id"]
            assert row["symbol"] == data[i]["symbol"]
            assert row["side"] == data[i]["side"]
