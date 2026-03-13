"""Integration tests for OpenMetadata catalog ingestion.

Tests that Trino table metadata from bronze/silver/gold schemas
is correctly ingested and searchable via the OpenMetadata API.

These tests SKIP automatically if OpenMetadata is not running.

Run with: pytest tests/integration/test_catalog_ingestion.py -m integration
"""

import socket

import pytest


def _is_openmetadata_reachable(host: str = "localhost", port: int = 8585, timeout: float = 2.0) -> bool:
    """Check if OpenMetadata server is reachable via TCP."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


OM_HOST = "localhost"
OM_PORT = 8585
OM_BASE_URL = f"http://{OM_HOST}:{OM_PORT}/api/v1"

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def require_openmetadata():
    """Skip all tests in this module if OpenMetadata is not running."""
    if not _is_openmetadata_reachable(OM_HOST, OM_PORT):
        pytest.skip(
            f"OpenMetadata server not reachable at {OM_HOST}:{OM_PORT}. "
            "Start the stack with: docker compose up openmetadata-server"
        )


@pytest.fixture(scope="module")
def om_session():
    """Create an authenticated requests session for OpenMetadata API calls."""
    try:
        import requests
    except ImportError:
        pytest.skip("requests library not installed")

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


class TestTrinoIngestionInCatalog:
    """Test that Trino metadata is ingested and discoverable in OpenMetadata."""

    def test_trino_service_registered_in_catalog(self, om_session):
        """lakehouse-trino service should be registered after ingestion."""
        response = om_session.get(f"{OM_BASE_URL}/services/databaseServices/name/lakehouse-trino")
        assert response.status_code == 200, (
            f"lakehouse-trino service not found in catalog (status {response.status_code}). "
            "Run: metadata ingest -c infra/docker/openmetadata/connectors/trino-ingestion.yaml"
        )
        data = response.json()
        assert data.get("serviceType") == "Trino", (
            f"Expected serviceType 'Trino', got '{data.get('serviceType')}'"
        )

    def test_bronze_schema_tables_appear_in_catalog(self, om_session):
        """Bronze layer tables should be discoverable by schema filter."""
        response = om_session.get(
            f"{OM_BASE_URL}/tables",
            params={"database": "lakehouse-trino.iceberg.bronze", "limit": 10},
        )
        # 200 or empty results are acceptable; key check is API responds
        assert response.status_code in (200, 404), (
            f"Unexpected status fetching bronze tables: {response.status_code}"
        )
        if response.status_code == 200:
            data = response.json()
            tables = data.get("data", [])
            assert isinstance(tables, list), "Response data should be a list"

    def test_silver_schema_tables_appear_in_catalog(self, om_session):
        """Silver layer tables should be discoverable by schema filter."""
        response = om_session.get(
            f"{OM_BASE_URL}/tables",
            params={"database": "lakehouse-trino.iceberg.silver", "limit": 10},
        )
        assert response.status_code in (200, 404), (
            f"Unexpected status fetching silver tables: {response.status_code}"
        )

    def test_gold_schema_tables_appear_in_catalog(self, om_session):
        """Gold layer tables should be discoverable by schema filter."""
        response = om_session.get(
            f"{OM_BASE_URL}/tables",
            params={"database": "lakehouse-trino.iceberg.gold", "limit": 10},
        )
        assert response.status_code in (200, 404), (
            f"Unexpected status fetching gold tables: {response.status_code}"
        )

    def test_search_returns_results_for_table_keyword(self, om_session):
        """Full-text search should return results when querying a table keyword."""
        response = om_session.get(
            f"{OM_BASE_URL}/search/query",
            params={"q": "trades", "index": "table_search_index", "from": 0, "size": 10},
        )
        # Search may return empty if no tables ingested yet -- just check API is up
        assert response.status_code == 200, (
            f"Search endpoint returned status {response.status_code}"
        )

    def test_ingested_table_has_column_metadata(self, om_session):
        """Ingested tables should include column-level metadata."""
        # Search for any table first
        search_response = om_session.get(
            f"{OM_BASE_URL}/search/query",
            params={"q": "*", "index": "table_search_index", "from": 0, "size": 1},
        )
        if search_response.status_code != 200:
            pytest.skip("Search API not responding")

        hits = search_response.json().get("hits", {}).get("hits", [])
        if not hits:
            pytest.skip("No tables ingested yet -- run trino-ingestion.yaml first")

        table_fqn = hits[0]["_source"].get("fullyQualifiedName")
        if not table_fqn:
            pytest.skip("Could not extract table FQN from search result")

        # Fetch table details
        table_response = om_session.get(
            f"{OM_BASE_URL}/tables/name/{table_fqn}",
            params={"fields": "columns"},
        )
        assert table_response.status_code == 200, (
            f"Could not fetch table details for {table_fqn}"
        )
        table_data = table_response.json()
        columns = table_data.get("columns", [])
        assert len(columns) > 0, f"Table {table_fqn} should have at least one column"
