# ADR-015: RBC Data Gateway — On-Prem Trust Boundary and Orchestrator for AI Data Access

| Field | Value |
| --- | --- |
| **Status** | Proposed |
| **Date** | 2026-05-02 |
| **Author** | George Chilakos (VP, Enterprise Data) |
| **Related** | ADR-002 (Trino as mandatory query gateway), ADR-012 (RBC Assist × Fabric Data Agent consumption pattern), ADR-014 (Semantic Plane Architecture) |

## Context

ADR-012 defined two patterns for RBC Assist consumption of Fabric Data Agent: Pattern 1 (Python/FastAPI) and Pattern 3 (Azure AI Foundry). The Data Hub Architecture commits to a federated mesh with per-LOB Fabric semantic models and per-LOB Fabric Data Agents. That commitment forces a question ADR-012 left implicit: **how does RBC Assist, running on RBC's on-prem OpenShift Container Platform (OCP), reach multiple Fabric Data Agents across multiple LOB hubs, with consistent governance, audit, and trust enforcement?**

Three options exist:

1. RBC Assist calls each Fabric Data Agent directly across the network boundary. Each agent call is independently authenticated and audited. RBC Assist holds the orchestration logic.
2. RBC Assist calls Microsoft Copilot Studio, which orchestrates across Fabric Data Agents using agent-to-agent (Model Context Protocol). Microsoft holds the orchestration logic; RBC inherits its maturity curve.
3. RBC Assist calls an on-prem gateway service that handles authentication, audit, prompt-injection defense, identity translation, federation routing, and cross-agent orchestration. The gateway holds the orchestration logic on-prem.

Option 1 fragments enforcement and creates an N-to-N integration problem (every consumer × every agent). Option 2 places critical orchestration logic in a Microsoft-controlled plane that is still maturing as of 2026 and over which RBC has limited operational visibility. Option 3 — the gateway pattern — concentrates enforcement in one component RBC controls, on RBC infrastructure, with full audit and operational visibility.

The decision is to adopt Option 3.

## Decision

Establish the **RBC Data Gateway** as the mandatory trust boundary and orchestrator for all AI data access at RBC. The gateway is realized as a FastAPI service running in containers on RBC's OpenShift Container Platform (OCP). All AI-driven data consumers — RBC Assist primarily, plus future agentic consumers including M365 Copilot when used in agentic mode — call the gateway. The gateway calls the appropriate downstream Fabric Data Agents and other semantic backends, composes responses where needed, and returns results to the consumer.

**Scope: AI traffic only.** Power BI continues to talk directly to Fabric semantic models via DirectQuery. Human-driven SQL continues to flow through Trino per ADR-002. The gateway exists to govern *agentic* access, where the consumer is an LLM-driven workflow rather than a human user with a deterministic query.

**Implementation: same as design.** The "RBC Data Gateway" is the architectural role; the FastAPI service on OCP is its implementation. They are not separate components.

**Orchestration responsibility: on-prem.** Per Option A above, the gateway itself is the orchestrator across multiple Fabric Data Agents. Copilot Studio agent-to-agent capabilities may be adopted later as the Microsoft orchestration plane matures, but the architectural commitment is to keep orchestration logic on RBC infrastructure for as long as is practical.

## Gateway responsibilities

The gateway is a single component with seven explicit responsibilities:

1. **Authentication and identity translation.** Validates the caller's Entra ID token, translates the user identity into the form Fabric Data Agent expects (delegated user identity by default, agent-author identity for specific automation), and propagates the identity end-to-end so that RLS, CLS, and Purview labels are enforced at the data layer.

2. **Authorization at the gateway boundary.** Enforces a policy layer separate from data-layer enforcement. The gateway can deny a call before it reaches Fabric (e.g., based on time-of-day, source application, request rate) without consuming Fabric capacity or data egress.

3. **Federation routing across hubs.** The gateway holds a routing map (configured, not hardcoded) of which Fabric Data Agent serves which domain. When RBC Assist asks "what is my client's full relationship," the gateway decomposes the query, calls the relevant per-hub agents, and composes the result. This is the orchestration responsibility.

4. **Prompt-injection defense.** Inbound prompts are scanned for known injection patterns, suspicious structures, and policy-violating content before being passed to Fabric Data Agent. Outbound responses are scanned for sensitive data leakage. This defense is in addition to (not instead of) Microsoft's own defenses inside Fabric.

5. **PII scrubbing and sensitivity enforcement.** Where the user's permissions require redaction, the gateway applies it before returning the response. This is a defense-in-depth layer; the primary enforcement is at the data layer via Purview labels.

6. **Audit and observability.** Every request and response is logged with full context: caller identity, prompt, downstream agents called, response, latency, costs. Audit logs flow to RBC's existing SIEM. Observability metrics flow to RBC's existing platform observability stack.

7. **Rate limiting and cost control.** Per-caller quotas, per-agent throttling, cost ceilings to prevent runaway agent calls. Critical because Fabric Data Agent serving compute is consumption-billed and a misbehaving consumer could materially impact Fabric capacity costs.

## Internal architecture of the gateway

The FastAPI service is structured as five logical components, deployed as one or more containers on OCP:

| Component | Purpose |
| --- | --- |
| **Auth layer** | Entra ID token validation, identity translation, Entra-to-Fabric identity propagation |
| **Policy layer** | Inbound policy evaluation (rate, time, source, content), outbound policy evaluation (sensitivity, PII) |
| **Orchestrator** | Decomposes complex requests into per-agent calls, manages parallelism, composes responses, handles partial failures |
| **Backend adapters** | Pluggable adapters for Fabric Data Agent (primary), Cortex Analyst (tactical, if used), and future backends. Each adapter handles the specifics of one downstream system |
| **Audit and metrics** | Structured logging, SIEM forwarding, observability metrics emission |

The orchestrator is the most consequential component. It is what makes the gateway more than a reverse proxy.

## What the gateway is NOT

To prevent scope creep, the gateway is explicitly *not*:

- **A semantic layer.** The gateway does not hold metric definitions, glossary terms, or business logic. Those live in Fabric semantic models. The gateway is a routing and enforcement layer.
- **A data layer.** The gateway does not store data, cache results long-term, or hold a denormalized copy of anything. Short-lived caching for performance is acceptable; data retention is not.
- **A consumer-facing UI.** RBC Assist, Power BI, and other consumers have their own UIs. The gateway is API-only.
- **A path for human-driven BI.** Power BI users do not go through the gateway. Human-driven SQL via Trino does not go through the gateway. The gateway exists for AI traffic specifically.
- **A replacement for Trino.** Trino remains the mandatory gateway for SQL and federated query per ADR-002. The gateway and Trino sit at different planes — the gateway above the semantic layer for AI, Trino above the storage layer for SQL.

## Decision drivers

1. **Concentration of enforcement.** A single chokepoint where authentication, authorization, prompt-injection defense, identity translation, and audit happen is dramatically simpler to govern, audit, and reason about than distributed enforcement across N consumers and M agents.

2. **On-prem control.** RBC's regulatory and operational posture strongly favors keeping critical agent orchestration logic on infrastructure RBC operates, monitors, and audits directly. Copilot Studio's orchestration is improving but cannot match this in the near term.

3. **Federation across hubs.** A federated mesh means agentic queries frequently span multiple hubs. Without an orchestrator, every consumer would have to know the hub topology and call agents individually — a leaky abstraction that breaks the mesh.

4. **Cost control.** Fabric capacity is consumption-billed at the agent serving layer. A gateway with rate limiting and cost ceilings is the only place to enforce per-consumer budget discipline.

5. **Existing OCP investment.** RBC has mature OpenShift Container Platform operations, a CI/CD pipeline for OCP services, and a security-review process that already covers FastAPI services. Building the gateway as one more OCP service incurs minimal new operational overhead.

## Alternatives considered

**Alternative A: Direct calls from RBC Assist to Fabric Data Agent.** Rejected. Fragments enforcement, creates N-to-N integration, no place to enforce cross-cutting concerns (cost, identity translation, prompt-injection defense as a unified layer).

**Alternative B: Copilot Studio as the orchestrator.** Rejected for now, revisitable later. Microsoft-controlled orchestration plane, limited operational visibility for RBC, capability still maturing. Worth re-evaluating in 18-24 months once Copilot Studio agent-to-agent matures and once RBC has operational experience with simpler integrations.

**Alternative C: Trino as the AI gateway as well as the SQL gateway.** Rejected. Trino is excellent at federated SQL but is not designed for prompt-injection defense, agent orchestration, or LLM-specific concerns. Conflating the two responsibilities would weaken both.

**Alternative D: Build the gateway as part of RBC Assist itself rather than a separate service.** Rejected. RBC Assist is one consumer of agentic data access; future consumers (operational AI agents, automation workflows, M365 Copilot in agentic mode) will need the same enforcement. The gateway must be a shared service.

## Consequences

### Positive

- One enforcement point for AI data access; one place to audit, secure, and observe.
- RBC retains orchestration control on-prem.
- Federation across hubs is encapsulated in the gateway, not exposed to every consumer.
- Cost ceilings and rate limiting are enforceable.
- Future agentic consumers slot in cleanly with no architectural change.

### Negative / Risks

- **Latency overhead.** Adding a gateway hop adds milliseconds to AI request latency. Mitigation: gateway runs in the same OCP cluster as RBC Assist, eliminating most network overhead. Validate empirically in pilot.
- **Single point of failure.** The gateway becomes critical infrastructure. Mitigation: multi-replica deployment on OCP, standard HA patterns, well-rehearsed runbooks.
- **Operational ownership and on-call burden.** A new service to operate. Mitigation: Platform team owns; standard OCP operational patterns; observability built in from day one.
- **Orchestrator complexity.** Decomposing complex queries across multiple agents and composing responses is non-trivial. Mitigation: start with simple routing and a small number of agents in MVP; add orchestration sophistication incrementally.

## Phasing

**Phase 1 — Single-agent MVP (Q3 2026).** Gateway routes RBC Assist calls to a single LOB Fabric Data Agent. All seven responsibilities operational at minimum viable level. No cross-agent orchestration yet. Goal: validate the pattern end-to-end.

**Phase 2 — Multi-agent orchestration (Q4 2026 – Q1 2027).** Gateway routes to two or more Fabric Data Agents, decomposes simple cross-hub queries, composes responses. First production cross-LOB use case (likely customer 360 or counterparty exposure).

**Phase 3 — Mature orchestration and additional consumers (Q2 2027 onwards).** Sophisticated decomposition, multiple agentic consumers beyond RBC Assist, full integration with the data product registry for dynamic agent discovery.

## Out of scope

- The internal logic of Fabric Data Agents (LLM choice, prompt design, retrieval logic) — those are Fabric concerns.
- The orchestration of non-AI workflows — Airflow handles those.
- The user-facing UX of RBC Assist — that is owned by the Assist team, not by the data platform.

## References

- ADR-002: Trino as mandatory query gateway
- ADR-012: RBC Assist × Fabric Data Agent consumption pattern (this ADR realizes Pattern 1 explicitly)
- ADR-014: Semantic Plane Architecture
- Data Hub Architecture document (companion)
