"""Integration tests for Nessie catalog serving tables on both S3 and MinIO.

Tests FNDTN-03: Centralized Iceberg catalog deployed supporting both storage backends.

Verifies that a single Nessie catalog instance can serve tables stored on
different S3-compatible backends (lakehouse-data and lakehouse-onprem buckets).

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
from src.synthetic.generators import (
    generate_positions,
    generate_trades,
    positions_schema,
    trades_schema,
)

pytestmark = pytest.mark.integration


class TestNessieDualStorage:
    """Tests for Nessie serving tables across both storage backends."""

    def test_nessie_dual_storage(self, spark_session, clean_nessie):
        """Verify both S3 buckets accessible from the same Nessie catalog.

        Creates one table on lakehouse-data and another on lakehouse-onprem,
        then verifies both are queryable from the same Spark session via
        the shared Nessie catalog.
        """
        ns = "test_dual"
        create_namespace(spark_session, ns)

        # Create trades table on lakehouse-data bucket
        trades_sch = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            trades_sch,
            location="s3://lakehouse-data/warehouse/test_dual/trades",
        )
        trades_data = generate_trades(30)
        write_data(spark_session, ns, "trades", trades_data, trades_sch)

        # Create positions table on lakehouse-onprem bucket
        positions_sch = positions_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "positions",
            positions_sch,
            location="s3://lakehouse-onprem/warehouse/test_dual/positions",
        )
        positions_data = generate_positions(20)
        write_data(spark_session, ns, "positions", positions_data, positions_sch)

        # Verify both tables are accessible from same catalog
        trades_df = read_table(spark_session, ns, "trades")
        positions_df = read_table(spark_session, ns, "positions")

        assert trades_df.count() == 30, "Trades table on lakehouse-data should have 30 rows"
        assert positions_df.count() == 20, "Positions table on lakehouse-onprem should have 20 rows"

        # Verify both tables appear in the namespace
        tables = spark_session.sql(f"SHOW TABLES IN lakehouse.{ns}").collect()
        table_names = {row["tableName"] for row in tables}
        assert "trades" in table_names, "Trades table should be visible in namespace"
        assert "positions" in table_names, "Positions table should be visible in namespace"
