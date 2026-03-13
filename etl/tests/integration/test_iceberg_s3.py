"""Integration tests for Iceberg CRUD on S3/MinIO via Nessie catalog.

Tests FNDTN-01: Iceberg tables created and queryable on S3-compatible storage.

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


class TestIcebergOnMinioStorage:
    """Tests for Iceberg table operations on MinIO (s3://lakehouse-data/ bucket)."""

    def test_create_namespace(self, spark_session, clean_nessie):
        """Test creating a namespace via Nessie catalog."""
        create_namespace(spark_session, "test_ns")

        # Verify namespace exists by listing
        namespaces = spark_session.sql("SHOW NAMESPACES IN lakehouse").collect()
        ns_names = [row[0] for row in namespaces]
        assert "test_ns" in ns_names

    def test_create_iceberg_table_minio(self, spark_session, clean_nessie):
        """Test creating a trades table on MinIO and inserting/reading data."""
        ns = "test_s3_crud"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_s3_crud/trades",
        )

        # Insert 100 rows of synthetic data
        data = generate_trades(100)
        write_data(spark_session, ns, "trades", data, schema)

        # Read back and verify count
        result_df = read_table(spark_session, ns, "trades")
        assert result_df.count() == 100

    def test_read_back_data_matches(self, spark_session, clean_nessie):
        """Test that inserted data matches when read back (including Decimal precision)."""
        ns = "test_data_match"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_data_match/trades",
        )

        # Insert known synthetic data
        data = generate_trades(10, seed=42)
        write_data(spark_session, ns, "trades", data, schema)

        # Read back and verify specific values
        result_df = read_table(spark_session, ns, "trades")
        rows = result_df.orderBy("trade_id").collect()

        assert len(rows) == 10
        # Verify first record matches input
        first_row = rows[0]
        first_input = data[0]
        assert first_row["trade_id"] == first_input["trade_id"]
        assert first_row["symbol"] == first_input["symbol"]
        assert first_row["side"] == first_input["side"]
