"""Integration tests for the benchmark harness.

Runs benchmark queries against Trino and PySpark, collecting latency
metrics. Tests validate that queries complete without error and results
are properly structured.

The comparison test logs results but does NOT assert on performance --
it captures metrics for analysis.

Requires Docker Compose services: Nessie, MinIO, Trino.
"""

import pytest

from src.iceberg_utils.benchmark import (
    BenchmarkResult,
    format_results,
    generate_benchmark_queries,
    run_benchmark,
)


@pytest.mark.slow
@pytest.mark.integration
class TestBenchmarks:
    """Benchmark integration tests for Trino and PySpark query performance."""

    @pytest.fixture(autouse=True)
    def setup_benchmark_data(self, spark_session, trino_connection, clean_nessie):
        """Create trades and positions tables with 10,000 rows for benchmarks."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.synthetic.generators import (
            generate_positions,
            generate_trades,
            positions_schema,
            trades_schema,
        )

        t_schema = trades_schema()
        p_schema = positions_schema()

        create_namespace(spark_session, "benchmark_ns")

        # Create and populate trades table (10,000 rows in batches)
        create_iceberg_table(
            spark_session,
            "benchmark_ns",
            "trades",
            t_schema,
            "s3://lakehouse-data/warehouse/benchmark_ns/trades",
        )
        # Write in batches to avoid memory issues
        for batch in range(10):
            trades = generate_trades(1000, seed=7000 + batch)
            # Offset trade_ids to avoid duplicates
            for t in trades:
                t["trade_id"] = t["trade_id"] + (batch * 1000)
            write_data(spark_session, "benchmark_ns", "trades", trades, t_schema)

        # Create and populate positions table (1,000 rows)
        create_iceberg_table(
            spark_session,
            "benchmark_ns",
            "positions",
            p_schema,
            "s3://lakehouse-data/warehouse/benchmark_ns/positions",
        )
        write_data(
            spark_session,
            "benchmark_ns",
            "positions",
            generate_positions(1000, seed=7100),
            p_schema,
        )

        self.spark = spark_session
        self.trino_conn = trino_connection

    def test_benchmark_trino(self):
        """Run all benchmark queries against Trino, verify all complete without error."""
        queries = generate_benchmark_queries("benchmark_ns")

        all_results = []
        for q in queries:
            # Skip join if positions table not available
            results = run_benchmark(
                self.trino_conn,
                q["sql"],
                q["name"],
                engine="trino",
                iterations=3,
            )
            assert len(results) == 3, f"Expected 3 results for {q['name']}"
            assert all(isinstance(r, BenchmarkResult) for r in results)
            assert all(r.latency_ms > 0 for r in results)
            all_results.extend(results)

        # Verify we got results for all queries
        query_names = {r.query_name for r in all_results}
        assert len(query_names) == 5, f"Expected 5 unique queries, got {query_names}"

    def test_benchmark_spark(self):
        """Run equivalent queries via PySpark, collect results."""
        # Spark benchmarks use DataFrame API
        import time

        from src.iceberg_utils.catalog import read_table

        results = []

        # Full scan count
        start = time.perf_counter_ns()
        count = read_table(self.spark, "benchmark_ns", "trades").count()
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        results.append(
            BenchmarkResult(
                query_name="full_scan_count",
                engine="spark",
                latency_ms=round(elapsed, 3),
                rows_returned=1,
                iteration=1,
            )
        )
        assert count == 10_000, f"Expected 10,000 trades, got {count}"

        # Aggregation
        start = time.perf_counter_ns()
        agg_df = self.spark.sql("SELECT symbol, SUM(notional) FROM lakehouse.benchmark_ns.trades GROUP BY symbol")
        agg_rows = agg_df.collect()
        elapsed = (time.perf_counter_ns() - start) / 1_000_000
        results.append(
            BenchmarkResult(
                query_name="aggregation",
                engine="spark",
                latency_ms=round(elapsed, 3),
                rows_returned=len(agg_rows),
                iteration=1,
            )
        )

        assert len(results) >= 2, "Expected at least 2 Spark benchmark results"
        assert all(r.latency_ms > 0 for r in results)

    def test_benchmark_comparison(self):
        """Compare Trino vs Spark latencies -- logs results, no performance assertions."""
        queries = generate_benchmark_queries("benchmark_ns")

        # Run Trino benchmarks (just count query for comparison)
        count_query = queries[0]  # full_scan_count
        trino_results = run_benchmark(
            self.trino_conn,
            count_query["sql"],
            count_query["name"],
            engine="trino",
            iterations=3,
        )

        # Format and log
        formatted = format_results(trino_results)
        assert "full_scan_count" in formatted
        assert "trino" in formatted

        # Verify results are structurally valid
        measured = [r for r in trino_results if r.iteration > 0]
        assert len(measured) == 2, "Expected 2 measured iterations (excl. warmup)"
        assert all(r.latency_ms > 0 for r in measured)
