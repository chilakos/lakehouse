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

import ast
import json
import subprocess
import tempfile
import warnings
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
DEV_DATA_DIR = PROJECT_ROOT / "docs" / "developer" / "data"
DEV_DIAGRAM_DIR = PROJECT_ROOT / "docs" / "developer" / "diagrams"
DEV_OUTPUT_DIR = PROJECT_ROOT / "docs" / "developer"
CATALOG_DATA_DIR = PROJECT_ROOT / "docs" / "catalog" / "data"
CATALOG_DIAGRAM_DIR = PROJECT_ROOT / "docs" / "catalog" / "diagrams"
CATALOG_OUTPUT_DIR = PROJECT_ROOT / "docs" / "catalog"
GLOSSARY_SEED_PATH = PROJECT_ROOT / "infra" / "docker" / "openmetadata" / "glossary-seed.json"
FRESHNESS_TRACKER_PATH = PROJECT_ROOT / "etl" / "src" / "governance" / "freshness_tracker.py"


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

    # --- Data flow page (ARCH-03) ---
    data_flow_html = template.render(
        page_type="data-flow",
        title="Data Flow Architecture",
        subtitle="Bronze - Silver - Gold Medallion Pipeline from Source to Consumer",
        svg_diagram=svg_content.get("data-flow", _placeholder_svg()),
        services=services,
        services_by_layer=services_by_layer,
        layers=layers_config,
        environments=environments,
        versions=versions,
        generation_date=generation_date,
    )
    data_flow_path = output_dir / "data-flow.html"
    data_flow_path.write_text(data_flow_html)
    rendered_files.append(data_flow_path)
    print(f"  Rendered: data-flow.html")

    # --- Service dependency page (ARCH-04) ---
    svc_dep_html = template.render(
        page_type="service-dependency",
        title="Service Dependency Graph",
        subtitle="Infrastructure Dependencies Auto-Generated from docker-compose.yml",
        svg_diagram=svg_content.get("service-dependency", _placeholder_svg()),
        services=services,
        services_by_layer=services_by_layer,
        layers=layers_config,
        environments=environments,
        versions=versions,
        generation_date=generation_date,
    )
    svc_dep_path = output_dir / "service-dependency.html"
    svc_dep_path.write_text(svc_dep_html)
    rendered_files.append(svc_dep_path)
    print(f"  Rendered: service-dependency.html")

    # --- Security layer page (ARCH-05) ---
    security_html = template.render(
        page_type="security-layer",
        title="Security Layer Architecture",
        subtitle="Apache Ranger RBAC, Column Masking, and Row-Level Security",
        svg_diagram=svg_content.get("security-layer", _placeholder_svg()),
        services=services,
        services_by_layer=services_by_layer,
        layers=layers_config,
        environments=environments,
        versions=versions,
        generation_date=generation_date,
    )
    security_path = output_dir / "security-layer.html"
    security_path.write_text(security_html)
    rendered_files.append(security_path)
    print(f"  Rendered: security-layer.html")

    # --- Governance stack page (ARCH-06 + ARCH-07 env table) ---
    governance_html = template.render(
        page_type="governance-stack",
        title="Governance Stack Architecture",
        subtitle="OpenLineage, Marquez, Grafana, and OpenMetadata for BCBS 239 Compliance",
        svg_diagram=svg_content.get("governance-stack", _placeholder_svg()),
        services=services,
        services_by_layer=services_by_layer,
        layers=layers_config,
        environments=environments,
        versions=versions,
        generation_date=generation_date,
    )
    governance_path = output_dir / "governance-stack.html"
    governance_path.write_text(governance_html)
    rendered_files.append(governance_path)
    print(f"  Rendered: governance-stack.html")

    # --- Architecture index page ---
    index_path = render_arch_index(
        template_dir=template_dir,
        output_dir=output_dir,
        compose_path=compose_path,
    )
    rendered_files.append(index_path)

    return rendered_files


def render_arch_index(
    template_dir: Path | None = None,
    output_dir: Path | None = None,
    compose_path: Path | str | None = None,
) -> Path:
    """Render the architecture index page with cards linking to all architecture pages.

    Args:
        template_dir: Directory containing Jinja2 templates.
        output_dir: Directory for rendered HTML output.
        compose_path: Path to docker-compose.yml for version extraction.

    Returns:
        Path to the rendered index.html file.
    """
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    if output_dir is None:
        output_dir = ARCH_OUTPUT_DIR

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = _create_jinja_env(template_dir)
    versions = extract_versions(compose_path)
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    arch_pages = [
        {
            "title": "Marketecture",
            "description": "Executive overview of the lakehouse platform with key statistics, capability groups, and technology landscape.",
            "audience": "Executives",
            "filename": "marketecture.html",
        },
        {
            "title": "Detailed Architecture",
            "description": "Complete service reference with ports, protocols, health checks, and dependencies for all 23 platform services.",
            "audience": "Engineers",
            "filename": "detailed-architecture.html",
        },
        {
            "title": "Data Flow",
            "description": "Bronze-Silver-Gold medallion pipeline from source ingestion through quality checks to business-ready analytics.",
            "audience": "Engineers",
            "filename": "data-flow.html",
        },
        {
            "title": "Service Dependencies",
            "description": "Infrastructure dependency graph auto-generated from docker-compose.yml depends_on relationships.",
            "audience": "Engineers",
            "filename": "service-dependency.html",
        },
        {
            "title": "Security Layer",
            "description": "Apache Ranger RBAC architecture with column-level masking, row-level security, and audit trail.",
            "audience": "Security",
            "filename": "security-layer.html",
        },
        {
            "title": "Governance Stack",
            "description": "OpenLineage, Marquez, Grafana, and OpenMetadata for BCBS 239 compliance and data lineage.",
            "audience": "Compliance",
            "filename": "governance-stack.html",
        },
    ]

    template = env.get_template("base_arch_index.html")
    html = template.render(
        title="Architecture Documentation",
        subtitle="Platform Architecture Visualizations and Service Reference",
        arch_pages=arch_pages,
        versions=versions,
        generation_date=generation_date,
    )

    output_path = output_dir / "index.html"
    output_path.write_text(html)
    print(f"  Rendered: architecture/index.html")
    return output_path


def extract_package_api(package_dir: Path) -> dict:
    """Extract public API from a Python package directory using AST parsing.

    Walks all .py files in the package (recursively), parsing each with the ast
    module to extract public classes, functions, their signatures, docstrings,
    and type annotations. Does NOT import any modules at runtime, avoiding
    PySpark and other heavy dependencies.

    Args:
        package_dir: Path to the Python package directory.

    Returns:
        Dict with keys: package_name (str), modules (list of module dicts).
        Each module dict has: name, path, classes (list), functions (list).
    """
    package_name = package_dir.name
    modules: list[dict] = []

    py_files = sorted(package_dir.rglob("*.py"))
    for py_file in py_files:
        if "__pycache__" in str(py_file):
            continue
        rel_path = py_file.relative_to(package_dir)

        # Skip __init__.py files that are empty or only have docstrings
        if py_file.name == "__init__.py":
            content = py_file.read_text().strip()
            if not content or all(
                line.strip() == "" or line.strip().startswith("#") or line.strip().startswith('"""') or line.strip().startswith("'''")
                for line in content.split("\n")
            ):
                continue

        try:
            source = py_file.read_text()
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            warnings.warn(f"Failed to parse {py_file}, skipping")
            continue

        classes: list[dict] = []
        functions: list[dict] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                cls_info = _extract_class_info(node)
                classes.append(cls_info)
            elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                func_info = _extract_function_info(node)
                functions.append(func_info)

        if classes or functions:
            modules.append({
                "name": py_file.stem,
                "path": str(rel_path),
                "classes": classes,
                "functions": functions,
            })

    return {"package_name": package_name, "modules": modules}


def _extract_class_info(node: ast.ClassDef) -> dict:
    """Extract class metadata from an AST ClassDef node."""
    bases = []
    for base in node.bases:
        try:
            bases.append(ast.unparse(base))
        except Exception:
            bases.append("?")

    docstring = ast.get_docstring(node) or ""
    methods: list[dict] = []

    for item in node.body:
        if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
            methods.append(_extract_function_info(item, is_method=True))

    return {
        "name": node.name,
        "bases": bases,
        "docstring": docstring,
        "methods": methods,
    }


def _extract_function_info(node: ast.FunctionDef, *, is_method: bool = False) -> dict:
    """Extract function/method metadata from an AST FunctionDef node."""
    docstring = ast.get_docstring(node) or ""

    args: list[str] = []
    for arg in node.args.args:
        if is_method and arg.arg == "self":
            continue
        if arg.annotation:
            try:
                annotation = ast.unparse(arg.annotation)
                args.append(f"{arg.arg}: {annotation}")
            except Exception:
                args.append(arg.arg)
        else:
            args.append(arg.arg)

    return_annotation = ""
    if node.returns:
        try:
            return_annotation = ast.unparse(node.returns)
        except Exception:
            pass

    return {
        "name": node.name,
        "args": args,
        "docstring": docstring,
        "return_annotation": return_annotation,
    }


def extract_all_apis(etl_src_dir: Path) -> list[dict]:
    """Extract APIs from all 8 ETL packages using AST parsing.

    Args:
        etl_src_dir: Path to etl/src/ directory containing the 8 packages.

    Returns:
        List of package API dicts from extract_package_api().
    """
    package_names = [
        "pipelines", "config", "governance", "quality",
        "semantic", "iceberg_utils", "lineage", "inventory",
    ]
    results: list[dict] = []
    for pkg_name in package_names:
        pkg_dir = etl_src_dir / pkg_name
        if pkg_dir.is_dir():
            results.append(extract_package_api(pkg_dir))
    return results


def render_developer_docs(
    data_dir: Path | None = None,
    diagram_dir: Path | None = None,
    template_dir: Path | None = None,
    output_dir: Path | None = None,
    compose_path: Path | str | None = None,
) -> list[Path]:
    """Render all developer documentation pages from YAML data + Jinja2 templates.

    Iterates YAML files in data_dir, renders each through base_developer.html
    template, and writes standalone HTML to output_dir. Supports page_type variants:
    guide, reference, faq, checklist, visualization.

    Args:
        data_dir: Directory containing developer docs YAML data files.
        diagram_dir: Directory containing .mmd Mermaid source files.
        template_dir: Directory containing Jinja2 templates.
        output_dir: Directory for rendered HTML output.
        compose_path: Path to docker-compose.yml for version extraction.

    Returns:
        List of Paths to rendered HTML files.
    """
    if data_dir is None:
        data_dir = DEV_DATA_DIR
    if diagram_dir is None:
        diagram_dir = DEV_DIAGRAM_DIR
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    if output_dir is None:
        output_dir = DEV_OUTPUT_DIR

    data_dir = Path(data_dir)
    diagram_dir = Path(diagram_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = _create_jinja_env(template_dir)
    versions = extract_versions(compose_path)
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Extract services for DEV-07/DEV-08
    overrides_path = ARCH_DATA_DIR / "services.yml"
    services = extract_services(compose_path, overrides_path)

    # Extract API data for DEV-10 (api-reference page)
    etl_src_dir = PROJECT_ROOT / "etl" / "src"
    api_packages = extract_all_apis(etl_src_dir) if etl_src_dir.is_dir() else []

    # Render Mermaid diagrams for DEV-06/DEV-11
    svg_content: dict[str, str] = {}
    if diagram_dir.exists():
        for mmd_file in sorted(diagram_dir.glob("*.mmd")):
            try:
                svg_content[mmd_file.stem] = render_mermaid_to_svg(mmd_file)
            except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
                svg_content[mmd_file.stem] = _placeholder_svg(str(exc))

    rendered_files: list[Path] = []
    template = env.get_template("base_developer.html")

    for data_file in sorted(data_dir.glob("*.yml")):
        doc_data = yaml.safe_load(data_file.read_text())
        if doc_data is None:
            continue
        html = template.render(
            **doc_data,
            versions=versions,
            services=services,
            svg_diagrams=svg_content,
            api_packages=api_packages,
            generation_date=generation_date,
        )
        output_name = doc_data.get("output_filename", f"{data_file.stem}.html")
        output_path = output_dir / output_name
        output_path.write_text(html)
        rendered_files.append(output_path)
        print(f"  Rendered: developer/{output_name}")

    return rendered_files


def render_dev_index(
    template_dir: Path | None = None,
    output_dir: Path | None = None,
    compose_path: Path | str | None = None,
) -> Path:
    """Render the developer docs index page with audience-tagged navigation cards.

    Loads dev-index.yml and renders through base_developer.html with the
    dev-index page_type, producing docs/developer/index.html.

    Args:
        template_dir: Directory containing Jinja2 templates.
        output_dir: Directory for rendered HTML output.
        compose_path: Path to docker-compose.yml for version extraction.

    Returns:
        Path to the rendered index.html file.
    """
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    if output_dir is None:
        output_dir = DEV_OUTPUT_DIR

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = _create_jinja_env(template_dir)
    versions = extract_versions(compose_path)
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Load dev-index data
    index_data_path = DEV_DATA_DIR / "dev-index.yml"
    index_data = yaml.safe_load(index_data_path.read_text())

    template = env.get_template("base_developer.html")
    html = template.render(
        **index_data,
        versions=versions,
        generation_date=generation_date,
    )

    output_path = output_dir / "index.html"
    output_path.write_text(html)
    print(f"  Rendered: developer/index.html")
    return output_path


def extract_cube_metrics(cube_dir: Path | None = None) -> list[dict]:
    """Extract metric definitions from Cube YAML files.

    Parses all *.yml files in the cubes directory, iterating each cube's
    measures to build a list of metric dicts with calculation details.

    Args:
        cube_dir: Path to Cube YAML directory. Defaults to semantic/model/cubes/.

    Returns:
        List of metric dicts with keys: cube_name, sql_table, measure_name,
        measure_type, description, glossary_term, sql.
    """
    if cube_dir is None:
        cube_dir = PROJECT_ROOT / "semantic" / "model" / "cubes"
    cube_dir = Path(cube_dir)

    metrics: list[dict] = []
    for yml_file in sorted(cube_dir.glob("*.yml")):
        data = yaml.safe_load(yml_file.read_text())
        if data is None:
            continue
        for cube in data.get("cubes", []):
            cube_name = cube.get("name", "")
            sql_table = cube.get("sql_table", "")
            for measure in cube.get("measures", []):
                meta = measure.get("meta", {}) or {}
                metrics.append({
                    "cube_name": cube_name,
                    "sql_table": sql_table,
                    "measure_name": measure.get("name", ""),
                    "measure_type": measure.get("type", ""),
                    "description": (measure.get("description", "") or "").strip(),
                    "glossary_term": meta.get("glossary_term", ""),
                    "sql": measure.get("sql", ""),
                })
    return metrics


def extract_glossary_terms(glossary_path: Path | None = None) -> dict[str, list[dict]]:
    """Load glossary-seed.json and group terms by business domain.

    Domain mapping uses each term's tags:
      - Trading: tags containing "trading" or ("finance" without "risk")
      - Risk: tags containing "risk"
      - Governance: tags containing "governance", "compliance", "privacy", "sla", "quality", "monitoring"
      - Infrastructure: tags containing "architecture", "medallion", "data-lake"

    Args:
        glossary_path: Path to glossary-seed.json. Defaults to GLOSSARY_SEED_PATH.

    Returns:
        Dict mapping domain name to list of term dicts. Each term has a slug field.
    """
    if glossary_path is None:
        glossary_path = GLOSSARY_SEED_PATH
    glossary_path = Path(glossary_path)

    data = json.loads(glossary_path.read_text())
    terms = data.get("terms", [])

    domain_rules: list[tuple[str, set[str]]] = [
        ("Infrastructure", {"architecture", "medallion", "data-lake"}),
        ("Governance", {"governance", "compliance", "privacy", "sla", "quality", "monitoring"}),
        ("Risk", {"risk"}),
        ("Trading", {"trading", "finance"}),
    ]

    grouped: dict[str, list[dict]] = {
        "Trading": [], "Risk": [], "Governance": [], "Infrastructure": [],
    }

    for term in terms:
        tags = {t.lower() for t in term.get("tags", [])}
        slug = term["name"].lower().replace(" ", "-").replace("_", "-")
        entry = {
            "name": term["name"],
            "slug": slug,
            "description": term.get("description", ""),
            "synonyms": term.get("synonyms", []),
            "relatedTerms": term.get("relatedTerms", []),
            "tags": list(tags),
        }

        assigned = False
        for domain_name, domain_tags in domain_rules:
            if tags & domain_tags:
                # Special case: "finance" + "risk" -> Risk, not Trading
                if domain_name == "Trading" and "risk" in tags:
                    continue
                grouped[domain_name].append(entry)
                assigned = True
                break
        if not assigned:
            grouped["Governance"].append(entry)

    return grouped


def extract_freshness_slas(tracker_path: Path | None = None) -> dict[str, dict]:
    """AST-parse freshness_tracker.py to extract DEFAULT_SLAS threshold values.

    Walks the AST to find the DEFAULT_SLAS dict assignment. For each entry,
    extracts FreshnessSLA() keyword arguments from ast.Constant nodes.

    Args:
        tracker_path: Path to freshness_tracker.py. Defaults to FRESHNESS_TRACKER_PATH.

    Returns:
        Dict mapping layer pattern (e.g. "gold.*") to
        {expected_hours, warning_hours, critical_hours}.
    """
    if tracker_path is None:
        tracker_path = FRESHNESS_TRACKER_PATH
    tracker_path = Path(tracker_path)

    source = tracker_path.read_text()
    tree = ast.parse(source, filename=str(tracker_path))

    slas: dict[str, dict] = {}

    for node in ast.walk(tree):
        # Handle both ast.Assign and ast.AnnAssign (type-annotated assignment)
        target_name = None
        value_node = None
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DEFAULT_SLAS":
                    target_name = target.id
                    value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "DEFAULT_SLAS":
                target_name = node.target.id
                value_node = node.value

        if target_name and value_node and isinstance(value_node, ast.Dict):
            for key_node, val_node in zip(value_node.keys, value_node.values):
                if isinstance(key_node, ast.Constant) and isinstance(val_node, ast.Call):
                    layer_key = key_node.value
                    kw_map: dict[str, float] = {}
                    for kw in val_node.keywords:
                        if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, (int, float)):
                            kw_map[kw.arg] = float(kw.value.value)
                    slas[layer_key] = {
                        "expected_hours": kw_map.get("expected_update_interval_hours", 0),
                        "warning_hours": kw_map.get("warning_threshold_hours", 0),
                        "critical_hours": kw_map.get("critical_threshold_hours", 0),
                    }
    return slas


def render_catalog_docs(
    data_dir: Path | None = None,
    diagram_dir: Path | None = None,
    template_dir: Path | None = None,
    output_dir: Path | None = None,
    compose_path: Path | str | None = None,
) -> list[Path]:
    """Render catalog HTML pages from YAML data + Jinja2 templates.

    Loads YAML data files from data_dir, renders each through base_catalog.html.
    Injects glossary_terms, freshness_slas, and versions at render time.

    Args:
        data_dir: Directory containing catalog YAML data files.
        diagram_dir: Directory containing .mmd Mermaid source files.
        template_dir: Directory containing Jinja2 templates.
        output_dir: Directory for rendered HTML output.
        compose_path: Path to docker-compose.yml for version extraction.

    Returns:
        List of Paths to rendered HTML files.
    """
    if data_dir is None:
        data_dir = CATALOG_DATA_DIR
    if diagram_dir is None:
        diagram_dir = CATALOG_DIAGRAM_DIR
    if template_dir is None:
        template_dir = TEMPLATE_DIR
    if output_dir is None:
        output_dir = CATALOG_OUTPUT_DIR

    data_dir = Path(data_dir)
    diagram_dir = Path(diagram_dir) if diagram_dir else CATALOG_DIAGRAM_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = _create_jinja_env(template_dir)
    versions = extract_versions(compose_path)
    generation_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Extract enrichment data
    glossary_terms = extract_glossary_terms()
    freshness_slas = extract_freshness_slas()
    cube_metrics = extract_cube_metrics()

    # Render Mermaid diagrams to SVG (with graceful fallback)
    svg_content: dict[str, str] = {}
    diagram_dir = Path(diagram_dir)
    if diagram_dir.exists():
        for mmd_file in sorted(diagram_dir.glob("*.mmd")):
            try:
                svg_content[mmd_file.stem] = render_mermaid_to_svg(mmd_file)
            except (RuntimeError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
                svg_content[mmd_file.stem] = _placeholder_svg(
                    f"Install @mermaid-js/mermaid-cli to render {mmd_file.name}"
                )

    rendered_files: list[Path] = []
    template = env.get_template("base_catalog.html")

    for data_file in sorted(data_dir.glob("*.yml")):
        doc_data = yaml.safe_load(data_file.read_text())
        if doc_data is None:
            continue
        html = template.render(
            **doc_data,
            glossary_terms=glossary_terms,
            freshness_slas=freshness_slas,
            cube_metrics=cube_metrics,
            svg_diagrams=svg_content,
            versions=versions,
            generation_date=generation_date,
        )
        output_name = doc_data.get("output_filename", f"{data_file.stem}.html")
        output_path = output_dir / output_name
        output_path.write_text(html)
        rendered_files.append(output_path)
        print(f"  Rendered: catalog/{output_name}")

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

    print("\nRendering developer docs...")
    dev_rendered = render_developer_docs()
    print(f"\n  {len(dev_rendered)} developer doc(s) rendered.")

    print("\nRendering developer index...")
    dev_index = render_dev_index()
    print(f"\n  Index: {dev_index}")

    print("\nRendering catalog docs...")
    catalog_rendered = render_catalog_docs()
    print(f"\n  {len(catalog_rendered)} catalog page(s) rendered.")

    print("\nDone.")
