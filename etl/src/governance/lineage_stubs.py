"""Legacy system lineage stub registration in Marquez.

Registers legacy data sources (Teradata, Snowflake) as dataset stubs in Marquez
so they appear in lineage graphs even before full migration. This ensures a
complete lineage picture from source to gold layer.

Usage::

    from src.governance.lineage_stubs import (
        register_legacy_lineage_stub,
        register_teradata_sources,
        register_snowflake_sources,
    )

    # Register all known Teradata sources
    results = register_teradata_sources("http://localhost:5000")

    # Register a single custom stub
    result = register_legacy_lineage_stub(
        marquez_url="http://localhost:5000",
        namespace="lakehouse",
        source_name="teradata.dw",
        dataset_name="custom_table",
        description="Custom legacy table",
        fields=[{"name": "id", "type": "INTEGER"}],
        tags=["legacy", "teradata"],
    )
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import requests

    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False
    logger.warning("requests library not available; lineage stub registration will be disabled")


def register_legacy_lineage_stub(
    marquez_url: str,
    namespace: str,
    source_name: str,
    dataset_name: str,
    description: str,
    fields: list[dict] | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Register a legacy dataset stub in Marquez via REST API.

    Creates or updates a DB_TABLE dataset in the specified Marquez namespace.
    This creates an upstream lineage node representing the legacy source.

    Args:
        marquez_url: Base URL of the Marquez API (e.g., "http://marquez:5000").
        namespace: Marquez namespace (e.g., "lakehouse").
        source_name: Logical source system name (e.g., "teradata.dw").
        dataset_name: Dataset/table name within the source (e.g., "trades_history").
        description: Human-readable description of the dataset.
        fields: Optional list of field dicts with keys "name" and "type".
        tags: Optional list of tag strings for the dataset.

    Returns:
        dict: Marquez API response body on success, or error dict on failure.
            Error dict has "error": True and "message": <str>.

    Example::

        result = register_legacy_lineage_stub(
            marquez_url="http://marquez:5000",
            namespace="lakehouse",
            source_name="teradata.dw",
            dataset_name="trades_history",
            description="Legacy Teradata trade history table",
            fields=[
                {"name": "trade_id", "type": "INTEGER"},
                {"name": "trade_date", "type": "DATE"},
            ],
            tags=["legacy", "teradata"],
        )
    """
    if not _REQUESTS_AVAILABLE:
        return {
            "error": True,
            "message": "requests library not installed; cannot register lineage stub",
        }

    url = f"{marquez_url.rstrip('/')}/api/v1/namespaces/{namespace}/datasets/{source_name}.{dataset_name}"

    payload: dict[str, Any] = {
        "type": "DB_TABLE",
        "physicalName": f"{source_name}.{dataset_name}",
        "description": description,
        "sourceName": source_name,
        "fields": fields or [],
        "tags": tags or [],
    }

    try:
        response = requests.put(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(
            "Registered lineage stub: %s.%s in namespace %s",
            source_name,
            dataset_name,
            namespace,
        )
        return response.json()
    except requests.exceptions.ConnectionError as exc:
        logger.warning("Cannot connect to Marquez at %s: %s", marquez_url, exc)
        return {"error": True, "message": f"Connection error: {exc}"}
    except requests.exceptions.HTTPError as exc:
        logger.warning("HTTP error registering stub %s.%s: %s", source_name, dataset_name, exc)
        return {"error": True, "message": f"HTTP error: {exc}"}
    except Exception as exc:
        logger.warning("Unexpected error registering stub %s.%s: %s", source_name, dataset_name, exc)
        return {"error": True, "message": f"Unexpected error: {exc}"}


def register_teradata_sources(
    marquez_url: str,
    namespace: str = "lakehouse",
) -> list[dict]:
    """Register all known Teradata source tables as lineage stubs in Marquez.

    Creates stub datasets representing legacy Teradata tables that feed into
    the lakehouse bronze layer. These stubs appear in Marquez lineage graphs
    as upstream nodes before the full Teradata-to-Iceberg migration.

    Args:
        marquez_url: Base URL of the Marquez API (e.g., "http://marquez:5000").
        namespace: Marquez namespace (default: "lakehouse").

    Returns:
        list[dict]: List of Marquez API responses, one per registered table.
    """
    teradata_tables = [
        {
            "source_name": "teradata.dw",
            "dataset_name": "trades_history",
            "description": (
                "Legacy Teradata trade history table. Contains all historical trade"
                " executions pre-migration. Source of truth for"
                " bronze.raw_trades_history in the lakehouse."
            ),
            "fields": [
                {"name": "trade_id", "type": "INTEGER"},
                {"name": "trade_date", "type": "DATE"},
                {"name": "settlement_date", "type": "DATE"},
                {"name": "security_id", "type": "VARCHAR"},
                {"name": "quantity", "type": "DECIMAL"},
                {"name": "price", "type": "DECIMAL"},
                {"name": "counterparty_id", "type": "INTEGER"},
                {"name": "business_unit", "type": "VARCHAR"},
            ],
            "tags": ["legacy", "teradata", "trades", "migration-source"],
        },
        {
            "source_name": "teradata.dw",
            "dataset_name": "positions_daily",
            "description": (
                "Legacy Teradata daily positions snapshot. End-of-day net positions"
                " per security per business unit. Source of truth for"
                " bronze.raw_positions_daily in the lakehouse."
            ),
            "fields": [
                {"name": "position_date", "type": "DATE"},
                {"name": "security_id", "type": "VARCHAR"},
                {"name": "business_unit", "type": "VARCHAR"},
                {"name": "net_quantity", "type": "DECIMAL"},
                {"name": "market_value_usd", "type": "DECIMAL"},
            ],
            "tags": ["legacy", "teradata", "positions", "migration-source"],
        },
        {
            "source_name": "teradata.dw",
            "dataset_name": "counterparty_master",
            "description": (
                "Legacy Teradata counterparty reference data. Master data for all"
                " trading counterparties including legal entity details and credit"
                " ratings. Source for silver.counterparty_master in the lakehouse."
            ),
            "fields": [
                {"name": "counterparty_id", "type": "INTEGER"},
                {"name": "legal_name", "type": "VARCHAR"},
                {"name": "lei_code", "type": "VARCHAR"},
                {"name": "credit_rating", "type": "VARCHAR"},
                {"name": "country_code", "type": "CHAR(2)"},
            ],
            "tags": ["legacy", "teradata", "reference-data", "migration-source"],
        },
    ]

    results = []
    for table in teradata_tables:
        result = register_legacy_lineage_stub(
            marquez_url=marquez_url,
            namespace=namespace,
            source_name=table["source_name"],
            dataset_name=table["dataset_name"],
            description=table["description"],
            fields=table["fields"],
            tags=table["tags"],
        )
        results.append(result)
        logger.info(
            "Registered Teradata stub: %s.%s -> %s",
            table["source_name"],
            table["dataset_name"],
            "OK" if not result.get("error") else "FAILED",
        )

    return results


def register_snowflake_sources(
    marquez_url: str,
    namespace: str = "lakehouse",
) -> list[dict]:
    """Register all known Snowflake datasets as lineage stubs in Marquez.

    Creates stub datasets representing Snowflake analytics exports that feed
    into the lakehouse. These stubs appear in Marquez lineage graphs as
    upstream nodes for Snowflake-originated data.

    Args:
        marquez_url: Base URL of the Marquez API (e.g., "http://marquez:5000").
        namespace: Marquez namespace (default: "lakehouse").

    Returns:
        list[dict]: List of Marquez API responses, one per registered dataset.
    """
    snowflake_datasets = [
        {
            "source_name": "snowflake.analytics",
            "dataset_name": "risk_metrics",
            "description": (
                "Snowflake risk analytics export. Aggregated VaR, Greeks, and"
                " stress-test results exported nightly from Snowflake risk platform."
                " Source for gold.risk_metrics_daily in the lakehouse."
            ),
            "fields": [
                {"name": "metric_date", "type": "DATE"},
                {"name": "business_unit", "type": "VARCHAR"},
                {"name": "asset_class", "type": "VARCHAR"},
                {"name": "var_1d_95pct", "type": "DECIMAL"},
                {"name": "var_10d_99pct", "type": "DECIMAL"},
                {"name": "stressed_var", "type": "DECIMAL"},
            ],
            "tags": ["snowflake", "risk", "analytics", "daily"],
        },
        {
            "source_name": "snowflake.analytics",
            "dataset_name": "trading_summary",
            "description": (
                "Snowflake trading summary export. Daily P&L, volume, and commission"
                " summaries by business unit and security type. Source for"
                " gold.trading_summary_daily in the lakehouse."
            ),
            "fields": [
                {"name": "summary_date", "type": "DATE"},
                {"name": "business_unit", "type": "VARCHAR"},
                {"name": "security_type", "type": "VARCHAR"},
                {"name": "trade_count", "type": "INTEGER"},
                {"name": "gross_pnl_usd", "type": "DECIMAL"},
                {"name": "net_pnl_usd", "type": "DECIMAL"},
                {"name": "total_volume_usd", "type": "DECIMAL"},
            ],
            "tags": ["snowflake", "trading", "pnl", "daily"],
        },
    ]

    results = []
    for dataset in snowflake_datasets:
        result = register_legacy_lineage_stub(
            marquez_url=marquez_url,
            namespace=namespace,
            source_name=dataset["source_name"],
            dataset_name=dataset["dataset_name"],
            description=dataset["description"],
            fields=dataset["fields"],
            tags=dataset["tags"],
        )
        results.append(result)
        logger.info(
            "Registered Snowflake stub: %s.%s -> %s",
            dataset["source_name"],
            dataset["dataset_name"],
            "OK" if not result.get("error") else "FAILED",
        )

    return results
