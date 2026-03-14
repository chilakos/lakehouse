#!/usr/bin/env python3
"""Render SWOT HTML deliverables from YAML data files + Jinja2 templates.

This module provides the HTML rendering pipeline for the lakehouse documentation.
It extracts platform versions from docker-compose.yml and renders SWOT analysis
documents as standalone HTML files with embedded CSS.

Usage:
    # As CLI:
    python docs/render_html.py

    # As module:
    from docs.render_html import render_swots, extract_versions
"""

from __future__ import annotations

from datetime import date, timezone, datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "docs" / "templates"
SWOT_DATA_DIR = PROJECT_ROOT / "docs" / "swot" / "data"
SWOT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "swot"
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.yml"


def extract_versions(compose_path: Path | str | None = None) -> dict[str, dict[str, str]]:
    """Extract service versions from docker-compose.yml image tags.

    Args:
        compose_path: Path to docker-compose.yml. Defaults to PROJECT_ROOT/docker-compose.yml.

    Returns:
        Dict mapping service name to {"version": version_string, "image": image_name}.
    """
    if compose_path is None:
        compose_path = COMPOSE_PATH
    compose_path = Path(compose_path)

    compose = yaml.safe_load(compose_path.read_text())
    versions: dict[str, dict[str, str]] = {}

    for service_name, config in compose.get("services", {}).items():
        image = config.get("image", "")
        if ":" in image:
            image_name, version = image.rsplit(":", 1)
            versions[service_name] = {
                "image": image_name,
                "version": version,
            }

    return versions


def _create_jinja_env(template_dir: Path | None = None) -> Environment:
    """Create a Jinja2 Environment configured for SWOT rendering.

    Args:
        template_dir: Path to templates directory. Defaults to TEMPLATE_DIR.

    Returns:
        Configured Jinja2 Environment.
    """
    if template_dir is None:
        template_dir = TEMPLATE_DIR

    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,  # HTML templates manage their own escaping
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_swots(
    data_dir: Path | None = None,
    template_dir: Path | None = None,
    output_dir: Path | None = None,
    compose_path: Path | str | None = None,
) -> list[Path]:
    """Render all SWOT YAML data files to standalone HTML.

    Loads each .yml file from data_dir, renders via base_swot.html template,
    and writes to output_dir as {name}-swot.html.

    Args:
        data_dir: Directory containing SWOT YAML data files.
        template_dir: Directory containing Jinja2 templates.
        output_dir: Directory for rendered HTML output.
        compose_path: Path to docker-compose.yml for version extraction.

    Returns:
        List of Paths to rendered HTML files.
    """
    if data_dir is None:
        data_dir = SWOT_DATA_DIR
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    if output_dir is None:
        output_dir = SWOT_OUTPUT_DIR

    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = _create_jinja_env(template_dir)
    versions = extract_versions(compose_path)
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    template = env.get_template("base_swot.html")
    rendered_files: list[Path] = []

    for data_file in sorted(data_dir.glob("*.yml")):
        swot_data = yaml.safe_load(data_file.read_text())
        if swot_data is None:
            continue

        html = template.render(
            **swot_data,
            versions=versions,
            generation_date=generation_date,
        )

        output_name = data_file.stem + "-swot.html"
        output_path = output_dir / output_name
        output_path.write_text(html)
        rendered_files.append(output_path)
        print(f"  Rendered: {output_name}")

    return rendered_files


def render_index(
    swot_data_files: list[Path] | None = None,
    template_dir: Path | None = None,
    output_dir: Path | None = None,
    compose_path: Path | str | None = None,
) -> Path:
    """Render the cross-SWOT index page from all YAML data files.

    Args:
        swot_data_files: List of SWOT YAML data file paths. Defaults to all in SWOT_DATA_DIR.
        template_dir: Directory containing Jinja2 templates.
        output_dir: Directory for rendered HTML output.
        compose_path: Path to docker-compose.yml for version extraction.

    Returns:
        Path to the rendered index.html file.
    """
    if swot_data_files is None:
        swot_data_files = sorted(SWOT_DATA_DIR.glob("*.yml"))
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    if output_dir is None:
        output_dir = SWOT_OUTPUT_DIR

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = _create_jinja_env(template_dir)
    versions = extract_versions(compose_path)
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load all SWOT summaries for index cards
    swot_summaries = []
    for data_file in swot_data_files:
        data = yaml.safe_load(Path(data_file).read_text())
        if data is None:
            continue
        swot_summaries.append({
            "title": data.get("title", "Untitled"),
            "subtitle": data.get("subtitle", ""),
            "status": data.get("status", "undecided"),
            "decision": data.get("decision", ""),
            "filename": data_file.stem + "-swot.html",
            "executive_summary": (data.get("executive_summary", "") or "")[:200],
            "strengths_count": len(data.get("strengths", [])),
            "weaknesses_count": len(data.get("weaknesses", [])),
            "opportunities_count": len(data.get("opportunities", [])),
            "threats_count": len(data.get("threats", [])),
        })

    template = env.get_template("base_index.html")
    html = template.render(
        title="SWOT Analyses Index",
        subtitle="Strategic Technology Decision Documentation",
        date=generation_date,
        swot_summaries=swot_summaries,
        versions=versions,
        generation_date=generation_date,
        next_review="2026-Q2",
    )

    output_path = output_dir / "index.html"
    output_path.write_text(html)
    print(f"  Rendered: index.html")
    return output_path


if __name__ == "__main__":
    print("Rendering SWOT analyses...")
    rendered = render_swots()
    print(f"\n  {len(rendered)} SWOT file(s) rendered.")

    if rendered:
        print("\nRendering index page...")
        index_path = render_index()
        print(f"\n  Index: {index_path}")

    print("\nDone.")
