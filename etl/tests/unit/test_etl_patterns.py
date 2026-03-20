"""Meta-tests for ETL patterns documentation.

Validates that docs/etl-patterns.md:
- Exists
- Contains all required sections (8 sections)
- Code examples reference importable modules

@pytest.mark.unit
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCS_DIR = Path(__file__).resolve().parents[3] / "docs"
ETL_PATTERNS_PATH = DOCS_DIR / "etl-patterns.md"

# Required section headings (## level)
REQUIRED_SECTIONS = [
    "1. Architecture Overview",
    "2. Creating a New Pipeline",
    "3. Quality Checks",
    "4. DAG Patterns",
    "5. Incremental Loading",
    "6. Mainframe Sources",
    "7. Testing",
    "8. Job Inventory",
]


@pytest.mark.unit
class TestEtlPatternsDoc:
    """Tests for ETL patterns documentation completeness and accuracy."""

    def test_etl_patterns_file_exists(self):
        """docs/etl-patterns.md must exist."""
        assert ETL_PATTERNS_PATH.exists(), f"ETL patterns documentation not found at {ETL_PATTERNS_PATH}"

    def test_etl_patterns_has_all_sections(self):
        """All 8 required sections must be present."""
        content = ETL_PATTERNS_PATH.read_text()
        for section in REQUIRED_SECTIONS:
            assert section in content, f"Missing required section: '{section}' in etl-patterns.md"

    def test_etl_patterns_has_minimum_length(self):
        """Documentation must be at least 100 lines (per must_haves)."""
        lines = ETL_PATTERNS_PATH.read_text().splitlines()
        assert len(lines) >= 100, f"etl-patterns.md has {len(lines)} lines, expected >= 100"

    def test_etl_patterns_has_code_examples(self):
        """Documentation must contain Python code examples."""
        content = ETL_PATTERNS_PATH.read_text()
        code_blocks = re.findall(r"```python\n(.*?)```", content, re.DOTALL)
        assert len(code_blocks) >= 3, f"Expected at least 3 Python code examples, found {len(code_blocks)}"

    def test_code_examples_reference_importable_modules(self):
        """Python import statements in code examples must reference real modules."""
        content = ETL_PATTERNS_PATH.read_text()
        code_blocks = re.findall(r"```python\n(.*?)```", content, re.DOTALL)

        # Extract all import statements from code blocks
        import_lines = []
        for block in code_blocks:
            for line in block.splitlines():
                stripped = line.strip()
                if stripped.startswith("from src.") or stripped.startswith("import src."):
                    import_lines.append(stripped)

        assert len(import_lines) > 0, "No src.* imports found in code examples"

        # Verify key module paths exist on disk
        src_root = Path(__file__).resolve().parents[2] / "src"
        for line in import_lines:
            # Extract module path from "from src.foo.bar import Baz"
            match = re.match(r"from (src\.\S+) import", line)
            if match:
                module_path = match.group(1).replace(".", "/")
                # Check if it's a package (__init__.py) or module (.py)
                py_file = src_root.parent / f"{module_path}.py"
                init_file = src_root.parent / module_path / "__init__.py"
                assert py_file.exists() or init_file.exists(), (
                    f"Import '{line}' references non-existent module: neither {py_file} nor {init_file} exists"
                )

    def test_documentation_mentions_financial_precision(self):
        """Documentation must mention DecimalType for financial precision."""
        content = ETL_PATTERNS_PATH.read_text()
        assert "DecimalType" in content, "Documentation must mention DecimalType for financial precision"

    def test_documentation_mentions_openlineage(self):
        """Documentation must mention OpenLineage for lineage tracking."""
        content = ETL_PATTERNS_PATH.read_text()
        assert "OpenLineage" in content, "Documentation must mention OpenLineage for lineage tracking"
