# ADR-016: Enterprise Conformance Tier (Tier 2)

|             |                                                                   |
| ----------- | ----------------------------------------------------------------- |
| **Status**  | Proposed (stub — full draft pending)                              |
| **Date**    | 2026-05-02                                                        |
| **Authors** | George Chilakos, VP Enterprise Data (Lumina / RBC)                |
| **Related** | ADR-009 (AI data hub architecture), ADR-013 (Ingestion as platform capability), ADR-014 (Fabric semantic plane), ADR-015 (RBC Data Gateway) |

---

## Context

Multiple ADRs and architecture documents in this repo reference an "Enterprise Conformance Tier" or "Tier 2" — a layer in the Enterprise Data Lakehouse that produces cross-LOB conformed datasets (Customer 360, Total Exposure, Household Rollups, Segment P&L) and the entity-resolution graph that supports them.

This ADR is a **placeholder**. It exists so that cross-references from the following documents resolve to a real ADR number:

- ADR-014 (Fabric semantic plane)
- `docs/lumina/data-hub-architecture.md`
- `docs/lumina/phase-1-pilot-plan.md`
- `docs/lumina/mvp-plan-q3-2026.md`
- The Lumina executive and detailed architecture diagrams

The full ADR will be drafted after the Q3 2026 MVP scoping is locked. The MVP plan deliberately does not require Tier 2 to be fully built — only the Counterparty conformed dimension is in scope for the MVP. Tier 2 in full is a Phase 3 (Q3 2027 onward) effort.

## What Tier 2 will cover (decisions to be made)

1. **Scope of the conformance layer.** Which datasets earn Tier 2 status. Initial candidates: Customer 360, Counterparty 360, Total Exposure, Household Rollups, Segment P&L.
2. **Entity resolution platform.** Property graph (Neptune, Neo4j) vs. RDF/OWL knowledge graph, federated via Trino. The architecture documents currently note this as "open question — FIBO-informed."
3. **Sponsorship and governance model.** Who funds and owns the Tier 2 datasets, given they are cross-LOB by definition. The proposed model is Enterprise Data ownership with LOB sponsorship for specific Tier 2 products.
4. **Promotion path from LOB hubs.** When a hub produces a dataset that earns enterprise scope, what is the formal process to absorb it into Tier 2? Architecture v2 calls this "sponsored absorption" but the criteria need codification.
5. **Relationship to Fabric semantic models.** Tier 2 is exposed through Fabric semantic models per ADR-014. The Enterprise semantic models in that ADR are the consumption surface for Tier 2.

## Why this is a stub today

The MVP timeline (Q3 2026) and the broader Lumina architecture do not require the full Tier 2 design to be settled to make progress. Forcing a premature decision on graph platform, scope, and governance would slow the MVP and lock in choices before we have evidence from the federated mesh in operation.

The forcing function for fully drafting this ADR is **the first cross-LOB Tier 2 product that has identified business sponsorship** — likely Customer 360 or Total Exposure, driven by Risk or Enterprise Strategy.

## Status

This stub ADR will be replaced with a full draft when the conditions above are met. Until then, treat any reference to "ADR-016" or "Enterprise Conformance Tier" as referring to this placeholder and the discussion in `docs/lumina/data-hub-architecture.md`, Section "Enterprise Conformance Tier."
