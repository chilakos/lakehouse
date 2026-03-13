"""Tests for the NL-to-SQL accuracy evaluation framework.

Validates golden dataset loading, accuracy calculation with complexity
filtering, evaluation report generation, and the run_evaluation flow
with mocked LLM and database connections.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.semantic.evaluation import (
    EvalResult,
    evaluate_accuracy,
    generate_evaluation_report,
    load_golden_dataset,
    run_evaluation,
)

# Path to golden datasets
_GOLDEN_DIR = Path(__file__).resolve().parents[2] / "src" / "semantic" / "golden_datasets"
_TRADING_PATH = _GOLDEN_DIR / "trading_questions.json"
_RISK_PATH = _GOLDEN_DIR / "risk_questions.json"


class TestLoadGoldenDataset:
    """Validate golden dataset loading."""

    def test_load_golden_dataset_returns_list(self):
        """load_golden_dataset must return a list of dicts."""
        dataset = load_golden_dataset(str(_TRADING_PATH))
        assert isinstance(dataset, list)
        assert len(dataset) > 0
        assert isinstance(dataset[0], dict)

    def test_golden_dataset_entry_has_required_fields(self):
        """Each entry must have question, sql, and complexity fields."""
        dataset = load_golden_dataset(str(_TRADING_PATH))
        for entry in dataset:
            assert "question" in entry, f"Missing 'question' in: {entry}"
            assert "sql" in entry, f"Missing 'sql' in: {entry}"
            assert "complexity" in entry, f"Missing 'complexity' in: {entry}"

    def test_golden_dataset_complexity_values(self):
        """complexity must be 'simple' or 'complex'."""
        dataset = load_golden_dataset(str(_TRADING_PATH))
        for entry in dataset:
            assert entry["complexity"] in ("simple", "complex"), (
                f"Invalid complexity: {entry['complexity']}"
            )


class TestTradingGoldenDataset:
    """Validate trading golden dataset contents."""

    def test_trading_dataset_has_simple_and_complex(self):
        """trading_questions.json must have both simple and complex entries."""
        dataset = load_golden_dataset(str(_TRADING_PATH))
        complexities = {e["complexity"] for e in dataset}
        assert "simple" in complexities
        assert "complex" in complexities

    def test_trading_dataset_min_size(self):
        """trading_questions.json must have at least 15 entries."""
        dataset = load_golden_dataset(str(_TRADING_PATH))
        assert len(dataset) >= 15, f"Only {len(dataset)} entries, need at least 15"

    def test_trading_sql_references_correct_table(self):
        """All trading SQL must reference gold.trading_metrics."""
        dataset = load_golden_dataset(str(_TRADING_PATH))
        for entry in dataset:
            assert "gold.trading_metrics" in entry["sql"], (
                f"SQL does not reference gold.trading_metrics: {entry['sql']}"
            )


class TestRiskGoldenDataset:
    """Validate risk exposure golden dataset contents."""

    def test_risk_dataset_has_simple_and_complex(self):
        """risk_questions.json must have both simple and complex entries."""
        dataset = load_golden_dataset(str(_RISK_PATH))
        complexities = {e["complexity"] for e in dataset}
        assert "simple" in complexities
        assert "complex" in complexities

    def test_risk_dataset_min_size(self):
        """risk_questions.json must have at least 15 entries."""
        dataset = load_golden_dataset(str(_RISK_PATH))
        assert len(dataset) >= 15, f"Only {len(dataset)} entries, need at least 15"

    def test_risk_sql_references_correct_table(self):
        """All risk SQL must reference gold.risk_exposure."""
        dataset = load_golden_dataset(str(_RISK_PATH))
        for entry in dataset:
            assert "gold.risk_exposure" in entry["sql"], (
                f"SQL does not reference gold.risk_exposure: {entry['sql']}"
            )


class TestEvalResult:
    """Validate EvalResult dataclass structure."""

    def test_eval_result_dataclass(self):
        """EvalResult must have all required fields."""
        result = EvalResult(
            question="test",
            golden_sql="SELECT 1",
            generated_sql="SELECT 1",
            golden_results=[(1,)],
            generated_results=[(1,)],
            match=True,
            complexity="simple",
            error=None,
        )
        assert result.question == "test"
        assert result.golden_sql == "SELECT 1"
        assert result.generated_sql == "SELECT 1"
        assert result.golden_results == [(1,)]
        assert result.generated_results == [(1,)]
        assert result.match is True
        assert result.complexity == "simple"
        assert result.error is None


class TestEvaluateAccuracy:
    """Validate accuracy computation with complexity filtering."""

    def _make_results(self, matches: list[tuple[bool, str]]) -> list[EvalResult]:
        """Create EvalResult list from (match, complexity) tuples."""
        return [
            EvalResult(
                question=f"q{i}",
                golden_sql="SELECT 1",
                generated_sql="SELECT 1",
                golden_results=[(1,)],
                generated_results=[(1,)] if m else [(2,)],
                match=m,
                complexity=c,
                error=None,
            )
            for i, (m, c) in enumerate(matches)
        ]

    def test_evaluate_accuracy_all_correct(self):
        """100% accuracy when all results match."""
        results = self._make_results([
            (True, "simple"),
            (True, "simple"),
            (True, "complex"),
        ])
        acc = evaluate_accuracy(results)
        assert acc["accuracy_pct"] == 100.0
        assert acc["total"] == 3
        assert acc["correct"] == 3

    def test_evaluate_accuracy_some_wrong(self):
        """Partial accuracy computed correctly."""
        results = self._make_results([
            (True, "simple"),
            (False, "simple"),
            (True, "complex"),
            (False, "complex"),
        ])
        acc = evaluate_accuracy(results)
        assert acc["accuracy_pct"] == 50.0
        assert acc["total"] == 4
        assert acc["correct"] == 2

    def test_evaluate_accuracy_filter_simple(self):
        """complexity_filter='simple' only counts simple entries."""
        results = self._make_results([
            (True, "simple"),
            (True, "simple"),
            (False, "complex"),
        ])
        acc = evaluate_accuracy(results, complexity_filter="simple")
        assert acc["accuracy_pct"] == 100.0
        assert acc["total"] == 2

    def test_evaluate_accuracy_filter_complex(self):
        """complexity_filter='complex' only counts complex entries."""
        results = self._make_results([
            (True, "simple"),
            (False, "complex"),
            (True, "complex"),
        ])
        acc = evaluate_accuracy(results, complexity_filter="complex")
        assert acc["accuracy_pct"] == 50.0
        assert acc["total"] == 2

    def test_evaluate_accuracy_empty_results(self):
        """Returns 0.0 accuracy for empty list."""
        acc = evaluate_accuracy([])
        assert acc["accuracy_pct"] == 0.0
        assert acc["total"] == 0
        assert acc["correct"] == 0


class TestRunEvaluation:
    """Validate run_evaluation with mocked LLM and DB."""

    def test_run_evaluation_mocked(self):
        """run_evaluation generates SQL for each golden question and compares."""
        # Mock engine
        mock_engine = MagicMock()
        mock_engine.ask.return_value = "SELECT SUM(total_notional) FROM gold.trading_metrics"

        # Mock connection
        mock_conn = MagicMock()
        # Return the same results for both golden and generated SQL
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [(100,)]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        dataset = [
            {
                "question": "What is the total notional?",
                "sql": "SELECT SUM(total_notional) FROM gold.trading_metrics",
                "complexity": "simple",
            },
            {
                "question": "How many trades?",
                "sql": "SELECT SUM(trade_count) FROM gold.trading_metrics",
                "complexity": "simple",
            },
        ]

        results = run_evaluation(mock_engine, mock_conn, dataset)

        assert len(results) == 2
        assert all(isinstance(r, EvalResult) for r in results)
        # Engine should be called for each question
        assert mock_engine.ask.call_count == 2


class TestEvaluationReport:
    """Validate evaluation report structure."""

    def test_evaluation_report_structure(self):
        """generate_evaluation_report returns dict with overall, simple, complex accuracy."""
        results = [
            EvalResult(
                question="q1", golden_sql="S1", generated_sql="S1",
                golden_results=[(1,)], generated_results=[(1,)],
                match=True, complexity="simple", error=None,
            ),
            EvalResult(
                question="q2", golden_sql="S2", generated_sql="S2",
                golden_results=[(2,)], generated_results=[(2,)],
                match=True, complexity="complex", error=None,
            ),
            EvalResult(
                question="q3", golden_sql="S3", generated_sql="S3x",
                golden_results=[(3,)], generated_results=[(99,)],
                match=False, complexity="complex", error=None,
            ),
        ]
        report = generate_evaluation_report(results)

        assert "overall" in report
        assert "simple" in report
        assert "complex" in report

        assert report["overall"]["accuracy_pct"] == pytest.approx(66.67, abs=0.1)
        assert report["simple"]["accuracy_pct"] == 100.0
        assert report["complex"]["accuracy_pct"] == 50.0

        # Thresholds
        assert "simple_pass" in report
        assert "complex_pass" in report
        assert report["simple_pass"] is True  # 100% >= 90%
        assert report["complex_pass"] is False  # 50% < 70%
