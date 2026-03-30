# ADR-006: Retrieval-Augmented Schema Linking for NL-to-SQL at Scale

**Status:** Accepted
**Date:** 2026-03-30
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)
**Raised by:** AI Semantic Layer architecture review (March 2026)

---

## Context

The NL-to-SQL engine (`etl/src/semantic/nl_to_sql.py`) currently prompt-stuffs ALL Cube YAML
definitions into the Claude system prompt via `metric_context.py`. With 2 Gold tables
(trading_metrics, risk_exposure) and ~10 measures, this produces ~50 lines of context that
fits comfortably in the prompt.

The Teradata migration will bring thousands of tables into the lakehouse. Even limiting
NL-to-SQL scope to Cube-modeled Gold tables, the platform will grow to 50-200+ modeled
tables across FSDM subject areas (Party, Account, Transaction, Instrument, Risk, Compliance).
At that scale, prompt-stuffing breaks down:

1. **Token budget:** 200 tables averaging 8 columns each produces 50,000-100,000 tokens
   of schema context. VLDB 2025 research ("Is Long Context All You Need?") confirms that
   passing unfiltered schema causes hallucinations — a "perfect schema" (only relevant
   tables) yields significantly higher accuracy.
2. **Cost:** Every question pays the full token cost of all schema context. Linear scaling.
3. **Few-shot examples:** The 5 hardcoded examples per domain in `prompt_builder.py` cannot
   scale to dozens of domains without competing for context space.
4. **No schema linking:** `load_cube_definitions()` loads everything. There is no logic to
   determine which tables are relevant to a given question.
5. **Manual domain routing:** The caller must pass `domain="trading"` explicitly. Users at
   scale will not know which domain their question maps to.

---

## Decision

**We will implement Retrieval-Augmented Schema Linking (RASL) using pgvector as the
vector store, sourced from OpenMetadata's REST API and Cube YAML definitions.**

The approach:

1. **Offline indexing:** Decompose each Cube YAML definition into entity chunks — table-level
   chunks (table name + description) and column-level chunks (measure/dimension name +
   description + glossary term). Embed each chunk using Amazon Titan Embeddings on Bedrock.
   Store in pgvector (PostgreSQL extension, reusing existing Postgres infrastructure).

2. **Online retrieval:** When a question arrives, embed it, retrieve the top-k most similar
   table and column chunks (e.g., top 10 tables, top 30 columns), and pass only those to
   the LLM as context.

3. **Few-shot retrieval:** Embed golden dataset question-SQL pairs. Retrieve the top-3 most
   similar examples dynamically, replacing the hardcoded domain-specific examples.

4. **Automatic domain routing:** The retrieval step eliminates the need for callers to specify
   a domain. The vector similarity search implicitly routes to the correct tables.

---

## Rationale

### 1. RASL is research-backed for enterprise scale

Amazon's RASL paper (2025) directly addresses the enterprise NL-to-SQL scaling problem and
demonstrates strong results on catalogs with 10,000+ tables. The approach decomposes schema
into embeddable chunks and retrieves relevant subsets — exactly our use case.

### 2. pgvector reuses existing infrastructure

PostgreSQL is already in the stack (Nessie metadata store, OpenMetadata database, Ranger
database). Adding the `pgvector` extension to the existing `om-db` container avoids new
infrastructure. The vector index for 200 tables with ~1,600 columns is approximately 10,000
chunks — trivially small for pgvector.

### 3. OpenMetadata API as the metadata source (not a separate catalog)

OpenMetadata v1.6 provides REST APIs (`/api/v1/tables`, `/api/v1/glossaryTerms`) that return
structured JSON with table descriptions, column metadata, tags, and glossary terms. Using
OpenMetadata as the source ensures the vector index is consistent with the authoritative
data catalog. No OpenMetadata upgrade required (v1.6 REST APIs are sufficient; we do not
need the v1.12+ semantic search feature because we are building a purpose-specific index
optimized for NL-to-SQL schema linking, not generic search).

### 4. Accuracy scoped to Cube-modeled Gold tables

At 1.5 PB across thousands of tables, NL-to-SQL cannot cover everything. The accuracy
commitment applies to **Cube-modeled Gold tables** — tables with hand-crafted YAML
definitions, rich descriptions, glossary term mappings, and golden dataset validation.

- **90% accuracy (simple queries)** and **70% accuracy (complex queries)** apply to
  Cube-modeled tables with golden datasets (AISEM-03 thresholds unchanged).
- **Unmodeled tables are out of scope** for NL-to-SQL. Engineers querying bronze/silver
  already know SQL. The AI layer serves analysts and BI consumers on the Gold layer.

The retrieval investment is about routing: finding the right 3-5 Cube-modeled tables out
of 50-200, not out of thousands. This is a tractable retrieval problem.

### 5. Titan Embeddings on Bedrock — no new infrastructure

Amazon Titan Text Embeddings v2 is available on Bedrock, which is already used for Claude.
No new embedding infrastructure needed. Embedding generation happens in the indexing
pipeline (Airflow DAG), not on the critical path of query execution.

---

## Alternatives Considered

### Schema Routing + Generation (DBCopilot-style)

A lightweight router model maps questions to relevant tables, followed by SQL generation.
Rejected because it requires training/maintaining a separate router model — more engineering
complexity than vector retrieval for comparable accuracy.

### Long-Context with Hierarchical Schema Compression

Compress schema into a two-level index (brief summary of all tables, then full detail for
selected tables). Rejected because VLDB 2025 research shows full-schema approaches
underperform filtered approaches even with long context. At 200+ tables, even compressed
index is 5,000-10,000 tokens per call with lower accuracy ceiling.

### OpenMetadata v1.12 Semantic Search

Upgrade OpenMetadata to use its built-in vector search. Rejected for now because: (a) requires
a major version upgrade (1.6 → 1.12+), (b) OpenMetadata search is optimized for human
discovery not NL-to-SQL schema linking, (c) we lose control over chunking, embedding strategy,
and retrieval tuning. Can be re-evaluated if OpenMetadata's search proves sufficient after
a future upgrade.

---

## Implementation Outline

### Phase 1: Vector Index Pipeline

```
Cube YAML files + OpenMetadata API
    ↓ (Airflow DAG: nightly or on-change)
Entity chunking:
    - Table chunk: "{table_name}: {description}. Columns: {column_list}"
    - Column chunk: "{table}.{column}: {description}. Glossary: {glossary_term}"
    - View chunk: "{view_name}: {description}. Includes: {member_list}"
    ↓
Titan Embeddings (Bedrock)
    ↓
pgvector (om-db PostgreSQL)
```

### Phase 2: Retrieval-Augmented NL-to-SQL

Replace `metric_context.py` full-load with:
1. Embed incoming question via Titan Embeddings
2. Retrieve top-k table chunks + top-k column chunks from pgvector
3. Retrieve top-3 similar golden dataset examples from pgvector
4. Build prompt with only the retrieved context (same prompt structure, smaller context)
5. Send to Claude Sonnet on Bedrock (unchanged)

### Phase 3: Evaluation and Tuning

Extend `evaluation.py` to measure:
- **Retrieval accuracy:** Were the correct tables/columns in the retrieved set?
- **End-to-end accuracy:** SQL correctness (existing metric)
- **Retrieval recall@k:** Tune k to balance context size vs. coverage

---

## Consequences

- `metric_context.py` will be refactored from "load everything" to "retrieve relevant subset"
- `prompt_builder.py` will move from hardcoded few-shot examples to dynamic retrieval
- The `domain` parameter in `NLToSQLEngine.generate_sql()` becomes optional (auto-routed)
- New dependency: pgvector extension on PostgreSQL
- New Airflow DAG: `index_cube_metadata` (runs on Cube YAML change or nightly)
- `evaluation.py` gains retrieval accuracy metrics alongside SQL accuracy

---

## When to Revisit

- If OpenMetadata v1.12+ semantic search proves sufficient for schema linking after upgrade
- If MCP becomes the primary interface pattern (MCP wraps the retrieval + generation, but
  the underlying RASL approach remains the same)
- If Cube ships a native retrieval layer that eliminates the need for external vector indexing
