"""Metric context parser for Cube YAML definitions.

Parses Cube semantic layer YAML files and builds structured text context
for LLM-based NL-to-SQL queries. This module is the AISEM-02 bridge:
the same YAML files that serve Cube (BI tool semantic layer) are parsed
here to provide metric definitions, table references, and dimension
information to the NL-to-SQL prompt.

Usage:
    definitions = load_cube_definitions("semantic/model")
    context = build_metric_context(definitions)
    # Pass `context` to LLM prompt for NL-to-SQL generation
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def load_cube_definitions(model_dir: str) -> list[dict]:
    """Load and parse all Cube YAML definitions from a model directory.

    Scans for *.yml files in the cubes/ and views/ subdirectories,
    parses each with yaml.safe_load, and returns a flat list of
    definition dicts annotated with type ("cube" or "view").

    Args:
        model_dir: Path to the Cube model directory (e.g., "semantic/model").

    Returns:
        List of dicts, each with at minimum "name" and "type" keys.
        Cube dicts include "sql_table", "measures", "dimensions".
        View dicts include "includes".
    """
    model_path = Path(model_dir)
    definitions: list[dict] = []

    # Parse cube definitions
    cubes_dir = model_path / "cubes"
    if cubes_dir.exists():
        for yml_file in sorted(cubes_dir.glob("*.yml")):
            try:
                data = yaml.safe_load(yml_file.read_text())
                for cube in data.get("cubes", []):
                    cube["type"] = "cube"
                    definitions.append(cube)
            except Exception:
                logger.warning("Failed to parse cube YAML: %s", yml_file, exc_info=True)

    # Parse view definitions
    views_dir = model_path / "views"
    if views_dir.exists():
        for yml_file in sorted(views_dir.glob("*.yml")):
            try:
                data = yaml.safe_load(yml_file.read_text())
                for view in data.get("views", []):
                    view["type"] = "view"
                    definitions.append(view)
            except Exception:
                logger.warning("Failed to parse view YAML: %s", yml_file, exc_info=True)

    logger.info(
        "Loaded %d definitions (%d cubes, %d views) from %s",
        len(definitions),
        sum(1 for d in definitions if d["type"] == "cube"),
        sum(1 for d in definitions if d["type"] == "view"),
        model_dir,
    )
    return definitions


def build_metric_context(definitions: list[dict]) -> str:
    """Build structured text context from Cube definitions for LLM prompts.

    Formats cube and view definitions into a structured text format
    with TABLE, METRIC, and DIMENSION lines that an LLM can use to
    generate accurate SQL queries.

    Args:
        definitions: List of definition dicts from load_cube_definitions().

    Returns:
        Structured text string suitable for inclusion in NL-to-SQL prompts.
    """
    lines: list[str] = []
    lines.append("=== AVAILABLE METRICS AND DIMENSIONS ===")
    lines.append("")

    for defn in definitions:
        if defn.get("type") == "cube":
            sql_table = defn.get("sql_table", "unknown")
            lines.append(f"TABLE: {sql_table}")
            lines.append(f"  CUBE: {defn['name']}")

            if defn.get("description"):
                desc = defn["description"].strip().replace("\n", " ")
                lines.append(f"  DESCRIPTION: {desc}")

            # Measures
            for measure in defn.get("measures", []):
                measure_type = measure.get("type", "unknown")
                lines.append(f"  METRIC: {measure['name']} (type={measure_type})")
                if measure.get("description"):
                    desc = measure["description"].strip().replace("\n", " ")
                    lines.append(f"    DESCRIPTION: {desc}")
                if measure.get("meta", {}).get("glossary_term"):
                    lines.append(f"    GLOSSARY: {measure['meta']['glossary_term']}")

            # Dimensions
            for dimension in defn.get("dimensions", []):
                dim_type = dimension.get("type", "string")
                lines.append(f"  DIMENSION: {dimension['name']} (type={dim_type})")
                if dimension.get("description"):
                    desc = dimension["description"].strip().replace("\n", " ")
                    lines.append(f"    DESCRIPTION: {desc}")

            lines.append("")

        elif defn.get("type") == "view":
            lines.append(f"VIEW: {defn['name']}")
            if defn.get("description"):
                desc = defn["description"].strip().replace("\n", " ")
                lines.append(f"  DESCRIPTION: {desc}")

            for include in defn.get("includes", []):
                for member in include.get("members", []):
                    lines.append(f"  INCLUDES: {member}")

            lines.append("")

    return "\n".join(lines)
