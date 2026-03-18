"""Benchmark harness for measuring query latency and throughput across engines.

Provides:
- BenchmarkResult dataclass for structured benchmark data
- run_benchmark() to time queries across multiple iterations
- generate_benchmark_queries() for standard benchmark query set
- format_results() for markdown table output
- save_results() for JSON persistence
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trino.dbapi import Connection


@dataclass
class BenchmarkResult:
    """Single benchmark measurement result.

    Attributes:
        query_name: Descriptive name of the query being benchmarked.
        engine: Query engine name (e.g., 'trino', 'spark').
        latency_ms: Query execution latency in milliseconds.
        rows_returned: Number of rows returned by the query.
        bytes_scanned: Bytes scanned during query (None if unavailable).
        timestamp: ISO timestamp of when the measurement was taken.
        iteration: Which iteration of the benchmark run (0 = warmup).
    """

    query_name: str
    engine: str
    latency_ms: float
    rows_returned: int
    bytes_scanned: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    iteration: int = 0


def run_benchmark(
    conn: Connection,
    query: str,
    query_name: str,
    engine: str,
    iterations: int = 5,
) -> list[BenchmarkResult]:
    """Run a query multiple times and record latency for each iteration.

    The first run is treated as a warmup (iteration=0) and is included
    in results but should be excluded from aggregated metrics.

    Args:
        conn: Active database connection (Trino DBAPI or similar).
        query: SQL query string to benchmark.
        query_name: Descriptive name for the query.
        engine: Name of the query engine (e.g., 'trino', 'spark').
        iterations: Total number of iterations including warmup.

    Returns:
        List of BenchmarkResult for each iteration (first is warmup).
    """
    results = []

    for i in range(iterations):
        cursor = conn.cursor()
        try:
            start_ns = time.perf_counter_ns()
            cursor.execute(query)
            rows = cursor.fetchall()
            elapsed_ns = time.perf_counter_ns() - start_ns

            latency_ms = elapsed_ns / 1_000_000

            results.append(
                BenchmarkResult(
                    query_name=query_name,
                    engine=engine,
                    latency_ms=round(latency_ms, 3),
                    rows_returned=len(rows),
                    bytes_scanned=None,
                    iteration=i,
                )
            )
        finally:
            cursor.close()

    return results


def generate_benchmark_queries(namespace: str) -> list[dict]:
    """Generate standard benchmark queries for a given namespace.

    Returns a set of queries covering common analytical patterns:
    full scan, filtered scan, aggregation, join, and point lookup.

    Args:
        namespace: Iceberg namespace containing benchmark tables.

    Returns:
        List of dicts with 'name' and 'sql' keys.
    """
    return [
        {
            "name": "full_scan_count",
            "sql": f"SELECT COUNT(*) FROM {namespace}.trades",
        },
        {
            "name": "filtered_scan",
            "sql": f"SELECT * FROM {namespace}.trades WHERE trade_date = DATE '2025-06-15'",
        },
        {
            "name": "aggregation",
            "sql": (f"SELECT symbol, SUM(notional) as total_notional FROM {namespace}.trades GROUP BY symbol"),
        },
        {
            "name": "join_trades_positions",
            "sql": (
                f"SELECT t.symbol, p.market_value "
                f"FROM {namespace}.trades t "
                f"JOIN {namespace}.positions p ON t.account_id = p.account_id"
            ),
        },
        {
            "name": "point_lookup",
            "sql": f"SELECT * FROM {namespace}.trades WHERE trade_id = 42",
        },
    ]


def format_results(results: list[BenchmarkResult]) -> str:
    """Format benchmark results as a markdown table.

    Excludes warmup iterations (iteration=0) from the summary.

    Args:
        results: List of BenchmarkResult to format.

    Returns:
        Markdown-formatted table string.
    """
    # Filter out warmup
    measured = [r for r in results if r.iteration > 0]

    if not measured:
        return "No benchmark results (only warmup data available)."

    # Group by query_name and engine
    groups: dict[tuple[str, str], list[BenchmarkResult]] = {}
    for r in measured:
        key = (r.query_name, r.engine)
        groups.setdefault(key, []).append(r)

    lines = [
        "| Query | Engine | Min (ms) | Avg (ms) | Max (ms) | P50 (ms) | Rows |",
        "|-------|--------|----------|----------|----------|----------|------|",
    ]

    for (query_name, engine), group in sorted(groups.items()):
        latencies = sorted(r.latency_ms for r in group)
        min_ms = latencies[0]
        max_ms = latencies[-1]
        avg_ms = sum(latencies) / len(latencies)
        p50_idx = len(latencies) // 2
        p50_ms = latencies[p50_idx]
        rows = group[0].rows_returned

        lines.append(
            f"| {query_name} | {engine} | {min_ms:.1f} | {avg_ms:.1f} | {max_ms:.1f} | {p50_ms:.1f} | {rows} |"
        )

    return "\n".join(lines)


def save_results(results: list[BenchmarkResult], output_path: str) -> None:
    """Save benchmark results to a JSON file.

    Creates parent directories if they do not exist.

    Args:
        results: List of BenchmarkResult to save.
        output_path: File path for the JSON output.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(r) for r in results]
    path.write_text(json.dumps(data, indent=2, default=str))
