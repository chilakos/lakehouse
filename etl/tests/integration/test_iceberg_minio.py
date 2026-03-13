"""Integration tests for Iceberg CRUD on MinIO on-prem bucket via Nessie catalog.

Tests FNDTN-02: Iceberg tables created and queryable on MinIO (on-prem S3-compatible).

Uses the lakehouse-onprem bucket to simulate on-prem storage.
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
from src.synthetic.generators import generate_positions, positions_schema


pytestmark = pytest.mark.integration


class TestIcebergOnPremStorage:
    """Tests for Iceberg table operations on MinIO on-prem bucket (s3://lakehouse-onprem/)."""

    def test_create_iceberg_table_onprem(self, spark_session, clean_nessie):
        """Test creating a positions table on MinIO on-prem bucket."""
        ns = "test_onprem"
        create_namespace(spark_session, ns)

        schema = positions_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "positions",
            schema,
            location="s3://lakehouse-onprem/warehouse/test_onprem/positions",
        )

        # Insert 50 rows
        data = generate_positions(50)
        write_data(spark_session, ns, "positions", data, schema)

        # Read back and verify count
        result_df = read_table(spark_session, ns, "positions")
        assert result_df.count() == 50

    def test_onprem_data_integrity(self, spark_session, clean_nessie):
        """Test that on-prem stored data maintains integrity."""
        ns = "test_onprem_integrity"
        create_namespace(spark_session, ns)

        schema = positions_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "positions",
            schema,
            location="s3://lakehouse-onprem/warehouse/test_onprem_integrity/positions",
        )

        data = generate_positions(20, seed=42)
        write_data(spark_session, ns, "positions", data, schema)

        result_df = read_table(spark_session, ns, "positions")
        rows = result_df.orderBy("position_id").collect()

        assert len(rows) == 20
        first_row = rows[0]
        first_input = data[0]
        assert first_row["position_id"] == first_input["position_id"]
        assert first_row["symbol"] == first_input["symbol"]
        assert first_row["sector"] == first_input["sector"]
