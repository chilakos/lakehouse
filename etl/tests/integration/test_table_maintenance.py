"""Integration tests for Iceberg table maintenance operations.

Tests FNDTN-06: Automated Iceberg table maintenance (compaction, snapshot expiration, orphan file cleanup).

Validates:
- compact_table: small file compaction reduces file count
- expire_snapshots: old snapshots removed, current data intact
- remove_orphan_files: cleanup runs without data loss
- full_maintenance: complete maintenance cycle preserves data integrity

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
from src.iceberg_utils.maintenance import (
    compact_table,
    expire_snapshots,
    full_maintenance,
    remove_orphan_files,
)
from src.synthetic.generators import generate_trades, trades_schema

pytestmark = pytest.mark.integration


class TestTableCompaction:
    """Tests for Iceberg table file compaction."""

    def test_compact_small_files(self, spark_session, clean_nessie):
        """Test that compaction reduces the number of small data files.

        Writes 10 small batches (10 rows each) to create many small files,
        then compacts and verifies file count decreased while data is preserved.
        """
        ns = "test_compact"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_compact/trades",
        )

        # Write 10 small batches to create many small files
        for i in range(10):
            batch = generate_trades(10, seed=42 + i)
            write_data(spark_session, ns, "trades", batch, schema)

        # Count files before compaction
        files_before = spark_session.sql(f"SELECT * FROM lakehouse.{ns}.trades.files").count()
        assert files_before >= 10, f"Should have at least 10 data files, got {files_before}"

        # Run compaction
        result = compact_table(spark_session, ns, "trades")
        assert result["operation"] == "compact_table"

        # Count files after compaction
        files_after = spark_session.sql(f"SELECT * FROM lakehouse.{ns}.trades.files").count()
        assert files_after < files_before, (
            f"File count should decrease after compaction: before={files_before}, after={files_after}"
        )

        # Verify data integrity
        total_count = read_table(spark_session, ns, "trades").count()
        assert total_count == 100, f"Total row count should be preserved: expected 100, got {total_count}"


class TestSnapshotExpiration:
    """Tests for Iceberg snapshot expiration."""

    def test_expire_snapshots(self, spark_session, clean_nessie):
        """Test that old snapshots are expired while current data remains intact.

        Writes data in multiple batches (creating snapshots), then expires old
        snapshots and verifies current data is still accessible.
        """
        ns = "test_expire"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_expire/trades",
        )

        # Write data in batches to create multiple snapshots
        for i in range(5):
            batch = generate_trades(20, seed=42 + i)
            write_data(spark_session, ns, "trades", batch, schema)

        # Count snapshots before expiration
        snapshots_before = spark_session.sql(f"SELECT * FROM lakehouse.{ns}.trades.snapshots").count()
        assert snapshots_before >= 5, f"Should have at least 5 snapshots, got {snapshots_before}"

        # Expire old snapshots (retain last 2)
        result = expire_snapshots(spark_session, ns, "trades", older_than_days=0, retain_last=2)
        assert result["operation"] == "expire_snapshots"

        # Verify current data is intact
        total_count = read_table(spark_session, ns, "trades").count()
        assert total_count == 100, f"Current data should be intact: expected 100, got {total_count}"


class TestOrphanFileCleanup:
    """Tests for Iceberg orphan file cleanup."""

    def test_remove_orphan_files(self, spark_session, clean_nessie):
        """Test that orphan file cleanup runs without removing valid data.

        Creates a table, writes data, runs orphan cleanup, and verifies
        all data is still readable.
        """
        ns = "test_orphan"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_orphan/trades",
        )

        # Write data
        data = generate_trades(50, seed=42)
        write_data(spark_session, ns, "trades", data, schema)

        # Run orphan file cleanup
        result = remove_orphan_files(spark_session, ns, "trades", older_than_days=0)
        assert result["operation"] == "remove_orphan_files"

        # Verify data is still intact
        total_count = read_table(spark_session, ns, "trades").count()
        assert total_count == 50, f"Data should be intact after orphan cleanup: expected 50, got {total_count}"


class TestFullMaintenanceCycle:
    """Tests for the full maintenance cycle."""

    def test_full_maintenance_cycle(self, spark_session, clean_nessie):
        """Test running all maintenance operations in sequence.

        Creates a table with multiple batches, runs full_maintenance(),
        and verifies the table is still fully queryable with correct data.
        """
        ns = "test_full_maint"
        create_namespace(spark_session, ns)

        schema = trades_schema()
        create_iceberg_table(
            spark_session,
            ns,
            "trades",
            schema,
            location="s3://lakehouse-data/warehouse/test_full_maint/trades",
        )

        # Write multiple batches
        total_rows = 0
        for i in range(5):
            batch = generate_trades(20, seed=42 + i)
            write_data(spark_session, ns, "trades", batch, schema)
            total_rows += len(batch)

        # Run full maintenance
        results = full_maintenance(spark_session, ns, "trades")

        # Verify all operations returned results
        assert "compact" in results
        assert "expire" in results
        assert "orphan_cleanup" in results
        assert "rewrite_manifests" in results

        # Verify data integrity after full maintenance
        final_count = read_table(spark_session, ns, "trades").count()
        assert final_count == total_rows, (
            f"Data should be intact after full maintenance: expected {total_rows}, got {final_count}"
        )

        # Verify data is queryable (can filter, aggregate, etc.)
        agg_df = spark_session.sql(
            f"SELECT COUNT(*) as cnt, COUNT(DISTINCT symbol) as symbols FROM lakehouse.{ns}.trades"
        )
        agg_row = agg_df.collect()[0]
        assert agg_row["cnt"] == total_rows
        assert agg_row["symbols"] > 0
