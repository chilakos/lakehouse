"""Unit tests for metric_context module.

Validates that Cube YAML files can be parsed into structured definitions
and formatted into LLM-ready context strings for NL-to-SQL queries.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = str(REPO_ROOT / "semantic" / "model")


@pytest.mark.unit
class TestLoadCubeDefinitions:
    """Tests for load_cube_definitions function."""

    def test_load_cube_definitions_parses_cubes(self):
        """load_cube_definitions returns list of dicts with cube names."""
        from src.semantic.metric_context import load_cube_definitions

        definitions = load_cube_definitions(MODEL_DIR)

        # Should have at least two cubes (trading_metrics, risk_exposure)
        cube_names = [d["name"] for d in definitions if d.get("type") == "cube"]
        assert "trading_metrics" in cube_names
        assert "risk_exposure" in cube_names

    def test_load_cube_definitions_parses_views(self):
        """load_cube_definitions includes view definitions."""
        from src.semantic.metric_context import load_cube_definitions

        definitions = load_cube_definitions(MODEL_DIR)

        view_names = [d["name"] for d in definitions if d.get("type") == "view"]
        assert "trading_dashboard" in view_names
        assert "risk_dashboard" in view_names


@pytest.mark.unit
class TestBuildMetricContext:
    """Tests for build_metric_context function."""

    def test_build_metric_context_includes_table_name(self):
        """output contains TABLE: gold.trading_metrics."""
        from src.semantic.metric_context import build_metric_context, load_cube_definitions

        definitions = load_cube_definitions(MODEL_DIR)
        context = build_metric_context(definitions)

        assert "TABLE: gold.trading_metrics" in context

    def test_build_metric_context_includes_measures(self):
        """output contains METRIC: total_notional."""
        from src.semantic.metric_context import build_metric_context, load_cube_definitions

        definitions = load_cube_definitions(MODEL_DIR)
        context = build_metric_context(definitions)

        assert "METRIC: total_notional" in context

    def test_build_metric_context_includes_dimensions(self):
        """output contains DIMENSION: symbol."""
        from src.semantic.metric_context import build_metric_context, load_cube_definitions

        definitions = load_cube_definitions(MODEL_DIR)
        context = build_metric_context(definitions)

        assert "DIMENSION: symbol" in context

    def test_build_metric_context_includes_descriptions(self):
        """output contains measure descriptions."""
        from src.semantic.metric_context import build_metric_context, load_cube_definitions

        definitions = load_cube_definitions(MODEL_DIR)
        context = build_metric_context(definitions)

        # Should contain at least a fragment of a measure description
        assert "notional" in context.lower()
