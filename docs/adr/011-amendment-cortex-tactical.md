# ADR-011 Amendment — Reframing the Semantic Layer Decision

| Field | Value |
| --- | --- |
| **Original ADR** | ADR-011: Snowflake Cortex as semantic layer with Fabric as Phase 2 (supersedes ADR-010) |
| **Amendment Date** | 2026-05-02 |
| **Amended By** | ADR-014 (Semantic Plane Architecture) |
| **Status of Original ADR** | Partially superseded — see below |

## What changes

ADR-011 originally framed the semantic layer decision as a temporal choice: **Cortex Semantic Views in Phase 1, Fabric semantic models in Phase 2, with Snowflake as the centerpiece of the semantic plane.**

That framing was directionally correct on Fabric but wrong on Cortex's role. ADR-014 reframes it as an **architectural** choice rather than a temporal one:

- The semantic plane is **unified** across Snowflake and Trino, not split along the compute boundary.
- **Fabric semantic models** are the enterprise standard for the semantic plane from Phase 1 onwards, not Phase 2.
- **Cortex Analyst** is repositioned as a **tactical, Snowflake-internal NL-to-SQL convenience**, not the enterprise semantic layer.
- The Phase 1 / Phase 2 distinction now refers to **rollout sequencing of LOB semantic models**, not to a switch in semantic-layer technology.

## Why the original framing no longer holds

Three facts have crystallized since ADR-011 was written:

1. **The data hub strategy has matured.** Most enterprise data sources, including the Teradata FSDM and the on-prem Iceberg estate, will be accessed via Trino, not Snowflake. Cortex cannot reach Trino. A Snowflake-bound semantic layer cannot serve the on-prem majority.

2. **Iceberg-everywhere implies semantic-layer-everywhere.** Iceberg under both Snowflake and Trino is the correct decoupling at the storage plane. The semantic plane must preserve that decoupling. Cortex re-binds the semantic layer to Snowflake; Fabric does not.

3. **The agent strategy needs one semantic surface.** RBC Assist's Pattern 3 architecture (ADR-012) cannot route based on where data physically sits. Agents must reason against a single semantic plane. Bifurcating the semantic layer turns this into a routing problem.

## What survives from ADR-011

- The decision to use **a tabular semantic model** (rather than RDF/OWL) for Tier 1 LOB consumption — unchanged.
- The recognition that **Snowflake is RBC's cloud data warehouse** — unchanged. Snowflake remains a primary compute engine.
- The framing that the **semantic layer is critical for AI consumption accuracy** — unchanged and reinforced by ADR-014.
- Existing Cortex Semantic View implementations are **not reversed**; they are scoped to Snowflake-internal workloads.

## What is replaced

- "Cortex as the Phase 1 semantic layer" → **Fabric semantic models as the Phase 1 enterprise semantic layer.**
- "Fabric in Phase 2" → **No Phase 2 technology switch. Phase 2 is LOB rollout breadth, not a re-platforming.**
- Implicit assumption that the semantic layer follows the compute engine → **Explicit principle that the semantic plane is independent of and unified above the compute plane.**

## Reading order

For anyone reading ADR-011 today: read this amendment first, then read ADR-014 in full, then refer back to ADR-011 for context on the original Cortex investigation. Treat ADR-014 as the authoritative semantic-plane architecture decision.
