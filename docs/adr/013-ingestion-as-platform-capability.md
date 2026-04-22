# ADR-013: Ingestion is a Platform Capability; Hubs Compose, They Do Not Ingest

**Status:** Proposed
**Date:** 2026-04-22
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)
**Raised by:** Domain hub / data product pattern discussion (April 2026)
**Related:** ADR-002 (Trino as mandatory query gateway), ADR-008 (OneLake evaluation), ADR-009 (AI data hub architecture), ADR-010 (Fabric Import semantic model), ADR-011 (Snowflake Cortex semantic layer), ADR-012 (RBC Assist Fabric data agent pattern)

---

## Context

The RBC lakehouse is maturing — Iceberg V2 on-prem, Nessie catalog, Gravitino policy
plane, Ranger enforcement, Trino query gateway, Python transformations, Fabric and
Snowflake Cortex as BI/AI semantic surfaces (ADR-010, ADR-011). As adoption broadens,
domain teams (Cards, Mortgages, Risk, Wealth, Capital Markets) are asking for more
autonomy, often framed as "data hubs" or "data products."

Within this push, a recurring request is **direct source ingestion into domain hubs** —
domains pulling raw data from systems of record (Teradata, mainframes, core banking,
vendor APIs) into their own hub space, outside the platform's central ingestion
framework.

Without a clear position, this risks fragmenting ingestion and conformance across
domains. That would materially undermine BCBS 239 compliance (Principles 2, 3, 4),
increase OSFI B-13 operational and cyber risk surface, and erode 35 years of FSDM
investment. It would also create competing enterprise definitions of "customer,"
"account," "exposure," etc. — the exact pathology BCBS 239 Principle 3 (Accuracy and
Integrity) is designed to prevent.

This ADR establishes where ingestion lives, where conformance lives, and where
domain autonomy legitimately applies.

---

## Decision

**Ingestion is a shared platform service, not a domain capability.**
**Conformance is a shared enterprise product, not a domain opinion.**
**Composition is where domains have autonomy.**

Concretely:

1. **Bronze (raw landing) is platform-owned.** All source systems are ingested exactly
   once, via the platform's ingestion framework, into a canonical Bronze zone. Every
   ingestion is registered in Nessie, lineage-tagged via OpenLineage, and quality-gated
   via Soda.

2. **Silver (enterprise conformance) is EDW-team-owned as a product.** FSDM-on-Iceberg
   is the authoritative enterprise data product, with an explicit data contract
   (schema, SLAs, quality thresholds, PII classification, stewardship). Entity
   resolution, enterprise keys, and business rules are applied here — once.

3. **Gold (hubs and products) is domain-owned.** Domains compose Gold products from
   Silver conformance and, where justified, from domain-specific Bronze sources. Hubs
   are Gold datasets with product status: explicit contract, named owner, published
   SLAs, committed consumers.

4. **Hubs consume from Silver. Hubs do not consume from Bronze** except for genuinely
   domain-specific data with no enterprise conformance equivalent (e.g., a
   Cards-specific vendor feed that no other domain uses).

5. **Governance is shared and uniformly enforced.** Gravitino is the single policy
   authoring plane. Ranger is the single enforcement engine. Hubs operate inside this
   governance — not alongside it, and never with bespoke policy implementations.

6. **Semantic layers sit above Gold, not within the medallion.** Fabric semantic model
   (ADR-010, ADR-012) for human BI; Snowflake Cortex / Teradata AI semantic layer for
   agents (ADR-011). Both source enterprise measure definitions from a canonical
   metric registry, applying the same "conform once, consume many" discipline at the
   semantic tier.

### Hub vs. Gold — Terminology Clarification

**Gold is a layer. Hub is a product status.** Gold describes where data sits and how
processed it is (medallion tier). Hub describes how a Gold dataset is packaged,
owned, and consumed (governance construct). A hub lives in Gold, but Gold contains
more than just hubs (feature stores, materialized views, performance layers,
semantic model sources). Not every Gold table earns hub status — hubs are the Gold
datasets that matter enough to formalize with a contract and named owner.

---

## Carve-Outs

Three exceptions with explicit boundaries:

- **Domain-specific sources with no enterprise equivalent** may be onboarded by the
  domain directly, using the platform's ingestion framework. Platform standards
  apply (lineage, quality, catalog); platform ownership of the pipeline does not.
- **Regulatory sandboxes and short-lived analytical datasets** follow a governed
  sandbox pattern with clear expiry and no production promotion path without full
  product review.
- **Legacy migration period** (OBIEE → Power BI, DataStage → Python): existing
  ingestion paths are documented and sunset-dated, not extended.

---

## Consequences

### Positive

- **Regulatory defensibility.** Aligns with BCBS 239 Principles 2 (Data Architecture),
  3 (Accuracy and Integrity, including lineage), and 4 (Completeness). Supports OSFI
  B-13 Technology Operations and Resilience by collapsing ingestion surface area.
- **One lineage path per source.** OpenLineage traces from source to report without
  ambiguity — critical for BCBS 239 Principle 3 demonstration in regulatory exams.
- **Preserves FSDM investment.** Repositions FSDM from "the warehouse" to "the
  enterprise's most important data product" — modernized delivery (Iceberg V2,
  versioned releases, Python transforms, real CI/CD), same semantics.
- **Reduces operational risk surface.** One ingestion framework means one
  credential surface, one monitoring target, one change-management path per source.
- **Enables genuine domain autonomy at the right layer.** Domains own composition,
  product shape, consumer relationships — the parts where domain expertise matters.

### Negative / Risks

- **Platform ingestion team becomes a capacity constraint.** If the platform is slow,
  domains will route around the principle. Mitigation: published SLAs, self-serve
  templates, transparent backlog — see Platform Ingestion Service Commitments (to be
  authored as companion doc).
- **Cultural friction with domains pushing for mesh-style autonomy.** Mitigation:
  frame the position as layered mesh (centralized substrate, federated composition)
  rather than centralization; engage domain leads as design partners on the SLAs.
- **FSDM must evolve faster than historically.** If FSDM cannot model new enterprise
  concepts (e.g., digital banking events) at pace, domains will have legitimate
  grounds to fork. Mitigation: time-bounded FSDM extension path as a committed
  product roadmap item.

---

## Alternatives Considered

**Alternative 1: Full mesh — domains own ingestion, conformance, and composition.**
Rejected. Fragments lineage and creates competing enterprise definitions. Materially
harder to defend under BCBS 239. Real-world implementations at other banks have
degraded into silos within 3-5 years without centralized substrate.

**Alternative 2: Full centralization — all layers owned centrally.**
Rejected. Ignores genuine value of domain expertise at the composition layer. Creates
bottleneck at central team for domain-specific product work. Slows delivery of
domain-shaped consumer surfaces (Cards hub, Risk hub) that require deep domain
knowledge.

**Alternative 3: Status quo — EDW-centric, lakehouse as annex.**
Rejected. Does not position the lakehouse as the enterprise platform. Perpetuates
EDW-vs-lakehouse framing that undermines the unification strategy and does not
create a clear home for domain product patterns.

**Alternative 4 (adopted): Layered ownership — platform substrate + enterprise
conformance + federated composition.**
Centralize what benefits from scale (ingestion, conformance, governance).
Federate what benefits from proximity (composition, consumer shape, domain logic).
Regulatory-defensible, organizationally sustainable, platform-scalable.

---

## Regulatory References

- **BCBS 239** — Principles for effective risk data aggregation and risk reporting
  (BIS, January 2013). Primary source: <https://www.bis.org/publ/bcbs239.pdf>.
  Principles 2 (Data Architecture and IT Infrastructure), 3 (Accuracy and Integrity),
  4 (Completeness) are the primary anchors for this ADR.
- **OSFI Guideline B-13** — Technology and Cyber Risk Management (effective January 1,
  2024). Primary source:
  <https://www.osfi-bsif.gc.ca/en/risks/technology-cyber-risk-management>. Technology
  Operations and Resilience domain is the primary anchor.
- **OSFI Guideline B-10** — Third-Party Risk Management (effective May 1, 2024).
  Relevant for vendor-sourced ingestion concentration risk.

---

## Companion Materials

- Position paper: `docs/position-papers/hub-ingestion-conformance-composition.md`
- Architecture diagram: `docs/architecture/diagrams/lakehouse-semantic-architecture.svg`
- Platform Ingestion Service Commitments: *to be authored* — publishes SLAs,
  templates, and self-serve patterns that give this ADR operational teeth.

---

## Open Questions

1. Who owns the Canonical Metric Registry — EDW team, BI team, or a new shared
   stewardship function? Depends on Fabric vs. Snowflake Cortex path resolution
   (ADR-010, ADR-011).
2. What is the governed sandbox pattern for short-lived analytical datasets, and
   which platform surface hosts it?
3. How does the FSDM extension path interact with the Teradata → Iceberg migration
   timeline? Can FSDM-on-Iceberg evolve faster than Teradata FSDM historically has?
4. Which two or three domain leads should be engaged as design partners on the
   Platform Ingestion Service Commitments? Candidates: Cards, Risk.
