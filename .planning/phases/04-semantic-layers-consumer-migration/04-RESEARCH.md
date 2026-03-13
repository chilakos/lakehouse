# Phase 4: Semantic Layers and Consumer Migration - Research

**Researched:** 2026-03-13
**Domain:** Semantic layer platforms, BI tool migration, NL-to-SQL with LLM
**Confidence:** HIGH (core stack), MEDIUM (NL-to-SQL accuracy patterns)

## Summary

Phase 4 requires three interlocking capabilities: (1) a unified semantic layer that defines business metrics once and serves them to both Tableau and Power BI, (2) BI tool migration from direct Teradata queries to lakehouse-backed semantic layer queries with performance parity, and (3) a custom NL-to-SQL system that leverages those same metric definitions to answer natural-language questions on pilot domains (trading + risk exposure).

The research recommends **Cube (open-source, self-hosted)** as the semantic layer platform. Cube provides a PostgreSQL wire-protocol SQL API that both Tableau and Power BI can connect to natively, YAML-based metric definitions that live in Git, Trino as a data source with pre-aggregation support for performance, and a well-documented architecture for feeding metric context to LLMs for NL-to-SQL. The dbt Semantic Layer (MetricFlow) was the primary alternative considered; it now supports Trino (added 2025) but requires dbt Cloud for BI integrations and does not align with the self-hosted, Git-native mono-repo approach established in prior phases. AtScale is commercial-only and out of scope for an open-source-first stack.

For NL-to-SQL, the research recommends **Claude API via Amazon Bedrock** for data residency compliance in financial services, with Cube's YAML metric definitions injected as context in a RAG-style prompt architecture. A golden evaluation dataset of ~100 question-SQL pairs per pilot domain provides the accuracy measurement foundation.

**Primary recommendation:** Deploy Cube (self-hosted Docker) connected to Trino, define trading + risk exposure metrics in YAML, connect Tableau/Power BI via Cube SQL API (Postgres protocol), and build NL-to-SQL as a Python service that reads Cube metric definitions as prompt context for Claude.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Metric definitions authored as code (YAML/SQL) in the mono-repo, versioned in Git, changes go through PR review
- Data engineers author definitions, business stakeholders review via PR comments/approval
- Security passes through to Trino -- Ranger column-masking and row-level filtering enforced at the query layer, no duplicate security logic in the semantic layer
- Pilot domains: trading metrics + risk exposure (two domains to validate cross-domain metric consistency)
- Phased migration by dashboard -- migrate one dashboard/workbook at a time, run old (Teradata direct) and new (lakehouse semantic layer) side-by-side, validate numbers match, then cut over
- Performance validation: pick 5-10 representative high-traffic dashboards, extract their SQL queries, run against both Teradata and lakehouse, compare latency/throughput
- Performance thresholds are case-by-case: interactive dashboards must match Teradata parity; scheduled reports/extracts can tolerate up to 2-3x slower
- Build custom NL-to-SQL using LLM with semantic layer metric definitions as context (not a vendor product)
- Pilot domains for NL-to-SQL: same as BI pilot (trading + risk exposure) -- proves AISEM-02 requirement
- Accuracy thresholds: tiered -- 90% correct on simple queries (single-domain lookups), 70% correct on complex queries (multi-join analytics)
- NL-to-SQL must use the same metric definitions that serve Tableau/Power BI
- Data engineering owns metric definitions, business reviews and approves via PR process
- Consistency enforcement: single-source architecture plus automated cross-tool testing as safety net
- Metric definitions link to OpenMetadata business glossary (Phase 3)
- Metric changes deploy through standard CI/CD pipeline (PR -> dev -> staging -> prod)

### Claude's Discretion
- Semantic layer platform selection (dbt Semantic Layer vs Cube vs AtScale vs other)
- BI connector approach (Trino JDBC/ODBC vs semantic layer API)
- LLM selection for NL-to-SQL (Claude API vs self-hosted)
- NL-to-SQL prompt engineering and evaluation framework design
- Risk exposure Gold pipeline design (new pipeline needed for second pilot domain)
- Cross-tool automated testing framework implementation
- Glossary-to-metric linking mechanism

### Deferred Ideas (OUT OF SCOPE)
- NL-to-SQL for all data domains -- REQUIREMENTS.md explicitly scopes to pilot domains
- Self-service SQL workspace for analysts (PLAT-V2-04) -- v2 scope
- Real-time metric updates (streaming) -- batch-first per REQUIREMENTS.md
- Data contracts between metric producers and consumers (PLAT-V2-03) -- v2 scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BISEM-01 | Unified metric definitions (revenue, risk exposure, etc.) in a semantic layer | Cube YAML data model with cubes/views; metrics defined once, consumed by all tools |
| BISEM-02 | Tableau connected to lakehouse via semantic layer (replacing direct Teradata queries) | Cube SQL API (Postgres wire protocol) -> Tableau connects as PostgreSQL data source |
| BISEM-03 | Power BI connected to lakehouse via semantic layer (replacing direct Teradata queries) | Cube SQL API (Postgres wire protocol) -> Power BI connects as PostgreSQL data source |
| BISEM-04 | BI query performance validated against current Teradata direct-query baselines | Cube pre-aggregations + Trino Iceberg optimizations; benchmark framework using existing trino.py utilities |
| AISEM-01 | NL-to-SQL capability deployed on curated high-confidence data domains | Custom Python service using Claude API with Cube metric definitions as RAG context |
| AISEM-02 | NL-to-SQL leverages BI semantic layer definitions for accuracy | Cube YAML files parsed and injected into LLM prompt; same metric definitions serve BI and AI |
| AISEM-03 | NL-to-SQL accuracy benchmarked and meeting target threshold on pilot domains | Golden evaluation dataset per domain; execution accuracy testing framework |
</phase_requirements>

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| Cube (cubejs/cube) | v0.36.x (latest stable) | Semantic layer platform | Open-source, self-hosted, Postgres wire protocol for BI tools, YAML data model, Trino native support, pre-aggregations for performance |
| Cube Store (cubejs/cubestore) | v0.36.x (matches Cube) | Pre-aggregation storage & query acceleration | Required for Cube pre-aggregations; handles caching and materialized query results |
| Trino | 479 (already deployed) | Query engine backing semantic layer | Already in stack; Cube connects to Trino via JDBC-style config |
| Anthropic Claude API (via Bedrock) | claude-sonnet-4-20250514 or later | LLM for NL-to-SQL generation | High SQL accuracy (73% raw, 90%+ with semantic context); Bedrock provides data residency in AWS |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| boto3 | >=1.35.0 (already in deps) | AWS Bedrock API client for Claude | NL-to-SQL service calling Claude via Bedrock |
| anthropic | >=0.40.0 | Anthropic Python SDK (optional, direct API fallback) | If Bedrock is not available, direct API with zero-data-retention addendum |
| trino[sqlalchemy] | >=0.330.0 (already in deps) | Trino DBAPI for benchmark queries | Performance benchmark harness comparing Teradata vs lakehouse |
| pytest + pytest-benchmark | >=8.0.0 (pytest in deps) | Test framework for accuracy and perf benchmarks | NL-to-SQL accuracy eval, BI perf benchmarks |
| Soda Core | >=3.5.0 (already in deps) | Cross-tool metric value reconciliation | Automated testing: same query through Tableau path and Power BI path produces identical results |
| PyYAML | >=6.0 | Parse Cube YAML definitions for NL-to-SQL context | Extracting metric metadata to build LLM prompts |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Cube (self-hosted) | dbt Semantic Layer (MetricFlow) | dbt SL added Trino support in 2025, but BI integrations (Tableau, Power BI connectors) require dbt Cloud -- conflicts with self-hosted mono-repo approach. MetricFlow is open-source for metric compilation but the serving layer is Cloud-only |
| Cube (self-hosted) | AtScale | Commercial-only product; no open-source option. Strong enterprise features but vendor lock-in contradicts open-source-first stack |
| Cube (self-hosted) | Trino views + JDBC direct | No metric governance, no caching/pre-aggregations, no unified definition layer. BI tools connect directly to Trino -- works but doesn't satisfy BISEM-01 (unified metric definitions) |
| Claude via Bedrock | Self-hosted open LLM (Llama 3, Mistral) | Lower SQL accuracy (typically 10-20% below frontier models); requires GPU infrastructure; no data residency concern since data stays local, but accuracy gap is significant for 90% target |
| Claude via Bedrock | Claude direct API + ZDR | Works for data residency with zero-data-retention addendum; Bedrock is simpler for AWS-native deployments |

**Installation:**
```bash
# Python dependencies (add to pyproject.toml)
pip install boto3 pyyaml

# Cube Docker images (add to docker-compose.yml)
# cubejs/cube:v0.36.0
# cubejs/cubestore:v0.36.0
```

## Architecture Patterns

### Recommended Project Structure
```
semantic/                         # New top-level directory for semantic layer
  model/
    cubes/
      trading_metrics.yml         # Cube definition for trading_metrics Gold table
      risk_exposure.yml           # Cube definition for risk exposure Gold table
      positions.yml               # Cube for Silver positions (if needed by views)
    views/
      trading_view.yml            # View exposing trading metrics + dimensions
      risk_exposure_view.yml      # View exposing risk metrics + dimensions
  schema/                         # Cube.js schema config
    cube.py                       # Dynamic schema generation (if needed)
etl/src/
  pipelines/gold/
    trading_metrics.py            # Existing Gold pipeline
    risk_exposure.py              # NEW: Risk exposure Gold pipeline
  semantic/                       # NEW: NL-to-SQL service module
    nl_to_sql.py                  # Core NL-to-SQL engine
    prompt_builder.py             # Builds prompts from Cube YAML + user question
    metric_context.py             # Parses Cube YAML files into structured context
    evaluation.py                 # Accuracy evaluation framework
    golden_datasets/
      trading_questions.json      # Golden Q&A pairs for trading domain
      risk_questions.json         # Golden Q&A pairs for risk exposure domain
etl/tests/unit/
  test_nl_to_sql.py              # NL-to-SQL unit tests (mocked LLM)
  test_metric_context.py         # Metric context parser tests
  test_risk_exposure_pipeline.py # Risk exposure Gold pipeline tests
  test_cube_models.py            # Cube YAML validation tests
  test_performance_benchmark.py  # BI perf benchmark tests
infra/docker/cube/
  .env                           # Cube environment config
  cube.js                        # Cube.js config file
```

### Pattern 1: Cube Semantic Layer on Trino/Iceberg
**What:** Cube reads from Trino (which reads Iceberg tables via Nessie catalog), defines metrics in YAML, serves them via SQL API (Postgres wire protocol) to BI tools.
**When to use:** All BI tool connections and metric-governed queries.
**Example:**
```yaml
# semantic/model/cubes/trading_metrics.yml
# Source: https://cube.dev/docs/product/data-modeling/overview
cubes:
  - name: trading_metrics
    sql_table: gold.trading_metrics

    measures:
      - name: total_notional
        sql: total_notional
        type: sum
        description: "Total notional value of trades (sum of price * quantity)"
        meta:
          glossary_term: "notional_value"

      - name: trade_count
        sql: trade_count
        type: sum
        description: "Total number of trades"

      - name: avg_price
        sql: avg_price
        type: avg
        description: "Average trade price"

    dimensions:
      - name: symbol
        sql: symbol
        type: string
        description: "Trading symbol (e.g., AAPL, JPM)"

      - name: side
        sql: side
        type: string
        description: "Trade direction: BUY or SELL"
```

### Pattern 2: Cube Views for BI Consumer Access
**What:** Views provide the denormalized, consumer-facing interface that BI tools query. They compose measures and dimensions from multiple cubes.
**When to use:** Every BI tool connection goes through views, not cubes directly.
**Example:**
```yaml
# semantic/model/views/trading_view.yml
# Source: https://cube.dev/docs/product/data-modeling/recipes/designing-metrics
views:
  - name: trading_dashboard
    description: "Trading metrics for BI dashboards"
    cubes:
      - join_path: trading_metrics
        includes:
          - total_notional
          - trade_count
          - avg_price
          - symbol
          - side
```

### Pattern 3: NL-to-SQL with Semantic Context Injection
**What:** Parse Cube YAML metric definitions, inject as structured context into LLM prompt, generate SQL against Trino.
**When to use:** All NL-to-SQL queries. This pattern satisfies AISEM-02 (same definitions serve BI and AI).
**Example:**
```python
# etl/src/semantic/prompt_builder.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


SYSTEM_PROMPT = """You are a SQL analyst for a financial services data lakehouse.
You generate Trino SQL queries based on natural language questions.

IMPORTANT RULES:
- Use ONLY the tables, columns, and metrics defined below
- Financial values use DECIMAL types - never use floating point arithmetic
- Always qualify table names with schema: gold.table_name
- For aggregations, use the pre-defined metric formulas exactly as specified

AVAILABLE METRICS AND TABLES:
{metric_context}

EXAMPLE QUERIES:
{few_shot_examples}
"""

USER_PROMPT = """Question: {question}

Generate a Trino SQL query to answer this question. Return ONLY the SQL query, no explanation."""


def build_prompt(
    question: str,
    metric_context: str,
    few_shot_examples: str,
) -> list[dict[str, str]]:
    """Build the LLM prompt with semantic layer context.

    Args:
        question: Natural language question from user.
        metric_context: Structured metric definitions from Cube YAML.
        few_shot_examples: Domain-specific example Q&A pairs.

    Returns:
        List of message dicts for the LLM API.
    """
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                metric_context=metric_context,
                few_shot_examples=few_shot_examples,
            ),
        },
        {
            "role": "user",
            "content": USER_PROMPT.format(question=question),
        },
    ]
```

### Pattern 4: Risk Exposure Gold Pipeline
**What:** New Gold pipeline aggregating positions + risk metrics for the second pilot domain.
**When to use:** Required for risk exposure pilot domain (AISEM-02 cross-domain validation).
**Example:**
```python
# etl/src/pipelines/gold/risk_exposure.py
# Follows established BasePipeline pattern from existing trading_metrics.py
class RiskExposureGoldPipeline(BasePipeline):
    """Gold pipeline for risk exposure metrics.

    Joins Silver positions with Silver risk_metrics by account_id,
    computes per-account/sector/currency aggregated risk exposure.

    Output columns:
    - account_id, sector, currency
    - total_market_value: sum of position market values
    - total_var_95, total_var_99: aggregated VaR
    - total_expected_shortfall: aggregated ES
    - position_count: number of positions
    """
```

### Anti-Patterns to Avoid
- **Defining metrics in BI tools:** Do NOT define calculated fields in Tableau or DAX measures in Power BI. All metric logic must live in Cube YAML. BI tools consume pre-defined metrics only.
- **Bypassing the semantic layer for performance:** Do NOT let BI tools connect directly to Trino to "work around" the semantic layer. Use Cube pre-aggregations for performance instead.
- **Duplicating security logic:** Do NOT add row/column filtering in Cube. Trino + Ranger already handles this. Cube queries pass through Trino which enforces Ranger policies.
- **Hardcoding metric definitions in NL-to-SQL prompts:** Do NOT copy-paste metric definitions into prompt templates. Parse them dynamically from the same Cube YAML files. This ensures AISEM-02 compliance.
- **Using floating point for financial calculations:** All financial metrics MUST use DecimalType. The existing codebase enforces this pattern (Decimal(38,4) for notional values).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic layer / metric definitions | Custom SQL views + metadata store | Cube YAML data model | Cube handles caching, API serving, pre-aggregations, BI tool compatibility. Custom views lack governance |
| BI tool connectivity protocol | Custom JDBC/ODBC proxy | Cube SQL API (Postgres wire protocol) | Cube implements full PostgreSQL wire protocol. Building a compatible proxy is months of work |
| Pre-aggregation / query caching | Custom materialized view refresh | Cube pre-aggregations + Cube Store | Cube handles incremental refresh, automatic query routing to pre-aggs, cache invalidation |
| LLM prompt orchestration | Custom prompt chain framework | Simple function-based prompt builder + boto3/anthropic SDK | NL-to-SQL is a single-turn prompt. Don't need LangChain, LlamaIndex, or agent frameworks for this |
| SQL validation / execution safety | Custom SQL parser + sanitizer | Trino query execution with read-only catalog + Ranger RBAC | Trino enforces permissions. The LLM-generated SQL runs through normal Trino auth. No custom sandboxing needed |
| Accuracy evaluation framework | Custom eval harness from scratch | pytest + execution accuracy comparison (execute both golden SQL and generated SQL, compare results) | Standard test framework. Execution accuracy is the industry-standard metric for text-to-SQL |

**Key insight:** The semantic layer is the hardest piece to get right -- it must serve BI tools, governance, and AI consumers simultaneously. Cube handles all three through its SQL API, YAML model, and REST/GraphQL APIs. Building a custom semantic layer is a multi-month effort that reinvents well-solved problems.

## Common Pitfalls

### Pitfall 1: Cube Pre-Aggregation Build Strategy with Trino
**What goes wrong:** Cube defaults to "simple" pre-aggregation build strategy for Trino. For large Gold tables, this can be slow because it pulls data through Cube rather than using export bucket (S3).
**Why it happens:** Trino's pre-aggregation support requires explicit export bucket configuration for the optimized path.
**How to avoid:** Configure `CUBEJS_DB_EXPORT_BUCKET` with S3/MinIO credentials so Cube can use the export bucket strategy. Since MinIO is already in the stack, reuse the same bucket configuration.
**Warning signs:** Pre-aggregation builds taking >10 minutes for tables that should take seconds.

### Pitfall 2: Decimal Precision Loss Through Cube
**What goes wrong:** Financial metrics lose precision when flowing through Cube's SQL API because Postgres wire protocol may downcast decimals.
**Why it happens:** Cube's Postgres wire protocol implementation may not preserve all decimal precision modes.
**How to avoid:** Test with actual Decimal(38,4) values end-to-end. Validate that total_notional values match between direct Trino query and Cube SQL API query. Add automated reconciliation tests.
**Warning signs:** Rounding differences between direct Trino queries and Cube-served queries.

### Pitfall 3: NL-to-SQL Accuracy Collapse on Enterprise Data
**What goes wrong:** LLMs achieve 85%+ on clean academic benchmarks but 10-20% on real enterprise schemas without semantic context.
**Why it happens:** Enterprise schemas have cryptic column names, complex joins, and business logic that LLMs cannot infer from schema alone.
**How to avoid:** Inject Cube metric definitions (human-readable descriptions, formulas, business terms) into every prompt. Use few-shot examples from the specific domain. The semantic layer IS the accuracy lever.
**Warning signs:** High accuracy on simple "SELECT * WHERE" queries but failures on aggregation or multi-table queries.

### Pitfall 4: BI Tool Connection Misconfiguration
**What goes wrong:** Tableau or Power BI connects but shows wrong data types, missing columns, or empty results.
**Why it happens:** Cube's SQL API exposes views, not raw tables. If views aren't configured correctly or the Cube schema doesn't match what the BI tool expects, the connection fails silently.
**How to avoid:** Test the Cube SQL API with psql first. Verify views return expected columns and types. Then connect BI tools. Use Cube's /readyz endpoint to verify health.
**Warning signs:** BI tool shows "no tables" or all columns as VARCHAR.

### Pitfall 5: Performance Regression After Migration
**What goes wrong:** Dashboards are slower after migration from Teradata to lakehouse semantic layer.
**Why it happens:** Teradata has decades of optimizer maturity. Trino + Iceberg may not match on specific query patterns without tuning.
**How to avoid:** (1) Baseline current Teradata query times BEFORE migration. (2) Use Cube pre-aggregations for high-traffic dashboards. (3) Ensure Iceberg tables are properly compacted and partitioned. (4) Accept 2-3x slower for batch/scheduled reports per locked decision.
**Warning signs:** P95 query latency increasing after migration.

### Pitfall 6: Semantic Layer Sync vs Manual Connection
**What goes wrong:** Teams try to use Cube Cloud's Semantic Layer Sync feature which auto-populates BI tool datasets, but this is a Cube Cloud-only feature, not available in Cube Core (self-hosted).
**Why it happens:** Documentation mixes Cloud and Core features without clear delineation.
**How to avoid:** With self-hosted Cube Core, BI tools connect via SQL API (Postgres wire protocol) manually. Tableau connects as "PostgreSQL" data source. Power BI connects as "PostgreSQL" data source. No automatic sync -- manual data source configuration.
**Warning signs:** Looking for "Semantic Layer Sync" in Cube Core settings and not finding it.

## Code Examples

### Cube Docker Compose Configuration
```yaml
# Source: https://cube.dev/docs/product/administration/deployment/core
# Add to docker-compose.yml

  cube-api:
    image: cubejs/cube:v0.36.0
    ports:
      - "4000:4000"    # REST/GraphQL API
      - "15432:15432"  # SQL API (Postgres wire protocol)
    environment:
      CUBEJS_DB_TYPE: trino
      CUBEJS_DB_HOST: trino
      CUBEJS_DB_PORT: "8080"
      CUBEJS_DB_USER: trino
      CUBEJS_DB_PRESTO_CATALOG: iceberg
      CUBEJS_DB_SCHEMA: gold
      CUBEJS_DEV_MODE: "true"        # false in production
      CUBEJS_API_SECRET: "cube_local_dev_secret"
      CUBEJS_PG_SQL_PORT: "15432"
      CUBEJS_SQL_USER: cube
      CUBEJS_SQL_PASSWORD: cube_local_dev
      CUBEJS_CUBESTORE_HOST: cubestore
      # Pre-aggregation export bucket (MinIO)
      CUBEJS_DB_EXPORT_BUCKET: s3://lakehouse-data/cube-preaggs
      CUBEJS_DB_EXPORT_BUCKET_TYPE: s3
      CUBEJS_DB_EXPORT_BUCKET_AWS_KEY: admin
      CUBEJS_DB_EXPORT_BUCKET_AWS_SECRET: admin123456
      CUBEJS_DB_EXPORT_BUCKET_AWS_REGION: us-east-1
      CUBEJS_DB_EXPORT_BUCKET_AWS_S3_ENDPOINT: http://minio:9000
    volumes:
      - ./semantic/model:/cube/conf/model:ro
      - ./semantic/schema:/cube/conf/schema:ro
    depends_on:
      trino:
        condition: service_healthy

  cubestore:
    image: cubejs/cubestore:v0.36.0
    ports:
      - "9999:9999"
    environment:
      CUBESTORE_REMOTE_DIR: /cube/data
    volumes:
      - cubestore-data:/cube/data
```

### Cube Metric Definition for Risk Exposure
```yaml
# semantic/model/cubes/risk_exposure.yml
cubes:
  - name: risk_exposure
    sql_table: gold.risk_exposure

    measures:
      - name: total_market_value
        sql: total_market_value
        type: sum
        description: "Total market value of positions across all accounts"
        meta:
          glossary_term: "market_value"

      - name: total_var_95
        sql: total_var_95
        type: sum
        description: "Aggregated Value-at-Risk at 95% confidence level"
        meta:
          glossary_term: "var_95"

      - name: total_var_99
        sql: total_var_99
        type: sum
        description: "Aggregated Value-at-Risk at 99% confidence level"
        meta:
          glossary_term: "var_99"

      - name: total_expected_shortfall
        sql: total_expected_shortfall
        type: sum
        description: "Aggregated Expected Shortfall (Conditional VaR)"
        meta:
          glossary_term: "expected_shortfall"

      - name: position_count
        sql: position_count
        type: sum
        description: "Number of positions in portfolio"

    dimensions:
      - name: account_id
        sql: account_id
        type: string
        description: "Trading account identifier"

      - name: sector
        sql: sector
        type: string
        description: "Industry sector classification"

      - name: currency
        sql: currency
        type: string
        description: "Position currency (USD, EUR, GBP, etc.)"
```

### NL-to-SQL Metric Context Parser
```python
# etl/src/semantic/metric_context.py
"""Parse Cube YAML metric definitions into structured LLM context.

Reads the same YAML files that Cube uses for BI tool queries,
ensuring AISEM-02 compliance: NL-to-SQL uses identical metric definitions.
"""
from __future__ import annotations

import glob
from pathlib import Path
from typing import Any

import yaml


def load_cube_definitions(model_dir: str) -> list[dict[str, Any]]:
    """Load all Cube YAML definitions from the model directory.

    Args:
        model_dir: Path to semantic/model directory.

    Returns:
        List of parsed cube definition dicts.
    """
    definitions: list[dict[str, Any]] = []
    for yaml_path in glob.glob(f"{model_dir}/**/*.yml", recursive=True):
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        if data and "cubes" in data:
            definitions.extend(data["cubes"])
        if data and "views" in data:
            definitions.extend(data["views"])
    return definitions


def build_metric_context(definitions: list[dict[str, Any]]) -> str:
    """Convert Cube definitions into structured text for LLM prompts.

    Args:
        definitions: List of parsed cube/view definitions.

    Returns:
        Formatted string describing all available tables, metrics, and dimensions.
    """
    lines: list[str] = []
    for defn in definitions:
        name = defn.get("name", "unknown")
        table = defn.get("sql_table", "N/A")
        desc = defn.get("description", "")

        lines.append(f"TABLE: {table} (semantic name: {name})")
        if desc:
            lines.append(f"  Description: {desc}")

        for measure in defn.get("measures", []):
            m_name = measure["name"]
            m_type = measure.get("type", "unknown")
            m_desc = measure.get("description", "")
            m_sql = measure.get("sql", "")
            lines.append(f"  METRIC: {m_name} = {m_type}({m_sql}) -- {m_desc}")

        for dim in defn.get("dimensions", []):
            d_name = dim["name"]
            d_type = dim.get("type", "unknown")
            d_desc = dim.get("description", "")
            lines.append(f"  DIMENSION: {d_name} ({d_type}) -- {d_desc}")

        lines.append("")

    return "\n".join(lines)
```

### Performance Benchmark Harness
```python
# etl/src/semantic/benchmark.py
"""BI query performance benchmark: Teradata baseline vs lakehouse semantic layer.

Uses existing trino.py utilities for lakehouse queries.
Teradata comparison queries provided as SQL files for manual baseline capture.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trino.dbapi import Connection


@dataclass
class BenchmarkResult:
    """Result of a single query benchmark run."""
    query_name: str
    source: str  # "teradata" or "lakehouse"
    latency_ms: float
    row_count: int


def benchmark_query(
    conn: Connection,
    query_name: str,
    sql: str,
    iterations: int = 5,
) -> list[BenchmarkResult]:
    """Run a query multiple times and record latency.

    Args:
        conn: Trino DBAPI connection (for lakehouse queries).
        query_name: Human-readable name for the benchmark.
        sql: SQL query to benchmark.
        iterations: Number of runs (default 5, discard first as warmup).

    Returns:
        List of BenchmarkResult for each iteration.
    """
    results: list[BenchmarkResult] = []
    for i in range(iterations):
        cursor = conn.cursor()
        start = time.perf_counter()
        cursor.execute(sql)
        rows = cursor.fetchall()
        elapsed = (time.perf_counter() - start) * 1000
        cursor.close()
        results.append(BenchmarkResult(
            query_name=query_name,
            source="lakehouse",
            latency_ms=elapsed,
            row_count=len(rows),
        ))
    return results
```

### NL-to-SQL Evaluation Framework
```python
# etl/src/semantic/evaluation.py
"""NL-to-SQL accuracy evaluation using golden datasets.

Measures execution accuracy: does the generated SQL produce
the same results as the golden (human-verified) SQL?
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trino.dbapi import Connection


@dataclass
class EvalResult:
    """Result of evaluating one question-SQL pair."""
    question: str
    golden_sql: str
    generated_sql: str
    golden_results: list[tuple]
    generated_results: list[tuple]
    match: bool
    complexity: str  # "simple" or "complex"
    error: str | None = None


def load_golden_dataset(path: str) -> list[dict]:
    """Load golden question-SQL pairs from JSON.

    Expected format:
    [
        {
            "question": "What is the total notional for AAPL BUY trades?",
            "sql": "SELECT total_notional FROM gold.trading_metrics WHERE symbol = 'AAPL' AND side = 'BUY'",
            "complexity": "simple"
        },
        ...
    ]
    """
    with open(path) as f:
        return json.load(f)


def evaluate_accuracy(
    results: list[EvalResult],
    complexity_filter: str | None = None,
) -> dict[str, float]:
    """Calculate accuracy metrics from evaluation results.

    Args:
        results: List of EvalResult from evaluation run.
        complexity_filter: Optional filter for "simple" or "complex".

    Returns:
        Dict with total, correct, and accuracy percentage.
    """
    filtered = results
    if complexity_filter:
        filtered = [r for r in results if r.complexity == complexity_filter]

    total = len(filtered)
    correct = sum(1 for r in filtered if r.match)
    accuracy = (correct / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "correct": correct,
        "accuracy_pct": round(accuracy, 1),
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| BI tools query data warehouse directly | Semantic layer mediates all BI queries | 2023-2025 | Metric governance, consistency, caching |
| dbt SL required Snowflake/BigQuery | dbt MetricFlow added Trino support | 2025 | Trino users can now use dbt SL (but Cloud-only for serving) |
| NL-to-SQL used schema-only context | Semantic layer context boosts accuracy 20%+ | 2024-2025 | "Mediocre LLM + rich semantic layer" beats "frontier LLM + raw schema" |
| Cube was JavaScript-only config | Cube supports YAML + Jinja + Python data models | 2024 | Git-friendly, PR-reviewable metric definitions |
| AtScale/Cube Cloud only for enterprise | Cube Core (open-source) has full SQL API | 2023+ | Self-hosted semantic layer with Postgres wire protocol for free |
| Text-to-SQL evaluated via exact match | Execution accuracy (run both, compare results) | 2024+ | More robust evaluation -- different SQL can produce same correct results |

**Deprecated/outdated:**
- Cube.js JavaScript schema files (*.js) -- still supported but YAML is now the recommended approach for data modeling
- dbt metrics (pre-MetricFlow) -- deprecated in dbt 1.6, replaced by MetricFlow semantic models
- Presto catalog name (`CUBEJS_DB_PRESTO_CATALOG`) -- Cube still uses this env var name for Trino, it is not actually deprecated

## Open Questions

1. **Cube v0.36.x exact version for Trino compatibility**
   - What we know: Cube documents Trino as a supported data source with CUBEJS_DB_TYPE=trino
   - What's unclear: Exact Cube version compatibility matrix with Trino 479
   - Recommendation: Pin to latest v0.36.x release; test connection in local Docker before committing. If issues arise, Cube is actively maintained and Trino 479 is recent

2. **MinIO as Cube pre-aggregation export bucket**
   - What we know: Cube supports S3 export bucket with custom endpoint. MinIO is S3-compatible
   - What's unclear: Whether Cube correctly handles path-style access for MinIO S3
   - Recommendation: Configure with `CUBEJS_DB_EXPORT_BUCKET_AWS_S3_ENDPOINT` pointing to MinIO. Test pre-aggregation builds early. Fallback to simple strategy if export bucket has issues

3. **Teradata baseline capture mechanism**
   - What we know: Need to compare lakehouse query times against Teradata baselines
   - What's unclear: How to capture Teradata query baselines without direct Teradata access in this environment (noted as a pending blocker in STATE.md)
   - Recommendation: Define representative SQL queries, capture Teradata baselines manually when access is available, store as JSON fixtures for automated comparison

4. **OpenMetadata glossary-to-metric linking mechanism**
   - What we know: Metric definitions should link to OpenMetadata business glossary terms. Cube supports `meta` tags on measures
   - What's unclear: Best mechanism for programmatic linking -- REST API call from CI/CD, or manual annotation
   - Recommendation: Use Cube `meta.glossary_term` field in YAML. Build a CI step that validates every `meta.glossary_term` exists in OpenMetadata glossary via REST API

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-benchmark |
| Config file | etl/pyproject.toml (existing `[tool.pytest.ini_options]`) |
| Quick run command | `cd etl && python -m pytest tests/unit -x -q` |
| Full suite command | `cd etl && python -m pytest tests/ -x --strict-markers` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BISEM-01 | Unified metric definitions parse correctly from YAML | unit | `cd etl && python -m pytest tests/unit/test_cube_models.py -x` | No -- Wave 0 |
| BISEM-02 | Tableau can query trading metrics via Cube SQL API | integration | `cd etl && python -m pytest tests/integration/test_cube_tableau.py -x` | No -- Wave 0 |
| BISEM-03 | Power BI can query trading metrics via Cube SQL API | integration | `cd etl && python -m pytest tests/integration/test_cube_powerbi.py -x` | No -- Wave 0 |
| BISEM-04 | Query performance meets Teradata baseline thresholds | integration | `cd etl && python -m pytest tests/integration/test_performance_benchmark.py -x` | No -- Wave 0 |
| AISEM-01 | NL-to-SQL generates valid SQL for pilot domain questions | unit | `cd etl && python -m pytest tests/unit/test_nl_to_sql.py -x` | No -- Wave 0 |
| AISEM-02 | NL-to-SQL prompt context matches Cube YAML definitions | unit | `cd etl && python -m pytest tests/unit/test_metric_context.py -x` | No -- Wave 0 |
| AISEM-03 | NL-to-SQL accuracy meets thresholds (90% simple, 70% complex) | integration | `cd etl && python -m pytest tests/integration/test_nl_accuracy.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd etl && python -m pytest tests/unit -x -q`
- **Per wave merge:** `cd etl && python -m pytest tests/ -x --strict-markers`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `etl/tests/unit/test_cube_models.py` -- validates Cube YAML structure, covers BISEM-01
- [ ] `etl/tests/unit/test_metric_context.py` -- validates context parser, covers AISEM-02
- [ ] `etl/tests/unit/test_nl_to_sql.py` -- validates prompt building and SQL generation (mocked LLM), covers AISEM-01
- [ ] `etl/tests/unit/test_risk_exposure_pipeline.py` -- validates risk exposure Gold pipeline
- [ ] `etl/tests/integration/test_cube_tableau.py` -- validates Cube SQL API connection (smoke test), covers BISEM-02
- [ ] `etl/tests/integration/test_cube_powerbi.py` -- validates Cube SQL API connection (smoke test), covers BISEM-03
- [ ] `etl/tests/integration/test_performance_benchmark.py` -- benchmark harness, covers BISEM-04
- [ ] `etl/tests/integration/test_nl_accuracy.py` -- golden dataset evaluation, covers AISEM-03
- [ ] Golden datasets: `etl/src/semantic/golden_datasets/trading_questions.json` and `risk_questions.json`
- [ ] Add `pyyaml` and `boto3` to pyproject.toml dependencies
- [ ] Add `pytest-benchmark` to dev dependencies

## Sources

### Primary (HIGH confidence)
- [Cube Documentation - Trino Data Source](https://cube.dev/docs/product/configuration/data-sources/trino) -- Trino configuration, env vars, pre-aggregation support
- [Cube Documentation - SQL API](https://cube.dev/docs/product/apis-integrations/sql-api) -- PostgreSQL wire protocol, configuration, authentication
- [Cube Documentation - Docker Deployment](https://cube.dev/docs/product/administration/deployment/core) -- Docker Compose architecture, image names, ports
- [Cube Documentation - Data Modeling](https://cube.dev/docs/product/data-modeling/overview) -- YAML schema, cubes, views, measures, dimensions
- [Cube Documentation - Designing Metrics](https://cube.dev/docs/product/data-modeling/recipes/designing-metrics) -- Entity-first vs metrics-first view patterns
- [Cube Documentation - Tableau Integration](https://cube.dev/docs/product/configuration/visualization-tools/tableau) -- Tableau SQL API connection setup
- [Cube Documentation - Power BI Integration](https://cube.dev/docs/product/configuration/visualization-tools/powerbi) -- Power BI SQL API and DAX API connection
- [dbt Documentation - MetricFlow Trino Support](https://docs.getdbt.com/docs/build/about-metricflow) -- Trino added as supported platform in 2025
- [Anthropic - Claude for Financial Services](https://www.anthropic.com/news/advancing-claude-for-financial-services) -- Financial services compliance, data residency

### Secondary (MEDIUM confidence)
- [Semantic Layer Architectures Explained (typedef.ai)](https://www.typedef.ai/resources/semantic-layer-architectures-explained-warehouse-native-vs-dbt-vs-cube) -- Cube vs dbt vs warehouse-native comparison
- [VentureBeat - Semantic Layer Accuracy](https://venturebeat.com/ai/headless-vs-native-semantic-layer-the-architectural-key-to-unlocking-90-text) -- "Mediocre LLM + enriched semantic layer outperforms frontier model flying blind"
- [AIMultiple - Text-to-SQL LLM Accuracy 2026](https://research.aimultiple.com/text-to-sql/) -- Claude 3.5 Sonnet at 73% raw, 90%+ with semantic context
- [NL2SQL System Design Guide 2025 (Medium)](https://medium.com/@adityamahakali/nl2sql-system-design-guide-2025-c517a00ae34d) -- Modular NL-to-SQL architecture with prompt generation service
- [Cube Blog - Semantic Layer and AI](https://cube.dev/blog/semantic-layer-and-ai-the-future-of-data-querying-with-natural-language) -- Cube AI API architecture, RAG approach

### Tertiary (LOW confidence)
- [Trino-Tableau-Connector (GitHub)](https://github.com/deliverbi/Trino-Tableau-Connector) -- Community Tableau connector for Trino direct JDBC; not needed if using Cube SQL API
- [PowerBITrinoConnector (GitHub)](https://github.com/CreativeDataEU/PowerBITrinoConnector) -- Community Power BI connector for Trino direct; not needed if using Cube SQL API

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Cube is well-documented for Trino, SQL API for BI tools is verified in official docs, Docker self-hosted deployment is straightforward
- Architecture: HIGH -- Patterns follow Cube's official documentation and established project conventions (BasePipeline, YAML config, Docker Compose)
- Pitfalls: MEDIUM -- Pre-aggregation + MinIO interaction and Decimal precision through Cube need hands-on validation
- NL-to-SQL accuracy: MEDIUM -- Industry research strongly supports semantic-layer-boosted accuracy, but specific thresholds (90% simple, 70% complex) need to be validated against this domain's complexity

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (30 days -- Cube and LLM landscape are relatively stable in the near term)
