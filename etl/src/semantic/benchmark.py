"""BI query performance benchmark harness.

Measures query execution latency against the lakehouse (Trino) to support
BISEM-04 performance validation. Provides statistical reporting (p50, p95,
avg) for side-by-side comparison with Teradata baselines.

Usage:
    from src.iceberg_utils.trino import get_trino_connection
    from src.semantic.benchmark import benchmark_query, generate_benchmark_report

    conn = get_trino_connection()
    results = benchmark_query(conn, "trading_summary", "SELECT * FROM gold.trading_metrics")
    report = generate_benchmark_report(results)
    print(report)

Teradata baselines can be stored as JSON fixtures and loaded for comparison
when Teradata access is available.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trino.dbapi import Connection

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark query execution.

    Attributes:
        query_name: Human-readable name identifying the query.
        source: Data source identifier (e.g., "trino", "teradata").
        latency_ms: Query execution latency in milliseconds.
        row_count: Number of rows returned by the query.
    """

    query_name: str
    source: str
    latency_ms: float
    row_count: int


def benchmark_query(
    conn: Connection,
    query_name: str,
    sql: str,
    iterations: int = 5,
    source: str = "trino",
) -> list[BenchmarkResult]:
    """Run a query multiple times and record execution latency.

    Executes the given SQL query `iterations` times against the provided
    connection, measuring wall-clock latency for each execution.

    Args:
        conn: Database connection (Trino or compatible DBAPI2).
        query_name: Human-readable name for the query being benchmarked.
        sql: SQL query string to execute.
        iterations: Number of times to execute the query (default: 5).
        source: Data source identifier for result tagging (default: "trino").

    Returns:
        List of BenchmarkResult, one per iteration.
    """
    results: list[BenchmarkResult] = []

    for i in range(iterations):
        cursor = conn.cursor()

        start = time.perf_counter()
        cursor.execute(sql)
        rows = cursor.fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        result = BenchmarkResult(
            query_name=query_name,
            source=source,
            latency_ms=elapsed_ms,
            row_count=len(rows),
        )
        results.append(result)

        logger.debug(
            "Benchmark %s iteration %d/%d: %.2f ms, %d rows",
            query_name,
            i + 1,
            iterations,
            elapsed_ms,
            len(rows),
        )

    return results


def generate_benchmark_report(results: list[BenchmarkResult]) -> dict:
    """Generate statistical summary from benchmark results.

    Groups results by query_name and computes p50 (median), p95, and
    average latency for each query.

    Args:
        results: List of BenchmarkResult from benchmark_query calls.

    Returns:
        Dict mapping query_name to stats dict with p50, p95, avg,
        min, max, iterations, and source keys.
    """
    from collections import defaultdict

    grouped: dict[str, list[float]] = defaultdict(list)
    sources: dict[str, str] = {}

    for r in results:
        grouped[r.query_name].append(r.latency_ms)
        sources[r.query_name] = r.source

    report: dict = {}

    for query_name, latencies in grouped.items():
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        # Percentile calculation
        p50_idx = int(n * 0.50)
        p95_idx = min(int(n * 0.95), n - 1)

        report[query_name] = {
            "p50": sorted_latencies[p50_idx],
            "p95": sorted_latencies[p95_idx],
            "avg": sum(sorted_latencies) / n,
            "min": sorted_latencies[0],
            "max": sorted_latencies[-1],
            "iterations": n,
            "source": sources[query_name],
        }

    return report
