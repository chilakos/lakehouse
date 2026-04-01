# ADR-010: Microsoft Fabric Import Semantic Model as BI and AI Surface Layer

**Status:** Accepted
**Date:** 2026-04-01
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)
**Raised by:** BI/AI surface layer evaluation (April 2026)
**Supersedes:** ADR-008 contingency pattern

---

## Context

The lakehouse needs a BI and AI consumption surface for Gold-layer data. The existing
Cube → PostgreSQL wire protocol path works today for the two Gold tables in scope
(trading_metrics, risk_exposure). As the Teradata migration scales Gold to 50-200+
modelled tables and the OBIEE → Power BI migration (~1,000 reports) proceeds, a
governed semantic layer becomes the critical path for BI delivery.

Simultaneously, RBC's AI assistant (RBC Assist) requires structured data grounding —
the ability to answer natural language questions against governed Gold-layer data with
per-user security enforcement.

Three consumption architecture options were evaluated:

| Option | Mechanism | Performance | Security | Complexity |
|---|---|---|---|---|
| DirectQuery to Trino | ODBC/JDBC from Power BI | Poor (every visual = Trino query) | ✅ Ranger only | Low |
| OneLake shortcuts + Direct Lake | XTable Iceberg→Delta, shortcut to on-prem S3 | Good | ⚠️ Split plane, RLS 403 | High |
| **Fabric Import semantic model** | Python ETL copy Gold→Delta, VertiPaq in-memory | **Best** | **✅ Cleanest** | **Medium** |

ADR-008 evaluated and rejected OneLake shortcuts. DirectQuery-only was rejected due to
unacceptable Power BI query performance and absence of a shared semantic layer. This ADR
documents the decision to adopt the Fabric Import semantic model pattern.

---

## Decision

**Adopt Microsoft Fabric's semantic layer in Import mode as the BI and AI surface for
Gold-layer data. Gold exists in two deliberate representations:**

1. **Iceberg V2 on on-prem S3 (MinIO)** — authoritative, Ranger-governed, compute plane
   (Trino, Teradata Vantage). This is the write target for all ETL pipelines.

2. **Delta in Fabric (OneLake)** — BI/AI surface plane only. A scheduled Python ETL job
   copies curated Gold tables from Iceberg into Fabric as Delta, V-Order optimised for
   VertiPaq. A Fabric Import semantic model reads this copy. No Iceberg readers, no XTable,
   no shortcuts.

**No OneLake shortcuts are used. No XTable metadata virtualization is in the path.**

---

## Architecture

```
Trino / Teradata Vantage
  ↓  (authoritative writes)
Gold Layer — Iceberg V2 on MinIO/S3
  │  Ranger-governed · Nessie-catalogued · OPTIMIZE + VACUUM enforced
  │
  ↓  Python ETL copy (scheduled, Gold-only, not Bronze/Silver)
     aws s3 sync or Trino → Pandas → Fabric Delta writer
     V-Order applied for VertiPaq optimisation

Fabric Lakehouse (Delta tables, Tables/ section)
  ↓
Fabric Semantic Model — Import mode
  ├── DAX measures, relationships, KPIs defined once
  ├── "Prep for AI" schema, verified answers, business term definitions
  ├── RLS at semantic model layer (not OneLake security layer)
  │
  ├── Power BI                     ← Import-speed VertiPaq queries
  ├── Tableau (XMLA endpoint)      ← Same model, same KPIs
  └── Fabric Data Agent
        ↓  NL2DAX published REST endpoint
      Azure AI Foundry
        ↓  MicrosoftFabricPreviewTool
      RBC Assist (custom chatbot)
        Entra ID identity end-to-end · raw data never leaves RBC
```

---

## Rationale

### 1. Import mode is the fastest BI query path

Import mode loads Gold data fully into VertiPaq — an in-memory columnar engine. It is
faster than Direct Lake (which still reads from Parquet files at query time) and
substantially faster than DirectQuery (which fires a Trino query per visual interaction).
For 1,000+ OBIEE report migrations, this performance difference is material.

### 2. Import mode enables the full AI Prep toolset

The "Prep for AI" feature in Power BI Desktop — which allows defining AI Data Schema,
Verified Answers, and AI Instructions to tune Fabric Data Agent NL2DAX accuracy — is
supported in Import and DirectQuery models but **not in Direct Lake**. Import mode is
therefore the correct foundation for the RBC Assist integration.

### 3. Security model is cleanest at semantic model layer

RLS defined on the Fabric semantic model applies uniformly to all consumers: Power BI,
Tableau (via XMLA), and the Fabric Data Agent. There is no OneLake shortcut cross-workspace
RLS path to fail (ADR-008 §2 identified this as a hard limitation). One RLS definition,
enforced everywhere.

### 4. No XTable translation risk

The Iceberg→Delta metadata virtualization via Apache XTable (used by OneLake shortcuts)
has known fidelity gaps: unsupported partition transforms, absolute path sensitivity,
single-metadata-set constraint, and silent fallback behaviour. A Python ETL copy to native
Delta eliminates this risk entirely. The copy is transparent, testable, and debuggable.

### 5. The Gold copy is small and cheap

Gold is pre-aggregated and curated. The Gold semantic model for BI consumption is not
petabytes — it is the subset of Gold tables modelled for analyst consumption, typically
gigabytes in VertiPaq. The copy cost is negligible relative to the operational clarity
it purchases.

### 6. One semantic model powers three consumption surfaces

The same Import semantic model serves Power BI (VertiPaq queries), Tableau (XMLA endpoint),
and RBC Assist (Fabric Data Agent → NL2DAX → Azure AI Foundry). A single DAX measure
definition is shared across all three surfaces. No diverging KPI definitions between tools.

### 7. RBC Assist integration is production-ready

Fabric Data Agents are standalone artifacts callable from Azure AI Foundry via
`MicrosoftFabricPreviewTool`. The agent uses the end user's Entra identity to generate
secure NL2DAX queries. Only schema/metadata is sent to Azure OpenAI — raw data never
leaves RBC's environment. This satisfies OSFI B-13 data residency requirements.

---

## Alternatives Considered

### DirectQuery to Trino from Power BI

Every visual interaction fires a Trino query. For a report with 10 visuals, opening it
executes 10 concurrent Trino queries. At 1,000+ migrated reports with concurrent users,
this is unacceptable query load on the compute plane. Additionally, there is no shared
semantic layer — each report author reimplements measures independently, breaking KPI
governance. Rejected.

### OneLake shortcuts + Direct Lake

Evaluated thoroughly in ADR-008. Rejected due to: XTable fidelity gaps, OPDG operational
overhead, key/secret-only auth for S3-compatible sources, RLS 403 errors on cross-workspace
shortcut paths, and split governance plane (Ranger on-prem + OneLake security in cloud).

### Direct Lake on native Delta copy (no Import)

Direct Lake reads Parquet files directly — faster than DirectQuery, slower than Import.
However: (a) Direct Lake on OneLake mode has no DirectQuery fallback — failures are hard
failures not graceful degradations, (b) "Prep for AI" is not available in Direct Lake,
(c) Import mode is the right choice for Gold-layer BI tables which are small enough to
fit in VertiPaq capacity. Direct Lake is the right choice if Gold semantic model size
exceeds Fabric capacity memory limits — this is a future migration trigger, not a
day-one decision.

---

## Implementation Notes

### Python ETL Copy Pattern (Gold → Fabric Delta)

```python
# Gold → Fabric copy pattern
# Runs as an Airflow DAG on the Gold refresh schedule

import pandas as pd
from pyiceberg.catalog import load_catalog
from deltalake import write_deltalake

# Read from Gold Iceberg (via Trino or PyIceberg)
catalog = load_catalog("nessie", **nessie_config)
table = catalog.load_table("gold.trading_metrics")
df = table.scan().to_pandas()

# Write to Fabric OneLake as Delta (V-Order applied by Fabric on first Direct Lake frame)
write_deltalake(
    "abfss://workspace@onelake.dfs.fabric.microsoft.com/lakehouse/Tables/gold_trading_metrics",
    df,
    mode="overwrite",
    schema_mode="overwrite",
)
```

### Fabric Data Agent → Azure AI Foundry Integration

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects.models import (
    PromptAgentDefinition,
    MicrosoftFabricPreviewTool,
    FabricDataAgentToolParameters,
    ToolProjectConnection,
)

project = AIProjectClient(
    endpoint=FOUNDRY_PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

fabric_connection = project.connections.get(FABRIC_CONNECTION_NAME)

agent = project.agents.create_version(
    agent_name="RBCAssistDataAgent",
    definition=PromptAgentDefinition(
        model="gpt-4o",
        instructions="You are RBC Assist. Answer questions about RBC financial data.",
        tools=[
            MicrosoftFabricPreviewTool(
                fabric_dataagent_preview=FabricDataAgentToolParameters(
                    project_connection_id=fabric_connection.id
                )
            )
        ],
    ),
)
```

### V-Order Optimisation

V-Order is a write-time optimisation applied to Delta Parquet files that sorts data
in VertiPaq-compatible order, giving near import-mode query performance for Direct Lake.
Apply it to the Fabric Delta copy:

```python
# In the Airflow DAG, after writing Delta:
# Run OPTIMIZE on the Fabric lakehouse SQL endpoint
import requests

sql = "OPTIMIZE gold_trading_metrics"
# POST to Fabric SQL Analytics Endpoint
```

---

## Fabric SKU Recommendation

For the OBIEE → Power BI migration (~1,000 reports, ~150 concurrent users):

| SKU | CU | Memory | Recommendation |
|---|---|---|---|
| F32 | 32 | 64 GB | Minimum for production BI |
| F64 | 64 | 128 GB | **Recommended** for 1,000+ reports |
| F128 | 128 | 256 GB | Reserve for peak trading periods |

Start with F64 (moderate scenario from the 3-year cost model), scale to F128 for quarter-end
and regulatory reporting peaks.

---

## Conditions for Revisiting

- **Direct Lake** if Gold semantic model size exceeds F64 memory limits (~100+ GB in VertiPaq)
- **Direct Lake** if Fabric ships "Prep for AI" support for Direct Lake mode
- **Remove Fabric entirely** if RBC Assist moves to a Trino-native NL-to-SQL architecture
  with equivalent per-user security enforcement
- **Increase copy frequency** from daily to intraday if business users require sub-daily
  refresh on specific Gold tables (e.g., intraday risk positions)

---

## Consequences

- Gold exists in two physical representations — this is intentional, not a data quality risk
- The Airflow pipeline gains a new DAG: `gold_to_fabric_copy` (runs after Gold refresh)
- Power BI and Tableau connect to the Fabric semantic model, not directly to Trino
- Cube remains in the stack for the NL-to-SQL schema linking path (ADR-006) and for any
  consumers that prefer the PostgreSQL wire protocol
- OBIEE report migration target: certified Fabric semantic model with RLS, replacing
  per-report Trino connections
- RBC Assist data grounding: Fabric Data Agent published endpoint, wired to Azure AI Foundry
- Governance split is explicit: Ranger governs the compute plane (Trino/Teradata/on-prem),
  Fabric semantic model RLS governs the BI/AI surface plane
