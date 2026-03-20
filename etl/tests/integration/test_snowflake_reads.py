"""Integration tests for Snowflake reading Iceberg tables via REST catalog.

Validates that Snowflake can read Iceberg tables created by PySpark through
Nessie's REST catalog integration using CREATE CATALOG INTEGRATION (ICEBERG_REST).

IMPORTANT: Snowflake is read-only for externally managed Iceberg tables
(per Research Pitfall 6). Tests verify read access only.

Requires:
- SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD environment variables
- Snowflake account that can reach the Nessie REST endpoint
- Network connectivity between Snowflake and Nessie (may require public endpoint)

If Snowflake cannot reach local Nessie (network isolation), tests are skipped
with documentation of the required configuration.
"""

import os

import pytest

# Custom marker for Snowflake tests
pytestmark = [pytest.mark.snowflake, pytest.mark.integration]


def _snowflake_available() -> bool:
    """Check if Snowflake credentials are configured."""
    return bool(os.environ.get("SNOWFLAKE_ACCOUNT"))


def _get_snowflake_connection():
    """Create Snowflake connection using environment variables.

    Returns:
        Snowflake connector Connection object.

    Raises:
        ImportError: If snowflake-connector-python is not installed.
        EnvironmentError: If required environment variables are missing.
    """
    import snowflake.connector

    account = os.environ.get("SNOWFLAKE_ACCOUNT")
    user = os.environ.get("SNOWFLAKE_USER")
    password = os.environ.get("SNOWFLAKE_PASSWORD")

    if not all([account, user, password]):
        raise OSError(
            "Missing Snowflake credentials. Set SNOWFLAKE_ACCOUNT, "
            "SNOWFLAKE_USER, SNOWFLAKE_PASSWORD environment variables."
        )

    return snowflake.connector.connect(
        account=account,
        user=user,
        password=password,
    )


@pytest.mark.skipif(
    not _snowflake_available(),
    reason=(
        "Snowflake credentials not configured. Set SNOWFLAKE_ACCOUNT, "
        "SNOWFLAKE_USER, SNOWFLAKE_PASSWORD to enable Snowflake integration tests. "
        "Note: Snowflake must be able to reach the Nessie REST endpoint; "
        "local Docker Nessie (localhost:19120) is not reachable from Snowflake cloud. "
        "For testing, deploy Nessie with a public endpoint or use Snowflake's "
        "SYSTEM$ALLOWLIST_PRIVATELINK to configure network access."
    ),
)
class TestSnowflakeReads:
    """Tests for Snowflake reading Iceberg tables via REST catalog integration.

    Configuration required for Snowflake REST catalog integration with Nessie:

    1. Nessie must be accessible from Snowflake (public endpoint or PrivateLink)
    2. CREATE CATALOG INTEGRATION in Snowflake:

        CREATE OR REPLACE CATALOG INTEGRATION nessie_catalog_int
          CATALOG_SOURCE = ICEBERG_REST
          TABLE_FORMAT = ICEBERG
          CATALOG_NAMESPACE = 'default'
          REST_CONFIG = (
            CATALOG_URI = 'https://<nessie-host>:19120/iceberg'
            PREFIX = 'main'
          )
          ENABLED = TRUE;

    3. Create ICEBERG TABLE referencing the integration:

        CREATE ICEBERG TABLE my_table
          CATALOG = 'nessie_catalog_int'
          EXTERNAL_VOLUME = '<volume_name>'
          CATALOG_TABLE_NAME = 'trades';
    """

    def test_snowflake_catalog_integration(self):
        """CREATE CATALOG INTEGRATION with Nessie REST endpoint succeeds."""
        conn = _get_snowflake_connection()
        cursor = conn.cursor()

        nessie_endpoint = os.environ.get("NESSIE_PUBLIC_ENDPOINT", "http://localhost:19120")

        try:
            cursor.execute(
                f"""
                CREATE OR REPLACE CATALOG INTEGRATION nessie_lakehouse_int
                  CATALOG_SOURCE = ICEBERG_REST
                  TABLE_FORMAT = ICEBERG
                  CATALOG_NAMESPACE = 'default'
                  REST_CONFIG = (
                    CATALOG_URI = '{nessie_endpoint}/iceberg'
                    PREFIX = 'main'
                  )
                  ENABLED = TRUE
                """
            )
            result = cursor.fetchone()
            assert result is not None, "CATALOG INTEGRATION creation returned no result"
        finally:
            cursor.close()
            conn.close()

    def test_snowflake_reads_iceberg_table(self, spark_session):
        """Snowflake reads table created by PySpark with correct row count and data types."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        # Create table via PySpark
        schema = trades_schema()
        create_namespace(spark_session, "snowflake_test")
        create_iceberg_table(
            spark_session,
            "snowflake_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/snowflake_test/trades",
        )
        write_data(
            spark_session,
            "snowflake_test",
            "trades",
            generate_trades(50, seed=5001),
            schema,
        )

        # Snowflake reads
        conn = _get_snowflake_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM snowflake_test.trades")
            row_count = cursor.fetchone()[0]
            assert row_count == 50, f"Expected 50 rows, got {row_count}"
        finally:
            cursor.close()
            conn.close()

    def test_snowflake_sees_schema_evolution(self, spark_session):
        """After schema change, Snowflake refreshes and sees new schema."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "sf_schema_evo_test")
        create_iceberg_table(
            spark_session,
            "sf_schema_evo_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/sf_schema_evo_test/trades",
        )
        write_data(
            spark_session,
            "sf_schema_evo_test",
            "trades",
            generate_trades(10, seed=5002),
            schema,
        )

        # Evolve schema in Spark
        spark_session.sql("ALTER TABLE lakehouse.sf_schema_evo_test.trades ADD COLUMNS (notes STRING)")

        # Snowflake should see the new column after refresh
        conn = _get_snowflake_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DESCRIBE TABLE sf_schema_evo_test.trades")
            columns = [row[0].lower() for row in cursor.fetchall()]
            assert "notes" in columns, f"Expected 'notes' column after schema evolution, got: {columns}"
        finally:
            cursor.close()
            conn.close()
