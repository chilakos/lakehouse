# ADR-009: AI Data Hub — RAG-Ready Data Serving Layer for the Lakehouse

**Status:** Accepted
**Date:** 2026-03-30
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)
**Raised by:** AI readiness architecture review (March 2026)

---

## Context

The lakehouse processes 1.5 PB across thousands of tables, with the Teradata FSDM as the
conforming model at the Silver layer. The current AI consumption path is NL-to-SQL only
(2 Gold tables, prompt-stuffed context, Claude on Bedrock). This covers a narrow use case:
analysts asking aggregation questions about trading metrics and risk exposure.

Financial services AI use cases extend well beyond NL-to-SQL:
- **Relationship manager copilot:** "Prepare a briefing for my meeting with the Chen family"
- **KYC/AML enrichment:** "Summarize the risk context for this counterparty"
- **Trade surveillance context:** "Show me the context around these flagged orders"
- **Risk narrative generation:** "What's driving the VaR increase on the Rates desk?"
- **Regulatory Q&A:** "How is HQLA calculated in our LCR report, and what sources contribute?"

These use cases require **pre-computed entity summaries** retrievable via semantic search
(RAG), not on-demand SQL generation. An analyst asking about a client's profile needs a
500-word narrative assembled from 15+ FSDM tables — not a SQL query they have to interpret.

The lakehouse currently has **no vector store, no embedding pipeline, no RAG infrastructure.**

---

## Decision

**We will build an AI Data Hub as a new layer above Gold, consisting of three tiers:
metadata embeddings (schema linking for NL-to-SQL), entity summary embeddings (RAG for
business context), and real-time query capability (NL-to-SQL via Cube semantic layer).**

An AI agent routes between these tiers based on the question type.

---

## Architecture

### The Data Journey: FSDM to AI-Ready

```
Source Systems (Core Banking, Trading Platforms, CRM, Market Data)
    ↓ CDC / Batch Extract (300+ sources)

Bronze Layer (Iceberg on Pure Storage)
    Raw, source-system-specific tables
    e.g., bronze.raw_trades_history, bronze.raw_positions_daily
    Transforms: format conversion only + metadata columns (source_system, ingestion_ts, batch_id)
    Quality gate: schema validation, PK not-null, PK unique
    ↓

Silver Layer (Iceberg on Pure Storage) — FSDM 3NF Conformed Model
    Cleansed, deduplicated, entity-resolved, FSDM-schema-conformed
    e.g., silver.fsdm_party, silver.fsdm_account, silver.fsdm_financial_transaction
    Transforms: dedup by PK (window function), business rule filters, FSDM conformance
    Quality gate: uniqueness, valid value ranges, referential integrity
    ↓

Gold Layer (Iceberg on Pure Storage) — Denormalized Business-Ready Tables
    Pre-aggregated, domain-oriented wide tables for analytics and AI
    e.g., gold.trading_metrics, gold.risk_exposure, gold.customer_360
    Transforms: multi-table joins across FSDM subject areas, aggregation, enrichment
    Quality gate: non-null dimensions, positive measures, cross-tool validation (Cube vs Trino)
    ↓

AI Data Hub — AI-Ready Serving Layer
    ├── Tier 1: Metadata Embeddings (pgvector)
    │   Schema descriptions, glossary terms, Cube YAML definitions
    │   → Serves NL-to-SQL schema linking (ADR-006)
    │
    ├── Tier 2: Entity Summary Embeddings (pgvector)
    │   Pre-computed text summaries per business entity
    │   → Serves RAG for client briefs, risk narratives, surveillance context
    │
    └── Tier 3: Real-Time Query (Cube + Trino)
        NL-to-SQL for current numbers, ad-hoc aggregations
        → Serves questions requiring fresh data or custom aggregations
```

### Tier 2: Entity Summary Design

Entity summaries are **text documents generated from Gold tables**, embedded into pgvector
for semantic search. Each entity type has a text template that converts structured data
to a natural language document.

**What gets pre-computed:**

| Entity Type | Source Gold Tables | Summary Content | Update Frequency |
|---|---|---|---|
| Client profile | customer_360, account_summary, transaction_summary | Demographics, AUM, portfolio allocation, risk profile, recent activity, RM assignment | Daily (overnight) |
| Account summary | account_detail, position_snapshot, pnl_daily | Account type, positions, performance, fee schedule, compliance flags | Daily |
| Counterparty profile | counterparty_360, kyc_status, compliance_events | Entity info, ownership structure, risk rating, transaction patterns, compliance history | Daily |
| Desk risk summary | risk_exposure, position_snapshot, var_daily | Positions by class, VaR metrics, limit utilization, top risk contributors, P&L attribution | Intraday (hourly) |
| Regulatory lineage | data_lineage_catalog | Report field → gold table → silver FSDM tables → bronze sources → transformation logic | On change |

**What does NOT get embedded:**
- Individual transaction rows (billions of records — use NL-to-SQL instead)
- Bronze/Silver layer data (not AI-ready; use Gold or summaries)
- Time-series data (use SQL for trend queries)

### The Agent Router

An AI agent with multiple tools decides how to answer each question:

```
User question
    ↓
AI Agent (Claude on Bedrock)
    ↓
    ├── Tool: search_metadata(query)
    │   → pgvector metadata index → returns relevant table/column definitions
    │   → Used for: "What tables have trading data?" / NL-to-SQL schema linking
    │
    ├── Tool: search_entities(query, entity_type)
    │   → pgvector entity index → returns pre-computed summaries
    │   → Used for: "Brief me on client X" / "Risk context for counterparty Y"
    │
    ├── Tool: run_query(question)
    │   → NL-to-SQL (ADR-006) → Cube/Trino → fresh results
    │   → Used for: "What was total notional for AAPL yesterday?"
    │
    └── Tool: lookup_glossary(term)
        → OpenMetadata API → business term definition
        → Used for: "What does CVaR mean in our context?"
    ↓
Agent synthesizes results → Response with citations
```

**Routing heuristics:**

| Question Signal | Route To | Example |
|---|---|---|
| Requires current numbers | NL-to-SQL (Tier 3) | "What is our VaR today?" |
| Requires aggregation | NL-to-SQL (Tier 3) | "Compare Q4 revenue across desks" |
| About a specific entity's profile | Entity RAG (Tier 2) | "Brief me on the Chen family" |
| Needs narrative/qualitative context | Entity RAG (Tier 2) | "What's the risk context for Oceanic Trading?" |
| About data definitions | Metadata RAG (Tier 1) | "What tables have position data?" |
| About a business term | Glossary lookup | "What is NSFR?" |

---

## Concrete FSDM-to-AI Examples

### Example 1: Client Intelligence (Party → Customer 360 → RAG)

**FSDM Silver tables involved (15+ table joins):**
```
silver.fsdm_party
    → silver.fsdm_individual (supertype join)
    → silver.fsdm_party_role (customer role)
    → silver.fsdm_party_relationship (spouse, employer, beneficial owner)
    → silver.fsdm_party_address → silver.fsdm_address → silver.fsdm_geographic_area
    → silver.fsdm_account → silver.fsdm_account_balance
    → silver.fsdm_agreement → silver.fsdm_agreement_party_role
    → silver.fsdm_financial_transaction (activity history)
    → silver.fsdm_contact_event → silver.fsdm_channel
    → silver.fsdm_risk_rating → silver.fsdm_credit_risk_assessment
```

**Gold table (denormalized):**
```sql
-- gold.customer_360
CREATE TABLE gold.customer_360 (
    party_id            BIGINT,
    customer_name       STRING,
    customer_type       STRING,       -- Individual / Organization
    segment             STRING,       -- HNW, Mass Affluent, Retail
    relationship_since  DATE,
    total_aum           DECIMAL(38,4),
    accounts            ARRAY<STRUCT<account_id STRING, type STRING, balance DECIMAL(38,4)>>,
    risk_score          INT,
    primary_rm          STRING,
    last_interaction    TIMESTAMP,
    snapshot_date       DATE          -- partition column for point-in-time
) USING iceberg
PARTITIONED BY (snapshot_date)
```

**AI Data Hub summary (embedded in pgvector):**
```
Client: Sarah Chen (party_id: 4829371). HNW segment, 12-year relationship.
Total AUM: $3.4M across 4 accounts: checking ($45K), savings ($312K),
brokerage ($2.1M — 55% US equities, 25% international, 15% fixed income, 5% cash),
mortgage ($580K remaining, 3.2% fixed, matures 2045).
YTD return: +7.2% (benchmark +8.1%, underperforming 90bps — underweight tech).
Upcoming: $500K CD maturing April 15. No ESG allocation despite expressed interest
(Nov 2025 meeting). Last interaction: Jan 2026 branch visit.
Primary channel: mobile (78%). Risk score: 7/10 (moderate-aggressive).
RM: David Park (NYC office). No compliance flags.
```

**RM asks:** "Prepare a briefing for my meeting with Sarah Chen tomorrow."
**Agent routes to:** Entity RAG (Tier 2) → retrieves the summary above → synthesizes briefing.

### Example 2: Risk Narrative (Risk → Desk Summary → RAG)

**FSDM Silver tables involved:**
```
silver.fsdm_risk_exposure
    → silver.fsdm_market_risk_position
    → silver.fsdm_financial_instrument → silver.fsdm_instrument_price
    → silver.fsdm_account (desk/book mapping)
    → silver.fsdm_party (counterparty)
```

**Gold table:**
```sql
-- gold.desk_risk_summary
CREATE TABLE gold.desk_risk_summary (
    desk_id             STRING,
    desk_name           STRING,
    business_line       STRING,
    total_notional      DECIMAL(38,4),
    var_99_1d           DECIMAL(18,2),
    var_99_10d          DECIMAL(18,2),
    expected_shortfall  DECIMAL(18,2),
    limit_pct           DECIMAL(5,2),
    breach_flag         BOOLEAN,
    top_contributors    ARRAY<STRUCT<instrument STRING, contribution_pct DECIMAL(5,2)>>,
    snapshot_date       DATE
) USING iceberg
PARTITIONED BY (snapshot_date)
```

**AI Data Hub summary:**
```
Rates Desk (desk_id: RATES-NA-01). Business line: Fixed Income.
Total notional: $2.3B in USD IRS. DV01: $1.2M.
VaR (99%, 1-day): $4.8M — up 15% from last week.
Driver: increased curve flattener exposure (5Y-10Y USD swap spread).
Limit utilization: 96% ($4.8M / $5.0M). BREACH on Tuesday (resolved Wed via partial unwind).
Top risk contributors: 5Y USD IRS (42%), 10Y USD IRS (28%), EUR/USD basis (15%).
Expected shortfall: $6.1M. Stressed VaR: $12.3M.
MTD P&L: +$3.2M. YTD: +$18.7M.
```

**CRO asks:** "What are the top risk concerns this week?"
**Agent routes to:** Entity RAG (Tier 2) → retrieves all desk summaries → filters for
breaches and significant changes → synthesizes top-3 narrative.

### Example 3: Trade Surveillance (Transaction → Alert Context → RAG)

**FSDM Silver tables involved:**
```
silver.fsdm_financial_transaction
    → silver.fsdm_transaction_party (trader, counterparty)
    → silver.fsdm_transaction_leg (instrument, venue, price, quantity)
    → silver.fsdm_financial_instrument → silver.fsdm_instrument_price
    → silver.fsdm_party (trader profile)
    → silver.fsdm_party_relationship (personal accounts, restricted list)
    → silver.fsdm_contact_event (communications around trade time)
```

**Gold table:**
```sql
-- gold.surveillance_alert_context
CREATE TABLE gold.surveillance_alert_context (
    alert_id            STRING,
    alert_type          STRING,       -- spoofing, front-running, insider_trading
    trader_name         STRING,
    trader_desk         STRING,
    flagged_trades      ARRAY<STRUCT<instrument STRING, side STRING, qty BIGINT, price DECIMAL(18,6), ts TIMESTAMP>>,
    trader_30d_pattern  STRUCT<avg_size BIGINT, avg_cancel_rate DECIMAL(5,2), alert_history INT>,
    instrument_context  STRUCT<avg_daily_volume BIGINT, price_move_bps DECIMAL(8,2)>,
    related_party_flags ARRAY<STRING>,
    snapshot_date       DATE
) USING iceberg
PARTITIONED BY (snapshot_date)
```

**Compliance analyst asks:** "Show me the context around alert SURV-2026-0847."
**Agent routes to:** Entity RAG (Tier 2) → retrieves alert context summary → synthesizes
narrative with trader pattern, instrument context, and related-party flags.

### Example 4: Regulatory Lineage (Cross-Domain → Lineage Graph → RAG)

**Agent routes to:** Metadata RAG (Tier 1) for data lineage, then NL-to-SQL (Tier 3) for
current numbers if needed.

**Regulatory analyst asks:** "How is HQLA calculated in our LCR report?"
**Response combines:** lineage metadata (which FSDM tables → which Gold aggregations →
which business rules) with current values from the Gold tables.

---

## Implementation

### Phase 1: Metadata Embeddings (covered by ADR-006)

pgvector with Cube YAML + OpenMetadata table/column metadata + glossary terms.
This is the NL-to-SQL schema linking foundation.

### Phase 2: Entity Summary Pipeline

1. Build Gold tables for key entity types (customer_360, desk_risk_summary, etc.)
   as new Gold pipelines following existing patterns in `etl/src/pipelines/gold/`
2. Create text template renderers that convert Gold table rows to summary documents
3. Embed summaries via Titan Embeddings on Bedrock
4. Store in pgvector with entity_type and entity_id metadata for filtered retrieval
5. Schedule via Airflow DAG: `generate_entity_summaries` (nightly for clients, hourly for risk)

### Phase 3: Agent Orchestration

1. Build the multi-tool agent with:
   - `search_metadata` → pgvector metadata index
   - `search_entities` → pgvector entity index
   - `run_query` → NL-to-SQL engine (refactored per ADR-006)
   - `lookup_glossary` → OpenMetadata API
2. Design for MCP compatibility (stateless tools with clear contracts) even if MCP protocol
   is not implemented immediately
3. Expose via API for multiple consumers (chatbot, Slack, IDE, BI tools)

### Phase 4: CDC-Driven Freshness (future)

Replace batch summary generation with CDC-to-embedding pipeline:
- Iceberg change tracking (`_commit_timestamp`) detects changed Gold table rows
- Changed entities re-summarized and re-embedded incrementally
- Staleness metadata (`last_updated`) included in every embedded document

---

## Embedding Strategy

### What to embed (by priority)

| Priority | Content | Chunk Strategy | Approximate Volume |
|---|---|---|---|
| P0 | Cube YAML definitions (table + column level) | One chunk per table, one per measure/dimension | ~2,000 chunks |
| P0 | FSDM business glossary terms | One chunk per term | ~500 chunks |
| P0 | Golden dataset Q&A pairs | One chunk per question-SQL pair | ~500 chunks |
| P1 | Client 360 summaries | One document per client | 500K-2M documents |
| P1 | Account summaries | One document per account | 1M-5M documents |
| P1 | Desk/portfolio risk summaries | One document per desk per day | ~10K documents |
| P2 | Counterparty profiles | One document per counterparty | ~50K documents |
| P2 | Surveillance alert contexts | One document per alert | ~100K documents |
| P3 | Regulatory lineage descriptions | One document per report field | ~5K documents |

### What NOT to embed

- Individual transaction rows (use NL-to-SQL)
- Bronze/Silver layer raw data
- Time-series data (use SQL for trends)
- Binary/blob data

### Embedding freshness tiers

| Data Type | Refresh Frequency | Method |
|---|---|---|
| Schema metadata | On DDL change or weekly | CI/CD trigger or scheduled |
| Business glossary | On change | OpenMetadata webhook |
| Client summaries | Daily (overnight) | Airflow DAG post Gold refresh |
| Risk summaries | Intraday (hourly) | Airflow DAG post risk calc |
| Alert contexts | Near real-time | Event-driven (surveillance system webhook) |

---

## Consequences

- New Gold tables required: customer_360, desk_risk_summary, surveillance_alert_context, etc.
- New ETL pipelines: summary text generation + embedding in `etl/src/pipelines/ai_hub/`
- pgvector gains a second index (entity summaries) alongside metadata index (ADR-006)
- New Airflow DAGs: `generate_entity_summaries`, `embed_entity_summaries`
- The NL-to-SQL engine evolves from a standalone tool to one of several tools in an agent
- Governance: entity summaries inherit the access control of their source Gold tables —
  the agent must enforce row-level security via metadata filters on pgvector queries
  (entity_type + user permission = filter predicate)

---

## When to Revisit

- If MCP adoption reaches the point where a standardized MCP server interface replaces
  the custom agent tool layer
- If a managed vector database (e.g., Amazon OpenSearch Serverless with vector engine)
  proves operationally simpler than pgvector at the entity summary scale (millions of docs)
- If Cube ships native RAG/embedding features that eliminate the need for a separate
  entity summary pipeline
