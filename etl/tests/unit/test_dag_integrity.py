"""DAG integrity tests ensuring all Airflow DAGs load without import errors.

Validates that:
- All Python files in the dags/ directory import without errors
- Each DAG file defines at least one DAG object
- DAG IDs are unique across all files
- Default args follow locked decisions (retries >= 3, exponential backoff)

Gracefully skips if Airflow is not installed.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Gracefully skip entire module if airflow is not installed
airflow = pytest.importorskip("airflow", reason="Airflow not installed -- skipping DAG integrity tests")

DAGS_DIR = Path(__file__).resolve().parents[2] / "dags"


def _mock_airflow_variables():
    """Mock Airflow Variable to avoid DB dependency during DAG import."""
    from unittest.mock import patch

    mock_var = MagicMock()
    mock_var.get.return_value = "http://localhost:19120"

    # Also mock Variable.get at class level
    return patch("airflow.models.Variable.get", return_value="http://localhost:19120")


def _load_dag_module(dag_file: Path):
    """Import a DAG file as a module and return it."""
    module_name = f"test_dag_load_{dag_file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, dag_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _get_dags_from_module(module):
    """Extract DAG objects from a loaded module."""
    from airflow.models import DAG

    return [obj for obj in vars(module).values() if isinstance(obj, DAG)]


def _get_dag_files() -> list[Path]:
    """Return all Python files in the dags directory (excluding __init__.py)."""
    if not DAGS_DIR.exists():
        return []
    return [f for f in DAGS_DIR.glob("*.py") if f.name != "__init__.py"]


@pytest.mark.unit
class TestDagIntegrity:
    """Test suite for DAG loading and structural validation."""

    def test_dags_directory_exists(self):
        """The dags/ directory must exist."""
        assert DAGS_DIR.exists(), f"DAGs directory not found: {DAGS_DIR}"

    def test_dag_files_exist(self):
        """At least one DAG file must exist."""
        dag_files = _get_dag_files()
        assert len(dag_files) > 0, "No DAG files found in dags/ directory"

    def test_dag_files_load_without_errors(self):
        """Every DAG file must import without raising exceptions."""
        dag_files = _get_dag_files()
        assert dag_files, "No DAG files to test"

        for dag_file in dag_files:
            with _mock_airflow_variables():
                try:
                    _load_dag_module(dag_file)
                except Exception as exc:
                    pytest.fail(f"DAG file {dag_file.name} failed to import: {exc}")

    def test_each_dag_file_defines_dag(self):
        """Each DAG file must define at least one DAG object."""
        dag_files = _get_dag_files()
        assert dag_files, "No DAG files to test"

        for dag_file in dag_files:
            with _mock_airflow_variables():
                module = _load_dag_module(dag_file)
                dags = _get_dags_from_module(module)
                assert len(dags) > 0, f"DAG file {dag_file.name} does not define any DAG objects"

    def test_dag_ids_are_unique(self):
        """All DAG IDs across all files must be unique."""
        dag_files = _get_dag_files()
        assert dag_files, "No DAG files to test"

        all_dag_ids: list[str] = []
        for dag_file in dag_files:
            with _mock_airflow_variables():
                module = _load_dag_module(dag_file)
                dags = _get_dags_from_module(module)
                all_dag_ids.extend(dag.dag_id for dag in dags)

        seen = set()
        duplicates = set()
        for dag_id in all_dag_ids:
            if dag_id in seen:
                duplicates.add(dag_id)
            seen.add(dag_id)

        assert not duplicates, f"Duplicate DAG IDs found: {duplicates}"

    def test_default_args_retry_policy(self):
        """All DAGs must have retries >= 3 per locked decision."""
        dag_files = _get_dag_files()
        assert dag_files, "No DAG files to test"

        for dag_file in dag_files:
            with _mock_airflow_variables():
                module = _load_dag_module(dag_file)
                dags = _get_dags_from_module(module)
                for dag in dags:
                    default_args = dag.default_args or {}
                    retries = default_args.get("retries", 0)
                    assert retries >= 3, f"DAG '{dag.dag_id}' has retries={retries}, expected >= 3 (locked decision)"

    def test_default_args_exponential_backoff(self):
        """All DAGs must have retry_exponential_backoff=True per locked decision."""
        dag_files = _get_dag_files()
        assert dag_files, "No DAG files to test"

        for dag_file in dag_files:
            with _mock_airflow_variables():
                module = _load_dag_module(dag_file)
                dags = _get_dags_from_module(module)
                for dag in dags:
                    default_args = dag.default_args or {}
                    assert default_args.get("retry_exponential_backoff") is True, (
                        f"DAG '{dag.dag_id}' missing retry_exponential_backoff=True (locked decision)"
                    )
