# ADR-014 Amendment — RBC Data Gateway and Operational Landing Reference

| Field | Value |
| --- | --- |
| **Original ADR** | ADR-014: Semantic Plane Architecture |
| **Amendment Date** | 2026-05-02 |
| **Amended By** | This amendment |
| **Status of Original ADR** | In effect; this amendment adds clarifications |
| **Companion ADRs** | ADR-015 (RBC Data Gateway — new) |

## What changes

ADR-014 established Fabric semantic models as the unified semantic plane above Snowflake and Trino, with Fabric Data Agent as the AI consumption surface. Two implicit assumptions in that ADR are made explicit by this amendment:

1. **AI consumption is mediated by an on-prem trust boundary.** RBC Assist and other agentic consumers do not call Fabric Data Agent directly across the network boundary. They call the **RBC Data Gateway** (FastAPI on OCP), which authenticates, audits, federates across hubs, defends against prompt injection, and orchestrates per-hub Fabric Data Agent calls. ADR-015 establishes the gateway as a separate, named architectural component.

2. **Operational data does not flow through the legacy EDW.** The original ADR-014 assumed operational data lands in the EDLH. This amendment makes explicit that operational data lands in a **Raw / Landing Zone in Iceberg**, sitting beneath both the EDLH and the LOB hubs. EDLH ingestion and LOB hub ingestion both pull from this shared Raw Zone. The legacy Teradata FSDM is no longer the gateway for operational data; it becomes a *source* feeding the Raw Zone via CDC during the transition period.

Neither change reverses ADR-014's core decision; both make it operationally precise.

## Updated consumption table

The original table in ADR-014 §Decision is amended as follows. The amended row is shown in bold.

| Plane | Components | Notes |
| --- | --- | --- |
| **Storage** | Iceberg V2 on object storage, Nessie catalog, Gravitino governance, Ranger enforcement | Unchanged |
| **Operational landing** | **Raw / Landing Zone in Iceberg, hybrid model: enterprise-shared sources via platform-mediated ingestion, LOB-specific sources via self-serve LOB-owned namespaces** | **New layer made explicit** |
| **Compute** | Snowflake (cloud), Trino (on-prem mandatory gateway per ADR-002) | Unchanged |
| **Semantic** | Fabric semantic models, single definition per metric, federated ownership | Unchanged |
| **AI gateway** | **RBC Data Gateway (FastAPI on OCP). Mandatory for all agentic consumers including RBC Assist. Power BI and human SQL bypass.** | **New layer made explicit; ADR-015** |
| **Consumption** | Power BI (direct to Fabric semantic models), RBC Assist (via gateway), M365 Copilot (via gateway when agentic), Trino SQL clients (per ADR-002), Cortex Analyst (tactical Snowflake-internal only) | Updated to reflect gateway routing |

## What is unchanged from ADR-014

- Fabric semantic models remain the unified semantic plane above both Snowflake and Trino.
- Cortex Analyst remains a tactical Snowflake-internal capability, not the enterprise standard.
- DirectQuery / Fabric Mirroring strategy for reaching Snowflake unchanged.
- DirectQuery to Trino strategy for reaching on-prem unchanged.
- Phasing and pilot plan unchanged in substance; the pilot now includes the gateway as one of the validated components.

## Cross-references

- For gateway design and decision rationale, see ADR-015.
- For operational landing zone design (hybrid platform-mediated and LOB self-serve), see the Data Hub Architecture document.
- For RBC Assist's specific consumption pattern through the gateway, ADR-012 should be read as describing **Pattern 1** (FastAPI / on-prem) which the gateway realizes. Pattern 3 (Azure AI Foundry direct) is deprecated as the production path; it remains available only as a fallback.
