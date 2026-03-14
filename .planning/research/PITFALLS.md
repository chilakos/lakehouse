# Pitfalls Research

**Domain:** Executive and Developer Documentation for Enterprise Lakehouse Data Platform (Financial Services)
**Researched:** 2026-03-14
**Confidence:** HIGH (well-documented failure modes across executive documentation, developer docs, architecture diagrams, and regulatory data catalogs; financial services specifics verified through BCBS 239 compliance literature)

## Critical Pitfalls

### Pitfall 1: SWOT Analyses Reflect Author Bias, Not Evidence-Based Assessment

**What goes wrong:**
SWOT analyses for the 6 technology decisions (catalog choice, Snowflake strategy, DataStage migration, data model strategy, BI semantic layer, AI semantic layer) become opinion documents that confirm pre-existing preferences rather than evidence-driven evaluations. Strengths and opportunities get inflated while weaknesses and threats are minimized. In group settings, this is amplified by groupthink -- team members coalesce around the most senior voice's preference. The result: leadership receives polished documents that look authoritative but contain asymmetric analysis that validates decisions already made, rather than genuinely informing them.

**Why it happens:**
Confirmation bias is inherent to SWOT methodology. Behavioral economics research shows leaders "invariably list too many opportunities and strengths, and too few weaknesses and threats" because overconfidence and optimism biases lead them to disregard risks. When the document author has already formed a preference (e.g., "we should use Nessie" or "we should retire Snowflake"), the SWOT becomes a justification exercise. In financial services, where decisions have regulatory and budget implications running to millions, this creates real risk: leadership signs off on a direction that was never genuinely challenged.

**How to avoid:**
- Require each SWOT to include quantified evidence for every item. "Nessie is better" is not a strength; "Nessie supports REST catalog spec, which 7 of 8 engines in our stack implement" is a strength.
- Apply the "devil's advocate" test: for each strength/opportunity, document a specific scenario where it becomes a weakness/threat. The existing Nessie SWOT in `docs/swot/nessie-catalog-swot.md` already does this reasonably well; use it as the quality bar.
- Have a different person write the Threats section than the Strengths section, or at minimum have someone review each section for symmetry.
- Include a "Confidence" column for each SWOT item indicating whether it is based on internal testing (HIGH), vendor documentation (MEDIUM), or team opinion (LOW).
- Reference the Phase 1 feasibility results where available -- this platform has actual benchmark data, not just theory.

**Warning signs:**
- Strengths section has 6+ items while Threats section has 2-3
- SWOT items use subjective language ("better," "easier," "modern") without metrics
- All 6 SWOT analyses reach the same conclusion the team already informally agreed on
- No SWOT item references actual platform test results or benchmark data from Phase 1
- Leadership asks "what could go wrong?" and the document has no substantive answer

**Phase to address:**
SWOT Analysis phase (first deliverable). Establish the evidence-based template and review process before writing all 6 analyses.

---

### Pitfall 2: Architecture Diagrams Diverge From Reality on Day One

**What goes wrong:**
The marketecture and detailed architecture diagrams are created as point-in-time snapshots, hand-crafted in a design tool or hand-coded HTML/SVG. Within weeks of creation, the actual infrastructure changes (Terraform updates, new services deployed, configuration changes) but the diagrams are never updated. The platform has Nessie, Trino, Iceberg, Airflow, Ranger, OpenMetadata, Cube, dbt, PySpark, MinIO, S3, and more -- that is 12+ major components. A single missed connection or outdated version number makes the entire diagram untrustworthy. Once engineers see one inaccuracy, they stop trusting the diagram entirely.

**Why it happens:**
Diagrams are typically created as static artifacts disconnected from the code and infrastructure that define the actual system. There is no automated feedback loop. The person who created the diagram moves on to other work. Nobody owns "diagram accuracy" as a responsibility. In this platform specifically, the stack is still evolving (Phase 1 plans are not all complete, Phase 2 ETL migration is ahead), so the architecture will change significantly during the documentation milestone.

**How to avoid:**
- For the detailed architecture diagram: generate it from code wherever possible. Use Mermaid, D2, or Structurizr DSL checked into the repo. When infrastructure changes, the diagram source changes in the same PR.
- For the marketecture: accept it is a marketing document that will need periodic human updates, but include a "Last verified: YYYY-MM-DD" date prominently. Schedule quarterly reviews.
- Include a version number and "as-of" date on every diagram. A diagram without a date is worse than no diagram.
- Store diagram source files alongside the infrastructure code they describe (e.g., architecture diagram source in `/docs/` with a CI step that renders it).
- In the detailed diagram, link each component to its actual deployment configuration (Terraform module, Docker Compose service, or Helm chart).

**Warning signs:**
- Diagram shows components or connections that do not exist in `docker-compose.yml`, Terraform modules, or deployment configs
- Diagram was last modified more than 30 days ago while infrastructure PRs have been merging weekly
- Team members reference "the old diagram" vs "the new diagram" -- there should be one diagram
- Diagram shows Teradata OTF integration as complete when Phase 1 Plan 04 (multi-engine validation) is still in progress

**Phase to address:**
Architecture Diagrams phase. Establish the diagram-as-code pattern and CI rendering before the initial creation, not after.

---

### Pitfall 3: Data Catalog Documentation Fails BCBS 239 Auditability Requirements

**What goes wrong:**
The data catalog/glossary documentation is created as static HTML pages or markdown files that describe data assets, business terms, and lineage. However, BCBS 239 (Principle 3: Accuracy and Integrity, Principle 6: Adaptability) requires that data definitions, lineage, and quality metrics be verifiable, current, and auditable -- not just documented. A static glossary that says "Customer ID: unique identifier for customers" without linking to the actual column in OpenMetadata, its lineage through Airflow/OpenLineage, its data quality scores from Soda, and its access controls in Ranger will fail regulatory review. Only 2 of 31 G-SIBs are fully BCBS 239 compliant as of 2024 -- most fail on exactly this kind of documentation gap.

**Why it happens:**
Documentation teams treat the data catalog deliverable as a writing exercise ("describe the data assets in plain language") rather than an integration exercise ("connect business definitions to the live metadata platform"). The platform already has OpenMetadata deployed (Phase 3 completed) with a business glossary capability (GOVN-04 is checked off). Creating a separate static HTML glossary that duplicates what OpenMetadata already provides -- but without the live linkage -- is worse than useless because it creates a second source of truth that will drift.

**How to avoid:**
- The data catalog documentation should be a curated view OF OpenMetadata, not a replacement for it. Generate or link to OpenMetadata for live definitions, lineage, and quality metrics.
- For the static HTML deliverable (needed for offline/executive access), auto-generate it from OpenMetadata's API so it stays in sync. Include a "Generated from OpenMetadata at [timestamp]" watermark.
- Map every glossary term to: (1) the OpenMetadata asset it describes, (2) the Ranger policy that governs access, (3) the OpenLineage lineage path, and (4) the Soda quality check results.
- Include BCBS 239 principle mapping in the catalog documentation itself -- auditors need to see which principle each artifact satisfies.
- Have a compliance officer or risk analyst review the catalog documentation, not just engineers.

**Warning signs:**
- Data catalog HTML has no links back to OpenMetadata
- Business terms are defined in prose but not linked to actual database columns or tables
- Lineage descriptions say "data flows from source X to table Y" without referencing OpenLineage job runs
- No mention of BCBS 239 principles anywhere in the documentation
- Data quality metrics are described qualitatively ("high quality") rather than quantitatively (99.7% completeness, 0 nulls in required fields)

**Phase to address:**
Data Catalog Documentation phase. Must integrate with the live OpenMetadata/governance stack, not be a standalone writing exercise.

---

### Pitfall 4: Developer Documentation Becomes Stale Within One Sprint

**What goes wrong:**
Developer onboarding guides, API references, and contributor guidelines are written once and immediately begin decaying. The onboarding guide says "run `docker-compose up`" but the compose file has been restructured. The API reference documents a function signature that was refactored. The contributor guidelines reference a CI workflow that has been replaced. At $150K/year average salary, each new hire spending a week fighting stale docs costs approximately $3,000 in lost productivity. With 40+ engineers, even modest turnover means this compounds fast. Worse: once developers learn docs are untrustworthy, they stop reading them entirely and default to asking colleagues or reading source code.

**Why it happens:**
Documentation is created as a separate deliverable from the code it describes. When code changes, there is no mechanism that forces documentation to update. PR review processes check code correctness but rarely check documentation accuracy. The platform is actively evolving (ETL migration in Phase 2, multi-engine validation in Phase 1 Plan 04), so the rate of change is high.

**How to avoid:**
- API reference documentation must be auto-generated from code. Use Sphinx with autodoc/AutoAPI for Python modules, or pdoc. The source of truth is docstrings in code, not a separate document.
- Onboarding guide must include testable commands. Add a CI job that runs the "getting started" steps from the onboarding guide in a clean environment. If the guide's commands fail, the CI fails.
- Contributor guidelines should reference CI workflow files by relative path, not by description. "See `.github/workflows/ci.yml` for the test pipeline" stays accurate; "The CI runs pytest then flake8" goes stale.
- Add a `docs-freshness` check: any documentation file not modified in 90 days while its corresponding code directory has been modified gets flagged for review.
- Include "last verified" dates on all procedural documentation (onboarding, setup guides).

**Warning signs:**
- Onboarding guide references files or directories that do not exist in the current repo
- API reference documents functions or classes not present in the current codebase
- New hire asks questions on Slack that are answered in the docs (meaning they either did not find them or did not trust them)
- Documentation PRs are never filed alongside code PRs that change documented behavior

**Phase to address:**
Developer Documentation phase. Establish the auto-generation pipeline and CI freshness checks as part of the documentation infrastructure, before writing content.

---

### Pitfall 5: Marketecture and Detailed Architecture Serve the Wrong Audience

**What goes wrong:**
The marketecture diagram includes too much technical detail (port numbers, protocol specifics, internal service names) making it incomprehensible to executives. Or conversely, the detailed architecture diagram is too abstract ("Data Layer -> Processing Layer -> Consumption Layer") to be useful to engineers. The two diagrams end up being slight variations of each other rather than genuinely different views for different audiences. Executives cannot answer "what does our platform do and what are its capabilities?" from the marketecture. Engineers cannot answer "how do I connect service X to service Y?" from the detailed diagram.

**Why it happens:**
The same person or team creates both diagrams, and they naturally gravitate toward one level of abstraction. Engineers writing for executives add too much technical detail because they think it demonstrates rigor. Product/management writing for engineers oversimplify because they do not understand the interconnections. The lakehouse platform is particularly susceptible because it has complex multi-engine interactions (Trino-Nessie-Iceberg-S3, Teradata-OTF-Iceberg, Snowflake-external-tables) that are hard to simplify without losing critical information.

**How to avoid:**
- Define explicit audience personas BEFORE creating either diagram. Marketecture audience: CIO, CFO, business unit leaders, regulators -- they care about capabilities, data flow direction, and trust/governance. Detailed architecture audience: data engineers, platform engineers, DevOps -- they care about ports, protocols, service dependencies, and failure modes.
- Marketecture rule: no component names that are not also brand names or plain English. "Data Catalog" not "OpenMetadata." "Query Engine" not "Trino 449." "Object Storage" not "MinIO with S3 API on port 9000."
- Detailed architecture rule: every component must show its actual deployment name, version, port, protocol, and connection dependency.
- Have an executive review the marketecture and an engineer review the detailed diagram -- the person reviewing should be the target audience, not the author's peer.
- Test: can a non-technical stakeholder explain the platform's value proposition after viewing the marketecture for 60 seconds? If not, it is too technical.

**Warning signs:**
- Executive stakeholders say "I don't understand the diagram" or never reference it in discussions
- Engineers say "the architecture diagram doesn't show how X connects to Y"
- Both diagrams look nearly identical at a distance
- Marketecture includes IP addresses, port numbers, or configuration details
- Detailed diagram uses marketing language like "unified data fabric" without showing actual service topology

**Phase to address:**
Architecture Diagrams phase. Define audience personas and conduct audience-specific reviews before finalizing.

---

### Pitfall 6: SWOT HTML Deliverables Become Inaccessible or Unrenderable

**What goes wrong:**
Standalone HTML files for the 6 SWOT analyses are built with external dependencies (CDN-hosted CSS frameworks, JavaScript libraries, web fonts, external images) that break when viewed offline, behind a corporate firewall, or after the CDN changes. Financial services firms often have restricted network access -- internal users viewing these HTMLs on air-gapped networks or through email attachments get broken layouts. Alternatively, the HTML is truly standalone but bloated (10+ MB per file) because all assets are inlined, making it impractical to email or load on older machines.

**Why it happens:**
Web developers default to referencing external resources (Bootstrap CDN, Google Fonts, Chart.js CDN). They test in development environments with full internet access and never test on a restricted network. Financial services IT environments are significantly more locked down than typical tech companies -- proxy servers, content filtering, and air-gapped networks are common.

**How to avoid:**
- All HTML must be truly standalone: inline all CSS, inline all JavaScript, embed all images as base64 data URIs, use system fonts (not web fonts).
- Target file size under 500 KB per SWOT document. This is achievable with inline CSS (no framework), minimal JS, and SVG charts instead of raster images.
- Test every HTML file by opening it from the local filesystem (`file://` protocol) with no internet connection. If anything breaks, it is not standalone.
- Use semantic HTML and CSS that degrades gracefully in older browsers -- many financial services firms are not on the latest Chrome.
- Include a print stylesheet so executives can print to PDF without layout breaking.

**Warning signs:**
- HTML files reference `https://cdn.` anything
- HTML files are larger than 2 MB each
- Opening the file locally shows unstyled content, missing fonts, or broken charts
- Print preview shows cut-off content or missing sections
- HTML uses JavaScript frameworks (React, Vue) when static HTML/CSS would suffice

**Phase to address:**
SWOT Analysis phase. Establish the standalone HTML template and test protocol before creating all 6 analyses.

---

### Pitfall 7: Documentation Ignores OpenMetadata as the Living Catalog

**What goes wrong:**
The documentation milestone creates a parallel universe of static documentation files that duplicate information already managed in OpenMetadata (data catalog, business glossary, lineage, data quality). This creates two sources of truth. When the OpenMetadata catalog is updated (new tables, changed definitions, updated lineage), the static documentation is not. Business users and regulators see conflicting information depending on which source they consult. The glossary in OpenMetadata says "Net Revenue = Gross Revenue - Returns - Discounts" while the HTML glossary says "Net Revenue = Total Revenue minus Costs" because someone wrote the HTML version from memory.

**Why it happens:**
Documentation is scoped as "create HTML files" rather than "create a documentation layer over existing metadata platforms." The team already has OpenMetadata deployed and populated (Phase 3 completed, GOVN-04 checked off). The documentation milestone risks treating docs as a greenfield exercise when it should be an integration exercise. Writers who are not familiar with OpenMetadata's API will default to manual content creation.

**How to avoid:**
- Audit OpenMetadata first: what business glossary terms, data assets, lineage graphs, and quality metrics already exist? The documentation deliverable should fill gaps in OpenMetadata, not duplicate it.
- For any data definition that exists in OpenMetadata, the static HTML documentation must link to or be generated from OpenMetadata. Never hand-write a definition that OpenMetadata already has.
- Use OpenMetadata's REST API to pull glossary terms, table descriptions, column descriptions, and lineage for the HTML generation. Build the generation pipeline as code in the repo.
- The contributor guidelines should document how to update OpenMetadata (not just the static docs) when data definitions change.
- Establish a single source of truth rule: data definitions live in OpenMetadata; static docs are generated views.

**Warning signs:**
- Documentation team is writing data definitions in a spreadsheet or markdown file instead of OpenMetadata
- Static glossary HTML has no "Source: OpenMetadata" attribution
- Data definitions in static docs differ from OpenMetadata definitions
- Nobody on the documentation team has OpenMetadata access or API familiarity
- The documentation plan does not mention OpenMetadata integration

**Phase to address:**
Data Catalog Documentation phase. Must be scoped as an integration with OpenMetadata from the start.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hand-write API reference instead of auto-generating from docstrings | Faster initial creation, more narrative control | Every code change requires manual doc update; docs go stale within weeks | Never -- always auto-generate API refs |
| Use a CSS framework (Bootstrap/Tailwind) via CDN for SWOT HTML | Fast, polished styling | Breaks on air-gapped networks, adds external dependency, bloats file size | Never for standalone HTML deliverables |
| Create architecture diagrams in Figma/draw.io instead of code (Mermaid/D2) | More visual control, designer-friendly | Diagrams cannot be versioned in git, no CI validation, no automated rendering from infra changes | Only for the marketecture (which is inherently a design artifact) |
| Write the data catalog as static markdown without OpenMetadata integration | Ship faster, no API integration work needed | Two sources of truth, regulatory risk from stale definitions, manual sync burden | Only as an interim milestone if OpenMetadata API is unavailable |
| Skip the print stylesheet for HTML deliverables | Saves 30 minutes of CSS work per document | Executives print to PDF and get broken layouts, cut-off tables, missing content | Never -- financial services executives print everything |
| Write contributor guidelines without linking to actual CI config files | Easier to write narrative docs | Guidelines describe a CI process that no longer exists after the next workflow change | Never -- always reference config files by path |

## Integration Gotchas

Common mistakes when connecting documentation to the existing platform.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OpenMetadata API for glossary generation | Assuming the API returns formatted HTML-ready content | OpenMetadata returns JSON; you need a rendering layer that formats definitions, lineage, and quality scores into your HTML template |
| Sphinx/pdoc for Python API docs | Running doc generation against installed packages instead of source | Generate from source tree to capture the latest code; add as a CI step so docs are rebuilt on every merge to main |
| Architecture diagram rendering in CI | Using a Mermaid/D2 rendering tool version in CI that differs from local development | Pin the renderer version in CI and document it in contributor guidelines; test rendering in the same Docker environment used for dev |
| OpenLineage lineage data for catalog docs | Pulling lineage from OpenLineage/Marquez API expecting complete graph | Lineage is only captured for pipelines that have actually run with OpenLineage integration; new or modified pipelines may have gaps; validate lineage completeness before generating docs |
| Ranger access policies for catalog documentation | Documenting access policies by reading Ranger UI manually | Use Ranger's REST API to pull current policies programmatically; manual documentation of security policies goes stale immediately |
| Cube/dbt semantic layer for BI documentation | Describing metric definitions in prose without referencing actual Cube/dbt model files | Link documentation to the actual YAML model files; metric definitions should be single-sourced from `semantic/cube/` or `dbt/` config |

## Performance Traps

Patterns that work at small scale but fail as the platform and documentation grow.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Inlining all images as base64 in HTML | SWOT HTML files balloon to 5+ MB; browsers lag on open | Use inline SVG for charts and diagrams; compress any raster images; keep total file under 500 KB | When executives try to email HTML files or open multiple simultaneously |
| Single monolithic HTML file for all API documentation | Page loads slowly; browser search is sluggish; no deep linking | Split API docs by module/package with an index page; or use a static site generator with search | When API surface exceeds 50+ modules (this platform has etl/, infra/, semantic/, dbt/) |
| Generating full data catalog HTML on every CI run | CI pipeline adds 5+ minutes; blocks deployments | Generate catalog docs on a scheduled nightly job or on-demand, not on every commit | When OpenMetadata has 500+ assets and the generation script queries all of them |
| Storing generated HTML in the git repo | Repository bloats; merge conflicts on generated files; git history fills with binary diffs | Generate HTML in CI and publish to an artifact store or GitHub Pages; keep only source files in git | When 6 SWOT HTMLs + architecture HTMLs + catalog HTML exceed 10 MB of generated content |

## Security Mistakes

Domain-specific security issues for documentation in financial services.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Including real data examples in documentation (customer IDs, account numbers, trade values) | PII/PCI exposure in documents that are shared broadly; regulatory violation | Use synthetic data exclusively in all documentation examples; add a CI check that scans docs for patterns matching real data formats |
| Embedding Ranger access policies with role names and permissions in public-facing docs | Reveals security architecture to potential attackers; social engineering vector | Document access control conceptually ("role-based, column-level masking for PII"); keep specific policy details in internal-only docs behind authentication |
| Hardcoding connection strings, API keys, or credentials in onboarding documentation | Credentials leak via document sharing, screenshots, or screen shares | Use environment variable references (`$TRINO_HOST`) and link to a secrets management guide; never put actual values in docs |
| Architecture diagrams showing internal network topology, IP ranges, and port numbers in executive-facing docs | Network reconnaissance information in broadly distributed documents | Marketecture uses abstract names only; detailed architecture restricts IP/port details to internal-only versions with access controls |
| SWOT analyses containing proprietary vendor pricing or contract terms | Vendor relationship damage; contract violation if shared externally | Reference pricing as "competitive" or "premium" with ranges; keep exact figures in confidential appendices |

## UX Pitfalls

Common user experience mistakes in documentation for this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| SWOT HTML uses tiny text, dense tables, and no visual hierarchy | Executives scan for 30 seconds and give up; miss critical recommendations | Use large headings, color-coded severity, executive summary at top, recommendation box prominently placed; design for scanning, not reading |
| Data catalog glossary organized alphabetically by technical column name | Business users cannot find the term they are looking for because they do not know the column name | Organize by business domain first (Risk, Finance, Customer, Trading), then by business concept name; include a search function |
| Onboarding guide assumes macOS and Homebrew | Engineers on Windows or Linux cannot follow setup steps | Document all three platforms or containerize the entire dev environment so the OS does not matter; the existing docker-compose.yml is the right foundation |
| Architecture diagrams use vendor-specific colors and logos that are meaningless to the audience | Viewers cannot distinguish components; accessibility issues for colorblind users | Use shape differentiation (rectangles for storage, cylinders for databases, hexagons for processing), clear labels, and patterns in addition to color |
| Contributor guidelines are a wall of text with no quick-start path | New contributors bounce off the document and ask a colleague instead | Structure as: (1) 5-minute quick start, (2) detailed process, (3) reference. Most contributors only need section 1 |
| API reference has no usage examples, only function signatures | Engineers read the signature but do not understand when or how to use the function | Every public function/class should have at least one usage example; auto-generate from doctests where possible |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **SWOT HTML:** Has all 4 quadrants filled in -- verify each item has quantified evidence, not just opinion statements
- [ ] **SWOT HTML:** Looks polished -- verify it opens correctly from local filesystem with no internet connection (`file://` protocol test)
- [ ] **SWOT HTML:** Has a recommendation section -- verify the recommendation explicitly addresses the specific decision context from PROJECT.md (e.g., "For our 1.5 PB Teradata-to-Iceberg migration" not generic advice)
- [ ] **Marketecture:** Shows the platform overview -- verify a non-technical stakeholder can explain what the platform does after 60 seconds of viewing
- [ ] **Detailed Architecture:** Shows all components -- verify every service in `docker-compose.yml` and every Terraform module in `infra/` is represented
- [ ] **Detailed Architecture:** Shows data flow -- verify it includes the error/failure paths, not just the happy path
- [ ] **Developer Onboarding:** Describes setup steps -- verify each command actually works by running them in a clean environment (empty checkout, no pre-existing Docker volumes)
- [ ] **API Reference:** Lists all modules -- verify it was auto-generated from current code, not hand-written (check generation timestamp)
- [ ] **API Reference:** Has function signatures -- verify it includes usage examples for the top 20 most-used functions
- [ ] **Data Catalog:** Lists data assets -- verify every definition links back to OpenMetadata and matches the OpenMetadata definition exactly
- [ ] **Data Catalog:** Includes lineage -- verify lineage descriptions match actual OpenLineage/Marquez data, not hand-drawn approximations
- [ ] **Contributor Guidelines:** Describes PR process -- verify the CI steps listed match what is actually in `.github/workflows/`
- [ ] **All HTML:** Renders correctly -- verify print-to-PDF produces readable output with no content cut off
- [ ] **All Documentation:** Contains no real data -- verify synthetic/example data is used throughout; scan for patterns matching production data formats

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SWOT analyses are biased/opinion-based | MEDIUM | Identify which of the 6 analyses lack evidence; add "Evidence" column to each SWOT item; conduct targeted research to fill gaps; have a different reviewer validate each analysis |
| Architecture diagrams diverge from reality | LOW | Run a reconciliation: compare diagram components against docker-compose.yml services, Terraform resources, and deployed infrastructure; update diagram source; add CI rendering step to prevent recurrence |
| Data catalog conflicts with OpenMetadata | HIGH | Audit all definitions in static docs vs OpenMetadata; resolve conflicts (OpenMetadata is authoritative); rebuild generation pipeline from OpenMetadata API; retire manually-written definitions |
| Developer docs have stale commands | LOW | Have a new team member follow the onboarding guide verbatim in a clean environment; document every failure; fix each issue; add CI test for critical setup commands |
| Standalone HTML breaks on restricted networks | LOW | Audit all HTML files for external references (`grep -r "https://" *.html`); inline all external resources; re-test on air-gapped machine |
| Real data leaked into documentation | HIGH | Immediately identify and remove all instances; audit git history for exposure; notify compliance team; replace with synthetic data; add CI scanning to prevent recurrence |
| Contributor guidelines describe non-existent CI process | LOW | Diff the guidelines against actual `.github/workflows/` files; update guidelines to reference config files by path instead of describing steps in prose |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SWOT bias (Pitfall 1) | SWOT Analysis (Phase 1 of docs milestone) | Each SWOT item has an "Evidence" or "Source" annotation; Threats/Weaknesses sections are at least 60% the length of Strengths/Opportunities |
| Architecture diagram drift (Pitfall 2) | Architecture Diagrams (Phase 2 of docs milestone) | Diagram source is in git; CI renders it; last render date is within 7 days of last infra change |
| BCBS 239 catalog compliance (Pitfall 3) | Data Catalog Documentation (Phase 4 of docs milestone) | Every glossary term maps to an OpenMetadata asset ID; BCBS 239 principle mapping document exists; compliance reviewer has signed off |
| Developer doc staleness (Pitfall 4) | Developer Documentation (Phase 3 of docs milestone) | API docs are auto-generated (check build timestamp); onboarding guide passes CI smoke test; freshness check is in CI pipeline |
| Wrong audience for diagrams (Pitfall 5) | Architecture Diagrams (Phase 2 of docs milestone) | Executive reviewed marketecture and confirmed clarity; engineer reviewed detailed diagram and confirmed completeness |
| HTML accessibility/renderability (Pitfall 6) | SWOT Analysis (Phase 1 of docs milestone) | All HTML files pass `file://` protocol test; all are under 500 KB; print-to-PDF produces readable output |
| Duplicate catalog vs OpenMetadata (Pitfall 7) | Data Catalog Documentation (Phase 4 of docs milestone) | Static docs include "Generated from OpenMetadata" timestamp; no manually-written data definitions exist that are not also in OpenMetadata |

## Sources

- [Common Pitfalls in SWOT Analysis -- CliffsNotes](https://www.cliffsnotes.com/study-notes/18991902)
- [Top 7 Common Mistakes in SWOT Analysis -- Medium](https://ryoleong.medium.com/common-mistakes-in-swot-analyses-ed50f94ab854)
- [Your SWOT Analysis is Broken -- Psychology Today / Inc.](https://www.psychologytoday.com/us/blog/intentional-insights/201911/your-swot-analysis-is-broken-heres-how-you-can-fix-it)
- [How SWOT Analysis Harms Leaders -- Lead Change](https://leadchangegroup.com/how-swot-analysis-harms-leaders/)
- [Documentation Rots. Here's How to Stop It -- DocsAlot](https://docsalot.dev/blog/documentation-rots-heres-how-to-stop-it)
- [Shifting to Continuous Documentation -- InfoQ](https://www.infoq.com/articles/continuous-documentation/)
- [8 Code Documentation Best Practices -- DeepDocs](https://deepdocs.dev/code-documentation-best-practices/)
- [BCBS 239 Guide 2025 -- Alation](https://www.alation.com/blog/bcbs-239-guide-compliance-best-practices-2025/)
- [BCBS 239 compliance: findings, failures and fixes -- IBM](https://www.ibm.com/new/product-blog/bcbs239-compliance)
- [BCBS 239 Principles: Complete Guide for 2026 -- OvalEdge](https://www.ovaledge.com/blog/bcbs-239-principles)
- [Data Architecture Diagrams: Practical Guide -- Instaclustr](https://www.instaclustr.com/education/data-architecture/data-architecture-diagrams-practical-2026-guide-with-examples/)
- [Infrastructure in Architectural Documentation -- INNOQ](https://www.innoq.com/en/articles/2025/05/infrastructure-in-architectural-documentation/)
- [Software Architecture: Marketecture vs Tarchitecture -- InformIT](https://www.informit.com/articles/article.aspx?p=31933)
- [Business Glossary Implementation Plan -- OvalEdge](https://www.ovaledge.com/blog/business-glossary-implementation-plan)
- [WCAG for Finance: Ensuring Accessibility -- WebAbility](https://www.webability.io/blog/wcag-for-finance-ensuring-accessibility-in-the-digital-banking-age)
- [Biases in Decision-Making: A Guide for CFOs -- McKinsey](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/biases-in-decision-making-a-guide-for-cfos)

---
*Pitfalls research for: Executive and Developer Documentation for Enterprise Lakehouse Data Platform (Financial Services)*
*Researched: 2026-03-14*
