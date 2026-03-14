#!/usr/bin/env python3
"""Render SWOT and Architecture HTML deliverables from YAML data files + Jinja2 templates.

This module provides the HTML rendering pipeline for the lakehouse documentation.
It extracts platform versions and service metadata from docker-compose.yml, and
renders SWOT analyses and architecture pages as standalone HTML files with embedded CSS.

Usage:
    # As CLI:
    python docs/render_html.py

    # As module:
    from docs.render_html import render_swots, render_architecture, extract_versions, extract_services
"""

from __future__ import annotations

import subprocess
import tempfile
from datetime import date, timezone, datetime
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "docs" / "templates"
SWOT_DATA_DIR = PROJECT_ROOT / "docs" / "swot" / "data"
SWOT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "swot"
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.yml"
ARCH_DIAGRAM_DIR = PROJECT_ROOT / "docs" / "architecture" / "diagrams"
ARCH_DATA_DIR = PROJECT_ROOT / "docs" / "architecture" / "data"
ARCH_OUTPUT_DIR = PROJECT_ROOT / "docs" / "architecture"


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


def extract_services(
    compose_path: Path | str | None = None,
    overrides_path: Path | str | None = None,
) -> dict[str, dict]:
    """Extract full service metadata from docker-compose.yml, merged with overrides.

    Parses docker-compose.yml for image, version, ports, healthcheck, depends_on
    per service. If overrides_path is provided, merges with services.yml to add
    description, protocol, primary_port, and layer assignment, then filters out
    services listed in exclude_from_diagrams.

    Args:
        compose_path: Path to docker-compose.yml. Defaults to COMPOSE_PATH.
        overrides_path: Path to services.yml override file. If None, returns raw
            docker-compose data without layer/description/protocol enrichment.

    Returns:
        Dict mapping service name to enriched metadata dict.
    """
    if compose_path is None:
        compose_path = COMPOSE_PATH
    compose_path = Path(compose_path)

    compose = yaml.safe_load(compose_path.read_text())
    services: dict[str, dict] = {}

    for name, config in compose.get("services", {}).items():
        image = config.get("image", "")
        if ":" in image:
            image_name, version = image.rsplit(":", 1)
        else:
            image_name = image
            version = "custom"

        ports = config.get("ports", [])
        hc = config.get("healthcheck", {})
        hc_test = hc.get("test", [])
        if isinstance(hc_test, list):
            healthcheck = " ".join(hc_test)
        else:
            healthcheck = str(hc_test) if hc_test else ""

        # depends_on can be a dict (with conditions) or a list
        deps_raw = config.get("depends_on", {})
        if isinstance(deps_raw, dict):
            deps = list(deps_raw.keys())
        elif isinstance(deps_raw, list):
            deps = list(deps_raw)
        else:
            deps = []

        services[name] = {
            "image": image_name,
            "version": version,
            "ports": [str(p) for p in ports],
            "healthcheck": healthcheck,
            "depends_on": deps,
        }

    if overrides_path is not None:
        overrides_path = Path(overrides_path)
        if overrides_path.exists():
            overrides = yaml.safe_load(overrides_path.read_text())

            # Build reverse lookup: service name -> layer slug
            layer_lookup: dict[str, str] = {}
            for layer_slug, layer_info in overrides.get("layers", {}).items():
                for svc_name in layer_info.get("services", []):
                    layer_lookup[svc_name] = layer_slug

            # Merge per-service overrides
            svc_overrides = overrides.get("services", {})
            for name in list(services.keys()):
                if name in svc_overrides:
                    services[name].update(svc_overrides[name])
                # Assign layer from layers config
                if name in layer_lookup:
                    services[name]["layer"] = layer_lookup[name]

            # Filter out excluded services
            for excluded in overrides.get("exclude_from_diagrams", []):
                services.pop(excluded, None)

    return services


def render_mermaid_to_svg(mmd_path: Path) -> str:
    """Render a .mmd Mermaid file to SVG string using mermaid-cli.

    Shells out to `npx -p @mermaid-js/mermaid-cli mmdc` to convert the Mermaid
    source file to SVG. Returns the SVG content as a string.

    Args:
        mmd_path: Path to the .mmd Mermaid source file.

    Returns:
        SVG content as a string.

    Raises:
        RuntimeError: If mmdc fails or is not available.
    """
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp:
        tmp_svg = Path(tmp.name)
    try:
        result = subprocess.run(
            [
                "npx", "-p", "@mermaid-js/mermaid-cli", "mmdc",
                "-i", str(mmd_path),
                "-o", str(tmp_svg),
                "-t", "neutral",
                "-b", "transparent",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"mmdc failed: {result.stderr}")
        return tmp_svg.read_text()
    finally:
        tmp_svg.unlink(missing_ok=True)


def _placeholder_svg(message: str = "Mermaid CLI required") -> str:
    """Return a placeholder SVG with an informational message.

    Used when mmdc is not available or fails during rendering.
    """
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 200">'
        '<rect width="600" height="200" fill="#f8fafc" stroke="#1a2332" stroke-width="2" rx="8"/>'
        '<text x="300" y="90" text-anchor="middle" font-family="sans-serif" '
        'font-size="16" fill="#64748b">Diagram Placeholder</text>'
        f'<text x="300" y="120" text-anchor="middle" font-family="sans-serif" '
        f'font-size="13" fill="#94a3b8">{message}</text>'
        '</svg>'
    )


def render_architecture(
    diagram_dir: Path | None = None,
    data_dir: Path | None = None,
    template_dir: Path | None = None,
    output_dir: Path | None = None,
    compose_path: Path | str | None = None,
) -> list[Path]:
    """Render architecture HTML pages from Mermaid diagrams and YAML data.

    Produces:
    - marketecture.html: Executive overview with stats banner, capability groups, Mermaid SVG
    - detailed-architecture.html: Service reference with HTML grid, CSS hover tooltips

    Args:
        diagram_dir: Directory containing .mmd Mermaid source files.
        data_dir: Directory containing services.yml and environments.yml.
        template_dir: Directory containing Jinja2 templates.
        output_dir: Directory for rendered HTML output.
        compose_path: Path to docker-compose.yml for service metadata extraction.

    Returns:
        List of Paths to rendered HTML files.
    """
    if diagram_dir is None:
        diagram_dir = ARCH_DIAGRAM_DIR
    if data_dir is None:
        data_dir = ARCH_DATA_DIR
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    if output_dir is None:
        output_dir = ARCH_OUTPUT_DIR

    diagram_dir = Path(diagram_dir)
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = _create_jinja_env(template_dir)
    versions = extract_versions(compose_path)
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Extract services with overrides
    overrides_path = data_dir / "services.yml"
    services = extract_services(compose_path, overrides_path)

    # Load environments data
    env_file = data_dir / "environments.yml"
    environments = []
    if env_file.exists():
        env_data = yaml.safe_load(env_file.read_text())
        environments = env_data.get("environments", [])

    # Load layer definitions from services.yml
    layers_config = {}
    if overrides_path.exists():
        overrides = yaml.safe_load(overrides_path.read_text())
        layers_config = overrides.get("layers", {})

    # Group services by layer
    services_by_layer: dict[str, list[dict]] = {}
    for layer_slug, layer_info in layers_config.items():
        layer_services = []
        for svc_name in layer_info.get("services", []):
            if svc_name in services:
                svc = dict(services[svc_name])
                svc["name"] = svc_name
                layer_services.append(svc)
        if layer_services:
            services_by_layer[layer_slug] = layer_services

    # Render Mermaid diagrams to SVG (with graceful fallback)
    svg_content: dict[str, str] = {}
    for mmd_file in sorted(diagram_dir.glob("*.mmd")):
        try:
            svg_content[mmd_file.stem] = render_mermaid_to_svg(mmd_file)
        except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
            print(f"  Warning: mmdc failed for {mmd_file.name}: {exc}")
            svg_content[mmd_file.stem] = _placeholder_svg(
                f"Install @mermaid-js/mermaid-cli to render {mmd_file.name}"
            )

    rendered_files: list[Path] = []
    template = env.get_template("base_architecture.html")

    # --- Marketecture page ---
    marketecture_html = template.render(
        page_type="marketecture",
        title="Platform Marketecture",
        subtitle="Enterprise Lakehouse Architecture Overview",
        svg_diagram=svg_content.get("marketecture", _placeholder_svg()),
        services=services,
        services_by_layer=services_by_layer,
        layers=layers_config,
        environments=environments,
        versions=versions,
        generation_date=generation_date,
    )
    market_path = output_dir / "marketecture.html"
    market_path.write_text(marketecture_html)
    rendered_files.append(market_path)
    print(f"  Rendered: marketecture.html")

    # --- Detailed architecture page ---
    detailed_html = template.render(
        page_type="detailed",
        title="Detailed Service Architecture",
        subtitle="Complete Service Reference with Ports, Protocols, and Dependencies",
        svg_diagram=svg_content.get("detailed-architecture", _placeholder_svg()),
        services=services,
        services_by_layer=services_by_layer,
        layers=layers_config,
        environments=environments,
        versions=versions,
        generation_date=generation_date,
    )
    detailed_path = output_dir / "detailed-architecture.html"
    detailed_path.write_text(detailed_html)
    rendered_files.append(detailed_path)
    print(f"  Rendered: detailed-architecture.html")

    return rendered_files


if __name__ == "__main__":
    print("Rendering SWOT analyses...")
    rendered = render_swots()
    print(f"\n  {len(rendered)} SWOT file(s) rendered.")

    if rendered:
        print("\nRendering index page...")
        index_path = render_index()
        print(f"\n  Index: {index_path}")

    print("\nRendering architecture pages...")
    arch_rendered = render_architecture()
    print(f"\n  {len(arch_rendered)} architecture page(s) rendered.")

    print("\nDone.")
