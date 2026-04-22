# The Hub in RBC's Lakehouse

## Position Paper — Ingestion, Conformance, and Composition

**Author:** George Chilakos, VP Enterprise Data
**Status:** Draft for discussion
**Related ADRs:** ADR-002 (Trino as query gateway), ADR-008 (OneLake shortcuts superseded), ADR-010 (Fabric Import semantic model), ADR-013 (proposed — ingestion as platform capability)

---

## Executive Summary

RBC is modernizing its enterprise data estate by building an open lakehouse adjacent to — and eventually surrounding — the Teradata EDW. As part of that modernization, there is an emerging push to adopt "data hub" or "data product" patterns, giving domains (Cards, Mortgages, Risk, Deposits, Wealth) more autonomy over the data they produce and consume.

This is directionally right. But without a clear architectural position, it risks becoming fragmented domain ownership of ingestion and conformance — which would directly undermine BCBS 239 compliance, materially increase OSFI B-13 operational and cyber risk surface, and erode 35 years of FSDM investment.

This paper sets the position.

**The core principle:**

> *Ingestion is a shared service, not a domain capability.*
> *Conformance is a shared product, not a domain opinion.*
> *Composition is where domains have autonomy.*

**The architecture, stated simply:**

- **Bronze (ingest once)** — platform-owned raw landing zone. One ingestion per source.
- **Silver (conform once)** — enterprise conformance layer. FSDM-on-Iceberg as the authoritative enterprise data product.
- **Gold (consume many)** — hubs and other products composing from Silver for differentiated consumers.

**The layered ownership model:**

- Platform owns the substrate (ingestion, catalog, policy plane, enforcement, quality, lineage) and Bronze.
- EDW team owns enterprise conformance — FSDM-on-Iceberg — as a first-class Silver-layer data product.
- Domains own Gold hubs, composed from Silver and, where justified, from domain-specific Bronze sources.
- Governance (Gravitino for policy authoring, Ranger for enforcement) is shared and uniformly enforced — not negotiated per domain.

**The regulatory backbone:** BCBS 239 Principles 2, 3, and 4 and OSFI B-13's Technology Operations and Resilience domain make fragmented ingestion and domain-owned conformance materially harder to defend in a regulatory exam. Centralized ingestion and conformance, with federated composition, is the lowest-risk path to compliance.

**The commitment back to domains:** Central ownership of ingestion and conformance is only defensible if the platform is fast, self-serve, and transparent. The platform must commit to published SLAs, templated onboarding, and domain autonomy over scope — otherwise domains will legitimately route around the principle.

**The recommendation:** Formalize this position as ADR-013, paired with a Platform Ingestion Service Commitments document. Use this position to frame the unification conversation with Vinh and Martin — the lakehouse isn't an annex to the EDW, it's the enterprise data platform, with FSDM as its most important product.

---

## 1. The Problem Statement

Three pressures are converging:

**First**, the lakehouse is real and the architecture is maturing — ADR-010 locks in the Fabric Import semantic model; ADR-002 establishes Trino as the mandatory query gateway; ADR-008 retired OneLake shortcuts. The stack is stabilizing on Iceberg V2 + Nessie + Gravitino + Ranger + Trino + Python.

**Second**, the organization is asking for data product and data hub patterns — domains want more control, central teams want to scale by federating, and the mesh vocabulary is in the air.

**Third**, the regulatory posture is tightening. BCBS 239 implementation remains the hardest problem at most G-SIBs and D-SIBs (BIS has said so publicly), and OSFI B-13 came into force in January 2024 with explicit expectations around technology architecture, operational resilience, and data-related cyber risk.

The tension: if "data hub" means domains ingest their own sources and conform their own enterprise entities, we end up with fragmented lineage, duplicated ingestion surfaces, and competing definitions of customer. That is the opposite of what BCBS 239 Principles 2, 3, and 4 require.

If "data hub" means domain-owned composable products sitting on shared ingestion and shared conformance, we get the best of both worlds — domain autonomy where it adds value, enterprise consistency where it's non-negotiable.

This paper makes the case for the second reading, architecturally and operationally.

---

## 2. The Core Principle

> *Ingestion is a shared service, not a domain capability.*
> *Conformance is a shared product, not a domain opinion.*
> *Composition is where domains have autonomy.*

Every architectural, governance, and organizational decision in this paper follows from this sentence. If the principle holds, the architecture works. If the principle erodes, the architecture fragments, and we spend the next decade reconciling "which customer count is right" in front of regulators.

---

## 3. The Medallion Mapping — Ingest Once, Conform Once, Consume Many

The principle maps directly onto the medallion architecture:

**Bronze — Ingest Once**
Platform-owned raw landing zone. Every source system lands exactly once, through the platform's ingestion framework, with schema registered in Nessie and lineage captured in OpenLineage. Bronze is immutable, append-only, fully auditable. No domain bypasses Bronze to pull from the source of record directly.

**Silver — Conform Once**
Enterprise conformance layer. This is where FSDM lives, recast as FSDM-on-Iceberg. Business rules applied, entities resolved, enterprise keys harmonized, history tracked via Iceberg V2. Silver produces the authoritative enterprise definitions of customer, account, transaction, exposure, balance, product. One conformance of each enterprise concept. Silver is owned by the EDW team as a first-class data product — with a contract, an owner, published SLAs, and stewardship.

**Gold — Consume Many**
Composition and consumption layer. Many products for many consumers, all built from the same Silver foundation. Gold is where hubs proliferate — Cards hub, Risk hub, Regulatory Reporting hub, ML Feature Store — because different consumers legitimately need different shapes of the same underlying truth. Gold products are owned by the domain teams that produce them, governed by the platform, and consumed by BI (Fabric, Tableau), AI agents (via Teradata AI semantic layer and the FastAPI trust boundary), and downstream systems.

The phrase "ingest once, conform once, consume many" is not a slogan — it's the operating model.

---

## 4. Hub vs. Gold Zone — A Distinction That Matters

The terms get used interchangeably. They shouldn't be.

**Gold is a layer. Hub is a product status.**

Gold describes *where data sits and how processed it is* — it's a maturity layer in the medallion. Hub describes *how data is packaged, owned, and consumed* — it's a governance construct.

A hub lives in Gold, but Gold contains more than just hubs. Gold can contain:

- Certified data products (hubs) — Cards hub, Risk hub, FSDM-derived enterprise reporting product.
- Derived analytical datasets — feature stores, regulatory reporting marts.
- Materialized views and performance layers — pre-computed aggregates for query speed.
- Semantic model sources — the Gold tables Fabric imports from per ADR-010.

The hub concept is a **governance and ownership overlay** on Gold. It designates a Gold dataset as a product with a contract, an owner, published SLAs, and committed consumers. Not every Gold table earns hub status, and that's fine — hubs are the Gold datasets that matter enough to formalize.

**The rule:** Gold hubs consume from Silver. They do not consume from Bronze, except for genuinely domain-specific data that has no enterprise conformance equivalent (e.g., a Cards-specific vendor feed that no other domain cares about).

When someone says "we want to build a hub," the diagnostic question is always: **built on what?**

- Built on Silver conformance → legitimate Gold-layer product, platform-approved pattern.
- Built on Bronze directly, bypassing Silver → red flag. They're re-conforming the data their own way, which creates competing enterprise definitions.

---

## 5. The Layered Ownership Model

The lakehouse has four ownership tiers, and they are not negotiable.

### Platform Substrate (Central — Enterprise Data Platform team)

Ingestion framework, Bronze raw zone, Nessie catalog, Gravitino policy plane, Ranger enforcement, Soda quality framework, OpenLineage, Trino query gateway, CI/CD (GitHub), deployment patterns.

This is the shared infrastructure every product depends on. Domains consume this. They do not reinvent it, fork it, or bypass it.

### Enterprise Conformed Product (EDW team — Silver as product owner)

FSDM-on-Iceberg — the authoritative enterprise model of customer, account, transaction, exposure, balance, product. Recast from "the warehouse" to "the enterprise's most important data product." Explicit contract (schema, SLAs, quality, PII classification), named owner, published stewardship, versioned releases.

Silver is owned centrally because enterprise conformance cannot be federated without breaking "one version of the truth." This is where 35 years of FSDM investment shows its value, and where the EDW team's institutional knowledge is a structural moat.

### Domain Products (Domain teams — Gold composers)

Cards hub, Mortgages hub, Risk hub, Wealth hub, Deposits hub, Capital Markets hub. Built by composing Silver (FSDM-on-Iceberg) with domain-specific Bronze sources, using the platform's standard toolkit (Iceberg, Trino, Python, the CI/CD and quality stack).

Domain teams own their domain logic, their derived metrics, their product contracts, and their consumer relationships. They do not own ingestion of enterprise sources. They do not own enterprise conformance.

### Consumption Surfaces (Central and domain, depending on surface)

Fabric semantic model for human BI (per ADR-010), Teradata AI semantic layer + FastAPI trust boundary for agents (RBC Assist, Borealis), Tableau for visualization, regulatory reporting pipelines, downstream operational integrations.

All consumers pull from certified products (Silver or Gold hubs). No consumer pulls from Bronze. No consumer bypasses the governance plane.

---

## 6. What a Hub IS

A hub, in this architecture, is a **certified, contract-backed data product** that lives in Gold (or is the Silver enterprise product itself) and serves multiple consumers.

The defining characteristics:

**Explicit contract.** Schema, refresh cadence, SLAs, quality thresholds, PII classification, access policy. Consumers know what they're getting, and when it changes.

**Named owner.** Not a committee. A person, with a team, accountable for quality, lineage, and breaking changes.

**Discoverable.** Registered in the catalog (Nessie + Gravitino metadata), with lineage back to authoritative source visible end-to-end via OpenLineage.

**Composable.** Built from Silver and/or from Bronze (for domain-specific sources only), using the platform's transformation framework. The build itself is governed, versioned, and reviewable.

**Enforced by the platform.** Ranger applies access policies. Soda gates quality. Gravitino governs the tags and policies that drive both. The product owner authors policy; the platform enforces it uniformly across all consumption channels.

---

## 7. What a Hub IS NOT

These are the anti-patterns. If someone proposes a hub that has any of these properties, it is not a hub — it is a silo with new branding.

**Not a source ingestion point.** Raw data lands in Bronze through the platform's ingestion service, full stop. A hub composes from Silver; it does not reach past Bronze to pull from Teradata, mainframes, Salesforce, or any source of record directly.

**Not a bypass around FSDM.** Where enterprise conformance exists in Silver, hubs consume it. They do not re-derive "customer" from raw and hope their version matches. If FSDM is wrong for a domain's need, the answer is to fix or extend FSDM as a product — not to fork it.

**Not a private kingdom.** A hub's contract is public. Its lineage is public. Its quality metrics are public. Domains do not get to hide their product behind "it's our data."

**Not a replacement for governance.** Building a hub does not grant the domain policy authority. Gravitino is the single policy plane. Ranger is the single enforcement engine. A hub operates inside that governance — not alongside it.

**Not a bespoke tech stack.** Hubs are built with the platform's tooling. A domain that wants to bring its own Spark cluster, its own orchestrator, its own catalog is not building a hub — they are building a silo that will fragment the estate.

---

## 8. The Regulatory Backbone

This is not architectural hygiene. It is regulatory defensibility.

### BCBS 239 — Principles for Effective Risk Data Aggregation and Risk Reporting

**Principle 2 — Data Architecture and IT Infrastructure.**
A bank should design, build, and maintain data architecture that fully supports its risk data aggregation capabilities, not only in normal times but also in times of stress or crisis. Fragmented ingestion — multiple domains pulling from the same source in different ways — is architecture that only works when nothing goes wrong. It does not scale to crisis conditions.

**Principle 3 — Accuracy and Integrity.**
A bank should be able to generate accurate and reliable risk data, with aggregation performed on a largely automated basis to minimize the probability of errors. This is where lineage lives. The BIS itself has publicly identified data lineage as the hardest BCBS 239 component for banks, citing legacy systems, distributed data estates, and the dynamic nature of lineage as the primary blockers. If three domains ingest the same source, we have three lineage paths to defend. One ingestion, many composers — one lineage path.

**Principle 4 — Completeness.**
A bank should be able to capture and aggregate all material risk data across the banking group, with breakdowns by business line, legal entity, asset type, industry, and region. That is only possible if underlying raw data is landed consistently and conformed once. Domain-owned ingestion turns enterprise aggregation into a reconciliation exercise instead of a query.

**Primary source:** [https://www.bis.org/publ/bcbs239.pdf](https://www.bis.org/publ/bcbs239.pdf)

### OSFI Guideline B-13 — Technology and Cyber Risk Management

Effective January 1, 2024. B-13 defines technology and cyber risk broadly — including risks arising from the people and processes that support technology assets — and is organized into three domains (Governance and Risk Management; Technology Operations and Resilience; Cyber Security) supported by 17 principles.

The relevant domain for this position is **Technology Operations and Resilience.** Every ingestion pipeline is a failure domain, a credential surface, a monitoring target, and a change-management risk. Collapsing ingestion into one governed platform capability materially reduces operational and cyber risk surface — exactly what B-13 asks FRFIs to manage down.

Third-party concentration and vendor dependency risks associated with source connectors are addressed under the companion **OSFI Guideline B-10 (Third-Party Risk Management)**, effective May 1, 2024.

**Primary source:** [https://www.osfi-bsif.gc.ca/en/risks/technology-cyber-risk-management](https://www.osfi-bsif.gc.ca/en/risks/technology-cyber-risk-management)

### The Composite Argument

Neither BCBS 239 nor OSFI B-13 explicitly says "thou shalt not ingest sources into domain hubs." What they say is:

- You must demonstrate end-to-end lineage from source to report (BCBS 239 Principle 3).
- You must architect for resilience under stress (BCBS 239 Principle 2; OSFI B-13 Technology Operations and Resilience).
- You must aggregate completely and consistently across the estate (BCBS 239 Principle 4).
- You must manage technology and cyber risk surface proactively (OSFI B-13).

Fragmented ingestion and domain-owned conformance make all four materially harder. Centralized ingestion and centralized conformance, with federated composition, is the architecturally simplest path to sustained compliance.

---

## 9. The Platform's Commitment Back to Domains

Central ownership of ingestion and conformance is only defensible if the platform is genuinely fast, self-serve, and transparent. If central ingestion is a bottleneck, domains will legitimately route around it — and the principle will erode.

The platform commits to the following:

**Time-to-onboard.** Target two weeks for standard source patterns (JDBC, CDC, file landing), six weeks for complex patterns (streaming, bespoke APIs, mainframe extracts). Published SLA, measured and reported.

**Self-serve ingestion templates.** Standard connector patterns that domains configure rather than request. A Cards team onboarding a vendor feed runs a templated onboarding flow; they do not raise a ticket and wait.

**Domain autonomy over scope, not standards.** Domain-specific sources — a Cards vendor API, a Mortgages partner feed — are onboarded by the domain using the platform's ingestion framework. Same tooling, same lineage, same catalog registration. The platform owns the *how*; the domain owns the *what*.

**Transparent backlog and capacity.** Domains see the ingestion team's work queue, SLA performance, and capacity forecasts. No black box.

**FSDM extension path.** When a domain needs an enterprise entity that FSDM doesn't model well, there is a clear, time-bounded path to extend FSDM — not a workaround to bypass it.

Without these commitments, the principle is just gatekeeping. With them, domains get faster outcomes than they would by building bespoke pipelines — and the architecture stays coherent.

---

## 10. Carve-Outs (Intellectual Honesty)

Three cases where the principle bends. Named explicitly so nobody claims the position is absolutist.

**Domain-specific sources that only the domain consumes.** A Cards vendor feed, a Wealth partner API, a Mortgages niche data service. These do not need enterprise-wide conformance because there is nothing to conform them to. The domain onboards the source via the platform's ingestion framework, lands it in Bronze within their product space, and builds their Gold hub directly from it. Platform standards apply (lineage, quality, catalog registration, governance). Platform ownership of the pipeline does not.

**Regulatory sandboxes and short-lived analytical datasets.** Model development, ad-hoc investigations, exploratory analytics. These need fast, low-ceremony access. The platform provides a governed sandbox pattern with clear expiry, classification rules, and no production promotion without going through the full product path.

**Legacy migration period.** During the OBIEE → Power BI and DataStage → Python migrations, some existing ingestion paths will persist. These are documented, not extended, and have sunset dates tied to the migration programs.

These are exceptions with explicit boundaries, not loopholes.

---

## 11. The One-Slide Version

**Platform owns ingestion. EDW owns conformance. Domains own composition.**

**Bronze is ingest-once. Silver is conform-once (FSDM-on-Iceberg). Gold is consume-many (hubs and products).**

**Governance is shared and enforced, not negotiated.**

**Regulatory anchors: BCBS 239 Principles 2, 3, 4; OSFI B-13 Technology Operations and Resilience.**

---

## 12. Recommended Next Moves

1. **Formalize this position as ADR-013** — "Ingestion is a Platform Capability; Hubs Compose, They Do Not Ingest" — in the `chilakos/lakehouse` repo.

2. **Write a companion Platform Ingestion Service Commitments document** that publishes the SLAs, templates, and self-serve patterns referenced in Section 9. Without this, the principle lacks teeth.

3. **Socialize with Vinh and Rex** using the layered ownership model as the framing device. Position the lakehouse as the enterprise data platform — not an EDW annex — with FSDM as its most important product. This aligns directly with the EDL / EDW / BI unification narrative.

4. **Use this position in the DMO talking points** as the governance backbone for the Gravitino / Ranger story. "One policy, enforced everywhere" is the consequence of this architecture, not an independent claim.

5. **Pre-empt the domain pushback** by engaging the first two or three domain leads (likely Cards and Risk) as design partners on the Platform Ingestion Service Commitments. If they shape the SLAs, they'll defend the principle.

---

*End of position paper.*
