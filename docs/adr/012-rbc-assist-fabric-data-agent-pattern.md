# ADR-012: RBC Assist × Fabric Data Agent Consumption Pattern — Phase 2 Extension to ADR-011

**Status:** Draft
**Date:** 2026-04-16
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)
**Raised by:** RBC Assist × Fabric Data Agent architecture review (April 2026)
**Extends:** ADR-011 (Snowflake Cortex as Access and Semantic Layer — Phased Fabric Extension)

---

## Context

ADR-011 establishes a phased access and semantic layer: Snowflake Cortex Analyst as the Phase 1 AI path (ship now), with Fabric as a parallel BI/AI surface in Phase 2 (when OBIEE → Power BI migration completes). Phase 2 adds Fabric Data Agent as a second NL path alongside Cortex Analyst, with the FastAPI trust boundary routing between backends.

This ADR documents **how RBC Assist (and other AI consumer apps) will integrate with Fabric Data Agent** when Phase 2 goes live. It does not revisit the phased decision in ADR-011 — that is authoritative. It scopes the integration pattern, the identity model, the orchestration layer, and the options for model governance over the LLM calls involved.

### What's different about Fabric Data Agent vs. Snowflake Cortex Analyst

The Phase 1 Cortex integration (per ADR-011) is a single POST endpoint returning SQL + results synchronously, with Snowflake session token auth. Phase 2 Fabric Data Agent is more complex:

1. **Identity model is different.** Fabric Data Agent supports **only On-Behalf-Of (OBO) identity passthrough** — the user's Microsoft Entra token is required for every call. Service Principal Name (SPN) authentication is not supported. This matches Cortex's user-identity model but rules out unattended background jobs against Fabric Data Agent.

2. **There are two LLM calls in the Fabric path, not one.**
   - **Orchestration LLM** — whichever model the consumer-side agent uses to decide "call the Fabric Data Agent tool with this question." This is under our governance.
   - **NL2DAX LLM inside Fabric Data Agent** — the Microsoft-managed Azure OpenAI Assistant that generates DAX from natural language. This is Microsoft-managed and opaque; RBC does not get to choose the model version.

3. **Consumer-side agent options.** Three technical patterns exist for how RBC Assist reaches Fabric Data Agent:
   - **Pattern 1** — Custom Python app (RBC Assist) calls Fabric Data Agent via Python SDK directly, through the FastAPI trust boundary
   - **Pattern 3** — Azure AI Foundry agent sits between RBC Assist and Fabric Data Agent, with Fabric Data Agent registered as a knowledge source on a Foundry project
   - **Pattern 2 (future)** — Copilot Studio in Teams/M365 uses native Fabric Data Agent connection and reuses a Foundry agent as its backend

4. **ADR-011 already decides the trust boundary.** The FastAPI trust boundary is the single agent entry point per ADR-011 — that does not change. This ADR describes what happens *inside* the Fabric branch of that router.

---

## Decision

**Phase 2a (default, ship first): Pattern 1 — RBC Assist (Python) calls Fabric Data Agent via the Python SDK through the existing FastAPI trust boundary. The FastAPI trust boundary gains a second backend route `fabric_data_agent` alongside the existing `snowflake_cortex` route from ADR-011.**

**Phase 2b (add if strategic): Pattern 3 — Introduce an Azure AI Foundry agent as an orchestration layer between FastAPI and Fabric Data Agent, with Fabric Data Agent registered as a Foundry knowledge source connection.** Pattern 3 is adopted only if RBC standardizes on Foundry as its enterprise AI agent runtime (strategic decision owned by Rex Davis / Vinh Tran / Borealis — out of scope for this ADR).

**Pattern 2 (Copilot Studio surfacing) is explicitly deferred.** It is a product-surface decision rather than a data-platform one and is not blocking. The architecture in this ADR composes forward: the same Foundry agent built in 2b can later be registered as a Copilot Studio tool, with no rebuild required.

### Core principles

1. **Fabric Data Agent is invoked only through the FastAPI trust boundary.** No RBC consumer app calls Fabric Data Agent directly. This is a direct extension of ADR-011 principle 3.

2. **Every call carries an end-user Entra token.** OBO identity passthrough is mandatory. No service-principal access to Fabric Data Agent is attempted. Workflows that cannot carry a user identity (scheduled reports, background agents, etc.) use a different path — direct XMLA read against the Fabric Import semantic model with a governed service identity, or direct Delta read — and are covered by separate governance.

3. **The orchestration LLM is RBC-approved regardless of pattern.** In Pattern 1 this is enforced by the FastAPI layer's model allowlist. In Pattern 3 this is enforced by Azure Policy applied to the Foundry project. In both cases the model the consumer-side agent uses to plan and respond is on the RBC-approved list.

4. **The NL2DAX LLM inside Fabric Data Agent is accepted as Microsoft-managed.** It is not selectable. The data layer governance (per-user RLS/OLS on the Fabric Import semantic model, Purview DLP, Entra identity passthrough, OBO audit) mitigates this. This is a known and accepted constraint.

5. **Phase 2a → Phase 2b is additive, not a replacement.** Introducing Foundry does not remove the FastAPI trust boundary. The FastAPI layer shrinks — orchestration and multi-tool routing move to Foundry — but RBC-specific PII rules, RBC audit format, cost attribution, and guardrails for the Teradata/Snowflake paths all remain in FastAPI.

---

## Architecture

### Phase 2a — Pattern 1 (default)

```
RBC Assist (Python) / Borealis
  ↓  (NL question + Entra ID user token)
FastAPI Trust Boundary
  │  Orchestrator LLM classifies the query and selects backend
  │  Applies RBC-specific guardrails (PII masking, prompt injection, cost caps)
  │  OBO token exchange scoped to target backend
  │  Logs query for OSFI B-13 audit
  ↓  (route: fabric_data_agent)
Fabric Data Agent (Python SDK)
  │  Receives OBO user token
  │  Internal Microsoft-managed Azure OpenAI Assistant
  │    parses question → generates DAX → executes under user identity
  │  Per-user RLS/OLS enforced by the Fabric Import semantic model
  ↓
Fabric Import Semantic Model (Gold copy in OneLake, per ADR-011 Phase 2)
  ↓
Delta tables in OneLake
  ↑  (Python ETL copy from Gold Iceberg V2 — same ETL pattern as ADR-010)
Gold — Iceberg V2 (on-prem, Nessie catalog)  [single source of truth per ADR-011]
```

The FastAPI trust boundary from ADR-011 gains a second route rule:

```
POST /v1/query                     → orchestrator selects backend
  ├── route: snowflake_cortex      → Snowflake Cortex Analyst REST API (Phase 1, existing)
  └── route: fabric_data_agent     → Fabric Data Agent via Python SDK (Phase 2a, new)
```

### Phase 2b — Pattern 3 (if Foundry is adopted)

```
RBC Assist (Python) / Borealis
  ↓  (NL question + Entra ID user token)
Thin FastAPI Trust Boundary
  │  RBC-specific PII rules, RBC audit format, cost attribution
  │  OBO exchange for Foundry-scoped token
  ↓
Azure AI Foundry agent
  │  Orchestration LLM (RBC-approved model enforced by Azure Policy)
  │  Entra Agent ID inventory for tenant-wide agent audit
  │  Content Safety, prompt shields
  │  Fabric Data Agent registered as a knowledge source connection
  │  Identity passthrough (OBO) to Fabric Data Agent
  ↓
Fabric Data Agent  →  Fabric Import Semantic Model  →  Delta in OneLake  →  Gold Iceberg V2
```

In Phase 2b the FastAPI layer becomes thinner: tool orchestration moves into the Foundry agent, and the FastAPI layer focuses on the controls that only RBC can enforce (local PII rules, SIEM integration, cost attribution per user/use-case, and the non-Foundry paths such as Snowflake Cortex and direct Teradata).

---

## Rationale

### 1. Start with Pattern 1 because it composes with the ADR-011 pattern

ADR-011 already defines the FastAPI trust boundary. Pattern 1 adds a second backend route to that boundary and uses the Fabric Data Agent Python SDK, which supports OBO natively. No new platform dependency. The integration surface is a routing rule and a new client adapter. The team can ship this without Foundry, without a new governance review, and without a new vendor relationship.

### 2. Pattern 3 (Foundry) is strategically valuable but requires a separate decision

Foundry adds meaningful governance that is hard to replicate in Python code:

- **Azure Policy model allowlist** for the orchestration LLM — declarative and auditable, not a config dict in FastAPI
- **Entra Agent ID** tenant-wide inventory, giving audit and InfoSec a single console to enumerate AI agents
- **Content Safety + prompt shields** built in
- **Multi-tool orchestration** as a platform feature — if Borealis later exposes additional tools, Foundry can register them as project connections rather than adding more FastAPI routes

However, Foundry also introduces a new platform to govern, bill against, and monitor. Whether RBC adopts Foundry as its enterprise AI agent runtime is a strategic decision owned by Rex Davis and Vinh Tran / Borealis. This ADR takes no position on that strategic question. It documents how Pattern 3 composes with Pattern 1 so that when the strategic question is answered, the architectural extension is already specified.

### 3. Pattern 2 (Copilot Studio) is deferred because it is a product-surface decision

Copilot Studio surfaces AI agents in Teams and M365 Copilot with native Microsoft Fabric Data Agent integration. It is a valuable future surface — particularly for end-user analytics consumption — but it is not blocking the Phase 2 agent integration. The architectural implication is important: a Copilot Studio agent can register a Foundry agent as its backend. So if Pattern 3 is adopted, Copilot Studio surfacing is a configuration layer on top, not a rebuild.

### 4. The NL2DAX opacity is a known constraint, not a blocker

Fabric Data Agent's internal Azure OpenAI Assistant is Microsoft-managed — RBC cannot select the model, cannot constrain it via Azure Policy, and cannot swap it. This was surfaced and accepted in the architecture review. The mitigations are:

- **Data-layer governance remains strong.** The user's OBO identity flows through to the Fabric Import semantic model; RLS/OLS is enforced per user; Purview DLP applies at the data layer; all query activity is audit-logged.
- **Azure OpenAI data terms apply.** RBC's existing enterprise agreement covers the NL2DAX call — no training on RBC data, data residency commitments, content safety policies.
- **Output validation on the FastAPI side.** Query results returned by Fabric Data Agent pass back through the FastAPI trust boundary, where RBC-specific output filters (PII masking, sensitivity checks) apply before the response reaches the consumer app.

For workloads where an opaque NL2DAX model is unacceptable, the Phase 1 Snowflake Cortex path remains available — Cortex Analyst runs Snowflake-hosted LLMs that RBC can constrain via Cortex configuration, and RBAC applies end-to-end.

### 5. Consistency with ADR-011's "backend-agnostic" principle

ADR-011 principle 4 establishes Phase 2 as additive to Phase 1. This ADR extends that: Pattern 1 is additive to Phase 1 (FastAPI gains a route), Pattern 3 is additive to Pattern 1 (Foundry sits between FastAPI and Fabric Data Agent). Each step is a clean extension rather than a rebuild.

---

## Alternatives Considered

### Skip FastAPI — call Fabric Data Agent directly from RBC Assist

Rejected. The FastAPI trust boundary is established by ADR-011 principle 3: no consumer app may query backends directly. Bypassing it would require re-implementing PII masking, audit logging, OBO orchestration, and cost attribution inside RBC Assist — and duplicating that work in every future consumer app. It also breaks the "single entry point" guarantee that compliance depends on.

### Use Fabric Data Agent as an MCP server from RBC Assist

Considered. Fabric Data Agents can function as MCP servers, exposing a single tool per data agent. Rejected as the primary pattern because the MCP-server mode is currently limited to VS Code client use and is not production-ready for a web-based consumer app. Revisit when Microsoft broadens MCP server client support beyond VS Code.

### Adopt Pattern 3 immediately (Foundry-first)

Considered. Rejected because (a) the Foundry-as-enterprise-runtime decision is not yet made by Rex / Vinh, and (b) Pattern 1 ships faster and does not foreclose Pattern 3. If Foundry is adopted strategically, the Pattern 1 → Pattern 3 migration is an incremental change (FastAPI route becomes a Foundry call; Fabric Data Agent moves from an SDK dependency to a Foundry connection).

### Adopt Pattern 2 immediately (Copilot Studio surfacing)

Considered. Rejected for the same reason as above — Pattern 2 composes cleanly on top of Pattern 3, and adopting it before the Foundry decision is made would couple the data-platform architecture to a product-surface choice prematurely. Copilot Studio remains on the roadmap as a consumer-facing surface once Foundry (if chosen) is in place.

---

## Governance

### Identity and auth

- **OBO only** for Fabric Data Agent — no SPN access. This is a Microsoft platform constraint, not an RBC choice.
- **FastAPI performs the OBO exchange** in Pattern 1; the Foundry agent performs it in Pattern 3. In both cases the user's Entra identity reaches Fabric Data Agent and the underlying semantic model.
- **Workloads without a user identity** (scheduled reports, Borealis background agents) are explicitly out of scope for Fabric Data Agent and must use the ADR-011 Phase 1 Snowflake Cortex path or a direct-access pattern (XMLA against the Fabric semantic model with a governed service identity, Delta read via service principal) governed separately.

### Model governance

| LLM call | Pattern 1 (default) | Pattern 3 (if adopted) |
|---|---|---|
| Orchestration LLM | RBC-approved list enforced in FastAPI | RBC-approved list enforced by Azure Policy on Foundry |
| NL2DAX LLM inside Fabric Data Agent | Microsoft-managed, opaque | Microsoft-managed, opaque — Foundry does not change this |
| Response composition LLM | Same as orchestration | Same as orchestration |

### Data-layer governance

Unchanged from ADR-011 Phase 2:

- Fabric Import semantic model enforces per-user RLS/OLS
- Microsoft Purview DLP applies to Fabric Data Agent queries
- Purview DSPM provides audit logging for agent interactions with sensitive data
- OneLake security governs the Delta copy

### Audit

- **Pattern 1:** FastAPI audit log is authoritative; captures NL question, user identity, backend selected, response summary, timestamps, latency, cost tokens
- **Pattern 3:** FastAPI audit log plus Azure Monitor agent-level audit plus Foundry's Entra Agent ID inventory. Entra Agent ID gives RBC InfoSec a tenant-wide view of which AI agents exist and what they have access to

---

## Implementation Notes

### Phase 2a (Pattern 1) — new FastAPI route

Extend `docs/architecture/fastapi-trust-boundary-spec.yaml` to document the `fabric_data_agent` backend. Add a new client adapter:

```python
# etl/src/semantic/clients/fabric_data_agent_client.py (new)
from fabric_data_agent_client import FabricDataAgentClient

def query_fabric_data_agent(
    question: str,
    user_obo_token: str,
    workspace_id: str,
    artifact_id: str,
) -> dict:
    """Call Fabric Data Agent via Python SDK with end-user OBO token."""
    # FastAPI trust boundary performs the OBO exchange before calling this
    client = FabricDataAgentClient(
        tenant_id=TENANT_ID,
        data_agent_url=f"https://api.fabric.microsoft.com/groups/{workspace_id}/aiskills/{artifact_id}",
        credential=OBOTokenCredential(user_obo_token),
    )
    return client.ask(question)
```

The orchestrator LLM in FastAPI selects `fabric_data_agent` vs. `snowflake_cortex` based on the query, the user's role, and (once Phase 2 is live) the query class (BI/analytics questions against the Fabric semantic model tend toward Fabric; ad-hoc analytics and cross-domain questions tend toward Snowflake Cortex).

### Phase 2b (Pattern 3) — Foundry agent setup

If adopted:

1. Create an Azure AI Foundry project governed by Azure Policy allowlisting RBC-approved models only (GPT-4o, Claude Sonnet, etc. — as per enterprise AI model policy)
2. Register Fabric Data Agent as a connection: connection type "Microsoft Fabric", workspace ID and artifact ID as secrets
3. Configure the Foundry agent's instructions to route Fabric-appropriate queries to the Fabric Data Agent tool
4. FastAPI gains a `foundry_agent` backend route that calls the Foundry agent endpoint with the user's OBO token; the Foundry agent handles onward routing to Fabric Data Agent (and any other registered tools)
5. Entra Agent ID configuration for the Foundry agent so InfoSec can enumerate it

---

## Conditions for Revisiting

- **Foundry strategic decision:** When Rex Davis / Vinh Tran resolve the Foundry-as-enterprise-runtime question, promote Pattern 3 to Accepted and the `foundry_agent` backend route is added to the FastAPI trust boundary. If Foundry is rejected strategically, Pattern 1 becomes the permanent answer.
- **MCP server client support:** If Microsoft broadens Fabric Data Agent MCP server support beyond VS Code to production web clients, consider an alternative pattern where RBC Assist consumes Fabric Data Agent via MCP rather than Python SDK.
- **Fabric Data Agent SPN support:** If Microsoft adds service-principal authentication to Fabric Data Agent (it is not supported today), revisit the scope to include unattended/background workloads.
- **Copilot Studio direction:** If RBC decides to surface RBC Assist through Teams/M365 Copilot, add Pattern 2 as a Phase 2c extension layered on top of Pattern 3 (or Pattern 1 if Foundry is rejected).
- **NL2DAX opacity becomes unacceptable:** If regulatory requirements evolve such that the Microsoft-managed NL2DAX model is not acceptable for RBC workloads, Fabric Data Agent is removed from the agent path. BI consumption via Power BI reports against the semantic model (which does not involve NL2DAX) continues; agent NL consumption falls back to Snowflake Cortex exclusively.

---

## Consequences

- The FastAPI trust boundary gains a second backend adapter (`fabric_data_agent`) when Phase 2 ships. This is an additive change — no impact on Phase 1 Cortex flow.
- The `fabric-data-agent-client` Python package (currently in preview) becomes a production dependency. A preview-to-GA watch is added to the platform roadmap.
- RBC Assist and other consumer apps require no code changes to gain Fabric Data Agent access — they continue to call FastAPI; FastAPI orchestrates backend selection.
- If Foundry is adopted (Pattern 3), the FastAPI layer becomes thinner — tool orchestration moves into Foundry — but the trust-boundary function remains. This is an internal refactor, not a breaking change for consumers.
- The Foundry-as-runtime question becomes a documented open decision with explicit architectural impact, making it easier for Rex / Vinh to resolve on a defined timeline.
- The companion deck `decks/rbc-assist-fabric-architecture-options.pptx` provides the executive narrative that supports this ADR and should be read alongside it.
