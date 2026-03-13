"""Source-to-lakehouse reconciliation framework.

Compares row counts, checksums, and aggregate values between a source
DataFrame and a target Iceberg table to validate data migration accuracy.
Supports QUAL-03 parallel-run validation of migrated DataStage jobs.

Usage:
    from src.quality.reconciliation import reconcile_table, ReconciliationResult

    result = reconcile_table(
        spark=spark,
        source_df=source_dataframe,
        target_table="silver.trades",
        checksum_columns=["price", "notional"],
        aggregate_columns={"quantity": "SUM", "price": "AVG"},
    )
    if not result.passed:
        report_reconciliation_failure(result)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession

from pyspark.sql import functions as F

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationResult:
    """Result of a source-to-target reconciliation comparison.

    Attributes:
        table_name: Name of the target table being reconciled.
        source_row_count: Number of rows in the source DataFrame.
        target_row_count: Number of rows in the target Iceberg table.
        row_count_match: Whether source and target row counts are equal.
        source_checksum: Sum of checksum columns from source (None if not computed).
        target_checksum: Sum of checksum columns from target (None if not computed).
        checksum_match: Whether checksums match within tolerance (None if not computed).
        source_aggregates: Dict of aggregate name -> value from source.
        target_aggregates: Dict of aggregate name -> value from target.
        aggregate_matches: Dict of aggregate name -> whether values match within tolerance.
        passed: Overall reconciliation result -- True only when all checks pass.
    """

    table_name: str
    source_row_count: int
    target_row_count: int
    row_count_match: bool
    source_checksum: Decimal | None = None
    target_checksum: Decimal | None = None
    checksum_match: bool | None = None
    source_aggregates: dict[str, Any] = field(default_factory=dict)
    target_aggregates: dict[str, Any] = field(default_factory=dict)
    aggregate_matches: dict[str, bool] = field(default_factory=dict)
    passed: bool = False


def _within_tolerance(
    source_val: Decimal | None,
    target_val: Decimal | None,
    tolerance: Decimal,
) -> bool:
    """Check if two values are within relative tolerance.

    Uses relative difference: abs(source - target) / max(abs(source), 1) <= tolerance.

    Args:
        source_val: Source value.
        target_val: Target value.
        tolerance: Maximum allowed relative difference.

    Returns:
        True if values are within tolerance or both are None.
    """
    if source_val is None and target_val is None:
        return True
    if source_val is None or target_val is None:
        return False

    source_dec = Decimal(str(source_val))
    target_dec = Decimal(str(target_val))

    denominator = max(abs(source_dec), Decimal("1"))
    relative_diff = abs(source_dec - target_dec) / denominator

    return relative_diff <= tolerance


def reconcile_table(
    spark: SparkSession,
    source_df: DataFrame,
    target_table: str,
    checksum_columns: list[str] | None = None,
    aggregate_columns: dict[str, str] | None = None,
    tolerance: Decimal = Decimal("0.01"),
) -> ReconciliationResult:
    """Compare source DataFrame with target Iceberg table for migration validation.

    Performs three levels of comparison:
    1. Row count: Exact match between source_df.count() and target table count.
    2. Checksum: Sum of specified numeric columns compared within tolerance.
    3. Aggregates: Specified aggregate functions (SUM, AVG, MIN, MAX) compared.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        source_df: Source DataFrame to compare against.
        target_table: Target Iceberg table name (e.g., "bronze.trades").
        checksum_columns: Columns to compute SUM checksum for comparison.
        aggregate_columns: Dict of {column_name: aggregate_function} to compare.
            Supported functions: SUM, AVG, MIN, MAX, COUNT.
        tolerance: Maximum allowed relative difference for numeric comparisons.

    Returns:
        ReconciliationResult with comparison details and overall pass/fail.
    """
    full_target = f"lakehouse.{target_table}"
    logger.info("Reconciling source DataFrame against %s", full_target)

    # 1. Row count comparison
    source_row_count = source_df.count()
    target_count_result = spark.sql(
        f"SELECT COUNT(*) as cnt FROM {full_target}"
    ).collect()
    target_row_count = target_count_result[0].cnt
    row_count_match = source_row_count == target_row_count

    logger.info(
        "Row counts -- source: %d, target: %d, match: %s",
        source_row_count,
        target_row_count,
        row_count_match,
    )

    # 2. Checksum comparison (if columns specified)
    source_checksum: Decimal | None = None
    target_checksum: Decimal | None = None
    checksum_match: bool | None = None

    if checksum_columns:
        # Compute source checksum: SUM of all checksum columns
        sum_exprs = [F.sum(F.col(col)).alias(f"sum_{col}") for col in checksum_columns]
        source_sums_row = source_df.agg(*sum_exprs).collect()[0]
        source_checksum = Decimal("0")
        for col in checksum_columns:
            val = source_sums_row[f"sum_{col}"]
            if val is not None:
                source_checksum += Decimal(str(val))

        # Compute target checksum via SparkSQL
        sum_sql = " + ".join(f"COALESCE(SUM({col}), 0)" for col in checksum_columns)
        target_checksum_result = spark.sql(
            f"SELECT {sum_sql} as checksum FROM {full_target}"
        ).collect()
        target_checksum = Decimal(str(target_checksum_result[0]["checksum"]))

        checksum_match = _within_tolerance(source_checksum, target_checksum, tolerance)

        logger.info(
            "Checksum -- source: %s, target: %s, match: %s",
            source_checksum,
            target_checksum,
            checksum_match,
        )

    # 3. Aggregate comparison (if columns specified)
    source_aggregates: dict[str, Any] = {}
    target_aggregates: dict[str, Any] = {}
    aggregate_matches: dict[str, bool] = {}

    if aggregate_columns:
        for col_name, agg_func in aggregate_columns.items():
            agg_key = f"{col_name}_{agg_func}"

            # Source aggregate
            func_map = {
                "SUM": F.sum,
                "AVG": F.avg,
                "MIN": F.min,
                "MAX": F.max,
                "COUNT": F.count,
            }
            spark_func = func_map.get(agg_func.upper())
            if spark_func is None:
                logger.warning("Unsupported aggregate function: %s", agg_func)
                continue

            source_agg_row = source_df.agg(
                spark_func(F.col(col_name)).alias(agg_key)
            ).collect()[0]
            source_val = source_agg_row[agg_key]
            source_aggregates[agg_key] = (
                Decimal(str(source_val)) if source_val is not None else None
            )

            # Target aggregate via SparkSQL
            target_agg_result = spark.sql(
                f"SELECT {agg_func}({col_name}) as {agg_key} FROM {full_target}"
            ).collect()
            target_val = target_agg_result[0][agg_key]
            target_aggregates[agg_key] = (
                Decimal(str(target_val)) if target_val is not None else None
            )

            match = _within_tolerance(
                source_aggregates[agg_key],
                target_aggregates[agg_key],
                tolerance,
            )
            aggregate_matches[agg_key] = match

            logger.info(
                "Aggregate %s -- source: %s, target: %s, match: %s",
                agg_key,
                source_aggregates[agg_key],
                target_aggregates[agg_key],
                match,
            )

    # Determine overall pass/fail
    passed = row_count_match
    if checksum_match is not None:
        passed = passed and checksum_match
    if aggregate_matches:
        passed = passed and all(aggregate_matches.values())

    logger.info("Reconciliation result: passed=%s", passed)

    return ReconciliationResult(
        table_name=target_table,
        source_row_count=source_row_count,
        target_row_count=target_row_count,
        row_count_match=row_count_match,
        source_checksum=source_checksum,
        target_checksum=target_checksum,
        checksum_match=checksum_match,
        source_aggregates=source_aggregates,
        target_aggregates=target_aggregates,
        aggregate_matches=aggregate_matches,
        passed=passed,
    )
