"""Semantic layer utilities for the lakehouse platform.

Provides:
- metric_context: Parses Cube YAML definitions into structured LLM-ready
  context for NL-to-SQL queries (AISEM-02 bridge).
- benchmark: BI query performance measurement harness for comparing
  lakehouse vs Teradata query latency (BISEM-04).
"""

from src.semantic.benchmark import BenchmarkResult, benchmark_query, generate_benchmark_report
from src.semantic.metric_context import build_metric_context, load_cube_definitions

__all__ = [
    "BenchmarkResult",
    "benchmark_query",
    "build_metric_context",
    "generate_benchmark_report",
    "load_cube_definitions",
]
