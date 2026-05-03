# Reconciliation Note — ADR-016 (Enterprise Conformance Tier) and ADR-017 (Operational vs Collaborative Data Products)

| Field | Value |
| --- | --- |
| **Document type** | Reconciliation note |
| **Date** | 2026-05-03 |
| **Author** | George Chilakos (VP, Enterprise Data) |
| **Status** | Draft for review alongside ADR-017 |
| **Intended outcome** | Update ADR-016 from stub to full draft, incorporating the ODP/CDP framing from ADR-017 |

---

## Why this note exists

ADR-016 (Enterprise Conformance Tier — Tier 2) currently exists as a stub in the repository. It was placed there as a forward reference from ADR-014 and from the Lumina architecture documents to describe a layer in the lakehouse that produces cross-LOB conformed datasets — Customer 360, Total Exposure, Household Rollups, Segment P&L — and the entity-resolution graph that supports them. The full ADR was deferred because the Q3 2026 MVP did not require Tier 2 to be fully built and because forcing premature decisions on graph platform, scope, and governance would have slowed the MVP.

ADR-017 (Operational vs Collaborative Data Products) introduces a governance frame that materially changes how the Enterprise Conformance Tier should be described, owned, and built. The two ADRs need to be reconciled before either is treated as a final position. This note proposes how.

## The relationship in one sentence

**The Enterprise Conformance Tier is the layer of the lakehouse where Collaborative Data Products with cross-LOB scope live, with the same governance model defined in ADR-017 applied to them.**

That is the entirety of the conceptual reconciliation. The detail is in what it changes for ADR-016 when it is drafted in full.

## Five reconciliations to make in the full ADR-016

### 1. Terminology — Tier 2 datasets are Collaborative Data Products

The stub of ADR-016 lists candidate Tier 2 datasets as "Customer 360, Total Exposure, Household Rollups, Segment P&L." Under ADR-017 these are all Collaborative Data Products by definition — they aggregate attributes from multiple ODPs across LOBs. The full ADR-016 should adopt CDP as the term and drop "Tier 2 dataset" as the primary noun, retaining "Tier 2" only as a tier classifier indicating enterprise scope (as distinct from LOB-scoped CDPs).

A revised classification reads: `cdp.<subject>.tier2` for enterprise-scoped CDPs that earn Tier 2 status, with the rest sitting at LOB scope. The naming convention defined in ADR-017 supports this with no change.

### 2. Ownership — Tier 2 is managed by Data Product Managers, accountable to multiple ODP owners

The stub of ADR-016 raises "Sponsorship and governance model" as an open question — "Who funds and owns the Tier 2 datasets, given they are cross-LOB by definition." ADR-017 resolves this directly:

- A Tier 2 CDP is **managed** by a Data Product Manager. The DPM role for Tier 2 sits in the Enterprise Data team (Lumina platform), not in any individual LOB. This is the right home because Tier 2 by definition crosses LOB boundaries.
- A Tier 2 CDP is **accountable** at the attribute level to the contributing ODP owners across the LOBs. Each attribute in a Tier 2 CDP has a named ODP owner who is on the hook for accuracy of that attribute.
- A Tier 2 CDP is **sponsored** by an LOB or by Enterprise Strategy/Risk for funding and prioritization purposes. Sponsorship is distinct from accountability — the sponsor pays for the work; the accountable parties make the data correct.

This three-way split (managed / accountable / sponsored) is what makes Tier 2 governance tractable. The full ADR-016 should adopt it.

### 3. Promotion path — from LOB CDP to Tier 2 CDP

The stub of ADR-016 raises "Promotion path from LOB hubs" as an open question. Under ADR-017 the promotion is now well-defined as a transition between two states of the same artefact type (CDP):

- An LOB-scoped CDP is published, owned and managed within the LOB.
- When the CDP is identified as having enterprise relevance — typically because two or more other LOBs are subscribing or because Risk/Finance/Strategy has a regulatory or strategic need for it — it is proposed for Tier 2 promotion.
- Promotion requires: (a) the existing attribute accountability map is reviewed and gaps closed where the broader audience exposes new contributing ODPs; (b) the DPM role transfers from the LOB to Enterprise Data; (c) sponsorship is named; (d) the SLA is recommitted at enterprise scope.
- The CDP technical artefact (the schema, the Fabric semantic model, the Iceberg table) remains in place. Promotion is a governance event, not a re-platforming event.

This is cleaner than the "sponsored absorption" framing in the existing architecture documents. The full ADR-016 should adopt it.

### 4. Entity resolution platform — defer the technology choice but commit to the governance frame

The stub of ADR-016 lists "Entity resolution platform — property graph (Neptune, Neo4j) vs. RDF/OWL knowledge graph" as an open question. ADR-017 does not change the technology answer to that question, but it does change the framing.

Entity resolution is a **shared service that supports CDP construction**, not a CDP itself. The output of entity resolution — a unified party key, a household graph, a counterparty hierarchy — is a *contributing input* to Tier 2 CDPs, not the CDP itself. This means the entity resolution platform is a platform component (like Trino, like Ranger), not a data product. Its accountability model is the standard platform-team accountability, not the CDP attribute accountability map.

This separation simplifies the open question. The full ADR-016 can defer the platform choice (FIBO-informed, graph database TBD) without that decision being on the critical path for the broader Tier 2 governance frame.

### 5. Relationship to Fabric semantic models

The stub of ADR-016 notes "Tier 2 is exposed through Fabric semantic models per ADR-014. The Enterprise semantic models in that ADR are the consumption surface for Tier 2." ADR-017 confirms this and adds the governance specifics:

- A Tier 2 CDP exposed through a Fabric semantic model is a CDP at both the storage layer (Iceberg Gold) and the consumption layer (Fabric semantic model). These are two representations of the same data product, not two separate data products.
- The DPM is responsible for both representations and for keeping them in sync.
- Attribute accountability flows to ODP owners regardless of which representation a consumer uses.

The full ADR-016 should make this explicit so that the relationship between the storage and semantic-model representations of a Tier 2 CDP is not ambiguous.

## What the full ADR-016 still needs to decide

Independently of ADR-017, the full draft of ADR-016 still needs to settle:

1. The list of Tier 2 CDPs in scope for 2026 and 2027 (out of the candidate set: Customer 360, Total Exposure, Household Rollups, Counterparty 360, Segment P&L).
2. The entity resolution platform choice — graph database, federation approach, FIBO alignment.
3. The funding model and sponsor for each Tier 2 CDP brought into scope.
4. The MVP cut: which Tier 2 CDPs are in the Q3 2026 MVP (the architecture currently targets Counterparty conformed dimension only) versus Phase 2 versus Phase 3.

These remain open. Nothing in ADR-017 changes them.

## Sequencing

The recommended sequence:

1. **ADR-017 reviewed and accepted** as the governance frame for all data products (ODP and CDP).
2. **ADR-014 amended in its governance section** to reference ADR-017 — Fabric semantic models are CDPs, owned by DPMs, with attribute accountability flowing to ODP owners. This is a small amendment (a single paragraph), not a re-draft.
3. **ADR-016 promoted from stub to full draft**, incorporating the five reconciliations in this note plus the four still-open items above. This is the larger piece of work and is gated on the MVP scope discussion.
4. **The ODP/CDP catalogue in MCS / data product registry** becomes the system of record for which CDPs are Tier 2 and which contributing ODPs are mapped. This is enforcement-level, not document-level, and becomes the operational reality of the governance frame.

The first three steps run in parallel to the existing Q3 2026 MVP work. None of this changes the MVP critical path.

## Alternative considered: collapse ADR-016 into ADR-017

A reasonable question is whether ADR-016 needs to exist at all once ADR-017 is in place. The argument for collapse: if Tier 2 CDPs are governed identically to other CDPs except for the scope and the location of the DPM (Enterprise Data rather than LOB), then ADR-017 already covers it.

The argument against collapse, which I take to be stronger: Tier 2 is sufficiently distinct on the technology side — entity resolution platform, federation graph, regulatory sensitivity — that it warrants its own ADR. ADR-017 is the governance frame; ADR-016 is the architectural and implementation detail of one specific tier within that frame. They are doing different jobs.

Recommendation: keep both, with ADR-016 explicitly building on ADR-017 in the way described in this note.

## References

- ADR-014: Semantic Plane Architecture
- ADR-015: RBC Data Gateway
- ADR-016: Enterprise Conformance Tier (Tier 2) — current stub
- ADR-017: Operational vs Collaborative Data Products — proposed
- `docs/lumina/data-hub-architecture.md` — Section "Enterprise Conformance Tier"
- `docs/lumina/mvp-plan-q3-2026.md` — for MVP scope of Tier 2 in 2026
