# Lumina Data Hub — Architecture & Plans

This folder contains the architecture and planning documents for the Lumina Data Hub program: a federated data mesh of LOB-aligned hubs sharing an enterprise lakehouse, with the RBC Data Gateway as the trust boundary for all agentic traffic.

## Documents

| Document | Purpose |
| --- | --- |
| [`data-hub-architecture.md`](data-hub-architecture.md) | Reference architecture v2 — federated mesh, two medallions, hybrid Snowflake + Trino, Raw Zone hybrid landing, governance and federation responsibilities. Eight architectural principles. |
| [`phase-1-pilot-plan.md`](phase-1-pilot-plan.md) | Two-pilot plan validating Fabric semantic models over both Snowflake (DirectQuery + Mirroring) and Trino. 12 weeks, three decision gates. |
| [`mvp-plan-q3-2026.md`](mvp-plan-q3-2026.md) | Q3 2026 PI plan — single Capital Markets hub, single certified product (Counterparty Risk Score), end-to-end through gateway. Six 2-week iterations + stabilization. |

## Diagrams

- [`../architecture/diagrams/lumina-data-hub-executive.svg`](../architecture/diagrams/lumina-data-hub-executive.svg) — 1-page boardroom view
- [`../architecture/diagrams/lumina-data-hub-detailed.svg`](../architecture/diagrams/lumina-data-hub-detailed.svg) — engineering reference

## Related ADRs

| ADR | Topic |
| --- | --- |
| [ADR-002](../adr/002-trino-as-mandatory-query-gateway.md) | Trino as mandatory query gateway |
| [ADR-009](../adr/009-ai-data-hub-architecture.md) | AI data hub architecture (foundational) |
| [ADR-011](../adr/011-snowflake-cortex-semantic-layer.md) + [amendment](../adr/011-amendment-cortex-tactical.md) | Cortex demoted to tactical Snowflake-internal |
| [ADR-012](../adr/012-rbc-assist-fabric-data-agent-pattern.md) | RBC Assist × Fabric Data Agent consumption pattern |
| [ADR-013](../adr/013-ingestion-as-platform-capability.md) | Ingestion as platform capability (hubs compose, not ingest) |
| [ADR-014](../adr/014-fabric-semantic-plane.md) + [amendment](../adr/014-amendment-gateway-and-landing.md) | Fabric semantic plane; gateway as trust boundary; Raw Zone landing |
| [ADR-015](../adr/015-rbc-data-gateway.md) | RBC Data Gateway (FastAPI on OCP) |
| [ADR-016](../adr/016-enterprise-conformance-tier.md) | Enterprise Conformance Tier (Tier 2) — stub, full draft pending |

## Status

Draft as of 2026-05-02. Awaiting reviewer alignment on:

1. Capital Markets as Q3 2026 MVP LOB
2. Counterparty Risk Score as MVP product
3. Risk function as first cross-hub consumer
4. Whether to draft ADR-016 in full now or after MVP scoping
