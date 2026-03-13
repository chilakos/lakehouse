"""Incremental loading utilities for watermark-based delta extraction.

Provides functions for:
- Extracting the last watermark (high-water mark) from an Iceberg table
- Building incremental queries that only extract new records since last watermark
- MERGE INTO upserts for incremental updates to Iceberg tables

Uses SparkSQL for watermark queries against the Iceberg catalog.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession

logger = logging.getLogger(__name__)


@dataclass
class IncrementalConfig:
    """Configuration for incremental loading.

    Attributes:
        watermark_column: Column name used as the high-water mark (e.g., trade_date, updated_at).
        source_table: Source table or query template for extraction.
        tolerance_seconds: Overlap tolerance in seconds to handle late-arriving data.
                          Default 0 means exact watermark cutoff.
    """

    watermark_column: str
    source_table: str
    tolerance_seconds: int = 0


def get_last_watermark(
    spark: SparkSession,
    iceberg_table: str,
    watermark_column: str,
) -> Any | None:
    """Get the last watermark value from an Iceberg table.

    Runs SELECT MAX({watermark_column}) FROM lakehouse.{iceberg_table}
    to determine the high-water mark for incremental extraction.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        iceberg_table: Iceberg table path (e.g., "bronze.trades").
        watermark_column: Column name to extract the max value from.

    Returns:
        The maximum value of the watermark column, or None if the table
        is empty or the column has no non-null values.
    """
    query = f"SELECT MAX({watermark_column}) AS max_watermark FROM lakehouse.{iceberg_table}"
    logger.info("Fetching last watermark: %s", query)

    result = spark.sql(query)
    rows = result.collect()

    if not rows:
        return None

    watermark_value = rows[0][0]
    logger.info("Last watermark for %s.%s: %s", iceberg_table, watermark_column, watermark_value)
    return watermark_value


def incremental_extract(
    spark: SparkSession,
    source_query_template: str,
    watermark_column: str,
    last_watermark: Any | None,
) -> DataFrame:
    """Extract data incrementally using a watermark-based filter.

    If last_watermark is None, performs a full extract (no WHERE filter).
    Otherwise, appends a WHERE clause to filter records where
    watermark_column > last_watermark.

    Args:
        spark: Active SparkSession.
        source_query_template: Base SQL query (e.g., "SELECT * FROM source_db.trades").
        watermark_column: Column name to filter on.
        last_watermark: Previous watermark value, or None for full extract.

    Returns:
        PySpark DataFrame with extracted records.
    """
    if last_watermark is None:
        query = source_query_template
        logger.info("Full extract (no watermark): %s", query)
    else:
        query = f"{source_query_template} WHERE {watermark_column} > '{last_watermark}'"
        logger.info("Incremental extract: %s", query)

    return spark.sql(query)


def merge_incremental(
    spark: SparkSession,
    target_table: str,
    df: DataFrame,
    merge_key: str,
) -> None:
    """Perform MERGE INTO for upserts using Iceberg's merge-on-read capability.

    Matches on merge_key, updates all columns on match, inserts new rows.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        target_table: Full Iceberg table name (e.g., "lakehouse.bronze.trades").
        df: DataFrame with new/updated records to merge.
        merge_key: Column name to match on (e.g., "trade_id").
    """
    # Register the incoming DataFrame as a temporary view for MERGE INTO
    temp_view = "_merge_source_temp"
    df.createOrReplaceTempView(temp_view)

    # Build column list for UPDATE and INSERT (all columns from the DataFrame)
    columns = df.columns

    update_clause = ", ".join(f"t.{col} = s.{col}" for col in columns if col != merge_key)
    insert_columns = ", ".join(columns)
    insert_values = ", ".join(f"s.{col}" for col in columns)

    merge_sql = f"""
        MERGE INTO {target_table} t
        USING {temp_view} s
        ON t.{merge_key} = s.{merge_key}
        WHEN MATCHED THEN UPDATE SET {update_clause}
        WHEN NOT MATCHED THEN INSERT ({insert_columns}) VALUES ({insert_values})
    """

    logger.info("Executing MERGE INTO %s on key %s", target_table, merge_key)
    spark.sql(merge_sql)
    logger.info("MERGE INTO completed for %s", target_table)
