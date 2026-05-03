# ADR-017: Operational vs Collaborative Data Products — Two-Type Model and Accountability Framework

| Field | Value |
| --- | --- |
| **Status** | Proposed |
| **Date** | 2026-05-03 |
| **Author** | George Chilakos (VP, Enterprise Data) |
| **Supersedes** | None |
| **Amends** | ADR-011 (governance section), ADR-012 (consumer accountability), ADR-014 (semantic plane ownership) |
| **Related** | ADR-002 (Trino as query gateway), ADR-005 (Python over dbt), ADR-016 (Enterprise Conformance Tier), ADR-015 (RBC Data Gateway) |
| **Type** | Governance / organizational — applies orthogonally across the technology stack |

## Context

Lumina has, to date, treated "data product" as a single concept: a curated, conformed table or semantic model exposed for downstream consumption. Under this single-type model, accountability defaults to whoever owns the technical artefact — typically a Lumina platform engineer or, at best, an EDW domain lead acting as a schema owner.

This is the most common failure mode in data mesh adoption. It produces, in practice, a more complex data warehouse: the technology improves but the governance does not. The team that builds the pipeline becomes accountable for the accuracy of attributes they neither produce nor have authority to fix. The business owners of the source systems remain disconnected from the downstream impact of their data quality decisions.

Three conditions in the current Lumina programme make this failure mode acute:

1. **Multi-source composition is the norm, not the exception.** The Customer 360 surface, the counterparty exposure view, and the FSDM-derived collaborative tables all aggregate attributes owned by P&CB, Capital Markets, Wealth, Risk, and Finance. No single business owner controls the full record.

2. **AI consumption amplifies upstream defects.** Under ADR-011, ADR-012, and ADR-014, AI agents (RBC Assist, Borealis) consume the semantic plane. An NL-to-SQL agent confidently asserting an answer derived from a wrong attribute is materially worse than a BI dashboard showing the same attribute, because the AI strips the consumer's ability to apply context.

3. **The Fabric semantic model layer is, by design, a *collaborative* surface.** It is not where source-of-truth accuracy is established. Treating it as such — making the Fabric semantic model owner accountable for the correctness of the underlying attribute — places accountability where authority does not exist.

The two-type model formalized in this ADR resolves all three.

## Decision

**Lumina recognizes two distinct types of data products, with different ownership, governance, and accountability models. Every data product registered in the Lumina catalogue must be classified as one of these two types.**

### Type 1: Operational Data Product (ODP)

An Operational Data Product is the authoritative, governed view of a business subject as held by the operational area that transacts on it.

| Attribute | Specification |
| --- | --- |
| **Owner** | The business leader of the operational area (e.g. Head of Mortgage Origination for the Mortgage Application ODP). |
| **Authority** | Owner has authority to direct changes to source-system data capture, validation, and remediation. |
| **Scope** | Wide — typically 80%+ of the source system's attribute surface. ODPs are deliberately rich because the operational team needs operational depth. |
| **Governance focus** | Operational accuracy, transactional completeness, source-system fitness. |
| **Storage layer** | Bronze and Silver Iceberg tables in the on-prem lakehouse, FSDM-aligned where applicable. |
| **Consumption rule** | **Consumers fit the ODP's model, not the reverse.** If Finance wants to use the Mortgage Application ODP, Finance performs the conformance to its own purpose. The ODP owner is not responsible for shaping the data for cross-domain use. |
| **Naming convention** | `odp.<domain>.<subject>` (e.g. `odp.mortgage.application`, `odp.deposits.account`). |

### Type 2: Collaborative Data Product (CDP)

A Collaborative Data Product is the cross-domain view assembled from multiple ODPs (and, where necessary, external sources) for use by parts of the organization other than the originating operational area.

| Attribute | Specification |
| --- | --- |
| **Manager (responsible)** | A **Data Product Manager** in the Lumina platform team or in a domain-aligned data team. Responsible for construction, monitoring, schema, SLAs, and holding contributors to account. |
| **Accountable parties** | **Multiple.** Each contributing ODP owner remains accountable for the accuracy of the attributes their ODP supplies. Accountability follows the source of the attribute, not the boundary of the CDP. |
| **Authority** | Manager has authority to define structure and quality gates. Manager does **not** have authority to fix upstream attribute defects — that authority remains with the contributing ODP owner. |
| **Scope** | Narrow and purpose-fit — typically 10–20% of the union of contributing ODP attributes, conformed for cross-organizational use. |
| **Governance focus** | Cross-domain consistency, master data cross-reference, semantic alignment, attribute-level lineage to source ODPs. |
| **Storage layer** | Gold Iceberg tables (on-prem) and Fabric semantic models (BI/AI surface). |
| **Consumption rule** | Consumers use the CDP as published. Conformance is done once, in the CDP, not repeatedly by each consumer. |
| **Naming convention** | `cdp.<subject>` (e.g. `cdp.customer_360`, `cdp.counterparty_exposure`). |

### Roles: Data Product Manager vs Data Product Owner

This ADR adopts terminology that diverges from the original Data Mesh paper.

- **Data Product Owner** — used in this ADR only for the business owner of an **Operational** Data Product. Has authority and accountability for the underlying business reality.
- **Data Product Manager** — the role responsible for a **Collaborative** Data Product. Constructs, monitors, and holds contributors to account, but is not the source of authority over the underlying attributes.

The distinction is deliberate: a CDP is built by coordinating across multiple ODP owners, not by owning the data itself. Calling the CDP role an "owner" misrepresents the authority structure and recreates the failure mode this ADR is designed to prevent.

### Attribute-level accountability for CDPs

A Collaborative Data Product registers an **attribute accountability map**: for every attribute in the CDP, the contributing ODP and the accountable business owner are recorded. This is the canonical record consulted when a quality issue is raised.

Example: `cdp.customer_360.credit_score` is accountable to the Risk function (via the Credit Bureau Integration ODP), not to the Customer 360 Data Product Manager. A defect in this attribute is routed to Risk for resolution; the DPM coordinates and tracks closure but does not own the fix.

Where the systems of record do not naturally support attribute-level accountability (as is common with FSDM-conformed tables), the ODP owner is the default accountable party for all attributes the ODP contributes to any CDP. A CDP may not be released to production without every contributing attribute mapped to a named accountable owner.

### Operational implications

1. **Catalogue.** The Lumina data product registry (the thin layer being built on top of the Metadata Capture Service — MCS) records each registered data product as either ODP or CDP, with the corresponding ownership and accountability model attached as part of the data product contract. Purview holds business glossary and governance metadata only and is not the system of record for data product classification or attribute accountability.

2. **CDP construction gate.** No CDP enters production without all contributing attributes mapped to accountable ODP owners and an active sign-off from each.

3. **Quality routing.** When a defect is raised on a CDP, the DPM routes the defect to the accountable ODP owner. The DPM's SLA is on routing time and closure tracking, not on the underlying fix.

4. **Semantic plane (ADR-014) implication.** Fabric semantic models are CDPs. Their owners are Data Product Managers, not Data Product Owners. The accountability for the correctness of metric definitions sits with the DPM; the accountability for the correctness of the underlying attribute values sits with the contributing ODP owners.

5. **AI consumption (ADR-011, ADR-012) implication.** RBC Assist and Borealis consume CDPs through the Fabric Data Agent. When an AI-mediated answer is challenged on accuracy grounds, the attribute accountability map is the artefact that determines who investigates.

6. **FSDM implication.** The FSDM, as it stands, is a single monolithic conformed model with no attribute-level accountability map. Under this ADR, FSDM-derived tables that are exposed for cross-domain use are CDPs and require the attribute accountability map to be populated retroactively. This is a programme of work, not a one-time exercise — see Implementation below.

## Rationale

### Why split the data product concept

A unified "data product" concept forces a single owner to take accountability for attributes they do not control. In multi-source composites — which is most enterprise data of consequence — this is structurally impossible. Either the owner refuses (and accountability becomes nominal), or the owner accepts (and the data product becomes a queue of defects with no actionable resolution path).

The split places accountability where authority sits and gives the cross-domain surface its own role — coordination, not ownership.

### Why "Manager" instead of "Owner" for CDPs

The Data Mesh paper's "Data Product Owner" terminology, in practice at RBC and in similar enterprises, has consistently been read as "the person you blame when the data is wrong." For CDPs, that person does not exist — there is no single party with the authority to fix cross-domain attribute defects. Naming the role "Manager" preserves the intent (someone is responsible for the product) while communicating accurately that they coordinate accountability rather than absorb it.

### Why attribute-level accountability

Whole companies are built around managing a single attribute (the credit score is the canonical example). Insisting on attribute-level accountability mapping is not excessive; it is the minimum precision required to make multi-source data products operationally manageable. Without it, the DPM has no defensible routing path when a defect arrives.

### Why not lean harder on technology

Technology can automate what has been made operational. It cannot create accountability where none has been negotiated. The tooling — MCS metadata capture, OpenLineage provenance, Soda Core quality gates, the data product registry — supports this ADR but does not substitute for it. The ADR is deliberately about the organizational model.

## Consequences

### Positive

- The Fabric semantic plane (ADR-014) gets a clean ownership model. DPMs own structure and SLAs; ODP owners own attribute accuracy.
- AI consumption (ADR-011, ADR-012) gets a defensible escalation path when answers are challenged.
- The "more complex data warehouse" failure mode is structurally avoided: the construct that distinguishes a mesh from a warehouse — distributed business accountability — is now operational, not aspirational.
- Migration of legacy reporting (OBIEE → Power BI/Fabric, ~1,000 reports) gains a governance frame: each report consumes one or more CDPs, each CDP has a defined accountability map, and report defects are routable.

### Negative / costs

- The attribute accountability mapping for FSDM-derived CDPs is a substantial programme of work. Initial estimate: 6–9 months of dedicated effort across the EDW team and contributing business areas.
- Some business areas will resist accepting accountability for attributes they have historically treated as "the EDW's problem." This is the political work the ADR makes visible — it does not remove it, and it does not pretend technology can substitute for it.
- The ODP/CDP distinction adds a registration step to the data product lifecycle. Without enforcement, teams will default to whatever is easiest, which is usually CDP without an accountability map. Catalogue tooling must enforce the gate.

### Neutral

- The two-type model does not change the technology stack, the medallion architecture, or the consumption patterns established in ADR-011, ADR-012, ADR-014, and ADR-015. It is a governance overlay, not a replacement.

## Implementation

### Phase 1 — Foundations (Q3 2026, 12 weeks)

1. Extend the data product registry (the layer being built on top of MCS) to support ODP/CDP classification and attribute accountability maps as first-class fields in the data product contract YAML.
2. Pilot the model on **two CDPs** chosen for political tractability and business value: candidates are `cdp.customer_360_lite` (P&CB) and `cdp.counterparty_exposure` (Capital Markets). Each pilot includes producing the attribute accountability map and securing sign-off from each contributing ODP owner.
3. Establish the Data Product Manager role formally — job description, RACI, reporting line. Initial DPMs are drawn from the Lumina platform team.

### Phase 2 — Rollout to existing FSDM-derived assets (Q4 2026 – Q2 2027)

1. Classify every existing collaborative artefact (FSDM-conformed tables, current Fabric semantic models, legacy reporting marts) as ODP or CDP.
2. For each classified CDP, produce the attribute accountability map. Run this as a tracked programme with monthly progress reviews to senior leadership.
3. Block the production release of any new CDP without a complete accountability map. Enforce in CI/CD and in the catalogue's release gates.

### Phase 3 — Steady state (Q3 2027 onwards)

1. The ODP/CDP distinction is the default vocabulary across Lumina, the EDW domain, and downstream consumers.
2. Attribute accountability maps are produced as part of CDP construction, not retrofitted.
3. Quality routing through accountability maps is the standard defect resolution path; ad-hoc routing through Lumina platform on-call is the exception.

## Open questions

1. **Where does the DPM role sit organizationally?** Initial proposal: in the Lumina platform team for cross-LOB CDPs, in domain teams for LOB-specific CDPs. This split needs validation with Vinh and the LOB heads.
2. **How is FSDM treated under this model?** The FSDM was implemented ~35 years ago as a single conformed model. It is most accurately classified as a *legacy CDP without an accountability map*. The retroactive mapping is in scope for Phase 2; the question is whether to also formalize FSDM-derived ODPs at the source-system level, which would clarify but also expand the initial mapping work.
3. **Relationship to the Enterprise Conformance Tier (ADR-016).** ADR-016 introduces a tier of enterprise-conformed data; that tier is composed of CDPs under this ADR. The two ADRs need to be reconciled in a single update once both are accepted — see the companion reconciliation note.
4. **External data and third-party feeds.** Bureau data, market data, regulatory feeds — these have no internal ODP. Treatment under this ADR: the team that ingests and curates the external feed is the accountable party, with the same authority constraints (they cannot fix the source data, only the ingestion). Worth a separate ADR if the volume of external CDPs grows.

## References

- Steve Jones, *There are two types of Data Products in a Data Mesh*, Feb 2022 — primary source for the two-type model and the accountability/responsibility distinction adopted here.
- Steve Jones, *A Data Mesh without Business Ownership is doomed to fail*, Oct 2023 — diagnostic frame for why the single-owner model fails.
- Zhamak Dehghani, *Data Mesh: Delivering Data-Driven Value at Scale*, O'Reilly 2022 — original Data Product Owner concept; this ADR explicitly diverges on terminology and on the unified-product framing.
- ADR-011, ADR-012, ADR-014, ADR-015, ADR-016 — Lumina architecture context.
