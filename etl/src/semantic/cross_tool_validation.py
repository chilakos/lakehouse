"""Cross-tool validation for Cube semantic layer.

Provides three validation capabilities:
1. Metric consistency: Compares query results between Cube SQL API and
   direct Trino queries to ensure the semantic layer returns identical values.
2. Glossary linking: Validates that all meta.glossary_term values in Cube
   YAML definitions reference real terms in the glossary-seed.json.
3. YAML structure: Validates that Cube YAML files have required fields
   (name, sql_table, measures with name/sql/type).

Usage:
    # Cross-tool metric consistency
    result = validate_metric_consistency(trino_conn, cube_conn, queries)

    # Glossary link validation
    result = validate_glossary_links("semantic/model", "glossary-seed.json")

    # YAML structure validation
    result = validate_cube_yaml_structure("semantic/model")
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Tolerance for Decimal comparison (4 decimal places)
_DECIMAL_TOLERANCE = Decimal("0.0001")


def validate_metric_consistency(
    trino_conn: Any,
    cube_conn: Any,
    queries: list[dict[str, str]],
) -> dict[str, Any]:
    """Compare query results between Cube SQL API and direct Trino queries.

    For each query dict (has ``name``, ``trino_sql``, ``cube_sql``), executes
    both queries and compares result sets. Decimal values are compared with
    4-decimal-place tolerance.

    Args:
        trino_conn: DBAPI2 connection to Trino.
        cube_conn: DBAPI2 connection to Cube SQL API.
        queries: List of query dicts with ``name``, ``trino_sql``, ``cube_sql``.

    Returns:
        Dict with ``pass`` (bool), ``results`` (list of per-query results),
        and ``mismatches`` (list of queries that did not match).
    """
    results: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []

    for query in queries:
        name = query["name"]
        trino_sql = query["trino_sql"]
        cube_sql = query["cube_sql"]

        # Execute Trino query
        trino_rows: list[tuple] = []
        try:
            with trino_conn.cursor() as cur:
                cur.execute(trino_sql)
                trino_rows = cur.fetchall()
        except Exception as exc:
            logger.warning("Trino query failed for %s: %s", name, exc)
            trino_rows = []

        # Execute Cube query
        cube_rows: list[tuple] = []
        try:
            with cube_conn.cursor() as cur:
                cur.execute(cube_sql)
                cube_rows = cur.fetchall()
        except Exception as exc:
            logger.warning("Cube query failed for %s: %s", name, exc)
            cube_rows = []

        # Compare results
        match = _compare_result_sets(trino_rows, cube_rows)

        result_entry = {
            "name": name,
            "match": match,
            "trino_row_count": len(trino_rows),
            "cube_row_count": len(cube_rows),
        }
        results.append(result_entry)

        if not match:
            mismatch_entry = {
                "name": name,
                "trino_rows": trino_rows,
                "cube_rows": cube_rows,
                "trino_row_count": len(trino_rows),
                "cube_row_count": len(cube_rows),
            }
            mismatches.append(mismatch_entry)

    all_pass = len(mismatches) == 0

    logger.info(
        "Metric consistency validation: %s (%d/%d queries matched)",
        "PASS" if all_pass else "FAIL",
        len(results) - len(mismatches),
        len(results),
    )

    return {
        "pass": all_pass,
        "results": results,
        "mismatches": mismatches,
    }


def _compare_result_sets(
    rows_a: list[tuple],
    rows_b: list[tuple],
) -> bool:
    """Compare two result sets with Decimal tolerance.

    Sorts both result sets and compares element-by-element. Decimal values
    are compared with 4-decimal-place tolerance. Non-Decimal values use
    exact equality.

    Args:
        rows_a: First result set.
        rows_b: Second result set.

    Returns:
        True if result sets match within tolerance.
    """
    if len(rows_a) != len(rows_b):
        return False

    try:
        sorted_a = sorted(rows_a)
        sorted_b = sorted(rows_b)
    except TypeError:
        sorted_a = rows_a
        sorted_b = rows_b

    for row_a, row_b in zip(sorted_a, sorted_b, strict=False):
        if len(row_a) != len(row_b):
            return False
        for val_a, val_b in zip(row_a, row_b, strict=False):
            if isinstance(val_a, Decimal) and isinstance(val_b, Decimal):
                if abs(val_a - val_b) > _DECIMAL_TOLERANCE:
                    return False
            elif val_a != val_b:
                return False

    return True


def validate_glossary_links(
    model_dir: str,
    glossary_path: str,
) -> dict[str, Any]:
    """Validate that all meta.glossary_term values exist in the glossary.

    Parses all Cube YAML files in the model directory, extracts
    ``meta.glossary_term`` values from measures, loads glossary-seed.json,
    and checks every term exists.

    Args:
        model_dir: Path to the Cube model directory (e.g., ``semantic/model``).
        glossary_path: Path to the glossary-seed.json file.

    Returns:
        Dict with ``pass`` (bool), ``valid_links`` (list of valid terms),
        and ``missing_terms`` (list of terms not found in glossary).
    """
    model_path = Path(model_dir)

    # Load glossary terms
    with open(glossary_path) as f:
        glossary_data = json.load(f)

    glossary_terms = {term["name"] for term in glossary_data.get("terms", [])}

    # Extract glossary_term values from YAML files
    found_terms: list[str] = []
    cubes_dir = model_path / "cubes"
    if cubes_dir.exists():
        for yml_file in sorted(cubes_dir.glob("*.yml")):
            try:
                data = yaml.safe_load(yml_file.read_text())
                for cube in data.get("cubes", []):
                    for measure in cube.get("measures", []):
                        meta = measure.get("meta", {})
                        term = meta.get("glossary_term")
                        if term:
                            found_terms.append(term)
            except Exception:
                logger.warning(
                    "Failed to parse YAML for glossary check: %s",
                    yml_file,
                    exc_info=True,
                )

    # Check each term exists in glossary
    valid_links: list[str] = []
    missing_terms: list[str] = []

    for term in found_terms:
        if term in glossary_terms:
            valid_links.append(term)
        else:
            missing_terms.append(term)

    all_pass = len(missing_terms) == 0

    logger.info(
        "Glossary link validation: %s (%d valid, %d missing)",
        "PASS" if all_pass else "FAIL",
        len(valid_links),
        len(missing_terms),
    )

    return {
        "pass": all_pass,
        "valid_links": valid_links,
        "missing_terms": missing_terms,
    }


def validate_cube_yaml_structure(
    model_dir: str,
) -> dict[str, Any]:
    """Validate Cube YAML files have required structural fields.

    For each YAML file in the cubes/ subdirectory, validates:
    (a) ``cubes`` key exists
    (b) Each cube has ``name`` and ``sql_table``
    (c) Each cube has at least one measure
    (d) Each measure has ``name``, ``sql``, ``type``

    Also checks views/ subdirectory for ``views`` key existence.

    Args:
        model_dir: Path to the Cube model directory (e.g., ``semantic/model``).

    Returns:
        Dict with ``pass`` (bool) and ``errors`` (list of error strings).
    """
    model_path = Path(model_dir)
    errors: list[str] = []

    # Validate cube YAML files
    cubes_dir = model_path / "cubes"
    if cubes_dir.exists():
        for yml_file in sorted(cubes_dir.glob("*.yml")):
            try:
                data = yaml.safe_load(yml_file.read_text())
            except Exception as exc:
                errors.append(f"{yml_file.name}: YAML parse error: {exc}")
                continue

            if "cubes" not in data:
                errors.append(f"{yml_file.name}: missing 'cubes' key")
                continue

            for cube in data["cubes"]:
                cube_name = cube.get("name", "<unnamed>")

                if "name" not in cube:
                    errors.append(f"{yml_file.name}: cube missing 'name'")

                if "sql_table" not in cube:
                    errors.append(f"{yml_file.name}: cube '{cube_name}' missing 'sql_table'")

                measures = cube.get("measures")
                if not measures:
                    errors.append(f"{yml_file.name}: cube '{cube_name}' has no measures")
                else:
                    for measure in measures:
                        m_name = measure.get("name", "<unnamed>")
                        missing_fields = []
                        for field in ("name", "sql", "type"):
                            if field not in measure:
                                missing_fields.append(field)
                        if missing_fields:
                            errors.append(
                                f"{yml_file.name}: cube '{cube_name}' "
                                f"measure '{m_name}' missing: {', '.join(missing_fields)}"
                            )

    # Validate view YAML files
    views_dir = model_path / "views"
    if views_dir.exists():
        for yml_file in sorted(views_dir.glob("*.yml")):
            try:
                data = yaml.safe_load(yml_file.read_text())
            except Exception as exc:
                errors.append(f"{yml_file.name}: YAML parse error: {exc}")
                continue

            if "views" not in data:
                errors.append(f"{yml_file.name}: missing 'views' key")

    all_pass = len(errors) == 0

    logger.info(
        "YAML structure validation: %s (%d errors)",
        "PASS" if all_pass else "FAIL",
        len(errors),
    )

    return {
        "pass": all_pass,
        "errors": errors,
    }
