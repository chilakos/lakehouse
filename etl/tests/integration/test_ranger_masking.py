"""Integration tests for Ranger column masking policies.

Tests verify that Ranger masking policies correctly mask sensitive columns
for different user roles (data_readers, data_engineers, data_admin).

Skipped if Ranger Admin is not running on ranger-admin:6080 or localhost:6080.

Requirements:
- Ranger Admin running with Trino service configured
- Trino connected to Ranger (access-control.name=ranger in config.properties)
- Bootstrap policies applied (run infra/docker/ranger/bootstrap-policies.py)
- gold.trades table with SSN and trader_email columns
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
class TestRangerMaskingPolicies:
    """Integration tests for Ranger column masking behavior via Trino."""

    @pytest.fixture(scope="class")
    def trino_conn_data_readers(self):
        """Trino connection as data_readers role."""
        try:
            import trino

            conn = trino.dbapi.connect(
                host=TRINO_HOST,
                port=TRINO_PORT,
                user="test_reader",
                http_headers={"X-Trino-Role": "data_readers"},
            )
            return conn
        except ImportError:
            pytest.skip("trino package not installed")

    @pytest.fixture(scope="class")
    def trino_conn_data_admin(self):
        """Trino connection as data_admin role."""
        try:
            import trino

            conn = trino.dbapi.connect(
                host=TRINO_HOST,
                port=TRINO_PORT,
                user="test_admin",
                http_headers={"X-Trino-Role": "data_admin"},
            )
            return conn
        except ImportError:
            pytest.skip("trino package not installed")

    def test_ssn_is_masked_for_data_readers(self, trino_conn_data_readers):
        """SSN column should be NULL or show only last 4 digits for data_readers."""
        cursor = trino_conn_data_readers.cursor()
        cursor.execute("SELECT ssn FROM iceberg.gold.trades LIMIT 5")
        rows = cursor.fetchall()

        for row in rows:
            ssn_value = row[0]
            # MASK_NULL: value is None; MASK_SHOW_LAST_4: only 4 chars
            if ssn_value is not None:
                assert len(str(ssn_value)) <= 4, f"SSN should be masked for data_readers, got: {ssn_value}"

    def test_ssn_is_unmasked_for_data_admin(self, trino_conn_data_admin):
        """SSN column should be unmasked (MASK_NONE) for data_admin."""
        cursor = trino_conn_data_admin.cursor()
        cursor.execute("SELECT ssn FROM iceberg.gold.trades LIMIT 5")
        rows = cursor.fetchall()

        unmasked_count = 0
        for row in rows:
            ssn_value = row[0]
            if ssn_value is not None and len(str(ssn_value)) > 4:
                unmasked_count += 1
        # At least some rows should have full SSN values
        assert unmasked_count > 0, "data_admin should see unmasked SSN values"

    def test_confidential_columns_hashed_for_data_readers(self, trino_conn_data_readers):
        """CONFIDENTIAL columns (e.g., trader_email) should be hashed for data_readers."""
        cursor = trino_conn_data_readers.cursor()
        cursor.execute("SELECT trader_email FROM iceberg.gold.trades LIMIT 5")
        rows = cursor.fetchall()

        for row in rows:
            email_value = row[0]
            if email_value is not None:
                # MASK_HASH produces hex digest, not valid email format
                assert "@" not in str(email_value), (
                    f"trader_email should be hashed for data_readers, got: {email_value}"
                )
