# Decks

Executive and working-group presentations for the Lumina / RBC Enterprise Data programme.

| File | Topic | Date |
|---|---|---|
| [rbc-assist-fabric-architecture-options.pptx](rbc-assist-fabric-architecture-options.pptx) | RBC Assist × Fabric Data Agent — Architecture Options. Three consumption patterns (custom Python+FastAPI, Foundry-mediated, Copilot Studio) and the unified semantic-layer target state. Companion README: [rbc-assist-fabric-architecture-options.README.md](rbc-assist-fabric-architecture-options.README.md). | Apr 2026 |
| [cloudera-exit-acceldata.pptx](cloudera-exit-acceldata.pptx) | Cloudera Exit — Acceldata-Led Approach. 25-slide executive deck. Four-path evaluation (A: all-cloud Databricks, B: Starburst+Databricks, C: Acceldata ODP, D: Snowflake) with Path C recommended. Adds Acceldata vs Pure OSS comparison and full upgrade-path coverage (in-place, sidecar, forklift) with sidecar+in-place fallback as the operational recommendation. Companion docs: [acceldata-odp-poc-plan.md](../docs/migration/acceldata-odp-poc-plan.md), [acceldata-odp-migration-plan.md](../docs/migration/acceldata-odp-migration-plan.md). | May 2026 |
| [rbc-assist-semantic-layer-architecture.pptx](rbc-assist-semantic-layer-architecture.pptx) | RBC Assist semantic layer architecture — executive deck referenced in ADR-011 documenting the FastAPI trust boundary and Snowflake Cortex Phase 1 architecture. | Apr 2026 |
| [fabric-ai-bi-semantic.pptx](fabric-ai-bi-semantic.pptx) | Define Once, Serve AI & BI — Fabric as the unified semantic layer. How Fabric today unifies Power BI and RBC Assist, the architecture, enforcement, and where Fabric alone falls short. Predates ADR-011; read alongside ADR-011 for current direction. | Apr 2026 |
| [raci-exec-r.pptx](raci-exec-r.pptx) | Who Is Responsible For What — exec 2-slide version. Slide 1: three-column ownership summary (Platform, DMO, Business). Slide 2: 5 critical hand-off points where unclear ownership creates the most risk. | Apr 2026 |

## Related docs

- [ADR-011 — Snowflake Cortex as Access and Semantic Layer (current)](../docs/adr/011-snowflake-cortex-semantic-layer.md)
- [ADR-010 — Fabric Import Semantic Layer (superseded by ADR-011)](../docs/adr/010-fabric-import-semantic-layer.md)
- [Full responsibility matrix (59 activities)](../docs/governance/responsibility-matrix.html)
- [Semantic single source architecture](../docs/architecture/semantic-single-source.html)
