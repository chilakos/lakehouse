"""Integration test conftest with service availability checks and cleanup fixtures."""

import os
import urllib.request

import pytest


def _http_health_check(url: str, timeout: float = 2.0) -> bool:
    """Check if an HTTP endpoint is reachable and returns 2xx."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def ensure_services():
    """Verify that Docker services (Nessie, MinIO, Trino) are running.

    Autouse session-scoped fixture: runs once at the start of integration tests.
    Skips the entire integration test session if services are unavailable.
    """
    nessie_uri = os.environ.get("NESSIE_URI", "http://localhost:19120")
    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    trino_host = os.environ.get("TRINO_HOST", "localhost")
    trino_port = os.environ.get("TRINO_PORT", "8080")

    services = {
        "Nessie": f"{nessie_uri}/api/v2/config",
        "MinIO": f"{minio_endpoint}/minio/health/live",
        "Trino": f"http://{trino_host}:{trino_port}/v1/info",
    }

    unreachable = []
    for name, url in services.items():
        if not _http_health_check(url):
            unreachable.append(name)

    if unreachable:
        pytest.skip(
            f"Docker services not running ({', '.join(unreachable)}). "
            "Start with: docker compose up -d"
        )


@pytest.fixture()
def clean_nessie(nessie_url):
    """Clean up Nessie catalog state before and after each integration test.

    Function-scoped: drops namespaces and tables created during the test.
    Uses Nessie REST API for cleanup.
    """
    import urllib.request
    import json

    iceberg_base = f"{nessie_url}/iceberg/main"

    def _list_namespaces() -> list[list[str]]:
        """List all namespaces in the Nessie catalog."""
        try:
            url = f"{iceberg_base}/namespaces"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return data.get("namespaces", [])
        except Exception:
            return []

    def _list_tables(namespace: str) -> list[str]:
        """List all tables in a namespace."""
        try:
            url = f"{iceberg_base}/namespaces/{namespace}/tables"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return [t["name"] for t in data.get("identifiers", [])]
        except Exception:
            return []

    def _drop_table(namespace: str, table: str) -> None:
        """Drop a table from the catalog."""
        try:
            url = f"{iceberg_base}/namespaces/{namespace}/tables/{table}?purgeRequested=true"
            req = urllib.request.Request(url, method="DELETE")
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

    def _drop_namespace(namespace: str) -> None:
        """Drop an empty namespace."""
        try:
            url = f"{iceberg_base}/namespaces/{namespace}"
            req = urllib.request.Request(url, method="DELETE")
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

    def _cleanup():
        """Remove all namespaces and their tables."""
        for ns_parts in _list_namespaces():
            ns = ".".join(ns_parts) if isinstance(ns_parts, list) else ns_parts
            for table in _list_tables(ns):
                _drop_table(ns, table)
            _drop_namespace(ns)

    # Clean before test
    _cleanup()

    yield

    # Clean after test
    _cleanup()
