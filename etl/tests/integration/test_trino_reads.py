"""Integration tests for Trino reading Iceberg tables from S3 and MinIO.

Validates that Trino can read Iceberg tables created by PySpark via
the shared Nessie REST catalog, on both MinIO storage backends.

Requires Docker Compose services: Nessie, MinIO, Trino.
"""

import pytest

from src.iceberg_utils.trino import execute_query, get_table_row_count, get_table_schema


@pytest.mark.integration
class TestTrinoReads:
    """Tests for Trino reading Spark-created Iceberg tables."""

    def test_trino_reads_spark_created_table(
        self, spark_session, trino_connection, clean_nessie
    ):
        """PySpark creates trades table with 100 rows, Trino reads all 100."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        # PySpark creates and populates table
        schema = trades_schema()
        create_namespace(spark_session, "trino_read_test")
        create_iceberg_table(
            spark_session,
            "trino_read_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/trino_read_test/trades",
        )
        trades = generate_trades(100, seed=1001)
        write_data(spark_session, "trino_read_test", "trades", trades, schema)

        # Trino reads the same table
        row_count = get_table_row_count(
            trino_connection, "trino_read_test", "trades"
        )
        assert row_count == 100, f"Expected 100 rows, got {row_count}"

        # Verify sample data matches
        rows = execute_query(
            trino_connection,
            "SELECT trade_id, symbol, side FROM trino_read_test.trades ORDER BY trade_id LIMIT 5",
        )
        assert len(rows) == 5
        assert rows[0][0] == 1  # First trade_id

    def test_trino_reads_both_storage_backends(
        self, spark_session, trino_connection, clean_nessie
    ):
        """Tables on lakehouse-data and lakehouse-onprem are both readable from Trino."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()

        # Create table on lakehouse-data (S3/cloud bucket)
        create_namespace(spark_session, "dual_storage_test")
        create_iceberg_table(
            spark_session,
            "dual_storage_test",
            "trades_cloud",
            schema,
            "s3://lakehouse-data/warehouse/dual_storage_test/trades_cloud",
        )
        write_data(
            spark_session, "dual_storage_test", "trades_cloud",
            generate_trades(50, seed=2001), schema,
        )

        # Create table on lakehouse-onprem (MinIO on-prem bucket)
        create_iceberg_table(
            spark_session,
            "dual_storage_test",
            "trades_onprem",
            schema,
            "s3://lakehouse-onprem/warehouse/dual_storage_test/trades_onprem",
        )
        write_data(
            spark_session, "dual_storage_test", "trades_onprem",
            generate_trades(30, seed=2002), schema,
        )

        # Trino reads both
        cloud_count = get_table_row_count(
            trino_connection, "dual_storage_test", "trades_cloud"
        )
        onprem_count = get_table_row_count(
            trino_connection, "dual_storage_test", "trades_onprem"
        )

        assert cloud_count == 50, f"Expected 50 cloud rows, got {cloud_count}"
        assert onprem_count == 30, f"Expected 30 on-prem rows, got {onprem_count}"

    def test_trino_reads_after_schema_evolution(
        self, spark_session, trino_connection, clean_nessie
    ):
        """PySpark adds column, Trino sees the new column in DESCRIBE and SELECT."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "schema_evo_test")
        create_iceberg_table(
            spark_session,
            "schema_evo_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/schema_evo_test/trades",
        )
        write_data(
            spark_session, "schema_evo_test", "trades",
            generate_trades(10, seed=3001), schema,
        )

        # Spark evolves the schema: add a new column
        spark_session.sql(
            "ALTER TABLE lakehouse.schema_evo_test.trades ADD COLUMNS (broker STRING)"
        )

        # Trino should see the new column
        trino_schema = get_table_schema(
            trino_connection, "schema_evo_test", "trades"
        )
        column_names = [col["name"] for col in trino_schema]
        assert "broker" in column_names, (
            f"Expected 'broker' column after schema evolution, got columns: {column_names}"
        )

        # Verify existing data still readable (broker should be null for old rows)
        rows = execute_query(
            trino_connection,
            "SELECT trade_id, broker FROM schema_evo_test.trades ORDER BY trade_id LIMIT 1",
        )
        assert len(rows) == 1
        assert rows[0][1] is None  # broker should be null for pre-evolution rows
