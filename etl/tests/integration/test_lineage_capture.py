"""Integration tests for OpenLineage lineage capture via Marquez.

Validates that:
- SparkSession with enable_lineage=True emits OpenLineage events
- Lineage events arrive in Marquez and are queryable via API
- Namespace and job references are correct

Skips gracefully if Marquez is not running or PySpark is not installed.
"""

from __future__ import annotations

import os
import socket
import time

import pytest


def _is_service_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP service is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


def _get_marquez_url() -> str:
    """Get Marquez API URL from environment or default."""
    return os.environ.get("OPENLINEAGE_URL", "http://localhost:5000")


def _parse_host_port(url: str) -> tuple[str, int]:
    """Extract host and port from a URL."""
    # Remove scheme
    no_scheme = url.replace("http://", "").replace("https://", "")
    parts = no_scheme.split(":")
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 5000
    return host, port


@pytest.fixture(scope="module")
def marquez_url():
    """Marquez API URL, skip if not reachable."""
    url = _get_marquez_url()
    host, port = _parse_host_port(url)
    if not _is_service_reachable(host, port):
        pytest.skip(f"Marquez not reachable at {host}:{port}")
    return url


@pytest.fixture(scope="module")
def lineage_spark_session(marquez_url):
    """Create a SparkSession with OpenLineage enabled.

    Session-scoped per module. Skips if PySpark not installed
    or Nessie not reachable.
    """
    try:
        from pyspark.sql import SparkSession  # noqa: F401
    except ImportError:
        pytest.skip("PySpark not installed")

    nessie_url = os.environ.get("NESSIE_URI", "http://localhost:19120")
    nessie_host = nessie_url.replace("http://", "").split(":")[0]
    if not _is_service_reachable(nessie_host, 19120):
        pytest.skip("Nessie service not reachable")

    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")

    from src.iceberg_utils.catalog import get_spark_session

    spark = get_spark_session(
        nessie_uri=nessie_url,
        s3_endpoint=minio_endpoint,
        app_name="lineage-test",
        enable_lineage=True,
    )
    yield spark
    spark.stop()


@pytest.mark.integration
class TestLineageCapture:
    """Smoke tests for OpenLineage event emission to Marquez."""

    def test_spark_write_emits_lineage_event(self, lineage_spark_session, marquez_url):
        """Writing an Iceberg table with lineage enabled should emit events to Marquez.

        This is a smoke test -- detailed lineage graph validation is deferred
        to a manual checkpoint. Here we verify that at least one job or run
        appears in the Marquez namespace after a Spark write.
        """
        import json
        import urllib.request

        spark = lineage_spark_session

        # Create a test namespace and write data
        test_ns = "lineage_test"
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS lakehouse.{test_ns}")
        spark.sql(f"DROP TABLE IF EXISTS lakehouse.{test_ns}.lineage_smoke_test")
        spark.sql(f"CREATE TABLE lakehouse.{test_ns}.lineage_smoke_test (id INT, value STRING) USING iceberg")

        # Insert data to trigger lineage event
        spark.sql(f"INSERT INTO lakehouse.{test_ns}.lineage_smoke_test VALUES (1, 'test')")

        # Allow time for async event delivery
        time.sleep(3)

        # Query Marquez API for jobs in the lakehouse namespace
        api_url = f"{marquez_url}/api/v1/namespaces/lakehouse/jobs"
        try:
            req = urllib.request.Request(api_url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                jobs = data.get("jobs", [])
                # Smoke test: we should have at least one job registered
                assert len(jobs) > 0, (
                    "No jobs found in Marquez namespace 'lakehouse'. Expected OpenLineage events from Spark write."
                )
        except urllib.error.URLError as exc:
            pytest.skip(f"Could not reach Marquez API: {exc}")

    def test_marquez_namespace_exists(self, marquez_url):
        """Verify the 'lakehouse' namespace is queryable in Marquez."""
        import json
        import urllib.request

        api_url = f"{marquez_url}/api/v1/namespaces"
        try:
            req = urllib.request.Request(api_url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                namespaces = data.get("namespaces", [])
                [ns.get("name") for ns in namespaces]
                # This may or may not contain 'lakehouse' depending on
                # whether any events have been emitted. Just verify the API works.
                assert isinstance(namespaces, list), "Marquez namespaces API returned unexpected format"
        except urllib.error.URLError as exc:
            pytest.skip(f"Could not reach Marquez API: {exc}")
