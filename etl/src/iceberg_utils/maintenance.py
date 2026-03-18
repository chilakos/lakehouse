"""Iceberg table maintenance procedures via PySpark.

Provides automated maintenance operations:
- compact_table: Rewrite small data files into larger ones (target 256 MB)
- expire_snapshots: Remove old snapshots beyond retention policy
- remove_orphan_files: Clean up files not referenced by any snapshot
- rewrite_manifests: Optimize manifest files for faster query planning
- full_maintenance: Run all four operations in sequence

Uses PySpark CALL procedures per Apache Iceberg Spark Procedures documentation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import SparkSession


def compact_table(
    spark: SparkSession,
    namespace: str,
    table_name: str,
    target_file_size_bytes: int = 268435456,
) -> dict:
    """Compact small data files into larger ones using rewrite_data_files.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        namespace: Table namespace.
        table_name: Table name.
        target_file_size_bytes: Target file size in bytes (default 256 MB).

    Returns:
        Dictionary with compaction results including files rewritten count.
    """
    full_table_name = f"{namespace}.{table_name}"

    result_df = spark.sql(f"""
        CALL lakehouse.system.rewrite_data_files(
            table => '{full_table_name}',
            options => map('target-file-size-bytes', '{target_file_size_bytes}')
        )
    """)

    rows = result_df.collect()
    if rows:
        row = rows[0]
        return {
            "operation": "compact_table",
            "table": full_table_name,
            "rewritten_data_files_count": row["rewritten_data_files_count"],
            "added_data_files_count": row["added_data_files_count"],
        }
    return {"operation": "compact_table", "table": full_table_name, "status": "no_result"}


def expire_snapshots(
    spark: SparkSession,
    namespace: str,
    table_name: str,
    older_than_days: int = 7,
    retain_last: int = 10,
) -> dict:
    """Expire old snapshots beyond the retention policy.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        namespace: Table namespace.
        table_name: Table name.
        older_than_days: Expire snapshots older than this many days.
        retain_last: Minimum number of recent snapshots to retain.

    Returns:
        Dictionary with expiration results.
    """
    full_table_name = f"{namespace}.{table_name}"
    cutoff = datetime.now(tz=UTC) - timedelta(days=older_than_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    result_df = spark.sql(f"""
        CALL lakehouse.system.expire_snapshots(
            table => '{full_table_name}',
            older_than => TIMESTAMP '{cutoff_str}',
            retain_last => {retain_last}
        )
    """)

    rows = result_df.collect()
    if rows:
        row = rows[0]
        return {
            "operation": "expire_snapshots",
            "table": full_table_name,
            "deleted_data_files_count": row["deleted_data_files_count"],
            "deleted_manifest_files_count": row["deleted_manifest_files_count"],
            "deleted_manifest_lists_count": row["deleted_manifest_lists_count"],
        }
    return {"operation": "expire_snapshots", "table": full_table_name, "status": "no_result"}


def remove_orphan_files(
    spark: SparkSession,
    namespace: str,
    table_name: str,
    older_than_days: int = 3,
) -> dict:
    """Remove orphan files not referenced by any snapshot.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        namespace: Table namespace.
        table_name: Table name.
        older_than_days: Only remove files older than this many days.

    Returns:
        Dictionary with cleanup results.
    """
    full_table_name = f"{namespace}.{table_name}"
    cutoff = datetime.now(tz=UTC) - timedelta(days=older_than_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    result_df = spark.sql(f"""
        CALL lakehouse.system.remove_orphan_files(
            table => '{full_table_name}',
            older_than => TIMESTAMP '{cutoff_str}'
        )
    """)

    rows = result_df.collect()
    return {
        "operation": "remove_orphan_files",
        "table": full_table_name,
        "orphan_file_count": len(rows),
    }


def rewrite_manifests(
    spark: SparkSession,
    namespace: str,
    table_name: str,
) -> dict:
    """Rewrite manifest files for faster query planning.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        namespace: Table namespace.
        table_name: Table name.

    Returns:
        Dictionary with manifest rewrite results.
    """
    full_table_name = f"{namespace}.{table_name}"

    result_df = spark.sql(f"""
        CALL lakehouse.system.rewrite_manifests(
            table => '{full_table_name}'
        )
    """)

    rows = result_df.collect()
    if rows:
        row = rows[0]
        return {
            "operation": "rewrite_manifests",
            "table": full_table_name,
            "rewritten_manifests_count": row["rewritten_manifests_count"],
            "added_manifests_count": row["added_manifests_count"],
        }
    return {"operation": "rewrite_manifests", "table": full_table_name, "status": "no_result"}


def full_maintenance(
    spark: SparkSession,
    namespace: str,
    table_name: str,
    compact_target_bytes: int = 268435456,
    expire_older_than_days: int = 7,
    expire_retain_last: int = 10,
    orphan_older_than_days: int = 3,
) -> dict:
    """Run all four maintenance operations in sequence.

    Order: compact -> expire snapshots -> remove orphans -> rewrite manifests.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        namespace: Table namespace.
        table_name: Table name.
        compact_target_bytes: Target file size for compaction (default 256 MB).
        expire_older_than_days: Snapshot expiration threshold in days.
        expire_retain_last: Minimum snapshots to retain.
        orphan_older_than_days: Orphan file cleanup threshold in days.

    Returns:
        Dictionary with combined results from all operations.
    """
    results = {
        "compact": compact_table(spark, namespace, table_name, compact_target_bytes),
        "expire": expire_snapshots(spark, namespace, table_name, expire_older_than_days, expire_retain_last),
        "orphan_cleanup": remove_orphan_files(spark, namespace, table_name, orphan_older_than_days),
        "rewrite_manifests": rewrite_manifests(spark, namespace, table_name),
    }
    return results
