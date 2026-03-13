---
phase: 04-semantic-layers-consumer-migration
plan: 02
subsystem: ai-semantic
tags: [nl-to-sql, bedrock, claude, prompt-builder, golden-datasets, evaluation, trino, accuracy]

# Dependency graph
requires:
  - phase: 04-semantic-layers-consumer-migration
    plan: 01
    provides: Cube YAML metric definitions, metric_context.py AISEM-02 bridge
provides:
  - NL-to-SQL prompt builder with Cube YAML metric context injection
  - NLToSQLEngine generating Trino SQL via Claude on Bedrock
  - Golden evaluation datasets for trading (16 Q&A) and risk exposure (16 Q&A) domains
  - Accuracy evaluation framework with tiered thresholds (90% simple, 70% complex)
affects: [04-03, ai-semantic, nl-to-sql]

# Tech tracking
tech-stack:
  added: [boto3-bedrock-runtime, claude-messages-api]
  patterns: [prompt-builder-with-metric-context, few-shot-domain-examples, golden-dataset-evaluation, tdd-red-green]

key-files:
  created:
    - etl/src/semantic/prompt_builder.py
    - etl/src/semantic/nl_to_sql.py
    - etl/src/semantic/evaluation.py
    - etl/src/semantic/golden_datasets/trading_questions.json
    - etl/src/semantic/golden_datasets/risk_questions.json
    - etl/tests/unit/test_prompt_builder.py
    - etl/tests/unit/test_nl_to_sql.py
    - etl/tests/unit/test_evaluation.py
  modified:
    - etl/src/semantic/__init__.py

key-decisions:
  - "SYSTEM_PROMPT enforces DECIMAL types (no floating point), schema-qualified table names (gold.*), and strict metric-only SQL generation"
  - "NLToSQLEngine uses Claude Sonnet on Bedrock (anthropic.claude-sonnet-4-20250514-v1:0) with configurable region and model ID"
  - "Domain-specific few-shot examples (5 per domain) hard-coded in prompt_builder for consistent guidance"
  - "Golden datasets: 16 entries each (8 simple + 8 complex) covering single-table lookups, aggregations, GROUP BY, HAVING, subqueries"
  - "Evaluation uses execution accuracy (result set comparison, order-independent) not string matching"

patterns-established:
  - "Prompt builder pattern: SYSTEM_PROMPT with {metric_context} and {few_shot_examples} placeholders"
  - "NLToSQLEngine wraps boto3 bedrock-runtime with markdown fence stripping and NLToSQLError exception"
  - "Golden dataset JSON format: {question, sql, complexity} with complexity in (simple, complex)"
  - "EvalResult dataclass pattern for evaluation tracking with per-question match/error detail"

requirements-completed: [AISEM-01, AISEM-02, AISEM-03]

# Metrics
duration: 4min
completed: 2026-03-13
---

# Phase 4 Plan 02: NL-to-SQL Engine and Evaluation Summary

**NL-to-SQL engine with Cube YAML metric context injection via Claude on Bedrock, golden evaluation datasets for trading and risk exposure, and tiered accuracy evaluation framework (AISEM-01/02/03)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-13T22:15:50Z
- **Completed:** 2026-03-13T22:20:10Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- NL-to-SQL prompt builder injects Cube YAML metric definitions as context, enforces DECIMAL types, schema-qualified tables, and metric-only SQL (AISEM-02)
- NLToSQLEngine generates Trino SQL via Claude on Bedrock with markdown fence stripping and NLToSQLError exception handling (AISEM-01)
- Domain-specific few-shot examples (5 per domain) for trading and risk exposure guide LLM toward correct SQL patterns
- Golden evaluation datasets: 16 entries each for trading and risk exposure with simple/complex classification
- Accuracy evaluation framework computes tiered metrics with AISEM-03 thresholds (90% simple, 70% complex)
- All 471 unit tests pass (36 new tests across 3 test files, zero regressions)

## Task Commits

Each task was committed atomically (TDD: test -> feat):

1. **Task 1: NL-to-SQL prompt builder and engine with Bedrock client**
   - `e156c6d` (test) - Failing tests for prompt builder and NL-to-SQL engine
   - `96aa11b` (feat) - NL-to-SQL prompt builder and engine with Bedrock client

2. **Task 2: Golden evaluation datasets and accuracy evaluation framework**
   - `9d87ab2` (test) - Failing tests for golden datasets and evaluation framework
   - `e287eda` (feat) - Golden evaluation datasets and accuracy evaluation framework
   - `f8206ff` (chore) - Updated semantic module exports

## Files Created/Modified
- `etl/src/semantic/prompt_builder.py` - LLM prompt construction with SYSTEM_PROMPT template, build_prompt, build_few_shot_examples
- `etl/src/semantic/nl_to_sql.py` - NLToSQLEngine class with Bedrock invoke_model, markdown fence stripping, NLToSQLError
- `etl/src/semantic/evaluation.py` - EvalResult dataclass, load_golden_dataset, evaluate_accuracy, run_evaluation, generate_evaluation_report
- `etl/src/semantic/golden_datasets/trading_questions.json` - 16 golden Q&A pairs for trading domain (8 simple, 8 complex)
- `etl/src/semantic/golden_datasets/risk_questions.json` - 16 golden Q&A pairs for risk exposure domain (8 simple, 8 complex)
- `etl/tests/unit/test_prompt_builder.py` - 8 tests for prompt template, build_prompt, few-shot examples
- `etl/tests/unit/test_nl_to_sql.py` - 8 tests for Bedrock calls, SQL extraction, markdown fences, engine API
- `etl/tests/unit/test_evaluation.py` - 17 tests for golden datasets, accuracy calculation, evaluation reports
- `etl/src/semantic/__init__.py` - Updated exports with NLToSQLEngine, evaluation, prompt_builder

## Decisions Made
- SYSTEM_PROMPT enforces DECIMAL types, schema-qualified tables (gold.*), and strict metric-only SQL generation for financial data accuracy
- NLToSQLEngine defaults to Claude Sonnet on Bedrock with configurable region and model ID for deployment flexibility
- Domain-specific few-shot examples hard-coded per domain (not dynamically generated) for consistent, predictable prompt behavior
- Golden datasets use 16 entries each (8 simple + 8 complex) covering the full range of query patterns from single lookups to subqueries
- Evaluation uses execution accuracy (result set comparison, order-independent) rather than SQL string matching for robust correctness measurement

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required. All LLM interactions mocked in tests.

## Next Phase Readiness
- NL-to-SQL engine ready for integration testing with live Bedrock endpoint (requires AWS credentials)
- Golden datasets ready for live evaluation runs against Trino when cluster is available
- Evaluation framework ready to produce accuracy reports against AISEM-03 thresholds
- All semantic module exports consolidated for Plan 03 consumer migration work

## Self-Check: PASSED

---
*Phase: 04-semantic-layers-consumer-migration*
*Completed: 2026-03-13*
