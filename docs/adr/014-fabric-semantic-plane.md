# ADR-014: Semantic Plane Architecture — Unified Semantic Layer Across Snowflake and Trino

| Field | Value |
| --- | --- |
| **Status** | Proposed |
| **Date** | 2026-05-02 |
| **Author** | George Chilakos (VP, Enterprise Data) |
| **Supersedes** | None |
| **Amends** | ADR-011 (Snowflake Cortex as semantic layer with Fabric as Phase 2) |
| **Related** | ADR-002 (Trino as mandatory query gateway), ADR-010 (Fabric Import semantic model), ADR-012 (RBC Assist × Fabric Data Agent consumption pattern), ADR-016 (Enterprise Conformance Tier — proposed) |

## Context

The Lumina lakehouse architecture establishes Iceberg as the open table format underneath both cloud (Snowflake) and on-prem (Trino) compute. The data hub concept allows teams to pull enterprise data sources into a common Iceberg-backed area and reshape them into LOB-aligned models. Compute is therefore deliberately heterogeneous and engine-agnostic at the storage layer.

The architectural question this ADR resolves: **where do business definitions live?**

ADR-011 originally proposed Cortex Semantic Views as the Phase 1 semantic layer with Fabric semantic models as Phase 2. That framing is now insufficient because:

1. The majority of RBC's data, including the Teradata FSDM and the on-prem Iceberg estate accessed through Trino, will not reside in Snowflake. Cortex Analyst is structurally Snowflake-bound — it cannot reach Trino, Teradata, or other on-prem sources. Making Cortex the enterprise semantic layer means making the cloud minority dictate the architecture for the on-prem majority.

2. The temptation to split the semantic layer along the compute boundary — Cortex Semantic Views over Snowflake, Fabric semantic models over Trino — recreates the EDW-vs-LOB-mart fragmentation that the lakehouse strategy is designed to escape. Every cross-platform metric would drift between two definitions, AI agents would route by deployment topology rather than by business meaning, and Iceberg's compute-interchangeability promise would be undermined at the metric layer.

3. RBC Assist's Pattern 3 architecture (Azure AI Foundry orchestration) requires a single semantic surface that the agent layer can reason against. A bifurcated semantic layer becomes a routing problem for agents rather than a semantic problem.

## Decision

Adopt a **unified semantic plane** sitting above both Snowflake and Trino, expressed as **Fabric semantic models** and consumed via **Fabric Data Agent**.

The architecture has four planes:

| Plane | Components | Notes |
| --- | --- | --- |
| **Storage** | Iceberg V2 on object storage, Nessie catalog, Gravitino governance, Ranger enforcement | Unchanged from existing ADRs |
| **Compute** | Snowflake (cloud-elastic workloads), Trino (on-prem federation, mandatory gateway per ADR-002) | Both read the same Iceberg tables |
| **Semantic** | **Fabric semantic models, single definition per metric, governed by Enterprise Data and LOB stewards jointly** | This is the new principle |
| **Consumption** | Power BI (human BI), Fabric Data Agent (conversational AI, invokable from RBC Assist via Pattern 3), Cortex Analyst (tactical, Snowflake-internal only) | Cortex demoted from "semantic layer" to "Snowflake-internal convenience" |

### Where each compute engine is queried

Fabric semantic models use **DirectQuery** to reach the appropriate compute engine per source:

- DirectQuery to Snowflake for Snowflake-resident data, with **Fabric Mirroring of Snowflake** as the performance fallback for high-concurrency or low-latency workloads (see Phase 1 pilot).
- DirectQuery to Trino for on-prem and federated data, including Iceberg tables exposed through the Trino gateway.
- Direct Lake mode for data already in OneLake.
- Power BI Import mode reserved for small, slow-changing reference data only.

### Where Cortex Analyst still earns its keep

Cortex Analyst remains available as a **tactical, Snowflake-internal NL-to-SQL convenience** for:

- Data science teams running iterative exploratory queries entirely within Snowflake.
- Snowflake-native applications that do not need cross-platform reach.
- Snowflake Marketplace data products consumed directly without crossing into the enterprise semantic layer.

Cortex Analyst is **not** the enterprise standard for AI consumption and is not invoked by RBC Assist.

## Decision drivers

1. **Cross-platform reach.** Fabric semantic models are the only candidate that can DirectQuery into Snowflake, Trino, Teradata (during the migration period), and Fabric-native sources uniformly. Cortex cannot reach beyond Snowflake.

2. **One business definition, one set of governance.** Splitting the semantic layer doubles the maintenance burden and guarantees drift on metrics that span LOBs. Risk, Finance, and the AI agent layer cannot tolerate this drift.

3. **Purview integration.** Fabric semantic models inherit Purview labels, lineage, and access policies natively. RBC's broader governance posture is increasingly Microsoft-centered; aligning the semantic plane to Purview reduces governance fragmentation.

4. **Agent orchestration maturity.** Fabric Data Agent integrates with Power BI Copilot, Microsoft 365 Copilot, Copilot Studio, and Azure AI Foundry via Model Context Protocol. This is the strongest agent-to-agent orchestration story available today and aligns with the Pattern 3 design in ADR-012.

5. **Storage-compute decoupling preserved.** Iceberg under both Snowflake and Trino is the correct decoupling at the storage plane. The semantic plane must preserve this decoupling, not re-bind to a single compute engine.

## Alternatives considered

**Alternative A: Cortex for cloud, Fabric for on-prem.** Rejected. Recreates EDW-vs-mart fragmentation at the semantic layer, doubles metric maintenance, forces AI agents to route by topology, and undermines the Iceberg decoupling strategy.

**Alternative B: Cortex Semantic Views as the enterprise semantic layer with Snowflake Iceberg federation reaching Trino sources.** Rejected. Snowflake's external table and Iceberg federation capabilities are real but not designed for the latency, concurrency, or governance integration needed for on-prem-first workloads. This approach also bets the architecture on Snowflake-led federation, which contradicts ADR-002's choice of Trino as the mandatory query gateway.

**Alternative C: A graph-based semantic layer (RDF/OWL via a knowledge graph platform).** Rejected for Tier 1. Tabular semantic models are the right abstraction for 80% of consumption (BI dashboards, single-LOB analytics). Graph semantics are reserved for the Enterprise Conformance Tier (ADR-016) where entity resolution and relationship spine genuinely need graph traversal.

**Alternative D: dbt Semantic Layer / Cube as platform-neutral semantic layer.** Considered. Both are technically capable of sitting above Snowflake and Trino. Rejected for Tier 1 because (a) neither has the Purview-native governance integration Fabric semantic models offer, (b) neither has the agent-orchestration maturity of Fabric Data Agent + Copilot Studio, and (c) introducing a third vendor at the semantic plane increases operational complexity without clear benefit given RBC's existing Microsoft footprint.

## Consequences

### Positive

- One set of business definitions across cloud and on-prem.
- One governance plane (Purview) for semantic metadata, labels, and lineage.
- One AI consumption surface (Fabric Data Agent) for RBC Assist, Power BI Copilot, and Microsoft 365 Copilot.
- Iceberg's storage-compute decoupling preserved through the semantic plane.
- Clear scoping of Cortex Analyst as a tactical capability rather than an architectural commitment.

### Negative / Risks

- **Performance risk on DirectQuery to Trino.** Fabric semantic model performance against Trino at high concurrency is unproven at RBC scale. Mitigation: Phase 1 pilot (see separate document) validates this empirically before broad rollout.
- **Performance risk on DirectQuery to Snowflake at high concurrency.** Mitigation: Fabric Mirroring of Snowflake provides a near-real-time replica in OneLake for performance-critical workloads. This capability is relatively new and must be validated in pilot.
- **Vendor concentration on Microsoft for the semantic and consumption planes.** Acknowledged. Mitigation: storage (Iceberg) and compute (Snowflake + Trino) remain heterogeneous, preserving optionality at the layers where it matters most.
- **Cortex Analyst capability investments may stall.** Acknowledged. The decision is to scope Cortex narrowly, not eliminate it. Snowflake-internal teams retain full Cortex Analyst access.
- **Migration path from existing Cortex Semantic Views to Fabric semantic models is non-trivial.** Mitigation: Phase 1 pilot defines the migration pattern; existing Cortex investments are not reversed but are scoped to Snowflake-internal use.

## Implementation phasing

**Phase 0 — Decision ratification (Q2 2026).** ADR-014 review with Vinh, Rex, and the EDW/EDL/Lakehouse domain leads. ADR-011 amended to reflect the new framing.

**Phase 1 — Pilot (Q3 2026).** See separate Phase 1 Pilot Plan document. Two LOB pilots (one Snowflake-resident, one Trino-resident), Fabric semantic models over both, Fabric Data Agent consumption, performance and governance validation.

**Phase 2 — LOB rollout (Q4 2026 – Q2 2027).** Per-LOB Fabric semantic models built out across P&CB, Capital Markets, Wealth, and Insurance. Cortex Semantic Views grandfathered for existing Snowflake-internal use.

**Phase 3 — Enterprise Conformance Tier (Q3 2027 onwards).** Tier 2 per ADR-016, including the entity-resolution graph and conformed enterprise dimensions, exposed through Fabric semantic models that span LOBs.

## Out of scope

- The choice of property graph vs. RDF for the Tier 2 entity-resolution layer (covered by ADR-016).
- Specific Power BI semantic model patterns (composite models, perspectives, calculation groups) — these are implementation guidance, not architectural decisions.
- Migration approach for the Teradata FSDM (covered by separate FSDM transition plan).

## References

- ADR-002: Trino as mandatory query gateway
- ADR-010: Fabric Import semantic model as BI/AI surface
- ADR-011: Snowflake Cortex as semantic layer with Fabric as Phase 2 (amended by this ADR)
- ADR-012: RBC Assist × Fabric Data Agent consumption pattern
- ADR-016 (proposed): Enterprise Conformance Tier for cross-LOB semantics
- Phase 1 Pilot Plan: Fabric Semantic Models over Snowflake and Trino (companion document)
- Allemang, Hendler, Gandon. *Semantic Web for the Working Ontologist*, 3rd edition, ACM Books, 2020. Chapters 1–2 (open-world / closed-world framing) and 14.4 (FIBO design philosophy as mapping target).
