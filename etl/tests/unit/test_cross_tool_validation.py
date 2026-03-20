"""Unit tests for cross-tool validation, glossary linking, and YAML structure validation.

Tests the cross-tool metric validation (Cube vs Trino), glossary link
verification (meta.glossary_term references exist in glossary-seed.json),
and Cube YAML structural validation. Also verifies CI workflow contains
the Cube YAML validation step.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

# Resolve paths relative to the repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


@pytest.mark.unit
class TestValidateMetricConsistency:
    """Tests for validate_metric_consistency -- cross-tool Cube vs Trino comparison."""

    def test_validate_metric_consistency_matching(self, tmp_path):
        """Returns pass=True when Cube and Trino return identical values."""
        from src.semantic.cross_tool_validation import validate_metric_consistency

        # Mock connections that return the same results
        trino_conn = MagicMock()
        trino_cursor = MagicMock()
        trino_cursor.fetchall.return_value = [
            ("AAPL", Decimal("1234567.8900")),
            ("MSFT", Decimal("9876543.2100")),
        ]
        trino_conn.cursor.return_value.__enter__ = MagicMock(return_value=trino_cursor)
        trino_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        cube_conn = MagicMock()
        cube_cursor = MagicMock()
        cube_cursor.fetchall.return_value = [
            ("AAPL", Decimal("1234567.8900")),
            ("MSFT", Decimal("9876543.2100")),
        ]
        cube_conn.cursor.return_value.__enter__ = MagicMock(return_value=cube_cursor)
        cube_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        queries = [
            {
                "name": "total_notional_by_symbol",
                "trino_sql": "SELECT symbol, SUM(total_notional) FROM gold.trading_metrics GROUP BY symbol",
                "cube_sql": "SELECT symbol, SUM(total_notional) FROM trading_dashboard GROUP BY symbol",
            }
        ]

        result = validate_metric_consistency(trino_conn, cube_conn, queries)

        assert result["pass"] is True
        assert len(result["results"]) == 1
        assert len(result["mismatches"]) == 0

    def test_validate_metric_consistency_mismatch(self):
        """Returns pass=False with diff details when values differ."""
        from src.semantic.cross_tool_validation import validate_metric_consistency

        trino_conn = MagicMock()
        trino_cursor = MagicMock()
        trino_cursor.fetchall.return_value = [("AAPL", Decimal("1000.0000"))]
        trino_conn.cursor.return_value.__enter__ = MagicMock(return_value=trino_cursor)
        trino_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        cube_conn = MagicMock()
        cube_cursor = MagicMock()
        cube_cursor.fetchall.return_value = [("AAPL", Decimal("9999.0000"))]
        cube_conn.cursor.return_value.__enter__ = MagicMock(return_value=cube_cursor)
        cube_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        queries = [
            {
                "name": "total_notional",
                "trino_sql": "SELECT symbol, total_notional FROM gold.trading_metrics",
                "cube_sql": "SELECT symbol, total_notional FROM trading_dashboard",
            }
        ]

        result = validate_metric_consistency(trino_conn, cube_conn, queries)

        assert result["pass"] is False
        assert len(result["mismatches"]) == 1
        assert result["mismatches"][0]["name"] == "total_notional"

    def test_validate_metric_consistency_decimal_precision(self):
        """Decimal(38,4) values compared correctly with tolerance."""
        from src.semantic.cross_tool_validation import validate_metric_consistency

        trino_conn = MagicMock()
        trino_cursor = MagicMock()
        # Values differ by less than 4-decimal precision tolerance
        trino_cursor.fetchall.return_value = [("AAPL", Decimal("1234.5678"))]
        trino_conn.cursor.return_value.__enter__ = MagicMock(return_value=trino_cursor)
        trino_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        cube_conn = MagicMock()
        cube_cursor = MagicMock()
        cube_cursor.fetchall.return_value = [("AAPL", Decimal("1234.5678"))]
        cube_conn.cursor.return_value.__enter__ = MagicMock(return_value=cube_cursor)
        cube_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        queries = [
            {
                "name": "decimal_precision_test",
                "trino_sql": "SELECT symbol, avg_price FROM gold.trading_metrics",
                "cube_sql": "SELECT symbol, avg_price FROM trading_dashboard",
            }
        ]

        result = validate_metric_consistency(trino_conn, cube_conn, queries)

        assert result["pass"] is True
        assert len(result["mismatches"]) == 0


@pytest.mark.unit
class TestValidateGlossaryLinks:
    """Tests for validate_glossary_links -- glossary_term existence validation."""

    def test_validate_glossary_links_all_valid(self, tmp_path):
        """Returns pass=True when all meta.glossary_term values exist in glossary-seed.json."""
        from src.semantic.cross_tool_validation import validate_glossary_links

        # Create a minimal cube YAML with glossary terms
        cubes_dir = tmp_path / "cubes"
        cubes_dir.mkdir()
        cube_yaml = {
            "cubes": [
                {
                    "name": "test_cube",
                    "sql_table": "gold.test",
                    "measures": [
                        {
                            "name": "m1",
                            "sql": "m1",
                            "type": "sum",
                            "meta": {"glossary_term": "Trade"},
                        },
                        {
                            "name": "m2",
                            "sql": "m2",
                            "type": "sum",
                            "meta": {"glossary_term": "Position"},
                        },
                    ],
                    "dimensions": [],
                }
            ]
        }
        (cubes_dir / "test.yml").write_text(yaml.dump(cube_yaml))

        # Create glossary with matching terms
        glossary = {"terms": [{"name": "Trade"}, {"name": "Position"}, {"name": "PII"}]}
        glossary_path = tmp_path / "glossary-seed.json"
        glossary_path.write_text(json.dumps(glossary))

        result = validate_glossary_links(str(tmp_path), str(glossary_path))

        assert result["pass"] is True
        assert len(result["valid_links"]) == 2
        assert len(result["missing_terms"]) == 0

    def test_validate_glossary_links_missing_term(self, tmp_path):
        """Returns pass=False listing missing terms."""
        from src.semantic.cross_tool_validation import validate_glossary_links

        cubes_dir = tmp_path / "cubes"
        cubes_dir.mkdir()
        cube_yaml = {
            "cubes": [
                {
                    "name": "test_cube",
                    "sql_table": "gold.test",
                    "measures": [
                        {
                            "name": "m1",
                            "sql": "m1",
                            "type": "sum",
                            "meta": {"glossary_term": "Trade"},
                        },
                        {
                            "name": "m1",
                            "sql": "m1",
                            "type": "sum",
                            "meta": {"glossary_term": "NonExistentTerm"},
                        },
                    ],
                    "dimensions": [],
                }
            ]
        }
        (cubes_dir / "test.yml").write_text(yaml.dump(cube_yaml))

        # Glossary without "NonExistentTerm"
        glossary = {"terms": [{"name": "Trade"}, {"name": "Position"}]}
        glossary_path = tmp_path / "glossary-seed.json"
        glossary_path.write_text(json.dumps(glossary))

        result = validate_glossary_links(str(tmp_path), str(glossary_path))

        assert result["pass"] is False
        assert "NonExistentTerm" in result["missing_terms"]


@pytest.mark.unit
class TestValidateCubeYamlStructure:
    """Tests for validate_cube_yaml_structure -- structural YAML validation."""

    def test_validate_cube_yaml_structure_valid(self, tmp_path):
        """Returns pass=True when all cubes have required fields."""
        from src.semantic.cross_tool_validation import validate_cube_yaml_structure

        cubes_dir = tmp_path / "cubes"
        cubes_dir.mkdir()
        cube_yaml = {
            "cubes": [
                {
                    "name": "test_cube",
                    "sql_table": "gold.test",
                    "measures": [
                        {"name": "m1", "sql": "m1", "type": "sum"},
                    ],
                    "dimensions": [],
                }
            ]
        }
        (cubes_dir / "test.yml").write_text(yaml.dump(cube_yaml))

        result = validate_cube_yaml_structure(str(tmp_path))

        assert result["pass"] is True
        assert len(result["errors"]) == 0

    def test_validate_cube_yaml_structure_missing_fields(self, tmp_path):
        """Returns pass=False when cube missing name, sql_table, or measures."""
        from src.semantic.cross_tool_validation import validate_cube_yaml_structure

        cubes_dir = tmp_path / "cubes"
        cubes_dir.mkdir()
        # Cube missing sql_table and measures
        cube_yaml = {
            "cubes": [
                {
                    "name": "bad_cube",
                }
            ]
        }
        (cubes_dir / "test.yml").write_text(yaml.dump(cube_yaml))

        result = validate_cube_yaml_structure(str(tmp_path))

        assert result["pass"] is False
        assert len(result["errors"]) > 0

    def test_validate_cube_yaml_structure_measure_missing_fields(self, tmp_path):
        """Returns pass=False when measure missing name, sql, or type."""
        from src.semantic.cross_tool_validation import validate_cube_yaml_structure

        cubes_dir = tmp_path / "cubes"
        cubes_dir.mkdir()
        cube_yaml = {
            "cubes": [
                {
                    "name": "test_cube",
                    "sql_table": "gold.test",
                    "measures": [
                        {"name": "m1"},  # missing sql and type
                    ],
                    "dimensions": [],
                }
            ]
        }
        (cubes_dir / "test.yml").write_text(yaml.dump(cube_yaml))

        result = validate_cube_yaml_structure(str(tmp_path))

        assert result["pass"] is False
        assert len(result["errors"]) > 0


@pytest.mark.unit
class TestCIWorkflowCubeValidation:
    """Tests that CI workflow includes Cube YAML validation step."""

    def test_ci_workflow_has_cube_validation_step(self):
        """ci.yml contains a step that validates Cube YAML definitions."""
        assert CI_WORKFLOW.exists(), f"CI workflow not found at {CI_WORKFLOW}"

        content = CI_WORKFLOW.read_text()

        # Should contain cube-yaml-validate job or step name
        assert "cube-yaml-validate" in content, "CI workflow missing cube-yaml-validate step"

        # Should reference cross_tool_validation module
        assert "cross_tool_validation" in content, "CI workflow missing cross_tool_validation import"
