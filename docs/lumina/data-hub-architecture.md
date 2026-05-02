# Lumina Data Hub Architecture (v2)

| Field | Value |
| --- | --- |
| **Document type** | Architecture specification |
| **Version** | v2 (supersedes v1 dated 2026-05-02) |
| **Date** | 2026-05-02 |
| **Author** | George Chilakos (VP, Enterprise Data) |
| **Status** | Draft for review with Vinh Tran |
| **Related ADRs** | ADR-002, ADR-011 amended, ADR-012, ADR-016 (proposed), ADR-014 (proposed) and amendment, ADR-015 (proposed) |

## What changed in v2

Three substantive changes from v1:

1. **RBC Data Gateway** added as an explicit architectural component sitting between consumption and the semantic plane for AI traffic. Realized as a FastAPI service on RBC's OpenShift Container Platform. Power BI and human-driven SQL bypass the gateway. See ADR-015.

2. **Raw / Landing Zone** added as an explicit layer beneath both the EDLH and the LOB hubs. Operational data lands here directly, not through the EDW. Hybrid landing model: enterprise-shared sources via platform-mediated ingestion, LOB-specific sources via self-serve LOB-owned namespaces.

3. **Teradata FSDM repositioned** as a source feeding the Raw Zone via CDC, rather than a peer hub. Decomposition continues to follow the existing FSDM transition plan.

## Executive summary

The Lumina Data Hub Architecture realizes Vinh's vision of giving each LOB a building zone to compose data products from multiple sources, supported by an Enterprise Data Lakehouse (EDLH) that provides conformed, authoritative shared data. The architecture is a **federated data mesh** with a **two-medallion pattern**: the EDLH runs its own enterprise medallion as a shared source of truth, and each LOB runs their own medallion inside their hub for LOB-specific products.

Operational data lands in a **shared Raw Zone in Iceberg**, accessible to both the EDLH and LOB hubs via hybrid ingestion (platform-mediated for enterprise-shared sources, self-serve for LOB-specific sources). LOB hubs publish certified data products through a registry layer that sits above MCS. AI consumption is mediated by the **RBC Data Gateway**, an on-prem FastAPI service that authenticates, audits, federates, and orchestrates calls across per-hub Fabric Data Agents. Cross-hub data access is mediated through certified products only — never direct.

The Enterprise Data team owns the platform, the EDLH, the conformed enterprise dimensions, the Tier 2 enterprise conformance layer, and the gateway. LOBs own their hubs, their data products, their semantic models, and their consumption surfaces. Federation is enforced through governance and through the gateway, not through forbidding LOB autonomy.

## Architectural principles

1. **The hub is a building zone, not a data warehouse.** LOBs use their hub to compose, transform, and shape data products. The hub is the LOB's domain in the data mesh sense.

2. **Two medallions, one platform.** The EDLH runs an enterprise medallion (bronze→silver→gold) for conformed shared data. Each hub runs its own internal medallion for LOB-specific data products. Both share the same Iceberg storage substrate, governance plane, and compute infrastructure.

3. **Operational data lands once, in the open.** A shared Raw Zone in Iceberg is the single landing surface for operational data. EDLH ingestion and LOB hub ingestion both read from it. The Raw Zone removes the legacy EDW as a bottleneck for LOB hub access to operational sources.

4. **The semantic plane is unified.** Per ADR-014, both EDLH and LOB hubs expose Fabric semantic models. Enterprise semantic models are authoritative for enterprise concepts; LOB semantic models are authoritative for LOB-derived concepts. Both governed under one Purview umbrella.

5. **AI consumption is mediated, human consumption is direct.** The RBC Data Gateway is the mandatory boundary for agentic consumers (RBC Assist, M365 Copilot in agentic mode, future agents). Power BI users and Trino SQL users bypass the gateway and talk to the semantic and storage planes directly.

6. **Cross-hub access is mediated, never direct.** LOBs consume certified data products from other hubs through the registry. No hub reads another hub's internals.

7. **Storage is open and engine-agnostic.** Iceberg V2 underneath both Snowflake (cloud-primary hubs) and Trino (on-prem-primary hubs).

8. **Federated governance is non-negotiable.** Platform team owns the rails. LOBs own the content. Both must hold for the mesh to work.

## The Raw / Landing Zone

The Raw Zone is the shared substrate where operational data first becomes part of the lakehouse. It is governed but not yet conformed. Two namespaces:

### Enterprise namespace (platform-mediated)

Sources where Enterprise Data is the natural ingestion owner because the source is enterprise-shared:

- Mainframe core banking
- General ledger
- Customer master
- Counterparty master
- Regulatory reference data
- Market data feeds (consumed enterprise-wide)
- Teradata FSDM (transitional, via CDC)

Ingestion is operated by the platform team. Patterns: change data capture (CDC) for transactional sources, scheduled batch for slowly-changing reference data, streaming ingestion (Kafka or equivalent) for high-velocity feeds. All landing is via Airflow-orchestrated jobs running governed pipelines.

### LOB-owned namespaces (self-serve)

One namespace per LOB. Sources where the LOB is the natural ingestion owner:

- *P&CB namespace*: branch systems, cards platforms, mortgage systems, auto loan systems
- *Capital Markets namespace*: trading platforms, market data the LOB subscribes to (Bloomberg, Reuters), risk engines
- *Wealth namespace*: custody systems, brokerage platforms, third-party performance data
- *Insurance namespace*: policy admin, claims, reinsurance feeds
- (Risk consumes from other namespaces via certified products; does not have its own raw sources)

Ingestion is operated by the LOB. The platform team provides the patterns: standardized ingestion templates (Airflow DAG templates, Kafka topic patterns, CDC patterns), the OCP-hosted ingestion runtime, governance hooks (Purview lineage, sensitivity labeling at landing time), and policy enforcement. LOBs implement against these patterns. New sources go through a lightweight onboarding process with the platform team.

### What lands and what does not

The Raw Zone holds operational data in its source-system shape. It does NOT hold:

- Curated or conformed data (that is Enterprise Bronze/Silver in the EDLH or Hub Bronze/Silver in the LOB hub).
- Data products published for cross-LOB consumption (that is the registry).
- Semantic-layer definitions (those are Fabric semantic models).
- Analytical aggregates (those are Hub Gold or Enterprise Gold).

Retention in the Raw Zone is governed by source-system retention policies and regulatory requirements, applied uniformly via Purview labels. Source-system schema evolution is handled via Iceberg schema evolution.

### Why this pattern

Two reasons. First, **decoupling**: removes the EDLH as a serial bottleneck on LOB access to operational data. A Capital Markets analyst pulling a feed from a trading platform does not have to wait for the Enterprise Data team to model it in Enterprise Bronze if Capital Markets is the natural domain owner. Second, **honesty**: the Raw Zone is what is *actually happening* in any modern lakehouse — operational data lands raw in the open table format and gets transformed downstream. Naming it explicitly makes the architecture truthful rather than implicit.

## What is inside an LOB hub

Inputs (four channels):

- **Conformed enterprise data** read from the EDLH gold layer (read-only, version-pinned via Nessie).
- **Raw Zone reads** — operational data from the LOB's own namespace, and selected reads from the Enterprise namespace where the LOB has access.
- **External data** the LOB subscribes to.
- **Self-service uploads** for analyst spreadsheets and curated reference data.

Internal medallion (Hub Bronze → Hub Silver → Hub Gold), Fabric semantic model on Hub Gold, Fabric Data Agent in the LOB workspace (with serving compute on enterprise capacity per ADR-014), and certified products published to the registry.

## What is inside the EDLH

The EDLH is the shared, authoritative enterprise lakehouse. It reads from the Raw Zone (Enterprise namespace primarily; LOB namespaces only when promoting an LOB product into enterprise scope) and exposes:

**Enterprise medallion.** Enterprise Bronze (raw landed conformed to a uniform schema), Enterprise Silver (conformed enterprise data including the conformed dimensions), Enterprise Gold (enterprise-wide aggregates and the Tier 2 enterprise conformance layer).

**Conformed enterprise dimensions.** Customer, Counterparty, Legal Entity, Product, GL Account, Org, Date. Owned by Enterprise Data, read by every hub.

**Tier 2 enterprise conformance layer (per ADR-016).** Customer 360, total exposure, household rollups, segment P&L. The cross-LOB rollup tier.

**Entity resolution and relationship spine.** Property graph (Neptune or Neo4j, federated via Trino) holding enterprise entity identity and relationships. Reads from Enterprise Silver, feeds Tier 2.

**Enterprise semantic models.** Fabric semantic models on Enterprise Gold for enterprise-wide consumption (enterprise customer view, enterprise risk view, enterprise finance view).

The EDLH is a *source* for the hubs (read-only, version-pinned via Nessie), not a peer hub. Hubs do not write back to the EDLH except via the promotion path.

## The RBC Data Gateway (per ADR-015)

The gateway is the mandatory trust boundary for AI traffic. AI consumers (RBC Assist primarily, M365 Copilot in agentic mode, future agentic consumers) call the gateway. The gateway routes to the appropriate Fabric Data Agents, orchestrates cross-hub queries, enforces auth and policy, defends against prompt injection, and audits everything.

**Implementation: FastAPI on OCP.** Same component, two names — "RBC Data Gateway" is the architectural role, the FastAPI service is the implementation.

**Bypass paths.** Power BI talks directly to Fabric semantic models via DirectQuery. Human-driven SQL goes through Trino per ADR-002. The gateway is for agentic traffic only.

**Orchestration: on-prem (per Option A in ADR-015).** When RBC Assist asks a cross-hub question, the gateway decomposes the request, calls multiple Fabric Data Agents, composes the response, and returns it. Copilot Studio agent-to-agent is not the production orchestration path in Phase 1; it may become an option in 18-24 months as the Microsoft orchestration plane matures.

See ADR-015 for the full responsibilities, internal architecture, and phasing of the gateway.

## Hub topology — primary and mirror

| LOB | Primary | Rationale |
| --- | --- | --- |
| P&CB Hub | On-prem (Trino) | Mainframe-heavy, latency-sensitive, regulated |
| Capital Markets Hub | Cloud (Snowflake) | Elastic compute for risk, market data, derivatives |
| Wealth Hub | Cloud (Snowflake) | Modern stack, lighter regulatory footprint |
| Insurance Hub | On-prem (Trino) | Legacy actuarial systems, on-prem source of truth |
| Risk Hub | Cloud (Snowflake) — open question | Cross-cuts LOBs; alternative: Risk consumes from Tier 2 without owning a hub |

Non-primary location holds a read-only mirror for cross-region access and DR.

## The data product lifecycle (unchanged from v1)

Propose → Build → Certify → Publish → Promote (optional). Contracts in Git, indexed by registry. See v1 §"The data product lifecycle" for full detail; substance unchanged.

## The catalog stack (unchanged from v1)

MCS (technical metadata), Nessie (storage catalog), Gravitino + Ranger (policy), data product registry layer (built on top of MCS), Purview (business glossary and governance metadata). Substance unchanged from v1.

## Fabric capacity model (unchanged from v1)

Tiered: Enterprise F128 (Tier 2 + agent serving compute), Shared LOB F128 (most LOBs), Dedicated F64 (Capital Markets confirmed, others on demand). Fabric Data Agents live in LOB workspaces; serving compute runs on enterprise capacity. Substance unchanged from v1.

## Governance and federation (clarified)

The split of responsibilities adds the gateway and the Raw Zone. Updated table:

| Concern | Platform team | LOB |
| --- | --- | --- |
| Iceberg infrastructure, Nessie, Gravitino, Ranger | ✓ | |
| **Raw Zone Enterprise namespace ingestion** | ✓ | |
| **Raw Zone LOB namespace ingestion patterns and runtime** | ✓ | |
| **Raw Zone LOB namespace pipeline implementation** | | ✓ |
| Trino cluster, Snowflake account, Fabric capacity | ✓ | |
| Conformed enterprise dimensions and Tier 2 layer | ✓ | |
| Data product registry and certification process | ✓ | |
| Purview taxonomy, sensitivity policies, glossary structure | ✓ | |
| **RBC Data Gateway (FastAPI on OCP)** | ✓ | |
| LOB hub workspace contents and configuration | | ✓ |
| LOB hub bronze/silver/gold pipelines | | ✓ |
| LOB Fabric semantic model definitions and metrics | | ✓ |
| LOB data product contracts and SLAs | | ✓ |
| Glossary terms in LOB domain | | ✓ |
| Consumer access to LOB-owned products | | ✓ |

## Identity, security, and access (updated)

- **Identity.** RBC Entra ID, inherited by Snowflake, Fabric, Trino, the Raw Zone, and the gateway.
- **Authorization.** Ranger policies authored in Gravitino, enforced at query time across Trino, Snowflake (via Iceberg integration), and Fabric. Gateway-layer authorization in addition for AI traffic.
- **Sensitivity classification.** Purview sensitivity labels applied at Raw Zone landing time and propagated through bronze/silver/gold and into semantic models.
- **AI access.** All agentic access through the gateway, which translates user identity to Fabric Data Agent's expected form (delegated user identity by default).
- **Cross-hub access.** Granted through registry subscription workflow, translated to Ranger policies.

## What this architecture deliberately does NOT do

(Unchanged from v1, with two additions noted in bold.)

- It does not replicate the EDLH inside every hub.
- It does not allow direct hub-to-hub data sharing outside the registry.
- It does not centralize transformations in a single team.
- It does not pre-define every possible data product.
- It does not eliminate the Teradata FSDM in Phase 1 — FSDM continues to feed the Raw Zone via CDC during decomposition.
- **It does not allow agentic consumers to call Fabric Data Agent directly.** All agentic traffic through the gateway.
- **It does not route operational data through the EDW.** Raw Zone is the operational landing.

## Phasing

Updated to reflect the gateway and Raw Zone:

**Phase 0 — Foundations (Q3 2026).** Raw Zone Enterprise namespace operational with first conformed dimensions (Customer, Counterparty). EDLH bronze/silver/gold operational against the Raw Zone. MCS connected. Initial Gravitino and Ranger policies. Enterprise Fabric capacity provisioned. **RBC Data Gateway MVP operational** (single-agent routing, full seven responsibilities at minimum viable level). FSDM CDC into Raw Zone established.

**Phase 1 — First two hubs (Q4 2026 – Q1 2027).** Capital Markets Hub (cloud-primary) and one on-prem-primary hub stood up. Each hub's LOB Raw Zone namespace operational. Each hub's Fabric semantic model and Fabric Data Agent operational. Gateway routes to both hubs. Data product registry MVP delivered. ADR-014 pilot completes during this phase. First certified products published.

**Phase 2 — LOB rollout (Q2 2027 – Q4 2027).** Remaining LOB hubs onboarded. Tier 2 enterprise conformance layer built out. Full registry workflows operational. Gateway multi-agent orchestration in production. RBC Assist Pattern 1 in production using cross-hub agent orchestration.

**Phase 3 — Maturity and FSDM decomposition (2028).** FSDM tables progressively absorbed into the EDLH or relevant LOB hubs. Legacy semantic layers (OBIEE, etc.) decommissioned. Promotion path actively used.

## Open questions (updated)

1. Risk Hub or Risk-as-Tier-2-only?
2. Insurance Hub primary location confirmed as on-prem; revisit if modernization roadmap accelerates.
3. Data product registry build vs. buy.
4. Cost allocation model for shared Fabric capacity.
5. External data ingestion patterns into the Raw Zone — direct LOB subscription or routed through Enterprise Data?
6. **Gateway HA and scaling targets** — to be defined during MVP design.
7. **Raw Zone retention and deletion policies** — defaults from source systems vs. uniform lakehouse policy. Likely needs a separate ADR.

## References

- ADR-002, ADR-011 amended, ADR-012, ADR-016 (proposed), ADR-014 (proposed) and amendment, ADR-015 (proposed)
- Phase 1 Pilot Plan: Fabric Semantic Models over Snowflake and Trino
- Three-Month MVP Plan (companion document, this iteration)
