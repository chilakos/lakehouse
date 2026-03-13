"""Environment-aware configuration for the lakehouse ETL framework.

Loads settings from environment variables with sensible defaults
matching the local Docker Compose development environment.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """Lakehouse ETL configuration settings.

    All values are loaded from environment variables with defaults
    suitable for local development (Docker Compose).
    """

    # Nessie catalog
    nessie_uri: str = field(default_factory=lambda: os.environ.get("NESSIE_URI", "http://localhost:19120"))
    nessie_warehouse: str = field(default_factory=lambda: os.environ.get("NESSIE_WAREHOUSE", "lakehouse"))

    # S3 (cloud)
    s3_endpoint: str = field(default_factory=lambda: os.environ.get("S3_ENDPOINT", ""))
    s3_region: str = field(default_factory=lambda: os.environ.get("S3_REGION", "us-east-1"))

    # MinIO (on-prem S3-compatible)
    minio_endpoint: str = field(default_factory=lambda: os.environ.get("MINIO_ENDPOINT", "http://localhost:9000"))
    minio_access_key: str = field(default_factory=lambda: os.environ.get("MINIO_ACCESS_KEY", "admin"))
    minio_secret_key: str = field(default_factory=lambda: os.environ.get("MINIO_SECRET_KEY", "admin123456"))

    # Trino
    trino_host: str = field(default_factory=lambda: os.environ.get("TRINO_HOST", "localhost"))
    trino_port: int = field(default_factory=lambda: int(os.environ.get("TRINO_PORT", "8080")))

    # Environment
    environment: str = field(default_factory=lambda: os.environ.get("ENVIRONMENT", "dev"))

    # OpenLineage
    openlineage_url: str = field(
        default_factory=lambda: os.environ.get("OPENLINEAGE_URL", "http://localhost:5000")
    )
    openlineage_namespace: str = field(
        default_factory=lambda: os.environ.get("OPENLINEAGE_NAMESPACE", "lakehouse")
    )

    # Airflow
    airflow_home: str = field(
        default_factory=lambda: os.environ.get("AIRFLOW_HOME", "/opt/airflow")
    )

    @property
    def nessie_api_url(self) -> str:
        """Full Nessie REST API v2 URL."""
        return f"{self.nessie_uri}/api/v2"

    @property
    def nessie_iceberg_url(self) -> str:
        """Nessie Iceberg REST catalog URL."""
        return f"{self.nessie_uri}/iceberg"

    @property
    def trino_url(self) -> str:
        """Trino JDBC-style connection URL."""
        return f"http://{self.trino_host}:{self.trino_port}"

    @classmethod
    def from_env(cls) -> "Settings":
        """Create Settings instance from current environment variables."""
        return cls()
