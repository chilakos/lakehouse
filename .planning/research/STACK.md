# Stack Research: Documentation Deliverables (v1.1)

**Domain:** Documentation generation for lakehouse platform (SWOT HTML pages, architecture diagrams, developer docs, API reference, data catalog docs)
**Researched:** 2026-03-14
**Confidence:** HIGH -- all recommended tools are mature, well-documented Python ecosystem staples

---

## Scope

This stack research covers ONLY the additions needed for milestone v1.1 documentation deliverables. The existing lakehouse stack (PySpark, Trino, Iceberg, Airflow, etc.) is validated and out of scope.

**Deliverables to produce:**
1. 6 SWOT analyses as polished standalone HTML with embedded CSS
2. Marketecture HTML page (executive-friendly platform overview)
3. Detailed architecture HTML page (component/port/flow diagram)
4. Developer onboarding documentation
5. Full API/module reference documentation (47 Python source files across 12 packages)
6. Contributor guidelines
7. Data catalog/glossary documentation for business users

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Jinja2 | 3.1.6 | HTML templating for SWOT pages, architecture pages, catalog docs | Already installed (dependency of Airflow/Soda). Industry standard for Python HTML generation. Template inheritance for consistent branding across all doc pages. No web framework needed -- standalone `Environment` + `FileSystemLoader` renders to static files. |
| Mermaid.js | 11.x (CDN) | Architecture diagrams, data flow diagrams, component diagrams | Text-based diagram-as-code renders client-side in the browser. No server-side rendering needed for standalone HTML pages. CDN embed means zero build dependencies. Supports flowcharts, C4-style architecture, sequence diagrams, entity-relationship diagrams. |
| pdoc | >=15.0.0,<17.0.0 | Python API/module reference documentation | Zero-config API doc generator. Reads existing docstrings and type annotations. Outputs standalone HTML. Supports Google-style, NumPy, and Markdown docstrings. Customizable templates. Far simpler than Sphinx for a project of this size (47 files). |
| Pygments | >=2.19.0,<3.0.0 | Syntax highlighting in developer docs and code examples | Already installed (dependency of Airflow). 500+ language support. HTML output with CSS classes. Used by pdoc internally. Upgrade from 2.17.2 to 2.19.x for latest Python 3.12 syntax support. |
| Markdown | >=3.7.0,<4.0.0 | Markdown-to-HTML conversion for developer guides and catalog docs | Standard Python Markdown processor. Extensions for tables, fenced code blocks, table of contents. Converts existing `.md` docs (etl-patterns.md, ADRs) to styled HTML pages. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| MarkupSafe | >=3.0.0,<4.0.0 | Safe HTML string handling (Jinja2 dependency) | Already installed (2.1.5). Upgrade alongside Jinja2. Auto-escapes untrusted content in templates. |
| PyYAML | >=6.0 | SWOT data ingestion from structured YAML files | Already installed (ETL dependency). Define SWOT strengths/weaknesses/opportunities/threats as YAML, render via Jinja2 templates. Separates content from presentation. |
| Pydantic | >=2.0.0 | Validate SWOT/catalog data models before rendering | Already in stack. Define typed models for SWOT entries, catalog glossary terms, architecture components. Catches data errors before they become rendering errors. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pdoc dev server | Live preview of API docs during development | `pdoc --port 8080 etl/src` serves with live reload. No additional tool needed. |
| Python http.server | Local preview of generated HTML pages | `python -m http.server 8000 -d docs/html/` -- built into Python stdlib. No installation. |
| ruff | Lint documentation generation scripts | Already in dev dependencies (0.9.x). Use for any new Python scripts in `docs/`. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Sphinx | Massive configuration overhead for 47 Python files. RST syntax has steep learning curve. Over-engineered for this project's API doc needs. | pdoc -- zero config, Markdown docstrings, standalone HTML output |
| MkDocs / MkDocs-Material | Full static site generator with its own build system, config files, nav structure. Adds operational complexity for what are essentially standalone HTML deliverables. | Jinja2 templates -- direct control, no build system, produces exactly the standalone HTML pages leadership expects |
| mkdocs-mermaid-to-svg / mmdc (CLI) | Adds Node.js dependency to a Python project. Server-side SVG rendering is unnecessary when Mermaid renders client-side in the browser. | Mermaid.js via CDN script tag -- renders in browser, zero build deps |
| WeasyPrint | HTML-to-PDF converter. Not in scope -- deliverables are HTML pages, not PDFs. Would add heavy C library dependencies (cairo, pango). | Deliver HTML. If PDF is later requested, browser Print-to-PDF works for these page types. |
| Docusaurus / GitBook / ReadTheDocs | Full documentation platforms with hosting, search, versioning. Over-engineering for internal deliverables shared as HTML files. | Jinja2 standalone HTML pages for SWOT/architecture. pdoc for API docs. |
| React / Vue / any JS framework | SWOT pages and architecture diagrams do not need SPA complexity. Standalone HTML with embedded CSS and Mermaid.js is sufficient. | Vanilla HTML + CSS + Mermaid.js CDN |
| Graphviz / D2 / PlantUML | Additional diagram tools when Mermaid covers all needed diagram types (flowcharts, C4, ER, sequence). Adding another tool fragments the diagram authoring experience. | Mermaid.js for all diagram types |
| Custom CSS framework build (Tailwind, PostCSS) | Build toolchain complexity for documentation pages. These pages need professional styling, not a design system. | Embedded CSS in Jinja2 templates. One shared `<style>` block per template. Clean, maintainable, self-contained. |

---

## Architecture: How the Pieces Fit Together

```
docs/
  templates/                    # Jinja2 HTML templates
    base.html                   # Shared layout: nav, footer, embedded CSS
    swot.html                   # SWOT analysis template (extends base)
    architecture.html           # Architecture diagram template (extends base)
    catalog.html                # Data catalog/glossary template (extends base)
    guide.html                  # Developer guide template (extends base)
  data/
    swot/                       # YAML files with SWOT content
      iceberg-catalog.yaml
      snowflake-strategy.yaml
      datastage-migration.yaml
      data-model-strategy.yaml
      bi-semantic-layer.yaml
      ai-semantic-layer.yaml
    catalog/                    # YAML files with data catalog entries
      glossary.yaml
      datasets.yaml
    architecture/               # Mermaid diagram definitions
      marketecture.mmd
      detailed.mmd
  scripts/
    build_docs.py               # Main build script: reads YAML, renders Jinja2 templates
    build_api_docs.py           # Runs pdoc to generate API reference
  output/                       # Generated HTML (gitignored, built by CI)
    swot/
    architecture/
    developer/
    api/
    catalog/

etl/src/                        # Existing 47 Python files -- pdoc reads these directly
```

### Data Flow

```
YAML content files ──> Pydantic validation ──> Jinja2 rendering ──> Standalone HTML pages
                                                    |
                                              Mermaid.js CDN ──> Diagrams render client-side
                                                    |
                                              Embedded CSS ──> Professional styling

Python source files ──> pdoc ──> API reference HTML
```

### Key Design Decisions

1. **Standalone HTML pages** -- Each HTML file works when opened directly in a browser or served from any web server. No build step needed to view. Leadership can open SWOT files directly.

2. **Content-presentation separation** -- SWOT analysis content lives in YAML files. Templates live in Jinja2 HTML files. This means subject matter experts can edit YAML without touching HTML/CSS, and designers can update templates without touching content.

3. **Client-side Mermaid rendering** -- Mermaid.js loads from CDN and renders diagrams in the browser. This avoids adding Node.js/Puppeteer/Chromium to the build pipeline. Diagrams are defined as text in `.mmd` files or inline in templates.

4. **Embedded CSS** -- Each base template includes a `<style>` block with all CSS. This keeps HTML files truly standalone (no external CSS file to lose). The CSS is defined once in the base template and inherited by all child templates.

---

## Detailed Technology Rationale

### Jinja2 for HTML Templating

**Why Jinja2 and not raw string formatting or f-strings:**
- Template inheritance (`{% extends "base.html" %}`) means one place to change header/footer/CSS across all pages
- Auto-escaping prevents XSS if any user-provided content enters templates
- Loops and conditionals for rendering SWOT matrices, catalog tables, etc.
- Filters (`{{ value | title }}`, `{{ text | markdown }}`) for data transformation in templates
- Already a transitive dependency -- zero additional installation

**Why Jinja2 and not a static site generator:**
- The output is ~15-20 HTML pages, not a documentation website
- No navigation structure, search index, or sitemap needed
- Leadership expects to open standalone HTML files, not visit a hosted site
- A 50-line Python build script replaces an entire SSG configuration

**Configuration:**
```python
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader("docs/templates"),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
```

### Mermaid.js for Architecture Diagrams

**Why Mermaid.js and not a Python diagramming library (diagrams, matplotlib, graphviz):**
- Text-based source (`.mmd` files) is version-controllable and diffable
- Renders in the browser -- no build dependency, no image pipeline
- Supports all needed diagram types: flowcharts (architecture), C4 (marketecture), ER (data model), sequence (data flow)
- Interactive -- users can zoom, pan in modern browsers
- Widely known by developers -- lower maintenance burden

**CDN Embedding (no npm/node required):**
```html
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: { curve: 'basis' }
  });
</script>
```

**Diagram blocks in HTML:**
```html
<pre class="mermaid">
graph LR
    A[Source Systems] --> B[Bronze Layer]
    B --> C[Silver Layer]
    C --> D[Gold Layer]
    D --> E[Cube Semantic Layer]
    E --> F[Tableau/Power BI]
    E --> G[NL-to-SQL AI]
</pre>
```

**Offline fallback:** If standalone HTML must work without internet access (air-gapped environments), download `mermaid.esm.min.mjs` (~200KB) and embed it alongside the HTML files. Add this as a build step option in `build_docs.py`.

### pdoc for API Reference Documentation

**Why pdoc and not Sphinx:**

| Criterion | pdoc | Sphinx |
|-----------|------|--------|
| Configuration | Zero config | conf.py + Makefile + RST files |
| Docstring format | Google/NumPy/Markdown (all work) | RST preferred, others via extensions |
| Setup time | `pip install pdoc && pdoc src/` | Hours of configuration |
| Output quality | Clean, modern HTML | Powerful but dated default theme |
| Learning curve | None for team of 40 | Significant -- RST syntax, directive system |
| Customization | Jinja2 templates (same as our stack) | Jinja2 templates (but within Sphinx ecosystem) |
| Project scale fit | Perfect for 47 files across 12 packages | Designed for large projects (CPython, Django) |

**Usage:**
```bash
# Generate API docs to output directory
pdoc etl/src/ -o docs/output/api/

# Live preview during development
pdoc etl/src/ --port 8080

# With custom template for branding consistency
pdoc etl/src/ -o docs/output/api/ --template-directory docs/templates/pdoc/
```

**pdoc reads the existing code structure directly:**
```
etl/src/
  pipelines/          --> API docs for BasePipeline, Bronze/Silver/Gold pipelines
  governance/         --> API docs for audit, classification, lineage, ranger
  quality/            --> API docs for scanner, reconciliation
  semantic/           --> API docs for NL-to-SQL, prompt builder, evaluation
  iceberg_utils/      --> API docs for catalog, trino, maintenance
  inventory/          --> API docs for catalog inventory, models
  config/             --> API docs for settings
  synthetic/          --> API docs for test data generation
```

### Markdown Library for Developer Guides

**Why the Python `markdown` library and not raw HTML:**
- Developer guides are best authored in Markdown (lower barrier for 40 engineers)
- Existing docs (`etl-patterns.md`, ADRs) are already Markdown
- Extensions handle tables, code blocks, TOC generation
- Output feeds into Jinja2 templates for consistent styling

**Configuration:**
```python
import markdown

md = markdown.Markdown(
    extensions=[
        "tables",
        "fenced_code",
        "codehilite",      # Uses Pygments for syntax highlighting
        "toc",             # Table of contents generation
        "attr_list",       # HTML attributes on Markdown elements
    ],
    extension_configs={
        "codehilite": {"css_class": "highlight", "linenums": False},
    },
)

html_content = md.convert(markdown_text)
```

---

## Installation

```bash
# Documentation dependencies (add to pyproject.toml [project.optional-dependencies])
pip install \
    "Jinja2>=3.1.0,<4.0.0" \
    "pdoc>=15.0.0,<17.0.0" \
    "Markdown>=3.7.0,<4.0.0" \
    "Pygments>=2.19.0,<3.0.0"

# Already installed (no action needed):
#   Jinja2 3.1.6     -- via Airflow/Soda dependency
#   MarkupSafe 2.1.5 -- via Jinja2 dependency
#   Pygments 2.17.2  -- via Airflow dependency (upgrade to 2.19.x recommended)
#   PyYAML 6.x       -- via ETL dependency
#   Pydantic 2.x     -- via ETL/Cube dependency

# NOT installed (new additions):
#   pdoc      -- API documentation generator
#   Markdown  -- Markdown-to-HTML conversion
```

### pyproject.toml Addition

```toml
[project.optional-dependencies]
docs = [
    "pdoc>=15.0.0,<17.0.0",
    "Markdown>=3.7.0,<4.0.0",
    "Pygments>=2.19.0,<3.0.0",
]
```

**Net new dependencies: 2** (pdoc, Markdown). Everything else is already installed or a transitive dependency. This is intentionally minimal.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Jinja2 standalone | MkDocs-Material | If deliverables evolve into a hosted documentation site with search, versioning, and navigation. Not needed for ~20 standalone HTML pages. |
| Jinja2 standalone | Sphinx | If the project grows to 500+ Python files with complex cross-referencing needs, or if RST-based documentation is preferred by the team. |
| Mermaid.js (CDN) | mermaid-cli (mmdc via npm) | If you need to pre-render diagrams as static SVG files (e.g., for embedding in PDFs or emails). Requires Node.js. |
| Mermaid.js (CDN) | Python `diagrams` library | If you need cloud-provider-specific icons (AWS, GCP, Azure) in architecture diagrams. Generates PNG/SVG from Python code. |
| pdoc | Sphinx + autodoc | If the team already uses RST docstrings, or if you need Sphinx-specific features like intersphinx linking to external projects. |
| pdoc | mkdocstrings (MkDocs plugin) | If you adopt MkDocs for all documentation and want API docs integrated into the same site. |
| Embedded CSS | Tailwind CSS (via CDN) | If the number of doc pages grows significantly and you want utility-class styling. For ~20 pages, embedded CSS is cleaner. |
| Markdown library | mistune | If you need a faster Markdown parser. Python-Markdown is fast enough for documentation builds and has better extension support. |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Jinja2 3.1.x | Python >=3.8 | Already installed 3.1.6. No upgrade needed. |
| pdoc >=15.0.0 | Python >=3.9 | Project requires >=3.11, so compatible. Uses Jinja2 internally for its own templates. |
| Markdown >=3.7.0 | Python >=3.8 | No conflicts with existing stack. |
| Pygments >=2.19.0 | Python >=3.8 | Upgrade from 2.17.2 to 2.19.x adds Python 3.12 syntax support, TOML improvements. |
| Mermaid.js 11.x | Any modern browser | CDN-loaded. No Python dependency. IE11 not supported (not a concern). |
| MarkupSafe 3.0.x | Python >=3.9, Jinja2 >=3.1.0 | Optional upgrade from 2.1.5. Not strictly required but adds Python 3.14 support. |

---

## CI/CD Integration

Documentation builds should be added to the existing GitHub Actions workflow:

```yaml
# .github/workflows/docs.yml (or add as job to existing CI)
docs-build:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - run: pip install -e ".[docs]"
    - run: python docs/scripts/build_docs.py
    - run: pdoc etl/src/ -o docs/output/api/
    - uses: actions/upload-artifact@v4
      with:
        name: documentation
        path: docs/output/
```

No Node.js setup step needed. No Docker services needed. Documentation builds are pure Python + CDN references.

---

## Stack Patterns by Variant

**If SWOT pages need to work in air-gapped/offline environments:**
- Download `mermaid.esm.min.mjs` from CDN and bundle alongside HTML files
- All CSS is already embedded -- no external dependencies
- Add a `--offline` flag to `build_docs.py` that switches CDN URLs to local file paths

**If leadership later requests PDF output:**
- Use browser Print-to-PDF (Ctrl+P) -- standalone HTML pages are print-friendly with `@media print` CSS rules in the base template
- If automated PDF generation is needed, add WeasyPrint at that point (not now)
- Do not pre-optimize for PDF -- the deliverables are HTML

**If the team later wants a hosted documentation site:**
- Migrate Jinja2 templates to MkDocs-Material (Markdown-native, similar template system)
- pdoc output can be hosted as-is or integrated via mkdocstrings
- This migration is straightforward because content is already in YAML/Markdown

---

## Sources

- [Jinja2 on PyPI](https://pypi.org/project/Jinja2/) -- Version 3.1.6 confirmed (HIGH confidence)
- [Jinja2 Template Designer Documentation](https://jinja.palletsprojects.com/en/stable/templates/) -- Template inheritance, filters, autoescaping (HIGH confidence)
- [pdoc on PyPI](https://pypi.org/project/pdoc/) -- Version 16.0.0 confirmed Oct 2025 (HIGH confidence)
- [pdoc documentation](https://pdoc.dev/) -- Zero-config usage, custom templates, output modes (HIGH confidence)
- [Mermaid.js official site](https://mermaid.js.org/) -- Version 11.x, CDN usage guide (HIGH confidence)
- [Mermaid.js Getting Started](https://mermaid.js.org/intro/getting-started.html) -- CDN embed pattern confirmed (HIGH confidence)
- [Mermaid.js GitHub releases](https://github.com/mermaid-js/mermaid/releases) -- Version 11.12.x latest (HIGH confidence)
- [Pygments on PyPI](https://pypi.org/project/Pygments/) -- Version 2.19.2 confirmed (HIGH confidence)
- [Python-Markdown on PyPI](https://pypi.org/project/Markdown/) -- Version 3.10.2, Feb 2026 (HIGH confidence)
- [MarkupSafe on PyPI](https://pypi.org/project/MarkupSafe/) -- Version 3.0.3, Sep 2025 (HIGH confidence)
- [Write HTML in Python with Jinja2](https://brandonjay.dev/posts/2021/write-html-in-python-with-jinja2) -- Standalone usage pattern without web framework (MEDIUM confidence)
- [pdoc vs Sphinx comparison](https://medium.com/@peterkong/comparison-of-python-documentation-generators-660203ca3804) -- Feature comparison supporting pdoc for smaller projects (MEDIUM confidence)
- [Mermaid CDN usage](https://mermaid.js.org/config/usage.html) -- Client-side rendering configuration (HIGH confidence)

---
*Stack research for: Lakehouse Documentation Deliverables (v1.1)*
*Researched: 2026-03-14*
