# ADR-011: Snowflake Cortex as Access and Semantic Layer — Phased Fabric Extension

**Status:** Accepted
**Date:** 2026-04-15
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)
**Raised by:** Leadership direction to ship on Snowflake first (April 2026)
**Supersedes:** ADR-010 (Fabric Import Semantic Model as BI and AI Surface Layer)

---

## Context

ADR-010 established Microsoft Fabric's Import semantic model as the sole BI and AI
consumption surface for Gold-layer data. That decision assumed Fabric readiness — capacity
provisioned, Power BI migration underway, Fabric Data Agent as the NL-to-SQL path for
RBC Assist.

Leadership has since directed a faster path to production: ship an AI semantic layer on
Snowflake now, with a clean extension path to Fabric when the BI migration completes.
The rationale is straightforward — Snowflake is already provisioned, Cortex Analyst is
GA with a REST API, and the OBIEE → Power BI migration timeline is not yet confirmed.
Waiting for Fabric delays RBC Assist data grounding by quarters.

Simultaneously, Snowflake has matured its semantic layer capabilities significantly:

- **Semantic Views** (`CREATE SEMANTIC VIEW` DDL) define metrics, dimensions, facts,
  and relationships as first-class database objects.
- **Cortex Analyst** provides NL-to-SQL over semantic views via a REST API, with
  Snowflake-hosted LLMs (no data leaves Snowflake's governance boundary).
- **Cortex Agents** orchestrate across Cortex Analyst (structured) and Cortex Search
  (unstructured) with configurable orchestration models (including Claude 4 Sonnet).
- Snowflake's **Iceberg external tables** read Gold Iceberg V2 via external volumes —
  zero-copy, no data duplication.

This ADR documents the decision to adopt a phased approach: Snowflake Cortex as the
Phase 1 access and semantic layer, with Fabric as a Phase 2 parallel BI/AI surface.

---

## Decision

**Phase 1 (ship now): Snowflake Cortex Analyst as the access and AI semantic layer
over Gold Iceberg V2. Phase 2 (ship when ready): Fabric as a parallel BI/AI surface.
FastAPI trust boundary routes between both backends.**

### Core principles

1. **Gold Iceberg V2 is the single source of truth.** Written once by the on-prem
   medallion pipeline (Bronze → Silver → Gold). Read by multiple engines. Never
   duplicated into Snowflake — only accessed via external volumes.

2. **The semantic model is defined once in GitHub (YAML) and deployed to each engine.**
   CI/CD translates the canonical YAML into Snowflake semantic views (Phase 1) and
   Fabric Import semantic models (Phase 2). One definition, two deployments.

3. **FastAPI is the single trust boundary for all AI agent queries.** No agent or
   consumer app may query Snowflake or Fabric directly. FastAPI handles orchestration,
   OBO auth, guardrails, backend routing, and audit logging.

4. **Phase 2 is additive.** Nothing in Phase 1 gets torn down or rebuilt when Fabric
   comes online. Snowflake continues serving NL analytics queries. Fabric adds the
   BI surface (Power BI) and optionally the Fabric Data Agent path.

---

## Architecture

### Phase 1 — Snowflake as access + semantic layer

```
RBC Assist / Borealis
  ↓  (NL question + Entra ID token)
FastAPI Trust Boundary
  │  Orchestrator LLM classifies query
  │  Acquires OBO token scoped to Snowflake
  │  Applies guardrails (prompt injection, PII masking)
  │  Logs query for OSFI B-13 audit
  ↓
Snowflake Cortex Analyst REST API
  POST /api/v2/cortex/analyst/message
  │  Reads semantic views at query time
  │  Generates + executes SQL under user identity
  │  RBAC enforced on underlying tables
  ↓
Snowflake Semantic Views (CREATE SEMANTIC VIEW)
  │  Metrics, dimensions, time grains, relationships
  │  Deployed from GitHub YAML via CI/CD
  ↓
Iceberg External Tables (external volumes)
  │  Zero-copy read — no data duplication
  ↓
Gold — Iceberg V2 (on-prem, Nessie catalog)
  │  Authoritative, Ranger-governed, FSDM-conformed
  ↓
Silver → Bronze → Sources (Teradata, Mainframe, APIs)
```

**BI consumers (Power BI, Tableau)** connect directly to Snowflake via SQL/ODBC
in Phase 1, querying the same Iceberg external tables. They do not go through
FastAPI — the trust boundary is for AI agent queries only.

### Phase 2 — Add Fabric as parallel BI/AI surface

```
FastAPI Trust Boundary (router)
  ├── NL analytics queries  → Snowflake Cortex Analyst REST API
  ├── BI/AI surface queries → Fabric Data Agent REST API
  └── Unstructured queries  → Snowflake Cortex Search

Power BI → Fabric Import Semantic Model (direct connection, not via FastAPI)

Semantic Model YAML (GitHub)
  ├── CI/CD → Snowflake semantic views
  └── CI/CD → Fabric Import semantic model (TMDL via XMLA)

Gold Iceberg V2 (single source of truth)
  ├── Snowflake: external volumes (zero-copy)
  └── Fabric: Delta copy to OneLake (Python ETL, same pattern as ADR-010)
```

---

## Rationale

### 1. Snowflake reads Iceberg natively — zero-copy beats Delta sync

ADR-010 required a Python ETL copy from Gold Iceberg → Fabric Delta. This introduced
a data duplication point, a copy latency window, and V-Order optimisation overhead.
Snowflake's external volumes read Gold Iceberg V2 directly via the Nessie (or Polaris)
catalog. No duplication, no conversion, no latency beyond catalog refresh. The "one
truth, two surfaces" story becomes "one truth, one read path" in Phase 1.

### 2. Cortex Analyst REST API is simpler than Fabric Data Agent

The Fabric Data Agent uses the OpenAI Assistants API pattern: create thread → send
message → create run → poll for completion. It requires OBO token exchange and has a
constraint that service principal auth is not supported.

Cortex Analyst exposes a single POST endpoint that returns SQL + results synchronously
(or via SSE streaming). Auth is a standard Snowflake session token. Multi-turn
conversation is built in. The integration surface is smaller and faster to ship.

### 3. Semantic model as code fits the existing workflow

Snowflake semantic views are DDL objects deployable via SQL. The canonical definition
lives in the GitHub lakehouse repo as YAML, translated to `CREATE SEMANTIC VIEW` DDL
by the CI/CD pipeline. This fits the existing ADR/PR/code-review workflow that the
Lumina team already uses for Nessie catalogs, Python pipelines, and Trino configs.

Contrast with Fabric: the Import semantic model is authored in Power BI Desktop or
Fabric UI, with limited programmatic deployment options (TMDL via XMLA is possible
but less mature). Moving to Fabric in Phase 2 adds the TMDL deployment target to
CI/CD — it does not replace the YAML source of truth.

### 4. Cortex Analyst respects Snowflake RBAC end-to-end

Cortex Analyst generates SQL that executes under the user's Snowflake role. RBAC
policies, row access policies, column masking policies, and data classification
tags all apply automatically. No data leaves Snowflake's governance boundary — the
LLMs (Mistral, Meta) run inside Snowflake Cortex. This satisfies OSFI B-13 data
residency requirements without additional configuration.

### 5. Cortex Agents provide structured + unstructured in one orchestrator

Snowflake Cortex Agents orchestrate across Cortex Analyst (structured NL-to-SQL)
and Cortex Search (unstructured document retrieval) in a single agent. This means
RBC Assist can answer questions that span both Gold-layer analytics and policy/
compliance documents without FastAPI needing to route between separate services.
The orchestration model can be configured to Claude 4 Sonnet.

### 6. FastAPI trust boundary is backend-agnostic by design

The FastAPI trust boundary pattern (originally designed for Fabric in the AI Data
Hub architecture, ADR-009) routes NL queries to a backend data engine. Swapping
Fabric for Snowflake Cortex changes the plumbing, not the pattern. Adding Fabric
as a second backend in Phase 2 is a routing rule addition, not a redesign.

The OpenAPI spec (`docs/architecture/fastapi-trust-boundary-spec.yaml`) defines
the contract: `POST /v1/query` accepts an NL question and returns a structured
answer regardless of which backend served it. The `X-Backend-Hint` header allows
callers to suggest a backend, but the orchestrator LLM makes the final decision.

### 7. Phase 2 Fabric extension is clean and additive

When Fabric is ready (OBIEE → Power BI migration complete, Fabric capacity
provisioned), the extension requires:

- FastAPI gains a second route (Fabric Data Agent REST API)
- CI/CD gains a second deployment target (YAML → Fabric Import semantic model)
- Gold Iceberg gets a Delta copy to OneLake (same ETL pattern as ADR-010)
- OneLake security (RLS/CLS) + Purview DLP added to governance stack

Nothing from Phase 1 is removed. Snowflake continues serving NL analytics queries.
Fabric adds the BI surface (Power BI reports, Fabric Data Agent for DAX queries).

---

## Alternatives Considered

### Stay with ADR-010 (Fabric-only)

Wait for Fabric readiness and ship the Import semantic model as the sole surface.
Rejected because: (a) delays RBC Assist data grounding by an unknown number of
quarters, (b) requires the Delta copy pipeline to be built before any AI queries
can run, and (c) leadership has explicitly directed a faster path.

### Snowflake only (no Fabric extension path)

Ship Snowflake Cortex and do not plan for Fabric. Rejected because: (a) the OBIEE →
Power BI migration is still happening — Power BI needs a Fabric semantic model, and
(b) Fabric Data Agents + Fabric IQ (ontology, graph) provide capabilities that
Snowflake does not (e.g., native Power BI integration, M365 Copilot surfacing).
The phased approach preserves optionality.

### Cube as standalone semantic layer

Use Cube (or a similar middleware) as the semantic layer between consumers and
Snowflake/Fabric. Cube provides REST/GraphQL APIs and can target multiple backends.
Rejected for Phase 1 because: (a) adds infrastructure to manage, (b) Cortex Analyst
already provides NL-to-SQL with a built-in semantic model, and (c) Cube does not
eliminate the need for Snowflake-native semantic views (Cortex Analyst requires them).
Cube remains a viable option if a third backend is added beyond Snowflake + Fabric.

### Direct Snowflake Cortex Agent (skip FastAPI)

Let Snowflake Cortex Agents handle all orchestration directly, removing the FastAPI
layer. Rejected because: (a) FastAPI provides RBC-specific guardrails, PII masking,
and audit logging not available in Cortex Agents, (b) FastAPI enables multi-backend
routing (Snowflake + future Fabric), and (c) the trust boundary pattern ensures no
AI agent ever writes raw SQL against production systems — a compliance requirement.

---

## Governance

### The Snowflake governance gap

ADR-002 established Trino as the mandatory query gateway with Ranger enforcement.
Snowflake bypasses Trino/Ranger entirely — this was previously identified as a
governance gap (noted during Snowflake and Databricks evaluation).

**Mitigation options (open decision — to be resolved before production):**

| Option | Mechanism | Parity with Ranger | Complexity |
|---|---|---|---|
| Snowflake native RBAC | Role hierarchy + row access policies mapped to same role structure | Partial — no attribute-based policies | Low |
| **Immuta on Snowflake** | Dynamic ABAC, column masking, purpose-based access | **Full parity** | Medium |
| Dual governance with policy mapping | Document the mapping between Ranger policies and Snowflake RBAC | Documented gap | Low |

Immuta is currently under evaluation (vendor meeting completed). Their Snowflake
integration is mature (native, not proxy-based) and supports dynamic ABAC policies
that map to Gravitino's policy authoring plane. Recommendation: proceed with
Immuta if evaluation confirms parity.

### Phase 2 governance additions

When Fabric comes online:

- OneLake security (RLS/CLS) enforces row- and column-level controls on the Delta copy
- Microsoft Purview DLP policies apply to Fabric Data Agent queries
- Purview DSPM provides audit logging for agent interactions with sensitive data
- The governance split is explicit: Snowflake RBAC governs the Cortex path,
  OneLake security governs the Fabric path, Ranger governs the on-prem compute path

---

## Implementation Notes

### FastAPI trust boundary — API contract

Full OpenAPI 3.0 spec: `docs/architecture/fastapi-trust-boundary-spec.yaml`

Key endpoints:

```
POST /v1/query          → NL question → routed to Snowflake or Fabric → structured answer
POST /v1/query/stream   → Same, with SSE streaming for real-time UX
POST /v1/query/feedback → User thumbs-up/down, fed to Cortex verified queries
GET  /v1/health         → Backend connectivity status
GET  /v1/backends       → Available backends and semantic models
```

Auth: Bearer token (Entra ID). FastAPI exchanges for OBO token scoped to target backend.

### Snowflake Cortex Analyst integration

```python
import requests

CORTEX_ENDPOINT = "https://<account>.snowflakecomputing.com/api/v2/cortex/analyst/message"

def query_cortex_analyst(question: str, session_token: str) -> dict:
    """Call Cortex Analyst REST API with a natural language question."""
    response = requests.post(
        CORTEX_ENDPOINT,
        headers={
            "Authorization": f"Snowflake Token=\"{session_token}\"",
            "Content-Type": "application/json",
        },
        json={
            "messages": [{"role": "user", "content": [{"type": "text", "text": question}]}],
            "semantic_model_file": "@RBC_LAKEHOUSE.GOLD.SEMANTIC_STAGE/semantic-model.yaml",
            # Or use semantic_view: "RBC_LAKEHOUSE.GOLD.ENTERPRISE_SEMANTIC_VIEW"
        },
    )
    return response.json()
```

### Semantic model deployment (CI/CD)

```bash
# Phase 1: Deploy YAML → Snowflake semantic view
# In GitHub Actions or Airflow DAG

snowsql -q "
  CREATE OR REPLACE SEMANTIC VIEW RBC_LAKEHOUSE.GOLD.ENTERPRISE_SEMANTIC_VIEW
  -- Generated from docs/architecture/semantic-model-template.yaml
  -- (CI/CD translates YAML → DDL)
"

# Phase 2 (future): Deploy YAML → Fabric Import semantic model
# tabular-editor deploy --tmdl generated-from-yaml.tmdl \
#   --server powerbi://api.powerbi.com/v1.0/myorg/workspace \
#   --database semantic-model-name
```

### Semantic model template

Template with FSDM Gold table mappings: `docs/architecture/semantic-model-template.yaml`

Covers:
- `fact_account_balance` — daily balance snapshots
- `fact_transaction` — customer transactions
- `dim_customer` — FSDM Party entity
- `dim_product` — product reference
- Relationships for star schema joins
- Verified queries (few-shot examples for Cortex Analyst accuracy)

---

## Conditions for Revisiting

- **Fabric Phase 2 trigger:** OBIEE → Power BI migration substantially complete,
  Fabric capacity (F64+) provisioned, and leadership approval to proceed
- **Remove Snowflake path** if Fabric Data Agent + semantic views achieve full
  parity with Cortex Analyst capabilities and Snowflake license is not justified
- **Add Cube** if a third data engine is added to the stack (beyond Snowflake + Fabric)
  and a portable semantic layer becomes necessary
- **Escalate governance** if Immuta evaluation does not confirm Ranger parity —
  may require restricting Snowflake to read-only analytical queries with Trino
  remaining as the governed write path

---

## Consequences

- ADR-010 is superseded. The Fabric Import semantic model remains the correct
  Phase 2 architecture but is no longer the sole or Phase 1 path.
- Snowflake external volumes must be configured to read Gold Iceberg V2 from
  on-prem S3/Pure Storage via the Nessie catalog.
- The GitHub lakehouse repo gains three new artifacts:
  - `docs/architecture/fastapi-trust-boundary-spec.yaml` (OpenAPI spec)
  - `docs/architecture/semantic-model-template.yaml` (FSDM Gold mapping)
  - `decks/rbc-assist-semantic-layer-architecture.pptx` (executive deck)
- The FastAPI trust boundary must be built and deployed (Python, FastAPI, ASGI).
- Snowflake Cortex Analyst must be enabled and configured with semantic views
  over the Gold Iceberg external tables.
- Governance gap must be resolved before production: Snowflake RBAC alone or
  Immuta integration. This is an open decision with a defined evaluation path.
- Consumer apps (RBC Assist, Borealis) integrate with FastAPI — they are
  backend-agnostic and will not change when Fabric is added in Phase 2.
