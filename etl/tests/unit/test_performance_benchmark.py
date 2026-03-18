"""Unit tests for the BI performance benchmark harness.

Validates BenchmarkResult dataclass structure, benchmark_query function
with mocked Trino connections, and generate_benchmark_report statistics.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestBenchmarkResultDataclass:
    """Tests for BenchmarkResult dataclass."""

    def test_benchmark_result_dataclass(self):
        """BenchmarkResult has query_name, source, latency_ms, row_count fields."""
        from src.semantic.benchmark import BenchmarkResult

        result = BenchmarkResult(
            query_name="test_query",
            source="trino",
            latency_ms=123.45,
            row_count=100,
        )
        assert result.query_name == "test_query"
        assert result.source == "trino"
        assert result.latency_ms == 123.45
        assert result.row_count == 100


@pytest.mark.unit
class TestBenchmarkQuery:
    """Tests for benchmark_query function."""

    def _make_mock_conn(self, rows=None):
        """Create a mock Trino connection."""
        if rows is None:
            rows = [(1, "a"), (2, "b"), (3, "c")]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = rows
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    def test_benchmark_query_returns_results(self):
        """benchmark_query returns list of BenchmarkResult (mocked Trino connection)."""
        from src.semantic.benchmark import BenchmarkResult, benchmark_query

        mock_conn = self._make_mock_conn()
        results = benchmark_query(
            conn=mock_conn,
            query_name="test_query",
            sql="SELECT 1",
            iterations=3,
        )

        assert isinstance(results, list)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, BenchmarkResult)
            assert r.query_name == "test_query"
            assert r.source == "trino"
            assert r.row_count == 3  # 3 rows in mock

    def test_benchmark_query_measures_latency(self):
        """each result has latency_ms > 0."""
        from src.semantic.benchmark import benchmark_query

        mock_conn = self._make_mock_conn()
        results = benchmark_query(
            conn=mock_conn,
            query_name="latency_test",
            sql="SELECT 1",
            iterations=2,
        )

        for r in results:
            assert r.latency_ms > 0, f"Expected latency_ms > 0, got {r.latency_ms}"

    def test_benchmark_query_default_iterations(self):
        """default is 5 iterations."""
        from src.semantic.benchmark import benchmark_query

        mock_conn = self._make_mock_conn()
        results = benchmark_query(
            conn=mock_conn,
            query_name="default_iter",
            sql="SELECT 1",
        )

        assert len(results) == 5


@pytest.mark.unit
class TestBenchmarkReport:
    """Tests for generate_benchmark_report function."""

    def test_benchmark_report_generates_summary(self):
        """generate_benchmark_report returns dict with p50, p95, avg latency per query."""
        from src.semantic.benchmark import BenchmarkResult, generate_benchmark_report

        results = [
            BenchmarkResult("q1", "trino", 10.0, 100),
            BenchmarkResult("q1", "trino", 20.0, 100),
            BenchmarkResult("q1", "trino", 30.0, 100),
            BenchmarkResult("q1", "trino", 40.0, 100),
            BenchmarkResult("q1", "trino", 50.0, 100),
            BenchmarkResult("q2", "trino", 5.0, 50),
            BenchmarkResult("q2", "trino", 15.0, 50),
            BenchmarkResult("q2", "trino", 25.0, 50),
        ]

        report = generate_benchmark_report(results)

        assert "q1" in report
        assert "q2" in report

        # Check q1 stats
        q1 = report["q1"]
        assert "p50" in q1
        assert "p95" in q1
        assert "avg" in q1
        assert q1["avg"] == pytest.approx(30.0, rel=0.01)

        # Check q2 stats
        q2 = report["q2"]
        assert "p50" in q2
        assert "p95" in q2
        assert "avg" in q2
        assert q2["avg"] == pytest.approx(15.0, rel=0.01)
