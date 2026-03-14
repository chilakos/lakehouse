"""Tests for the SWOT, Architecture, and Developer Documentation HTML render pipeline.

Validates that rendered HTML meets all phase requirements:
- SWOT-01: Shared CSS template with embedded styles
- SWOT-02: Nessie Catalog SWOT renders correctly
- SWOT-09: Interactive collapsible sections (CSS-only details/summary)
- SWOT-10: Responsive tablet-friendly design
- ARCH-09: Version-stamped footers with generation date and component versions
- ARCH-01: Marketecture HTML with stats banner and capability groups
- ARCH-02: Detailed architecture with all services grouped by layer
- ARCH-08: CSS hover tooltips on service nodes
- DEV-01: Developer onboarding guide
- DEV-02: Repository structure walkthrough
- DEV-03: First pipeline tutorial
- DEV-09: Day 1 checklist (printable)
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest
import yaml

# Ensure docs/ is importable
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from docs.render_html import extract_versions, render_swots  # noqa: E402
from docs.render_html import extract_services, render_architecture  # noqa: E402
from docs.render_html import render_developer_docs  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SWOT_YAML = textwrap.dedent("""\
    title: "Test SWOT Analysis"
    subtitle: "Option A vs Option B"
    status: decided
    decision: "Option A"
    prepared_for: "Leadership Review"
    date: "2026-03-14"
    phase: "Phase 1 - Test"
    next_review: "2026-Q2"

    executive_summary: |
      This is a test executive summary for validation purposes.
      Option A is recommended based on evidence.

    recommendation: |
      Option A is recommended because of its superior performance
      and lower total cost of ownership.

    strengths:
      - id: S1
        title: "Low Cost"
        description: "Option A has the lowest TCO."
        evidence: "$0 license cost vs $50k/year for Option B"
      - id: S2
        title: "Open Source"
        description: "Apache 2.0 licensed."
        evidence: "Apache 2.0 license; community-driven"

    weaknesses:
      - id: W1
        title: "Small Community"
        description: "Smaller community than Option B."
        evidence: "500 GitHub stars vs 5000"

    opportunities:
      - id: O1
        title: "Growing Adoption"
        description: "Rapid industry adoption."
        evidence: "3x YoY growth in contributors"

    threats:
      - id: T1
        title: "Competitor Momentum"
        description: "Option C gaining traction."
        evidence: "Option C raised $100M Series D"
        mitigation: "REST API compatibility means switching cost is low."

    decision_matrix:
      criteria:
        - "License cost"
        - "Community size"
        - "Performance"
      options:
        Option A:
          - "Free"
          - "Growing"
          - "High"
        Option B:
          - "$50k/year"
          - "Large"
          - "Medium"
""")


@pytest.fixture
def sample_data_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with a sample SWOT YAML data file."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "test-swot.yml").write_text(SAMPLE_SWOT_YAML)
    return data_dir


@pytest.fixture
def template_dir() -> Path:
    """Return the project template directory."""
    return _project_root / "docs" / "templates"


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    out = tmp_path / "output"
    out.mkdir()
    return out


@pytest.fixture
def rendered_html(sample_data_dir: Path, template_dir: Path, output_dir: Path) -> str:
    """Render a sample SWOT and return the HTML content."""
    results = render_swots(
        data_dir=sample_data_dir,
        template_dir=template_dir,
        output_dir=output_dir,
    )
    assert len(results) >= 1, "render_swots should produce at least one file"
    return results[0].read_text()


# ---------------------------------------------------------------------------
# SWOT-01: Embedded CSS
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_css_embedded(rendered_html: str) -> None:
    """Rendered HTML must contain an embedded <style> block (SWOT-01)."""
    assert "<style>" in rendered_html, "Missing embedded <style> block"


@pytest.mark.unit
def test_no_external_css(rendered_html: str) -> None:
    """Rendered HTML must NOT contain external stylesheet links (SWOT-01)."""
    assert '<link rel="stylesheet"' not in rendered_html, "External CSS link found"


# ---------------------------------------------------------------------------
# SWOT-10: Responsive design
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_responsive_meta_viewport(rendered_html: str) -> None:
    """Rendered HTML must contain a meta viewport tag (SWOT-10)."""
    assert '<meta name="viewport"' in rendered_html, "Missing responsive viewport meta tag"


@pytest.mark.unit
def test_responsive_tablet_breakpoint(rendered_html: str) -> None:
    """Rendered HTML must contain tablet breakpoint media query (SWOT-10)."""
    assert "@media (max-width: 768px)" in rendered_html, "Missing tablet breakpoint"


# ---------------------------------------------------------------------------
# SWOT-09: Collapsible sections
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_collapsible_details_elements(rendered_html: str) -> None:
    """Rendered HTML must contain details and summary elements (SWOT-09)."""
    assert "<details" in rendered_html, "Missing <details> element"
    assert "<summary" in rendered_html, "Missing <summary> element"


@pytest.mark.unit
def test_print_details_expansion(rendered_html: str) -> None:
    """Print CSS must force details-content expansion (SWOT-09)."""
    assert "details-content" in rendered_html, "Missing ::details-content print rule"


# ---------------------------------------------------------------------------
# ARCH-09: Version-stamped footer
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_footer_generation_date(rendered_html: str) -> None:
    """Rendered HTML footer must contain generation date string (ARCH-09)."""
    assert "Generated:" in rendered_html, "Missing generation date in footer"


@pytest.mark.unit
def test_footer_version_strings(rendered_html: str) -> None:
    """Rendered HTML footer must contain version strings from docker-compose.yml (ARCH-09)."""
    # At minimum: nessie, trino, cube-api should be present
    html_lower = rendered_html.lower()
    version_keywords = ["nessie", "trino", "cube"]
    found = sum(1 for kw in version_keywords if kw in html_lower)
    assert found >= 3, f"Expected at least 3 version strings, found {found}"


# ---------------------------------------------------------------------------
# Branding: Navy/Gold
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_navy_color_in_css(rendered_html: str) -> None:
    """CSS must contain navy color #1a2332."""
    assert "#1a2332" in rendered_html, "Missing navy color #1a2332"


@pytest.mark.unit
def test_gold_color_in_css(rendered_html: str) -> None:
    """CSS must contain gold accent #c8a961."""
    assert "#c8a961" in rendered_html, "Missing gold accent #c8a961"


@pytest.mark.unit
def test_system_font_stack(rendered_html: str) -> None:
    """CSS must contain system font stack with Segoe UI."""
    assert '"Segoe UI"' in rendered_html or "'Segoe UI'" in rendered_html, \
        'Missing system font stack (should contain "Segoe UI")'


# ---------------------------------------------------------------------------
# extract_versions()
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_extract_versions_returns_dict() -> None:
    """extract_versions() must return a dict with service keys from docker-compose.yml."""
    compose_path = _project_root / "docker-compose.yml"
    if not compose_path.exists():
        pytest.skip("docker-compose.yml not found")
    versions = extract_versions(compose_path=compose_path)
    assert isinstance(versions, dict)
    assert "nessie" in versions, "Missing nessie in versions"
    assert "trino" in versions, "Missing trino in versions"
    assert "cube-api" in versions, "Missing cube-api in versions"


# ---------------------------------------------------------------------------
# render_swots() produces .html output
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_render_swots_produces_html(
    sample_data_dir: Path, template_dir: Path, output_dir: Path
) -> None:
    """render_swots() must produce .html files from .yml data files."""
    results = render_swots(
        data_dir=sample_data_dir,
        template_dir=template_dir,
        output_dir=output_dir,
    )
    assert len(results) >= 1, "No HTML files produced"
    for p in results:
        assert p.suffix == ".html", f"Expected .html file, got {p.suffix}"
        assert p.exists(), f"Rendered file does not exist: {p}"
        content = p.read_text()
        assert "<!DOCTYPE html>" in content, "Missing DOCTYPE in rendered HTML"


# ---------------------------------------------------------------------------
# Architecture: Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def compose_path() -> Path:
    """Return path to the project's docker-compose.yml."""
    p = _project_root / "docker-compose.yml"
    if not p.exists():
        pytest.skip("docker-compose.yml not found")
    return p


@pytest.fixture
def arch_data_dir() -> Path:
    """Return path to architecture data directory."""
    return _project_root / "docs" / "architecture" / "data"


@pytest.fixture
def arch_diagram_dir() -> Path:
    """Return path to architecture diagrams directory."""
    return _project_root / "docs" / "architecture" / "diagrams"


@pytest.fixture
def arch_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for architecture pages."""
    out = tmp_path / "arch_output"
    out.mkdir()
    return out


@pytest.fixture
def rendered_architecture(
    arch_diagram_dir: Path,
    arch_data_dir: Path,
    template_dir: Path,
    arch_output_dir: Path,
    compose_path: Path,
) -> dict[str, str]:
    """Render architecture pages and return dict of filename -> HTML content."""
    results = render_architecture(
        diagram_dir=arch_diagram_dir,
        data_dir=arch_data_dir,
        template_dir=template_dir,
        output_dir=arch_output_dir,
        compose_path=compose_path,
    )
    return {p.name: p.read_text() for p in results}


# ---------------------------------------------------------------------------
# ARCH-01: extract_services() metadata
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_extract_services_ports(compose_path: Path) -> None:
    """extract_services() returns dict with ports, healthcheck, depends_on for all services."""
    services = extract_services(compose_path=compose_path)
    assert isinstance(services, dict)
    # Should have all 25 docker-compose services
    assert len(services) >= 25, f"Expected >= 25 services, got {len(services)}"
    # Check specific port values
    assert any("8080" in str(p) for p in services["trino"]["ports"]), \
        "Trino should have port 8080"
    assert any("9000" in str(p) for p in services["minio"]["ports"]), \
        "MinIO should have port 9000"
    # Each service should have required keys
    for name, svc in services.items():
        assert "ports" in svc, f"{name} missing 'ports'"
        assert "healthcheck" in svc, f"{name} missing 'healthcheck'"
        assert "depends_on" in svc, f"{name} missing 'depends_on'"


@pytest.mark.unit
def test_extract_services_excludes_init(compose_path: Path, arch_data_dir: Path) -> None:
    """After merging with services.yml, init containers are filtered out."""
    services = extract_services(
        compose_path=compose_path,
        overrides_path=arch_data_dir / "services.yml",
    )
    assert "minio-init" not in services, "minio-init should be excluded"
    assert "airflow-init" not in services, "airflow-init should be excluded"


@pytest.mark.unit
def test_extract_services_layer_assignment(compose_path: Path, arch_data_dir: Path) -> None:
    """Services merged with services.yml have layer, description, protocol keys."""
    services = extract_services(
        compose_path=compose_path,
        overrides_path=arch_data_dir / "services.yml",
    )
    # After merge with overrides, services should have layer metadata
    for name, svc in services.items():
        assert "layer" in svc, f"{name} missing 'layer' after override merge"
        assert "description" in svc, f"{name} missing 'description' after override merge"
        assert "protocol" in svc, f"{name} missing 'protocol' after override merge"


# ---------------------------------------------------------------------------
# ARCH-01: Marketecture stats banner and capability groups
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_marketecture_stats_banner(rendered_architecture: dict[str, str]) -> None:
    """Marketecture HTML contains stats banner with key numbers (ARCH-01)."""
    html = rendered_architecture["marketecture.html"]
    assert "1.5 PB" in html, "Missing '1.5 PB' in stats banner"
    assert "300+" in html, "Missing '300+' in stats banner"
    assert "40+" in html, "Missing '40+' in stats banner"
    assert "Query Engines" in html or "query engines" in html.lower(), \
        "Missing 'Query Engines' in stats banner"


@pytest.mark.unit
def test_marketecture_capability_groups(rendered_architecture: dict[str, str]) -> None:
    """Marketecture HTML contains all 8 capability group labels (ARCH-01)."""
    html = rendered_architecture["marketecture.html"]
    groups = [
        "Sources", "ETL", "Ingestion", "Iceberg Lakehouse",
        "Query Engines", "Semantic", "Consumers", "Governance", "Security",
    ]
    for group in groups:
        assert group in html, f"Missing capability group label: '{group}'"


# ---------------------------------------------------------------------------
# ARCH-02: Detailed architecture all services
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_detailed_arch_all_services(rendered_architecture: dict[str, str]) -> None:
    """Detailed architecture HTML contains at least 20 service-node divs (ARCH-02)."""
    html = rendered_architecture["detailed-architecture.html"]
    count = html.count("service-node")
    # At least 20 service-node occurrences (CSS class + div instances for 23 non-init services)
    assert count >= 20, f"Expected >= 20 service-node occurrences, got {count}"


# ---------------------------------------------------------------------------
# ARCH-08: CSS hover tooltips
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_css_hover_tooltips(rendered_architecture: dict[str, str]) -> None:
    """Detailed architecture HTML contains tooltip CSS class and hover rule (ARCH-08)."""
    html = rendered_architecture["detailed-architecture.html"]
    assert "service-tooltip" in html, "Missing 'service-tooltip' CSS class"
    assert ".service-node:hover .service-tooltip" in html, \
        "Missing CSS hover rule for tooltips"


# ---------------------------------------------------------------------------
# ARCH-03: Data flow medallion path
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_data_flow_medallion_path(rendered_architecture: dict[str, str]) -> None:
    """Data-flow.html contains Bronze, Silver, Gold medallion layers (ARCH-03)."""
    html = rendered_architecture["data-flow.html"]
    assert "Bronze" in html, "Missing 'Bronze' in data flow page"
    assert "Silver" in html, "Missing 'Silver' in data flow page"
    assert "Gold" in html, "Missing 'Gold' in data flow page"
    # Should show at least one end-to-end path element
    assert "Sources" in html or "Ingestion" in html, \
        "Missing source/ingestion reference in data flow"


# ---------------------------------------------------------------------------
# ARCH-04: Service dependency edges
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_service_dependency_edges(rendered_architecture: dict[str, str]) -> None:
    """Service-dependency.html shows depends_on relationships (ARCH-04)."""
    html = rendered_architecture["service-dependency.html"]
    html_lower = html.lower()
    # Should contain key dependency terms
    assert "nessie" in html_lower, "Missing 'nessie' in dependency graph"
    assert "trino" in html_lower, "Missing 'trino' in dependency graph"
    assert "depends" in html_lower, "Missing 'depends' keyword in dependency page"


# ---------------------------------------------------------------------------
# ARCH-05: Security layer with Ranger
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_security_ranger_services(rendered_architecture: dict[str, str]) -> None:
    """Security-layer.html contains Ranger services and RBAC flow (ARCH-05)."""
    html = rendered_architecture["security-layer.html"]
    html_lower = html.lower()
    assert "ranger-admin" in html_lower, "Missing 'ranger-admin' in security page"
    assert "ranger-solr" in html_lower, "Missing 'ranger-solr' in security page"
    assert "ranger-zk" in html_lower, "Missing 'ranger-zk' in security page"
    assert "rbac" in html_lower or "role-based" in html_lower, \
        "Missing RBAC reference in security page"


# ---------------------------------------------------------------------------
# ARCH-06: Governance lineage flow
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_governance_lineage_flow(rendered_architecture: dict[str, str]) -> None:
    """Governance-stack.html contains OpenLineage-Marquez-Grafana flow (ARCH-06)."""
    html = rendered_architecture["governance-stack.html"]
    assert "OpenLineage" in html, "Missing 'OpenLineage' in governance page"
    assert "Marquez" in html, "Missing 'Marquez' in governance page"
    assert "Grafana" in html, "Missing 'Grafana' in governance page"
    assert "BCBS 239" in html or "lineage" in html.lower(), \
        "Missing BCBS 239 or lineage reference in governance page"


# ---------------------------------------------------------------------------
# ARCH-07: Environment comparison table
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_environment_table_columns(rendered_architecture: dict[str, str]) -> None:
    """Governance-stack.html contains environment table with dev/staging/prod (ARCH-07)."""
    html = rendered_architecture["governance-stack.html"]
    assert "Development" in html, "Missing 'Development' environment column"
    assert "Staging" in html, "Missing 'Staging' environment column"
    assert "Production" in html, "Missing 'Production' environment column"
    assert "Docker Compose" in html, "Missing 'Docker Compose' deployment method"
    assert "Terraform" in html, "Missing 'Terraform' deployment method"


# ---------------------------------------------------------------------------
# Architecture Index: links to all 6 architecture pages
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_architecture_index_links(rendered_architecture: dict[str, str]) -> None:
    """Architecture index.html links to all 6 architecture HTML pages."""
    html = rendered_architecture["index.html"]
    expected_pages = [
        "marketecture.html",
        "detailed-architecture.html",
        "data-flow.html",
        "service-dependency.html",
        "security-layer.html",
        "governance-stack.html",
    ]
    for page in expected_pages:
        assert page in html, f"Missing link to '{page}' in architecture index"
    # Verify audience tags are present
    assert "Executives" in html, "Missing 'Executives' audience tag"
    assert "Engineers" in html, "Missing 'Engineers' audience tag"
    assert "Security" in html, "Missing 'Security' audience tag"
    assert "Compliance" in html, "Missing 'Compliance' audience tag"


# ---------------------------------------------------------------------------
# Developer Docs: Fixtures
# ---------------------------------------------------------------------------

SAMPLE_GUIDE_YAML = textwrap.dedent("""\
    title: "Test Guide"
    subtitle: "A test guide page"
    page_type: "guide"
    sections:
      - heading: "Getting Started"
        content: "Follow these steps to set up your environment."
        code_blocks:
          - language: "bash"
            code: "docker-compose up -d"
      - heading: "Verify"
        content: "Check that services are running."
""")

SAMPLE_CHECKLIST_YAML = textwrap.dedent("""\
    title: "Test Checklist"
    subtitle: "Day 1 items"
    page_type: "checklist"
    sections:
      - heading: "Setup"
        bullet_items:
          - text: "Clone the repo"
            verify: "ls -la"
          - text: "Docker Compose up"
            verify: "docker ps | wc -l"
      - heading: "First Steps"
        bullet_items:
          - text: "Run tests"
            verify: "pytest"
""")

SAMPLE_REFERENCE_YAML = textwrap.dedent("""\
    title: "Test Reference"
    subtitle: "API reference page"
    page_type: "reference"
    sections:
      - heading: "Module: pipelines"
        entries:
          - name: "BasePipeline"
            type: "class"
            description: "Abstract base class for all pipelines."
          - name: "PipelineConfig"
            type: "class"
            description: "Frozen dataclass for pipeline configuration."
""")

SAMPLE_FAQ_YAML = textwrap.dedent("""\
    title: "Test FAQ"
    subtitle: "Troubleshooting"
    page_type: "faq"
    sections:
      - category: "Docker"
        entries:
          - symptom: "OOM killed"
            fix: "Increase memory"
            why: "Spark needs more than 2GB"
          - symptom: "Port conflict"
            fix: "Stop other containers"
            why: "Ports are already bound"
""")


@pytest.fixture
def dev_data_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with sample developer docs YAML files."""
    data_dir = tmp_path / "dev_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def dev_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for developer docs."""
    out = tmp_path / "dev_output"
    out.mkdir()
    return out


# ---------------------------------------------------------------------------
# Developer Docs: render_developer_docs() - guide page_type
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_docs_render_guide(
    dev_data_dir: Path, template_dir: Path, dev_output_dir: Path,
) -> None:
    """render_developer_docs() with page_type: guide produces valid HTML with DOCTYPE, navy branding, and version footer."""
    (dev_data_dir / "test-guide.yml").write_text(SAMPLE_GUIDE_YAML)
    results = render_developer_docs(
        data_dir=dev_data_dir,
        template_dir=template_dir,
        output_dir=dev_output_dir,
    )
    assert len(results) >= 1, "render_developer_docs should produce at least one file"
    html = results[0].read_text()
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    assert "#1a2332" in html, "Missing navy branding"
    assert "Generated:" in html, "Missing version footer"
    assert "Test Guide" in html, "Missing page title"
    assert "Getting Started" in html, "Missing section heading"
    assert "docker-compose up -d" in html, "Missing code block content"


# ---------------------------------------------------------------------------
# Developer Docs: render_developer_docs() - checklist page_type
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_docs_render_checklist(
    dev_data_dir: Path, template_dir: Path, dev_output_dir: Path,
) -> None:
    """render_developer_docs() with page_type: checklist produces HTML with checkbox items and @media print CSS."""
    (dev_data_dir / "test-checklist.yml").write_text(SAMPLE_CHECKLIST_YAML)
    results = render_developer_docs(
        data_dir=dev_data_dir,
        template_dir=template_dir,
        output_dir=dev_output_dir,
    )
    assert len(results) >= 1
    html = results[0].read_text()
    assert 'type="checkbox"' in html, "Missing checkbox input elements"
    assert "@media print" in html, "Missing @media print CSS"
    assert "Clone the repo" in html, "Missing checklist item text"
    assert "docker ps" in html, "Missing verify command"


# ---------------------------------------------------------------------------
# Developer Docs: render_developer_docs() - reference page_type
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_docs_render_reference(
    dev_data_dir: Path, template_dir: Path, dev_output_dir: Path,
) -> None:
    """render_developer_docs() with page_type: reference produces HTML with table structures."""
    (dev_data_dir / "test-reference.yml").write_text(SAMPLE_REFERENCE_YAML)
    results = render_developer_docs(
        data_dir=dev_data_dir,
        template_dir=template_dir,
        output_dir=dev_output_dir,
    )
    assert len(results) >= 1
    html = results[0].read_text()
    assert "<table" in html, "Missing table element"
    assert "BasePipeline" in html, "Missing class name in reference"
    assert "PipelineConfig" in html, "Missing PipelineConfig in reference"


# ---------------------------------------------------------------------------
# Developer Docs: render_developer_docs() - faq page_type
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_docs_render_faq(
    dev_data_dir: Path, template_dir: Path, dev_output_dir: Path,
) -> None:
    """render_developer_docs() with page_type: faq produces HTML with details/summary collapsible entries."""
    (dev_data_dir / "test-faq.yml").write_text(SAMPLE_FAQ_YAML)
    results = render_developer_docs(
        data_dir=dev_data_dir,
        template_dir=template_dir,
        output_dir=dev_output_dir,
    )
    assert len(results) >= 1
    html = results[0].read_text()
    assert "<details" in html, "Missing <details> element for FAQ"
    assert "<summary" in html, "Missing <summary> element for FAQ"
    assert "OOM killed" in html, "Missing FAQ symptom"
    assert "Increase memory" in html, "Missing FAQ fix"


# ---------------------------------------------------------------------------
# Developer Docs: render_developer_docs() - skip empty YAML
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_docs_render_skip_empty(
    dev_data_dir: Path, template_dir: Path, dev_output_dir: Path,
) -> None:
    """render_developer_docs() skips empty/None YAML files without error."""
    (dev_data_dir / "empty.yml").write_text("")
    (dev_data_dir / "valid.yml").write_text(SAMPLE_GUIDE_YAML)
    results = render_developer_docs(
        data_dir=dev_data_dir,
        template_dir=template_dir,
        output_dir=dev_output_dir,
    )
    # Should only produce 1 file (skip empty)
    assert len(results) == 1, f"Expected 1 file (empty skipped), got {len(results)}"


# ---------------------------------------------------------------------------
# Developer Docs: code_block macro
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_docs_code_block_macro(
    dev_data_dir: Path, template_dir: Path, dev_output_dir: Path,
) -> None:
    """code_block macro produces pre/code HTML with syntax class."""
    (dev_data_dir / "code-test.yml").write_text(SAMPLE_GUIDE_YAML)
    results = render_developer_docs(
        data_dir=dev_data_dir,
        template_dir=template_dir,
        output_dir=dev_output_dir,
    )
    assert len(results) >= 1
    html = results[0].read_text()
    assert "<pre>" in html, "Missing <pre> element from code_block macro"
    assert "<code" in html, "Missing <code> element from code_block macro"
    assert "language-" in html, "Missing language class on code element"


# ---------------------------------------------------------------------------
# Developer Docs: Fixtures for real YAML data files
# ---------------------------------------------------------------------------

@pytest.fixture
def real_dev_data_dir() -> Path:
    """Return path to the real developer docs YAML data directory."""
    return _project_root / "docs" / "developer" / "data"


@pytest.fixture
def real_dev_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory for real developer docs."""
    out = tmp_path / "real_dev_output"
    out.mkdir()
    return out


@pytest.fixture
def rendered_developer_pages(
    real_dev_data_dir: Path, template_dir: Path, real_dev_output_dir: Path,
) -> dict[str, str]:
    """Render real developer docs and return dict of filename -> HTML content."""
    results = render_developer_docs(
        data_dir=real_dev_data_dir,
        template_dir=template_dir,
        output_dir=real_dev_output_dir,
    )
    return {p.name: p.read_text() for p in results}


# ---------------------------------------------------------------------------
# DEV-01: Onboarding guide
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_onboarding(rendered_developer_pages: dict[str, str]) -> None:
    """DEV-01: Onboarding HTML contains docker-compose, service verification, prerequisites."""
    html = rendered_developer_pages["onboarding.html"]
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    assert "docker compose up -d" in html or "docker-compose up" in html, \
        "Missing docker-compose launch command"
    assert "curl" in html, "Missing service verification curl commands"
    assert "localhost:8081" in html or "8081" in html, "Missing Airflow health check"
    assert "trino" in html.lower(), "Missing Trino verification"
    assert "Python" in html or "python" in html, "Missing Python prerequisite"
    assert "Docker" in html, "Missing Docker prerequisite"


# ---------------------------------------------------------------------------
# DEV-02: Repository structure
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_repo_structure(rendered_developer_pages: dict[str, str]) -> None:
    """DEV-02: Repo structure HTML contains directory names and key file descriptions."""
    html = rendered_developer_pages["repo-structure.html"]
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    # Top-level directories
    assert "etl/" in html, "Missing etl/ directory"
    assert "docs/" in html, "Missing docs/ directory"
    assert "infra/" in html, "Missing infra/ directory"
    # Key files
    assert "docker-compose.yml" in html, "Missing docker-compose.yml"
    assert "pyproject.toml" in html, "Missing pyproject.toml"
    # ETL subdirectories
    assert "pipelines/" in html or "pipelines" in html, "Missing pipelines directory"
    assert "governance/" in html or "governance" in html, "Missing governance directory"


# ---------------------------------------------------------------------------
# DEV-03: First pipeline tutorial
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_first_pipeline(rendered_developer_pages: dict[str, str]) -> None:
    """DEV-03: First pipeline HTML contains BasePipeline, hello world, step-by-step code blocks."""
    html = rendered_developer_pages["first-pipeline.html"]
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    assert "BasePipeline" in html, "Missing BasePipeline reference"
    assert "hello" in html.lower(), "Missing hello-world synthetic example"
    assert "<pre>" in html, "Missing code blocks"
    assert "from src.pipelines.base import" in html, "Missing full import path"
    assert "MedallionLayer" in html, "Missing MedallionLayer reference"
    assert "extract" in html, "Missing extract() method reference"
    assert "transform" in html, "Missing transform() method reference"


# ---------------------------------------------------------------------------
# DEV-09: Day 1 checklist
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_day1_checklist(rendered_developer_pages: dict[str, str]) -> None:
    """DEV-09: Day 1 checklist HTML contains checkboxes, @media print CSS, links to other pages."""
    html = rendered_developer_pages["day1-checklist.html"]
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    assert 'type="checkbox"' in html, "Missing checkbox input elements"
    assert "@media print" in html, "Missing @media print CSS"
    # Checklist items
    assert "Clone" in html, "Missing clone repo item"
    assert "Docker" in html, "Missing Docker item"
    assert "test suite" in html or "pytest" in html, "Missing test suite item"
    # Links to detailed pages
    assert "onboarding.html" in html, "Missing link to onboarding page"
    assert "first-pipeline.html" in html, "Missing link to first pipeline page"
    # Print CSS for compact layout
    assert "8pt" in html, "Missing compact print font size"


# ---------------------------------------------------------------------------
# DEV-04: ETL Patterns Reference
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_etl_patterns(rendered_developer_pages: dict[str, str]) -> None:
    """DEV-04: ETL patterns HTML contains all 8 sections from etl-patterns.md with code block elements."""
    html = rendered_developer_pages["etl-patterns.html"]
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    # Medallion architecture content
    assert "Medallion" in html or "medallion" in html.lower(), "Missing Medallion architecture reference"
    # All 8 section headings (numbered in the YAML)
    section_markers = [
        "Architecture Overview",    # Section 1
        "Creating a New Pipeline",  # Section 2
        "Quality",                  # Section 3 (Data Quality Integration)
        "DAG Patterns",             # Section 4 (Airflow DAG Patterns)
        "Incremental Loading",      # Section 5
        "Mainframe",                # Section 6
        "Testing Patterns",         # Section 7
        "Quick Reference",          # Section 8
    ]
    for marker in section_markers:
        assert marker in html, f"Missing section: '{marker}'"
    # Reference table structure
    assert "<table" in html, "Missing table elements for reference entries"
    assert "BasePipeline" in html, "Missing BasePipeline reference"


# ---------------------------------------------------------------------------
# DEV-05: Testing Guide
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_testing_guide(rendered_developer_pages: dict[str, str]) -> None:
    """DEV-05: Testing guide HTML contains pytest markers, CI gate info, and output snippets."""
    html = rendered_developer_pages["testing.html"]
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    assert "pytest" in html, "Missing pytest reference"
    # All 4 markers
    assert "unit" in html, "Missing 'unit' marker"
    assert "integration" in html, "Missing 'integration' marker"
    assert "slow" in html, "Missing 'slow' marker"
    assert "snowflake" in html, "Missing 'snowflake' marker"
    # Formatted output snippet (pre-formatted pytest output)
    assert "test session starts" in html, "Missing formatted pytest output snippet"
    assert "passed" in html, "Missing test pass result in output snippet"
    # CI gate behavior
    assert "ci.yml" in html or "CI" in html, "Missing CI gate reference"
    assert "ruff" in html, "Missing ruff linter reference"


# ---------------------------------------------------------------------------
# DEV-06: CI/CD Workflow
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_cicd(rendered_developer_pages: dict[str, str]) -> None:
    """DEV-06: CI/CD HTML contains staging, production, workflow names, and Mermaid SVG or placeholder."""
    html = rendered_developer_pages["cicd.html"]
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    assert "staging" in html.lower(), "Missing 'staging' environment reference"
    assert "production" in html.lower() or "prod" in html.lower(), \
        "Missing 'production' environment reference"
    # Workflow names
    assert "ci.yml" in html, "Missing ci.yml workflow reference"
    assert "deploy-dev.yml" in html or "deploy-dev" in html, "Missing deploy-dev workflow"
    assert "deploy-staging.yml" in html or "deploy-staging" in html, "Missing deploy-staging workflow"
    assert "deploy-prod.yml" in html or "deploy-prod" in html, "Missing deploy-prod workflow"
    # Mermaid SVG or placeholder
    assert "svg" in html.lower() or "diagram" in html.lower() or "Placeholder" in html, \
        "Missing Mermaid SVG or placeholder for CI/CD flow diagram"


# ---------------------------------------------------------------------------
# DEV-07: Service URL Reference
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_service_urls(rendered_developer_pages: dict[str, str]) -> None:
    """DEV-07: Service URL HTML contains localhost, service names from docker-compose, and port numbers."""
    html = rendered_developer_pages["service-urls.html"]
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    assert "localhost" in html, "Missing localhost URLs"
    # Key services from docker-compose.yml
    service_names = ["airflow", "trino", "minio", "nessie", "grafana"]
    for svc in service_names:
        assert svc in html.lower(), f"Missing service '{svc}' in service URL reference"
    # Port numbers should be present (dynamic from extract_services)
    assert "8080" in html or "8081" in html, "Missing common port numbers"
    assert "9000" in html or "9001" in html, "Missing MinIO port"
    assert "19120" in html, "Missing Nessie port"
    # Dynamic services table from extract_services()
    assert "<table" in html, "Missing services table"
    assert "All Platform Services" in html, "Missing dynamic services table heading"


# ---------------------------------------------------------------------------
# DEV-08: Troubleshooting FAQ
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_developer_troubleshooting(rendered_developer_pages: dict[str, str]) -> None:
    """DEV-08: Troubleshooting FAQ HTML has Symptom-Fix-Why entries with collapsible details elements."""
    html = rendered_developer_pages["troubleshooting.html"]
    assert "<!DOCTYPE html>" in html, "Missing DOCTYPE"
    # Symptom-Fix-Why format
    html_lower = html.lower()
    assert "symptom" in html_lower or "Spark executor OOM" in html, \
        "Missing symptom references in FAQ"
    assert "Fix:" in html, "Missing 'Fix:' label in FAQ entries"
    assert "Why:" in html, "Missing 'Why:' label in FAQ entries"
    # Collapsible details/summary elements
    details_count = html.count("<details")
    assert details_count >= 8, \
        f"Expected at least 8 FAQ entries with <details>, got {details_count}"
    assert "<summary" in html, "Missing <summary> elements for FAQ"
    # Categories
    assert "Docker" in html, "Missing 'Docker and Services' category"
    assert "Testing" in html, "Missing 'Testing' category"
    # Specific troubleshooting content
    assert "OOM" in html or "memory" in html.lower(), "Missing OOM/memory troubleshooting entry"
    assert "Nessie" in html, "Missing Nessie troubleshooting entry"
