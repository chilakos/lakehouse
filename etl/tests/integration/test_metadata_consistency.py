"""Cross-engine metadata consistency validation tests.

Validates that Spark and Trino see identical table metadata (schema,
row counts, data) when querying the same Iceberg tables through the
shared Nessie catalog.

Requires Docker Compose services: Nessie, MinIO, Trino.
"""

import pytest

from src.iceberg_utils.trino import (
    execute_ddl,
    execute_query,
    get_table_row_count,
    get_table_schema,
)


@pytest.mark.integration
class TestMetadataConsistency:
    """Cross-engine metadata consistency tests between Spark and Trino."""

    def test_metadata_consistent_spark_trino(
        self, spark_session, trino_connection, clean_nessie
    ):
        """Same table queried from Spark and Trino returns identical schema and row count."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            read_table,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "consistency_test")
        create_iceberg_table(
            spark_session,
            "consistency_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/consistency_test/trades",
        )
        write_data(
            spark_session, "consistency_test", "trades",
            generate_trades(100, seed=6001), schema,
        )

        # Spark metadata
        spark_df = read_table(spark_session, "consistency_test", "trades")
        spark_count = spark_df.count()
        spark_columns = [f.name for f in spark_df.schema.fields]

        # Trino metadata
        trino_count = get_table_row_count(
            trino_connection, "consistency_test", "trades"
        )
        trino_schema = get_table_schema(
            trino_connection, "consistency_test", "trades"
        )
        trino_columns = [col["name"] for col in trino_schema]

        # Assert consistency
        assert spark_count == trino_count, (
            f"Row count mismatch: Spark={spark_count}, Trino={trino_count}"
        )
        assert spark_columns == trino_columns, (
            f"Schema mismatch:\n  Spark columns: {spark_columns}\n  Trino columns: {trino_columns}"
        )

    def test_metadata_consistent_after_write(
        self, spark_session, trino_connection, clean_nessie
    ):
        """After Trino writes, Spark reads see the new data (and vice versa)."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            read_table,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "write_consistency_test")
        create_iceberg_table(
            spark_session,
            "write_consistency_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/write_consistency_test/trades",
        )
        write_data(
            spark_session, "write_consistency_test", "trades",
            generate_trades(20, seed=6002), schema,
        )

        # Verify initial consistency
        spark_count_initial = read_table(
            spark_session, "write_consistency_test", "trades"
        ).count()
        trino_count_initial = get_table_row_count(
            trino_connection, "write_consistency_test", "trades"
        )
        assert spark_count_initial == trino_count_initial == 20

        # Trino writes additional row
        execute_ddl(
            trino_connection,
            """
            INSERT INTO write_consistency_test.trades
            VALUES (
                2001, DATE '2025-07-01', 'GS', 'BUY', 'LIMIT',
                250, DECIMAL '350.0000', DECIMAL '87500.0000',
                'ACCT-7001', 'TRD-701', 'NYSE', DATE '2025-07-02'
            )
            """,
        )

        # Spark should see 21 rows after refresh
        spark_session.catalog.refreshTable(
            "lakehouse.write_consistency_test.trades"
        )
        spark_count_after = read_table(
            spark_session, "write_consistency_test", "trades"
        ).count()
        assert spark_count_after == 21, (
            f"Spark expected 21 rows after Trino write, got {spark_count_after}"
        )

        # Now Spark writes, verify Trino sees it
        write_data(
            spark_session, "write_consistency_test", "trades",
            generate_trades(5, seed=6003), schema,
        )
        trino_count_after = get_table_row_count(
            trino_connection, "write_consistency_test", "trades"
        )
        assert trino_count_after == 26, (
            f"Trino expected 26 rows after Spark write, got {trino_count_after}"
        )

    def test_schema_visible_all_engines(
        self, spark_session, trino_connection, clean_nessie
    ):
        """After schema evolution via Spark, Trino sees identical schema."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "schema_vis_test")
        create_iceberg_table(
            spark_session,
            "schema_vis_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/schema_vis_test/trades",
        )
        write_data(
            spark_session, "schema_vis_test", "trades",
            generate_trades(10, seed=6004), schema,
        )

        # Get pre-evolution schema from both engines
        spark_df_before = spark_session.table("lakehouse.schema_vis_test.trades")
        spark_cols_before = [f.name for f in spark_df_before.schema.fields]

        trino_schema_before = get_table_schema(
            trino_connection, "schema_vis_test", "trades"
        )
        trino_cols_before = [col["name"] for col in trino_schema_before]

        assert spark_cols_before == trino_cols_before

        # Evolve schema: add two columns via Spark
        spark_session.sql(
            "ALTER TABLE lakehouse.schema_vis_test.trades ADD COLUMNS (clearing_house STRING)"
        )
        spark_session.sql(
            "ALTER TABLE lakehouse.schema_vis_test.trades ADD COLUMNS (fee DECIMAL(18,4))"
        )

        # Verify Spark sees new columns
        spark_session.catalog.refreshTable("lakehouse.schema_vis_test.trades")
        spark_df_after = spark_session.table("lakehouse.schema_vis_test.trades")
        spark_cols_after = [f.name for f in spark_df_after.schema.fields]

        assert "clearing_house" in spark_cols_after
        assert "fee" in spark_cols_after

        # Verify Trino sees same columns
        trino_schema_after = get_table_schema(
            trino_connection, "schema_vis_test", "trades"
        )
        trino_cols_after = [col["name"] for col in trino_schema_after]

        assert "clearing_house" in trino_cols_after, (
            f"Trino missing 'clearing_house': {trino_cols_after}"
        )
        assert "fee" in trino_cols_after, (
            f"Trino missing 'fee': {trino_cols_after}"
        )

        # Full schema order should match
        assert spark_cols_after == trino_cols_after, (
            f"Schema mismatch after evolution:\n"
            f"  Spark: {spark_cols_after}\n"
            f"  Trino: {trino_cols_after}"
        )
