"""Root conftest with shared fixtures for the lakehouse ETL test suite.

Provides session-scoped fixtures for:
- SparkSession configured with Iceberg/Nessie REST catalog
- Nessie REST API URL
- Trino database connection
- MinIO (boto3 S3) client
- AWS S3 client (skips if credentials unavailable)
"""

import os
import socket

import pytest


def _is_service_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if a TCP service is reachable."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


@pytest.fixture(scope="session")
def nessie_url() -> str:
    """Nessie REST API base URL from environment or default."""
    return os.environ.get("NESSIE_URI", "http://localhost:19120")


@pytest.fixture(scope="session")
def minio_endpoint() -> str:
    """MinIO endpoint URL from environment or default."""
    return os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")


@pytest.fixture(scope="session")
def trino_host() -> str:
    """Trino host from environment or default."""
    return os.environ.get("TRINO_HOST", "localhost")


@pytest.fixture(scope="session")
def trino_port() -> int:
    """Trino port from environment or default."""
    return int(os.environ.get("TRINO_PORT", "8080"))


@pytest.fixture(scope="session")
def spark_session(nessie_url, minio_endpoint):
    """Create a SparkSession configured for Iceberg with Nessie REST catalog.

    Session-scoped: created once per test run, stopped on teardown.
    Skips if PySpark is not installed or Nessie is not reachable.
    """
    try:
        from pyspark.sql import SparkSession
    except ImportError:
        pytest.skip("PySpark not installed")

    nessie_host = nessie_url.replace("http://", "").split(":")[0]
    if not _is_service_reachable(nessie_host, 19120):
        pytest.skip("Nessie service not reachable")

    minio_access_key = os.environ.get("MINIO_ACCESS_KEY", "admin")
    minio_secret_key = os.environ.get("MINIO_SECRET_KEY", "admin123456")

    spark = (
        SparkSession.builder.appName("lakehouse-test")
        .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1")
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.lakehouse.type", "rest")
        .config("spark.sql.catalog.lakehouse.uri", f"{nessie_url}/iceberg")
        .config("spark.sql.catalog.lakehouse.warehouse", "lakehouse")
        .config("spark.sql.catalog.lakehouse.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.lakehouse.s3.endpoint", minio_endpoint)
        .config("spark.sql.catalog.lakehouse.s3.access-key-id", minio_access_key)
        .config("spark.sql.catalog.lakehouse.s3.secret-access-key", minio_secret_key)
        .config("spark.sql.catalog.lakehouse.s3.path-style-access", "true")
        .config("spark.sql.defaultCatalog", "lakehouse")
        .master("local[*]")
        .getOrCreate()
    )

    yield spark
    spark.stop()


@pytest.fixture(scope="session")
def trino_connection(trino_host, trino_port):
    """Create a Trino database connection.

    Session-scoped: created once per test run, closed on teardown.
    Skips if trino package is not installed or Trino is not reachable.
    """
    try:
        import trino
    except ImportError:
        pytest.skip("trino package not installed")

    if not _is_service_reachable(trino_host, trino_port):
        pytest.skip("Trino service not reachable")

    conn = trino.dbapi.connect(
        host=trino_host,
        port=trino_port,
        user="test",
        catalog="iceberg",
        schema="default",
    )

    yield conn
    conn.close()


@pytest.fixture(scope="session")
def minio_client(minio_endpoint):
    """Create a boto3 S3 client configured for MinIO.

    Session-scoped: created once per test run.
    Skips if boto3 is not installed or MinIO is not reachable.
    """
    try:
        import boto3
    except ImportError:
        pytest.skip("boto3 not installed")

    minio_host = minio_endpoint.replace("http://", "").split(":")[0]
    if not _is_service_reachable(minio_host, 9000):
        pytest.skip("MinIO service not reachable")

    client = boto3.client(
        "s3",
        endpoint_url=minio_endpoint,
        aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY", "admin"),
        aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY", "admin123456"),
        region_name="us-east-1",
    )

    yield client


@pytest.fixture(scope="session")
def s3_client():
    """Create a boto3 S3 client for AWS S3 using default credential chain.

    Session-scoped: created once per test run.
    Skips if boto3 is not installed or AWS credentials are unavailable.
    """
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError
    except ImportError:
        pytest.skip("boto3 not installed")

    try:
        client = boto3.client("s3")
        # Verify credentials are available by making a lightweight call
        client.list_buckets()
    except (NoCredentialsError, Exception):
        pytest.skip("AWS credentials not available")

    yield client
