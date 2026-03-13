"""OpenLineage configuration for Spark sessions.

Provides Spark config keys to enable the OpenLineage Spark agent,
which emits lineage events to Marquez (or any OpenLineage-compatible backend).

Usage:
    from src.lineage.config import get_openlineage_spark_config

    ol_config = get_openlineage_spark_config()
    # Apply to SparkSession.builder via .config(key, value)
"""

from __future__ import annotations

import os

OPENLINEAGE_NAMESPACE = "lakehouse"

# Default OpenLineage transport URL (Marquez API in Docker Compose)
_DEFAULT_OPENLINEAGE_URL = "http://marquez:5000"

# OpenLineage Spark agent Maven coordinate
OPENLINEAGE_SPARK_PACKAGE = "io.openlineage:openlineage-spark_2.12:1.25.0"


def get_openlineage_spark_config(
    url: str | None = None,
    namespace: str | None = None,
) -> dict[str, str]:
    """Return Spark configuration dict for OpenLineage integration.

    The returned dict contains all spark.* keys needed to enable the
    OpenLineage Spark listener, which captures dataset and job lineage
    events and sends them to a Marquez backend via HTTP.

    Args:
        url: OpenLineage backend URL. Defaults to OPENLINEAGE_URL env var
             or http://marquez:5000.
        namespace: OpenLineage namespace. Defaults to OPENLINEAGE_NAMESPACE env var
                   or "lakehouse".

    Returns:
        Dict of {spark_config_key: value} to apply to SparkSession.builder.
    """
    if url is None:
        url = os.environ.get("OPENLINEAGE_URL", _DEFAULT_OPENLINEAGE_URL)
    if namespace is None:
        namespace = os.environ.get("OPENLINEAGE_NAMESPACE", OPENLINEAGE_NAMESPACE)

    return {
        "spark.extraListeners": "io.openlineage.spark.agent.OpenLineageSparkListener",
        "spark.openlineage.transport.type": "http",
        "spark.openlineage.transport.url": url,
        "spark.openlineage.transport.endpoint": "api/v1/lineage",
        "spark.openlineage.namespace": namespace,
    }
