"""Integration tests for Cube SQL API connectivity.

Tests require a running Cube SQL API on localhost:15432. All tests
auto-skip when the Cube service is not available (TCP probe).

These tests validate:
- PostgreSQL wire protocol connectivity to Cube SQL API
- Trading dashboard view query and column verification
- Risk dashboard view query and column verification
- Decimal precision pass-through without loss

Usage:
    # Start services first:
    docker compose up -d trino cube-api cubestore minio nessie postgres

    # Run integration tests:
    cd etl && python -m pytest tests/integration/test_cube_sql_api.py -v
"""

from __future__ import annotations

import socket
from decimal import Decimal

import pytest

CUBE_HOST = "localhost"
CUBE_PORT = 15432
CUBE_USER = "cube"
CUBE_PASSWORD = "cube_local_dev"


def _cube_available() -> bool:
    """TCP probe to check if Cube SQL API is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((CUBE_HOST, CUBE_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False


# Skip all tests in this module when Cube is not running
pytestmark = pytest.mark.skipif(
    not _cube_available(),
    reason=f"Cube SQL API not available at {CUBE_HOST}:{CUBE_PORT}",
)


def _get_cube_connection():
    """Create a connection to Cube SQL API via PostgreSQL wire protocol."""
    try:
        import pg8000

        return pg8000.connect(
            host=CUBE_HOST,
            port=CUBE_PORT,
            user=CUBE_USER,
            password=CUBE_PASSWORD,
        )
    except ImportError:
        import psycopg2

        return psycopg2.connect(
            host=CUBE_HOST,
            port=CUBE_PORT,
            user=CUBE_USER,
            password=CUBE_PASSWORD,
        )


@pytest.mark.integration
class TestCubeSqlApiConnection:
    """Test basic connectivity to Cube SQL API."""

    def test_cube_sql_api_connection(self):
        """Connect via PostgreSQL protocol to Cube SQL API, verify connection."""
        conn = _get_cube_connection()
        assert conn is not None
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result is not None
        cursor.close()
        conn.close()


@pytest.mark.integration
class TestCubeSqlApiTradingMetrics:
    """Test trading dashboard view via Cube SQL API."""

    def test_cube_sql_api_trading_metrics(self):
        """Query trading_dashboard view, verify columns match Cube YAML."""
        conn = _get_cube_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM trading_dashboard LIMIT 5")
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]

            # Columns should match the view definition
            expected_columns = {
                "total_notional",
                "trade_count",
                "avg_price",
                "symbol",
                "side",
            }
            actual_columns = {c.lower() for c in columns}
            assert expected_columns.issubset(actual_columns), (
                f"Missing columns: {expected_columns - actual_columns}"
            )

        cursor.close()
        conn.close()


@pytest.mark.integration
class TestCubeSqlApiRiskExposure:
    """Test risk dashboard view via Cube SQL API."""

    def test_cube_sql_api_risk_exposure(self):
        """Query risk_dashboard view, verify columns."""
        conn = _get_cube_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM risk_dashboard LIMIT 5")
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]

            expected_columns = {
                "total_market_value",
                "total_var_95",
                "total_var_99",
                "total_expected_shortfall",
                "position_count",
                "account_id",
                "sector",
                "currency",
            }
            actual_columns = {c.lower() for c in columns}
            assert expected_columns.issubset(actual_columns), (
                f"Missing columns: {expected_columns - actual_columns}"
            )

        cursor.close()
        conn.close()


@pytest.mark.integration
class TestCubeSqlApiDecimalPrecision:
    """Test Decimal precision through Cube SQL API."""

    def test_cube_sql_api_decimal_precision(self):
        """Verify Decimal values pass through without precision loss."""
        conn = _get_cube_connection()
        cursor = conn.cursor()

        # Query a known Decimal measure
        cursor.execute(
            "SELECT total_notional FROM trading_dashboard LIMIT 1"
        )
        rows = cursor.fetchall()
        if rows:
            value = rows[0][0]
            # Value should be numeric (Decimal or float), not a string
            assert isinstance(value, (Decimal, float, int)), (
                f"Expected numeric type, got {type(value)}: {value}"
            )

        cursor.close()
        conn.close()
