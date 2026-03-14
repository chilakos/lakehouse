"""Tests for the SWOT HTML render pipeline.

Validates that rendered HTML meets all phase requirements:
- SWOT-01: Shared CSS template with embedded styles
- SWOT-02: Nessie Catalog SWOT renders correctly
- SWOT-09: Interactive collapsible sections (CSS-only details/summary)
- SWOT-10: Responsive tablet-friendly design
- ARCH-09: Version-stamped footers with generation date and component versions
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
