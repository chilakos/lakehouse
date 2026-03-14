# Phase 5: HTML Foundation and SWOT Analyses - Research

**Researched:** 2026-03-14
**Domain:** Jinja2 HTML templating, CSS standalone documents, SWOT strategic analysis content
**Confidence:** HIGH

## Summary

Phase 5 builds the shared CSS/HTML template infrastructure using Python Jinja2 and produces 6 executive-grade SWOT analysis documents as standalone HTML files. The stack is straightforward: Jinja2 3.1.6 and PyYAML 6.0.1 are already installed in the project environment. HTML files must work on `file://` protocol with zero external dependencies -- all CSS embedded in `<style>` blocks, system fonts only, no JavaScript.

The primary technical challenge is the CSS-only collapsible sections requirement. The `<details>/<summary>` HTML elements provide native collapse/expand behavior, but CSS alone historically could not force them open for print. As of September 2025, the `::details-content` pseudo-element is baseline across modern browsers, enabling `@media print { details::details-content { display: block; } }` to expand all sections when printing. This is the recommended approach.

The highest-value deliverables are the 2 undecided SWOTs (Snowflake Strategy, Data Model Strategy) which unblock active leadership decisions. Research confirms Snowflake now supports ICEBERG_REST catalog integrations (connecting to Nessie) and has moved Polaris to "Snowflake Open Catalog" as a managed service. The Data Model SWOT requires inferring FSDM coverage from existing schema definitions and codebase patterns.

**Primary recommendation:** Use Jinja2 template inheritance with a single `base_swot.html` template, YAML data files per SWOT, and a Python render script that extracts versions from `docker-compose.yml` for the ARCH-09 footer. Keep all CSS in a shared `<style>` block included via Jinja2 `{% block %}` inheritance.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Corporate navy & gold palette: dark navy (#1a2332) headers, gold (#c8a961) accents -- traditional financial services aesthetic
- Plain document style header: title, date, and status only -- McKinsey/Gartner report feel, no logo image
- Color-coded SWOT quadrants: green (Strengths), blue (Opportunities), yellow (Weaknesses), red (Threats) -- classic executive format
- System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif`) -- no external fonts
- All CSS embedded in `<style>` block -- truly standalone HTML files
- `@media print` rules for clean print-to-PDF
- Responsive design for tablet reading (CSS media queries)
- Collapsible `<details>`/`<summary>` sections -- CSS-only, no JavaScript
- 4 decided SWOTs (Nessie, Phased Python, Cube, Build-own NL-to-SQL): Full competitive analysis with pros/cons
- 2 undecided SWOTs (Snowflake Strategy, Data Model Strategy): Present balanced analysis with clear recommendation backed by evidence
- Each SWOT includes: executive summary with recommendation, 2x2 grid, detailed S/W/O/T sections with evidence, decision matrix/comparison table, mitigations for every threat
- Existing Nessie SWOT markdown is the content template -- convert and enhance for all 6
- Snowflake and Data Model SWOTs: Use web research for market positioning and infer from codebase
- Dashboard-style card layout for cross-SWOT index with status badges
- Decided badges (green), Undecided/Pending Decision badges (amber)
- Every HTML deliverable includes footer with: generation date, platform component versions, next review date
- Footer template built into the shared CSS/Jinja2 base template so all downstream phases inherit it

### Claude's Discretion
- Exact CSS spacing, margins, and typography sizing
- Jinja2 template structure and YAML data file format for SWOT content
- How deep to go on each alternative in the decided SWOTs
- Collapsible section grouping (which sections are collapsed by default)
- Exact responsive breakpoints

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SWOT-01 | Shared CSS template with embedded styles, print-friendly layout, professional typography, and consistent color palette | Jinja2 template inheritance + embedded `<style>` block; `@media print` rules; system font stack; navy/gold palette |
| SWOT-02 | Iceberg Catalog SWOT (Glue vs Nessie vs HMS vs Polaris) -- Decided: Nessie | Existing `docs/swot/nessie-catalog-swot.md` (176 lines) is complete content; convert to HTML via template |
| SWOT-03 | Snowflake Strategy SWOT (Retire vs Keep vs Maintain) -- Undecided | Snowflake ICEBERG_REST catalog research; consumption pricing analysis; competitive positioning vs Trino |
| SWOT-04 | DataStage Migration SWOT (Big-bang vs phased vs parallel-run) -- Decided: Phased Python | Evidence from `docs/etl-patterns.md` (565 lines); existing BasePipeline framework in `etl/src/` |
| SWOT-05 | Data Model Strategy SWOT (Keep FSDM vs evolve vs new medallion) -- Undecided | FSDM background research; infer coverage from schema definitions; medallion evolution patterns |
| SWOT-06 | BI Semantic Layer SWOT (Direct vs dbt vs AtScale vs Cube) -- Decided: Cube | Evidence from `semantic/model/` Cube YAML files; Cube v0.36.0 in docker-compose.yml |
| SWOT-07 | AI Semantic Layer SWOT (Build vs buy) -- Decided: Build-own | Evidence from `etl/src/semantic/nl_to_sql.py`; Claude on Bedrock architecture |
| SWOT-08 | Cross-SWOT index page with decision status summary and badges | Dashboard card layout; Jinja2 index template; decided (green) / undecided (amber) badges |
| SWOT-09 | Interactive collapsible sections (CSS-only details/summary) | `<details>/<summary>` HTML elements; `::details-content` pseudo-element for print expansion |
| SWOT-10 | Responsive tablet-friendly design across all SWOT HTML deliverables | CSS media queries at 768px breakpoint; fluid typography with `clamp()`; container max-width |
| ARCH-09 | Version-stamped footers on all HTML deliverables with generation date and component versions | Python script extracts versions from `docker-compose.yml`; Jinja2 base template footer block |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1.6 | HTML template engine | Already installed; Python-native (matches v1.0 stack); template inheritance for base/child pattern |
| PyYAML | 6.0.1 | SWOT content data files | Already installed; human-readable format for SWOT content; easy to edit |
| Python | 3.12.3 | Render script runtime | Already installed; project standard runtime |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `re` (stdlib) | 3.12 | Parse docker-compose.yml image tags | Extract version numbers for ARCH-09 footer |
| `datetime` (stdlib) | 3.12 | Generation timestamps | Footer generation date |
| `pathlib` (stdlib) | 3.12 | File path handling | Template and output file management |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 | Mako | Jinja2 already installed, more widespread, better template inheritance |
| YAML data files | JSON data files | YAML is more readable for long-form SWOT text content; multi-line strings are natural |
| PyYAML | ruamel.yaml | Both installed; PyYAML simpler API for read-only usage |

**Installation:**
```bash
# Nothing to install -- all dependencies already present
python3 -c "import jinja2; import yaml; print('Ready')"
```

## Architecture Patterns

### Recommended Project Structure
```
docs/
  templates/
    base_swot.html          # Jinja2 base template (CSS, footer, layout)
    base_index.html          # Jinja2 base for index pages
    macros/
      swot_grid.html         # 2x2 SWOT grid macro
      decision_matrix.html   # Comparison table macro
      collapsible.html       # details/summary wrapper macro
  swot/
    data/
      nessie-catalog.yml     # SWOT content data (1 per analysis)
      snowflake-strategy.yml
      datastage-migration.yml
      data-model-strategy.yml
      bi-semantic-layer.yml
      ai-semantic-layer.yml
      versions.yml           # Platform component versions for footer
    nessie-catalog-swot.md   # Existing markdown (kept for reference)
    nessie-catalog-swot.html # Generated HTML
    snowflake-strategy-swot.html
    datastage-migration-swot.html
    data-model-strategy-swot.html
    bi-semantic-layer-swot.html
    ai-semantic-layer-swot.html
    index.html               # Cross-SWOT index page
  render_html.py             # Python script to render all templates
```

### Pattern 1: Jinja2 Template Inheritance
**What:** Single base template defines layout, CSS, and footer; child templates override content blocks.
**When to use:** Every SWOT page and every downstream HTML deliverable (Phases 6-8).
**Example:**
```python
# Source: Jinja2 official docs (https://jinja.palletsprojects.com/en/stable/templates/)
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

env = Environment(
    loader=FileSystemLoader("docs/templates"),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

template = env.get_template("base_swot.html")
output = template.render(
    title="Iceberg Catalog SWOT Analysis",
    status="Decided",
    decision="Nessie",
    swot_data=swot_data,
    versions=version_data,
    generation_date="2026-03-14",
)

Path("docs/swot/nessie-catalog-swot.html").write_text(output)
```

### Pattern 2: YAML Data Files for SWOT Content
**What:** Each SWOT analysis has a YAML file containing structured content (executive summary, strengths, weaknesses, etc.) that the Jinja2 template renders.
**When to use:** All 6 SWOT analyses.
**Example:**
```yaml
# docs/swot/data/nessie-catalog.yml
title: "Iceberg Catalog SWOT Analysis"
subtitle: "Glue vs Nessie vs HMS vs Polaris"
status: decided
decision: "Nessie"
prepared_for: "Leadership Review"
date: "2026-03-14"
phase: "Phase 1 - Foundation and Feasibility Validation"
next_review: "2026-Q2"

executive_summary: |
  Nessie is an open-source transactional catalog for Apache Iceberg that
  implements the Iceberg REST catalog specification...

recommendation: |
  Nessie is the recommended catalog choice based on REST catalog compliance,
  multi-engine support, and branching capabilities.

strengths:
  - id: S1
    title: "Open-Source with No License Cost"
    description: |
      Nessie is Apache 2.0 licensed with no vendor lock-in...
    evidence: "Apache 2.0 license; no per-query pricing"

weaknesses:
  - id: W1
    title: "Smaller Community Than Hive Metastore"
    description: |
      Hive Metastore has decades of production deployment history...
    evidence: "Stack Overflow tag comparison; GitHub stars"

# ... opportunities, threats (with mitigations), decision_matrix
```

### Pattern 3: Version Extraction from docker-compose.yml
**What:** Python script parses `docker-compose.yml` to extract image tags for the ARCH-09 footer.
**When to use:** Render script, every HTML generation.
**Example:**
```python
import re
import yaml
from pathlib import Path

def extract_versions(compose_path: str = "docker-compose.yml") -> dict:
    """Extract service versions from docker-compose.yml image tags."""
    compose = yaml.safe_load(Path(compose_path).read_text())
    versions = {}
    for service_name, config in compose.get("services", {}).items():
        image = config.get("image", "")
        if ":" in image:
            name, version = image.rsplit(":", 1)
            versions[service_name] = {
                "image": name,
                "version": version,
            }
    return versions
# Expected output includes: nessie 0.107.4, trino 479, cube v0.36.0,
# ranger 2.8.0, marquez 0.50.0, openmetadata 1.6.0, etc.
```

### Pattern 4: CSS-Only Collapsible Sections
**What:** Use native `<details>/<summary>` HTML elements for collapse/expand. Use `::details-content` pseudo-element to force expansion in print.
**When to use:** All SWOT documents for detailed sections (S/W/O/T breakdown, decision matrix).
**Example:**
```html
<!-- Collapsed by default -->
<details>
  <summary>Strengths (4 items)</summary>
  <div class="swot-section strengths">
    <!-- strength items -->
  </div>
</details>

<!-- Open by default (executive summary, recommendation) -->
<details open>
  <summary>Executive Summary</summary>
  <div class="exec-summary">
    <!-- content -->
  </div>
</details>
```

```css
/* Base details styling */
details {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  margin-bottom: 1rem;
  overflow: hidden;
}

summary {
  padding: 0.75rem 1rem;
  background: #f8fafc;
  cursor: pointer;
  font-weight: 600;
  color: #1a2332;
  list-style: none;
}

summary::-webkit-details-marker { display: none; }
summary::marker { display: none; }

summary::before {
  content: "\25B6"; /* right-pointing triangle */
  display: inline-block;
  margin-right: 0.5rem;
  transition: transform 0.2s;
}

details[open] > summary::before {
  transform: rotate(90deg);
}

/* Print: force all sections open */
@media print {
  details::details-content {
    display: block !important;
  }
  summary::before {
    display: none;
  }
}
```

### Pattern 5: Responsive Tablet Design
**What:** CSS media queries for tablet-width reading, fluid typography.
**When to use:** All HTML deliverables.
**Example:**
```css
:root {
  --content-max-width: 900px;
  --side-padding: 2rem;
}

body {
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: 0 var(--side-padding);
  font-size: clamp(0.95rem, 1.5vw, 1.1rem);
  line-height: 1.6;
}

/* Tablet breakpoint */
@media (max-width: 768px) {
  :root {
    --side-padding: 1rem;
  }

  .swot-grid {
    grid-template-columns: 1fr; /* Stack quadrants vertically */
  }

  table {
    font-size: 0.85rem;
  }
}

/* Print */
@media print {
  body {
    max-width: none;
    padding: 0;
    font-size: 10pt;
  }

  @page {
    margin: 2cm;
  }
}
```

### Anti-Patterns to Avoid
- **External CDN references:** Never link to Bootstrap, Tailwind, Google Fonts, or any external resource. Files must render on `file://` protocol with no internet.
- **JavaScript for interactivity:** No JavaScript. Use `<details>/<summary>` for collapsible sections, CSS for all visual effects.
- **Separate CSS files:** All CSS must be embedded in `<style>` blocks within each HTML file. No `<link rel="stylesheet">` to external files (Jinja2 inheritance handles sharing the CSS across templates, but each rendered HTML is self-contained).
- **Pixel-based typography:** Use `rem`, `em`, `clamp()`, and `pt` (for print). Avoid fixed `px` for font sizes.
- **Hardcoded version numbers:** Always extract from `docker-compose.yml` or a versions config file. Never hardcode "Nessie 0.107.4" in templates.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML templating | String concatenation or f-strings | Jinja2 template inheritance | Escaping, inheritance, macros, filters; f-strings produce XSS-vulnerable unmaintainable code |
| YAML parsing | Regex-based extraction | PyYAML `safe_load` | Handles edge cases, multi-line strings, anchors |
| CSS grid layout | Manual float-based layout | CSS Grid (`display: grid`) | Native 2x2 grid for SWOT quadrants; `grid-template-columns: 1fr 1fr` |
| Collapsible sections | Custom checkbox hack | `<details>/<summary>` elements | Native HTML, accessible, keyboard-navigable, no JS needed |
| Print styling | Separate print page generation | `@media print` CSS rules | Browser-native Print-to-PDF works with `@media print` |
| Version extraction | Manual version tracking | Parse `docker-compose.yml` image tags | Single source of truth; always current |

**Key insight:** This phase is 90% content authoring and 10% tooling. The templating infrastructure is simple; the hard work is writing rigorous, evidence-backed SWOT content that meets McKinsey/Gartner quality standards.

## Common Pitfalls

### Pitfall 1: CSS Not Truly Embedded
**What goes wrong:** Templates render with `<link rel="stylesheet" href="styles.css">` instead of inline `<style>`. Files break when opened from `file://` or emailed.
**Why it happens:** Developer habit of separating CSS files.
**How to avoid:** Jinja2 base template must contain the full `<style>` block. The rendered HTML file must be self-contained. Verify by opening the HTML file directly from filesystem.
**Warning signs:** Any `<link>` tag in rendered output; any external URL in the HTML.

### Pitfall 2: `<details>` Not Expanding in Print
**What goes wrong:** Collapsed sections remain hidden when printing to PDF, losing content.
**Why it happens:** CSS historically could not control `<details>` open state. The `::details-content` pseudo-element is available since September 2025 but easy to forget.
**How to avoid:** Include `@media print { details::details-content { display: block !important; } }` in the base template. Test by using browser print preview. As a belt-and-suspenders fallback, use the `open` attribute on sections that should always be visible (executive summary, recommendation).
**Warning signs:** Print preview showing collapsed triangles or missing content.

### Pitfall 3: SWOT Content Without Evidence
**What goes wrong:** SWOT items state opinions without quantified evidence. Leadership dismisses as "consultant fluff."
**Why it happens:** Rushing through content creation without citing specific data points.
**How to avoid:** Every SWOT item (S/W/O/T) must have an `evidence` field in the YAML. Template should render evidence inline. Use specific numbers: version numbers, pricing, benchmark results, community metrics.
**Warning signs:** SWOT items with only 1-2 generic sentences; no numbers or citations.

### Pitfall 4: Undecided SWOTs That Don't Enable Decisions
**What goes wrong:** Snowflake and Data Model SWOTs present options but don't give leadership enough information to actually decide.
**Why it happens:** Fear of being wrong; presenting "balanced" analysis that is actually uncommitted.
**How to avoid:** Each undecided SWOT must include a clear recommendation with reasoning. The recommendation should be explicit: "We recommend X because Y, unless leadership has information about Z that changes the calculus." Include a decision matrix with weighted criteria.
**Warning signs:** Undecided SWOTs that end with "it depends" instead of a recommendation.

### Pitfall 5: Responsive Design Breaking Tables
**What goes wrong:** Decision matrix tables overflow on tablet screens, requiring horizontal scroll.
**Why it happens:** Tables with many columns don't naturally shrink.
**How to avoid:** Use `overflow-x: auto` on table containers. Reduce font size in tables at tablet breakpoint. Consider stacking some table columns on narrow screens.
**Warning signs:** Horizontal scrollbar appearing on 768px width.

### Pitfall 6: Version Footer Becoming Stale
**What goes wrong:** Footer shows versions from last render, not current state.
**Why it happens:** Versions hardcoded or cached.
**How to avoid:** Render script always reads `docker-compose.yml` fresh at render time. Include generation timestamp in footer.
**Warning signs:** Footer version doesn't match docker-compose.yml.

## Code Examples

### Base SWOT Template Structure
```html
{# docs/templates/base_swot.html #}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }} - Lakehouse Architecture</title>
  <style>
    {% block styles %}
    {# === RESET & BASE === #}
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      max-width: 900px;
      margin: 0 auto;
      padding: 2rem;
      color: #2d3748;
      line-height: 1.6;
      font-size: clamp(0.95rem, 1.5vw, 1.1rem);
    }

    {# === HEADER === #}
    .doc-header {
      background: #1a2332;
      color: white;
      padding: 2rem;
      border-radius: 8px 8px 0 0;
      margin: -2rem -2rem 2rem -2rem;
    }
    .doc-header h1 { color: #c8a961; font-size: 1.8rem; }
    .doc-header .meta { color: #94a3b8; margin-top: 0.5rem; }
    .status-badge {
      display: inline-block;
      padding: 0.25rem 0.75rem;
      border-radius: 4px;
      font-weight: 600;
      font-size: 0.85rem;
    }
    .status-decided { background: #22c55e; color: white; }
    .status-undecided { background: #f59e0b; color: #1a2332; }

    {# === SWOT GRID === #}
    .swot-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin: 1.5rem 0;
    }
    .swot-quadrant {
      padding: 1.25rem;
      border-radius: 6px;
      border: 2px solid;
    }
    .swot-strengths { border-color: #22c55e; background: #f0fdf4; }
    .swot-weaknesses { border-color: #eab308; background: #fefce8; }
    .swot-opportunities { border-color: #3b82f6; background: #eff6ff; }
    .swot-threats { border-color: #ef4444; background: #fef2f2; }

    {# === DETAILS/SUMMARY === #}
    details {
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      margin-bottom: 1rem;
    }
    summary {
      padding: 0.75rem 1rem;
      background: #f8fafc;
      cursor: pointer;
      font-weight: 600;
      color: #1a2332;
      list-style: none;
    }
    summary::-webkit-details-marker { display: none; }
    summary::marker { display: none; }
    summary::before {
      content: "\25B6";
      display: inline-block;
      margin-right: 0.5rem;
      font-size: 0.75em;
      transition: transform 0.2s;
    }
    details[open] > summary::before {
      transform: rotate(90deg);
    }
    details > :not(summary) { padding: 1rem; }

    {# === TABLES === #}
    table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
    th, td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
    th { background: #1a2332; color: white; font-weight: 600; }
    tr:nth-child(even) { background: #f8fafc; }

    {# === FOOTER === #}
    .doc-footer {
      margin-top: 3rem;
      padding-top: 1.5rem;
      border-top: 2px solid #1a2332;
      font-size: 0.85rem;
      color: #64748b;
    }
    .doc-footer .versions { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; }
    .doc-footer .version-item { white-space: nowrap; }

    {# === RESPONSIVE === #}
    @media (max-width: 768px) {
      body { padding: 1rem; }
      .doc-header { margin: -1rem -1rem 1.5rem -1rem; padding: 1.5rem; }
      .swot-grid { grid-template-columns: 1fr; }
      table { font-size: 0.85rem; }
      .table-container { overflow-x: auto; }
    }

    {# === PRINT === #}
    @media print {
      body { max-width: none; padding: 0; font-size: 10pt; color: black; }
      .doc-header { background: white; color: #1a2332; border: 2px solid #1a2332; }
      .doc-header h1 { color: #1a2332; }
      details::details-content { display: block !important; }
      summary::before { display: none; }
      .swot-grid { break-inside: avoid; }
      .swot-quadrant { break-inside: avoid; }
      a { text-decoration: none; color: inherit; }
      @page { margin: 2cm; }
    }
    {% endblock styles %}
  </style>
</head>
<body>
  {% block header %}
  <header class="doc-header">
    <h1>{{ title }}</h1>
    <p class="meta">
      <span class="status-badge status-{{ status }}">{{ status|capitalize }}</span>
      {% if decision %} | Decision: {{ decision }}{% endif %}
      | {{ date }}
    </p>
  </header>
  {% endblock header %}

  {% block content %}{% endblock content %}

  {% block footer %}
  <footer class="doc-footer">
    <p>Generated: {{ generation_date }} | Next review: {{ next_review }}</p>
    <div class="versions">
      {% for name, info in versions.items() %}
      <span class="version-item">{{ name }}: {{ info.version }}</span>
      {% endfor %}
    </div>
  </footer>
  {% endblock footer %}
</body>
</html>
```

### SWOT Quadrant 2x2 Grid Macro
```html
{# docs/templates/macros/swot_grid.html #}
{% macro swot_grid(strengths, weaknesses, opportunities, threats) %}
<div class="swot-grid">
  <div class="swot-quadrant swot-strengths">
    <h3>Strengths</h3>
    <ul>
      {% for item in strengths %}
      <li><strong>{{ item.id }}: {{ item.title }}</strong></li>
      {% endfor %}
    </ul>
  </div>
  <div class="swot-quadrant swot-weaknesses">
    <h3>Weaknesses</h3>
    <ul>
      {% for item in weaknesses %}
      <li><strong>{{ item.id }}: {{ item.title }}</strong></li>
      {% endfor %}
    </ul>
  </div>
  <div class="swot-quadrant swot-opportunities">
    <h3>Opportunities</h3>
    <ul>
      {% for item in opportunities %}
      <li><strong>{{ item.id }}: {{ item.title }}</strong></li>
      {% endfor %}
    </ul>
  </div>
  <div class="swot-quadrant swot-threats">
    <h3>Threats</h3>
    <ul>
      {% for item in threats %}
      <li><strong>{{ item.id }}: {{ item.title }}</strong></li>
      {% endfor %}
    </ul>
  </div>
</div>
{% endmacro %}
```

### Render Script Structure
```python
#!/usr/bin/env python3
"""Render all SWOT HTML deliverables from YAML data + Jinja2 templates."""

from __future__ import annotations

import yaml
from datetime import date
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "docs" / "templates"
SWOT_DATA_DIR = PROJECT_ROOT / "docs" / "swot" / "data"
SWOT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "swot"
COMPOSE_PATH = PROJECT_ROOT / "docker-compose.yml"


def extract_versions() -> dict:
    """Extract service versions from docker-compose.yml image tags."""
    compose = yaml.safe_load(COMPOSE_PATH.read_text())
    versions = {}
    key_services = ["nessie", "trino", "cube-api", "ranger-admin",
                    "marquez", "openmetadata-server"]
    for svc, cfg in compose.get("services", {}).items():
        if svc in key_services:
            image = cfg.get("image", "")
            if ":" in image:
                _, ver = image.rsplit(":", 1)
                versions[svc] = {"version": ver}
    return versions


def render_swots():
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    versions = extract_versions()
    generation_date = date.today().isoformat()

    for data_file in sorted(SWOT_DATA_DIR.glob("*.yml")):
        swot_data = yaml.safe_load(data_file.read_text())
        template = env.get_template("base_swot.html")
        html = template.render(
            **swot_data,
            versions=versions,
            generation_date=generation_date,
        )
        output_name = data_file.stem + "-swot.html"
        (SWOT_OUTPUT_DIR / output_name).write_text(html)
        print(f"  Rendered: {output_name}")

    # Render index page
    # ... similar pattern with index template


if __name__ == "__main__":
    render_swots()
```

## SWOT Content Research

### SWOT-02: Iceberg Catalog (Decided: Nessie)
**Content source:** `docs/swot/nessie-catalog-swot.md` (176 lines, complete)
**Action:** Convert existing markdown to YAML data format. Enhance with 2x2 grid summary.
**Confidence:** HIGH -- content already exists and is comprehensive.

### SWOT-03: Snowflake Strategy (Undecided -- HIGHEST PRIORITY)
**Research findings for content:**
- Snowflake supports ICEBERG_REST catalog integration (documented in Snowflake official docs). This enables Snowflake to read Iceberg tables via Nessie without data copying.
- Snowflake Open Catalog (formerly Polaris) is GA. Free until April 30, 2025; billing begins mid-2026.
- Snowflake consumption pricing: credits cost $2-4 each on-demand, $1.50-2.50 with annual commitments. Compute is ~80% of bill.
- Trino-based lakehouse can achieve up to 55% lower TCO over 3 years vs Snowflake (Starburst benchmark data -- note vendor bias).
- Three strategic options: (1) Retire Snowflake entirely, route all queries through Trino; (2) Keep Snowflake as Iceberg compute-only via ICEBERG_REST; (3) Maintain current state with data copies.
- Key decision factors: existing Snowflake skillsets on team, current contract terms, workload types (ad-hoc BI vs batch ETL), governance/audit requirements.
**Confidence:** MEDIUM -- Snowflake pricing varies by contract; Starburst TCO claims are vendor-sourced.

### SWOT-04: DataStage Migration (Decided: Phased Python)
**Content sources:**
- `docs/etl-patterns.md` (565 lines): Comprehensive ETL patterns guide already written
- `etl/src/pipelines/`: BasePipeline framework with working implementations
- v1.0 delivered ETL-01 through ETL-05 successfully
**Key evidence points:** 480 tests passing, pilot migration of 5-10 DataStage jobs complete, BasePipeline pattern established, Airflow orchestration working.
**Confidence:** HIGH -- evidence is in the codebase.

### SWOT-05: Data Model Strategy (Undecided -- HIGHEST PRIORITY)
**Research findings for content:**
- Teradata FSDM is a proprietary data model for financial services covering: Party, Account, Instrument, Transaction, Risk, Compliance domains.
- Current state: "partially followed" (from PROJECT.md) -- implies some tables aligned, others not.
- Three strategic options: (1) Keep FSDM as-is in new lakehouse; (2) Evolve FSDM incrementally, adding medallion conventions while preserving entity names; (3) New medallion-native model (break from FSDM).
- Key insight from codebase: Gold tables (`gold.trading_metrics`, `gold.risk_exposure`) already follow medallion patterns, not strict FSDM entity naming. This suggests de facto evolution is already happening.
- Backward compatibility is critical: 40+ engineers know FSDM conventions; breaking changes have high friction.
- `glossary-seed.json` not found in repository root -- may need to be created or located elsewhere.
**Confidence:** MEDIUM -- FSDM coverage must be inferred from codebase; no direct FSDM schema files found.

### SWOT-06: BI Semantic Layer (Decided: Cube)
**Content sources:**
- `semantic/model/cubes/trading_metrics.yml` and `risk_exposure.yml`: Working Cube model definitions
- `docker-compose.yml`: Cube v0.36.0 deployed with Trino backend, SQL API on port 15432
- v1.0 delivered BISEM-01 through BISEM-04 (Tableau and Power BI connected)
**Key evidence points:** Cube provides unified metric definitions, PostgreSQL wire protocol for BI tools, pre-aggregation support, glossary term linkage.
**Confidence:** HIGH -- working implementation in codebase.

### SWOT-07: AI Semantic Layer (Decided: Build-own)
**Content sources:**
- `etl/src/semantic/nl_to_sql.py`: NLToSQLEngine using Claude Sonnet on Bedrock
- `etl/src/semantic/metric_context.py`, `prompt_builder.py`: Supporting modules
- `etl/src/semantic/golden_datasets/`: Evaluation datasets
- v1.0 delivered AISEM-01 through AISEM-03
**Key evidence points:** Uses Cube YAML definitions as context for LLM prompts; few-shot examples per domain; accuracy benchmarked (AISEM-03 confirmed).
**Confidence:** HIGH -- working implementation in codebase.

## Platform Versions (from docker-compose.yml)

For the ARCH-09 version-stamped footer, these are the definitive versions:

| Service | Image | Version |
|---------|-------|---------|
| Nessie | ghcr.io/projectnessie/nessie | 0.107.4 |
| Trino | trinodb/trino | 479 |
| Cube API | cubejs/cube | v0.36.0 |
| Cube Store | cubejs/cubestore | v0.36.0 |
| Ranger Admin | apache/ranger | 2.8.0 |
| Marquez | marquezproject/marquez | 0.50.0 |
| OpenMetadata | docker.getcollate.io/openmetadata/server | 1.6.0 |
| PostgreSQL | postgres | 15 |
| Elasticsearch | docker.elastic.co/elasticsearch/elasticsearch | 8.15.0 |
| Grafana | grafana/grafana | latest |
| Prometheus | prom/prometheus | latest |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JS-based accordions | `<details>/<summary>` native HTML | HTML5 (2014+), widely adopted | No JavaScript needed for collapsible sections |
| CSS cannot open `<details>` | `::details-content` pseudo-element | September 2025 (baseline) | CSS-only print expansion now possible |
| Separate CSS files | Embedded `<style>` for standalone | N/A (project requirement) | Files work on file:// protocol |
| px-based responsive | `clamp()` fluid typography | 2023-2025 | Fewer breakpoints needed, smoother scaling |
| Snowflake data copies | Snowflake ICEBERG_REST integration | 2024-2025 | Snowflake can read Iceberg tables via REST catalog without data copies |
| Polaris (separate project) | Snowflake Open Catalog (managed Polaris) | Late 2024 | Polaris rebranded as Snowflake service; free until 2025, billing mid-2026 |

**Deprecated/outdated:**
- Checkbox-hack collapsible CSS: Superseded by native `<details>/<summary>` elements. Do not use hidden checkbox pattern.
- `<details>` without `::details-content`: Old print workaround required JavaScript. With `::details-content` now baseline, CSS-only print expansion is the standard approach.

## Open Questions

1. **`glossary-seed.json` location**
   - What we know: Referenced in CONTEXT.md as evidence for SWOT-05 (Data Model Strategy)
   - What's unclear: File not found at repository root or common locations
   - Recommendation: Check if it was created during v1.0 Phase 3 (governance) or if it needs to be created. If absent, infer FSDM terms from Cube YAML model definitions and Gold table schemas.

2. **Snowflake contract terms**
   - What we know: Snowflake exists in current architecture with data copies from Teradata/Cloudera
   - What's unclear: Current contract terms, credit commitments, expiration dates
   - Recommendation: SWOT-03 should note this as a factor leadership must supply. Present analysis assuming contract flexibility.

3. **FSDM schema coverage depth**
   - What we know: "Partially followed" per PROJECT.md. Gold tables use medallion naming, not strict FSDM.
   - What's unclear: Exact percentage of tables aligned to FSDM vs freeform
   - Recommendation: Infer from Bronze/Silver/Gold table naming patterns in the codebase. The SWOT can present what the codebase shows without claiming exact coverage percentages.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ (from pyproject.toml dev dependencies) |
| Config file | `etl/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd etl && python -m pytest tests/ -x -m unit --timeout=30` |
| Full suite command | `cd etl && python -m pytest tests/ -ra` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SWOT-01 | Shared CSS template renders valid HTML with embedded styles | unit | `python -m pytest tests/test_html_render.py::test_css_embedded -x` | No -- Wave 0 |
| SWOT-02 | Nessie SWOT renders with all sections | unit | `python -m pytest tests/test_html_render.py::test_nessie_swot -x` | No -- Wave 0 |
| SWOT-03 | Snowflake SWOT renders with recommendation | unit | `python -m pytest tests/test_html_render.py::test_snowflake_swot -x` | No -- Wave 0 |
| SWOT-04 | DataStage SWOT renders with evidence | unit | `python -m pytest tests/test_html_render.py::test_datastage_swot -x` | No -- Wave 0 |
| SWOT-05 | Data Model SWOT renders with decision matrix | unit | `python -m pytest tests/test_html_render.py::test_data_model_swot -x` | No -- Wave 0 |
| SWOT-06 | BI Semantic SWOT renders with Cube evidence | unit | `python -m pytest tests/test_html_render.py::test_bi_semantic_swot -x` | No -- Wave 0 |
| SWOT-07 | AI Semantic SWOT renders with NL-to-SQL evidence | unit | `python -m pytest tests/test_html_render.py::test_ai_semantic_swot -x` | No -- Wave 0 |
| SWOT-08 | Index page links all 6 SWOTs with correct badges | unit | `python -m pytest tests/test_html_render.py::test_index_page -x` | No -- Wave 0 |
| SWOT-09 | HTML contains details/summary elements | unit | `python -m pytest tests/test_html_render.py::test_collapsible_sections -x` | No -- Wave 0 |
| SWOT-10 | HTML contains responsive meta viewport and media queries | unit | `python -m pytest tests/test_html_render.py::test_responsive_meta -x` | No -- Wave 0 |
| ARCH-09 | Footer contains generation date and version strings | unit | `python -m pytest tests/test_html_render.py::test_version_footer -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd etl && python -m pytest tests/test_html_render.py -x --timeout=30`
- **Per wave merge:** `cd etl && python -m pytest tests/ -ra`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `etl/tests/test_html_render.py` -- covers SWOT-01 through SWOT-10, ARCH-09 (validates rendered HTML structure)
- [ ] Test fixtures: sample YAML data files for template rendering tests
- [ ] Render script must be importable (not just a CLI script) for test usage

## Sources

### Primary (HIGH confidence)
- Jinja2 official documentation (https://jinja.palletsprojects.com/en/stable/templates/) -- template inheritance, Environment, FileSystemLoader
- MDN `<details>` element (https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details) -- open attribute, browser support
- MDN `::details-content` (https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Selectors/::details-content) -- baseline September 2025, print expansion capability
- Snowflake official docs (https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration-rest) -- ICEBERG_REST catalog integration
- Project codebase: `docker-compose.yml` (574 lines) -- definitive version inventory
- Project codebase: `docs/swot/nessie-catalog-swot.md` (176 lines) -- existing SWOT content template
- Project codebase: `etl/pyproject.toml` -- Python dependencies and test configuration

### Secondary (MEDIUM confidence)
- W3C CSSWG issue #2084 (https://github.com/w3c/csswg-drafts/issues/2084) -- `::details-content` proposal history
- BrowserStack responsive breakpoints guide (https://www.browserstack.com/guide/responsive-design-breakpoints) -- 768px tablet breakpoint standard
- Snowflake pricing (https://mammoth.io/blog/snowflake-pricing/) -- consumption pricing model ($2-4/credit)
- Starburst Trino vs Snowflake comparison (https://www.starburst.io/blog/snowflake-alternatives/) -- TCO claims (vendor-sourced, treat with caution)

### Tertiary (LOW confidence)
- FSDM coverage in this project: inferred from codebase patterns, not from a definitive schema inventory
- Snowflake exact contract pricing: varies by organization, cannot be researched externally

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Jinja2/PyYAML already installed and verified; standard Python templating
- Architecture: HIGH -- Template inheritance pattern is well-documented; CSS patterns verified against MDN
- Pitfalls: HIGH -- `::details-content` print behavior verified via MDN; file:// protocol requirements clear
- SWOT content (decided): HIGH -- 4 of 6 SWOTs have strong evidence in existing codebase
- SWOT content (undecided): MEDIUM -- Snowflake and Data Model SWOTs require synthesis from web research and codebase inference

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable domain; CSS specs and Jinja2 unlikely to change)
