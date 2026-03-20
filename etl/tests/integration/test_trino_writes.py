"""Integration tests for Trino writing to Iceberg tables.

Validates that Trino can INSERT, UPDATE, DELETE, and MERGE rows in
Iceberg tables, and that PySpark can read back those changes.

IMPORTANT: Per Research anti-pattern, designate one write-owner per table
in production. These tests validate Trino write capability, not
recommend concurrent multi-engine writes.

Requires Docker Compose services: Nessie, MinIO, Trino.
"""

import pytest

from src.iceberg_utils.trino import execute_ddl


@pytest.mark.integration
class TestTrinoWrites:
    """Tests for Trino writing to Iceberg tables visible to PySpark."""

    def test_trino_insert(self, spark_session, trino_connection, clean_nessie):
        """Trino INSERT INTO adds rows to Iceberg table, PySpark read confirms."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            read_table,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "trino_write_test")
        create_iceberg_table(
            spark_session,
            "trino_write_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/trino_write_test/trades",
        )
        # Write initial data via PySpark
        write_data(
            spark_session,
            "trino_write_test",
            "trades",
            generate_trades(10, seed=4001),
            schema,
        )

        # Trino inserts additional rows
        execute_ddl(
            trino_connection,
            """
            INSERT INTO trino_write_test.trades
            VALUES (
                1001, DATE '2025-06-15', 'AAPL', 'BUY', 'MARKET',
                500, DECIMAL '150.2500', DECIMAL '75125.0000',
                'ACCT-5001', 'TRD-501', 'NYSE', DATE '2025-06-16'
            )
            """,
        )

        # PySpark reads back -- should see 11 rows
        spark_session.catalog.refreshTable("lakehouse.trino_write_test.trades")
        df = read_table(spark_session, "trino_write_test", "trades")
        assert df.count() == 11, f"Expected 11 rows after Trino INSERT, got {df.count()}"

    def test_trino_update(self, spark_session, trino_connection, clean_nessie):
        """Trino UPDATE modifies rows, PySpark read confirms changes."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            read_table,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "trino_update_test")
        create_iceberg_table(
            spark_session,
            "trino_update_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/trino_update_test/trades",
        )
        write_data(
            spark_session,
            "trino_update_test",
            "trades",
            generate_trades(10, seed=4002),
            schema,
        )

        # Trino updates: change side to 'SELL' for trade_id = 1
        execute_ddl(
            trino_connection,
            "UPDATE trino_update_test.trades SET side = 'SELL' WHERE trade_id = 1",
        )

        # PySpark reads back -- trade_id=1 should now be SELL
        spark_session.catalog.refreshTable("lakehouse.trino_update_test.trades")
        df = read_table(spark_session, "trino_update_test", "trades")
        row = df.filter("trade_id = 1").collect()
        assert len(row) == 1
        assert row[0]["side"] == "SELL", f"Expected SELL, got {row[0]['side']}"

    def test_trino_delete(self, spark_session, trino_connection, clean_nessie):
        """Trino DELETE removes rows, PySpark read confirms row count decreased."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            read_table,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "trino_delete_test")
        create_iceberg_table(
            spark_session,
            "trino_delete_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/trino_delete_test/trades",
        )
        write_data(
            spark_session,
            "trino_delete_test",
            "trades",
            generate_trades(10, seed=4003),
            schema,
        )

        # Trino deletes trade_id = 1
        execute_ddl(
            trino_connection,
            "DELETE FROM trino_delete_test.trades WHERE trade_id = 1",
        )

        # PySpark reads back -- should see 9 rows
        spark_session.catalog.refreshTable("lakehouse.trino_delete_test.trades")
        df = read_table(spark_session, "trino_delete_test", "trades")
        assert df.count() == 9, f"Expected 9 rows after DELETE, got {df.count()}"

    def test_trino_merge(self, spark_session, trino_connection, clean_nessie):
        """Trino MERGE (upsert) works correctly."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            read_table,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "trino_merge_test")
        create_iceberg_table(
            spark_session,
            "trino_merge_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/trino_merge_test/trades",
        )
        write_data(
            spark_session,
            "trino_merge_test",
            "trades",
            generate_trades(5, seed=4004),
            schema,
        )

        # Trino MERGE: update trade_id=1, insert trade_id=999
        execute_ddl(
            trino_connection,
            """
            MERGE INTO trino_merge_test.trades AS t
            USING (
                VALUES
                    (1, DATE '2025-06-15', 'MSFT', 'BUY', 'LIMIT',
                     100, DECIMAL '300.0000', DECIMAL '30000.0000',
                     'ACCT-9999', 'TRD-999', 'NASDAQ', DATE '2025-06-16'),
                    (999, DATE '2025-06-15', 'GOOGL', 'SELL', 'MARKET',
                     200, DECIMAL '175.5000', DECIMAL '35100.0000',
                     'ACCT-8888', 'TRD-888', 'NYSE', DATE '2025-06-17')
            ) AS s(trade_id, trade_date, symbol, side, trade_type,
                   quantity, price, notional, account_id, trader_id,
                   exchange, settlement_date)
            ON t.trade_id = s.trade_id
            WHEN MATCHED THEN
                UPDATE SET symbol = s.symbol, side = s.side, quantity = s.quantity,
                           price = s.price, notional = s.notional
            WHEN NOT MATCHED THEN
                INSERT VALUES (s.trade_id, s.trade_date, s.symbol, s.side, s.trade_type,
                               s.quantity, s.price, s.notional, s.account_id, s.trader_id,
                               s.exchange, s.settlement_date)
            """,
        )

        # PySpark reads back
        spark_session.catalog.refreshTable("lakehouse.trino_merge_test.trades")
        df = read_table(spark_session, "trino_merge_test", "trades")

        # Should have 6 rows: 5 original + 1 new (trade_id=999), trade_id=1 updated
        assert df.count() == 6, f"Expected 6 rows after MERGE, got {df.count()}"

        # Verify the update: trade_id=1 should now be MSFT
        row_1 = df.filter("trade_id = 1").collect()
        assert row_1[0]["symbol"] == "MSFT", f"Expected MSFT, got {row_1[0]['symbol']}"

        # Verify the insert: trade_id=999 should exist
        row_999 = df.filter("trade_id = 999").collect()
        assert len(row_999) == 1, "Expected trade_id=999 to be inserted"
        assert row_999[0]["symbol"] == "GOOGL"
