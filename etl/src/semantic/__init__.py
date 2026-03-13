"""Semantic layer utilities for the lakehouse platform.

Provides:
- metric_context: Parses Cube YAML definitions into structured LLM-ready
  context for NL-to-SQL queries (AISEM-02 bridge).
- benchmark: BI query performance measurement harness for comparing
  lakehouse vs Teradata query latency (BISEM-04).
- prompt_builder: Constructs LLM prompts with metric context and few-shot
  examples for NL-to-SQL generation.
- nl_to_sql: NLToSQLEngine for generating Trino SQL via Claude on Bedrock.
- evaluation: Accuracy evaluation framework with golden dataset comparison
  and tiered accuracy thresholds (AISEM-03).
- cross_tool_validation: Cross-tool metric consistency, glossary linking,
  and YAML structure validation for CI/CD quality gates.
"""

from src.semantic.benchmark import BenchmarkResult, benchmark_query, generate_benchmark_report
from src.semantic.cross_tool_validation import (
    validate_cube_yaml_structure,
    validate_glossary_links,
    validate_metric_consistency,
)
from src.semantic.evaluation import EvalResult, evaluate_accuracy, generate_evaluation_report, load_golden_dataset
from src.semantic.metric_context import build_metric_context, load_cube_definitions
from src.semantic.nl_to_sql import NLToSQLEngine, NLToSQLError
from src.semantic.prompt_builder import build_few_shot_examples, build_prompt

__all__ = [
    "BenchmarkResult",
    "EvalResult",
    "NLToSQLEngine",
    "NLToSQLError",
    "benchmark_query",
    "build_few_shot_examples",
    "build_metric_context",
    "build_prompt",
    "evaluate_accuracy",
    "generate_benchmark_report",
    "generate_evaluation_report",
    "load_cube_definitions",
    "load_golden_dataset",
    "validate_cube_yaml_structure",
    "validate_glossary_links",
    "validate_metric_consistency",
]
