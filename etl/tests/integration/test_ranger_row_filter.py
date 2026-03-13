"""Integration tests for Ranger row-level filter policies.

Tests verify that Ranger row-filter policies correctly restrict rows visible
to users in business-unit-specific Ranger groups.

Skipped if Ranger Admin is not running on ranger-admin:6080 or localhost:6080.

Requirements:
- Ranger Admin running with Trino service configured
- Trino connected to Ranger (access-control.name=ranger in config.properties)
- Bootstrap policies applied (run infra/docker/ranger/bootstrap-policies.py)
- gold.trades table with business_unit column containing wealth_mgmt, investment_banking rows
- Ranger groups: wealth_mgmt, investment_banking, risk_management
"""

import os
import socket

import pytest

RANGER_HOST = os.environ.get("RANGER_HOST", "localhost")
RANGER_PORT = int(os.environ.get("RANGER_PORT", "6080"))
TRINO_HOST = os.environ.get("TRINO_HOST", "localhost")
TRINO_PORT = int(os.environ.get("TRINO_PORT", "8080"))


def _is_service_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP service is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


ranger_available = pytest.mark.skipif(
    not _is_service_reachable(RANGER_HOST, RANGER_PORT),
    reason=f"Ranger Admin not running on {RANGER_HOST}:{RANGER_PORT}",
)


@pytest.mark.integration
@ranger_available
class TestRangerRowFiltering:
    """Integration tests for Ranger row-level security behavior via Trino."""

    @pytest.fixture(scope="class")
    def trino_conn_wealth_mgmt(self):
        """Trino connection as wealth_mgmt group member."""
        try:
            import trino

            conn = trino.dbapi.connect(
                host=TRINO_HOST,
                port=TRINO_PORT,
                user="wealth_mgmt_user",
                http_headers={"X-Trino-Role": "data_readers"},
            )
            return conn
        except ImportError:
            pytest.skip("trino package not installed")

    @pytest.fixture(scope="class")
    def trino_conn_data_admin(self):
        """Trino connection as data_admin (sees all rows)."""
        try:
            import trino

            conn = trino.dbapi.connect(
                host=TRINO_HOST,
                port=TRINO_PORT,
                user="admin_user",
                http_headers={"X-Trino-Role": "data_admin"},
            )
            return conn
        except ImportError:
            pytest.skip("trino package not installed")

    def test_wealth_mgmt_sees_only_own_business_unit(self, trino_conn_wealth_mgmt):
        """Users in wealth_mgmt group should only see rows where business_unit='wealth_mgmt'."""
        cursor = trino_conn_wealth_mgmt.cursor()
        cursor.execute("SELECT DISTINCT business_unit FROM iceberg.gold.trades")
        rows = cursor.fetchall()

        business_units = {row[0] for row in rows}
        assert "investment_banking" not in business_units, (
            "wealth_mgmt user should not see investment_banking rows"
        )
        assert "risk_management" not in business_units, (
            "wealth_mgmt user should not see risk_management rows"
        )

    def test_data_admin_sees_all_rows(self, trino_conn_data_admin):
        """data_admin should see all rows (no row filter applied)."""
        cursor = trino_conn_data_admin.cursor()
        cursor.execute("SELECT DISTINCT business_unit FROM iceberg.gold.trades")
        rows = cursor.fetchall()

        business_units = {row[0] for row in rows}
        # Admin should see at least multiple business units
        assert len(business_units) > 1, (
            f"data_admin should see all business units, got: {business_units}"
        )

    def test_row_filter_applies_on_select_star(self, trino_conn_wealth_mgmt):
        """Row filter should apply on SELECT * queries."""
        cursor = trino_conn_wealth_mgmt.cursor()
        cursor.execute("SELECT * FROM iceberg.gold.trades LIMIT 100")
        rows = cursor.fetchall()

        # All returned rows should be for wealth_mgmt
        # Column index for business_unit depends on table schema -- use column name check
        cursor.execute("DESCRIBE iceberg.gold.trades")
        columns = [row[0] for row in cursor.fetchall()]

        if "business_unit" in columns:
            bu_idx = columns.index("business_unit")
            for row in rows:
                assert row[bu_idx] == "wealth_mgmt", (
                    f"SELECT * should only return wealth_mgmt rows, got: {row[bu_idx]}"
                )

    def test_row_filter_applies_on_count(self, trino_conn_wealth_mgmt, trino_conn_data_admin):
        """Row filter should apply on SELECT count(*) -- wealth_mgmt < total count."""
        cursor_reader = trino_conn_wealth_mgmt.cursor()
        cursor_reader.execute("SELECT count(*) FROM iceberg.gold.trades")
        reader_count = cursor_reader.fetchone()[0]

        cursor_admin = trino_conn_data_admin.cursor()
        cursor_admin.execute("SELECT count(*) FROM iceberg.gold.trades")
        admin_count = cursor_admin.fetchone()[0]

        assert reader_count < admin_count, (
            f"wealth_mgmt reader ({reader_count}) should see fewer rows than admin ({admin_count})"
        )
