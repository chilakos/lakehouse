"""Integration tests for Iceberg schema evolution operations.

Tests FNDTN-04: Iceberg schema evolution works without data rewrites across all engines.

Validates:
- Add column: adding a new column to an existing table
- Widen type: widening INT to BIGINT
- Metadata-only: no data file rewrites during schema evolution

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


class TestSchemaEvolution:
    """Tests for Iceberg schema evolution operations."""

    def test_add_column(self, spark_session, clean_nessie):
        """Test adding a new column to an existing Iceberg table.

        After adding settlement_currency, existing data should have null
        for the new column, and the column should appear in the schema.
        """
        ns = "test_schema_evo"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_schema_evo/trades",
        )

        # Insert initial data
        data = generate_trades(20, seed=42)
        write_data(spark_session, ns, "trades", data, schema)

        # Add a new column
        spark_session.sql(f"ALTER TABLE lakehouse.{ns}.trades ADD COLUMN settlement_currency STRING")

        # Verify column appears in schema
        result_df = read_table(spark_session, ns, "trades")
        column_names = result_df.columns
        assert "settlement_currency" in column_names, f"settlement_currency should be in schema, got: {column_names}"

        # Verify existing data has null for new column
        rows = result_df.collect()
        for row in rows:
            assert row["settlement_currency"] is None, "Existing rows should have null for new column"

    def test_widen_type(self, spark_session, clean_nessie):
        """Test widening a column type from INT to BIGINT.

        After widening quantity from INT to BIGINT, existing data should
        still be readable with correct values.
        """
        ns = "test_widen_type"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_widen_type/trades",
        )

        # Insert initial data
        data = generate_trades(15, seed=42)
        write_data(spark_session, ns, "trades", data, schema)

        # Widen quantity from INT to BIGINT
        spark_session.sql(f"ALTER TABLE lakehouse.{ns}.trades ALTER COLUMN quantity TYPE BIGINT")

        # Verify data is still readable and values are correct
        result_df = read_table(spark_session, ns, "trades")
        rows = result_df.orderBy("trade_id").collect()

        assert len(rows) == 15, "All rows should still be readable after type widening"

        # Verify specific quantity values match original data
        for i, row in enumerate(rows):
            assert row["quantity"] == data[i]["quantity"], (
                f"Quantity mismatch at row {i}: expected {data[i]['quantity']}, got {row['quantity']}"
            )

    def test_schema_evolution_no_data_rewrite(self, spark_session, clean_nessie):
        """Test that schema evolution is metadata-only (no data file rewrites).

        After adding a column, the number of data files should remain the same,
        proving it is a metadata-only change.
        """
        ns = "test_no_rewrite"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_no_rewrite/trades",
        )

        # Insert data
        data = generate_trades(25, seed=42)
        write_data(spark_session, ns, "trades", data, schema)

        # Count data files before evolution
        files_before = spark_session.sql(f"SELECT * FROM lakehouse.{ns}.trades.files").count()

        # Perform schema evolution (add column)
        spark_session.sql(f"ALTER TABLE lakehouse.{ns}.trades ADD COLUMN broker_code STRING")

        # Count data files after evolution
        files_after = spark_session.sql(f"SELECT * FROM lakehouse.{ns}.trades.files").count()

        assert files_after == files_before, (
            f"File count should not change after schema evolution: before={files_before}, after={files_after}"
        )

        # Verify data is still intact
        result_df = read_table(spark_session, ns, "trades")
        assert result_df.count() == 25
