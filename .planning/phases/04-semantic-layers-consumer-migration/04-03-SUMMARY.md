---
phase: 04-semantic-layers-consumer-migration
plan: 03
subsystem: testing, semantic, ci
tags: [cross-tool-validation, cube, trino, glossary, ci-cd, integration-tests, nl-to-sql, evaluation]

# Dependency graph
requires:
  - phase: 04-01
    provides: "Cube YAML metric definitions, Docker services, risk exposure Gold pipeline"
  - phase: 04-02
    provides: "NL-to-SQL engine, golden evaluation datasets, accuracy evaluation framework"
provides:
  - "Cross-tool validation module (Cube vs Trino metric consistency)"
  - "Glossary link validation (meta.glossary_term to glossary-seed.json)"
  - "Cube YAML structure validation (required fields, measures)"
  - "Integration test stubs for Cube SQL API and NL-to-SQL accuracy"
  - "CI/CD pipeline with Cube YAML and glossary validation steps"
  - "Human-verified Phase 4 semantic layer deliverables"
affects: []

# Tech tracking
tech-stack:
  added: [psycopg2, pg8000]
  patterns: [cross-tool-validation, glossary-link-verification, yaml-structure-validation, integration-test-skip-guards]

key-files:
  created:
    - etl/src/semantic/cross_tool_validation.py
    - etl/tests/unit/test_cross_tool_validation.py
    - etl/tests/integration/test_cube_sql_api.py
    - etl/tests/integration/test_nl_accuracy.py
  modified:
    - .github/workflows/ci.yml
    - etl/src/semantic/__init__.py
    - infra/docker/openmetadata/glossary-seed.json

key-decisions:
  - "Cross-tool validation uses Decimal(38,4) tolerance for financial metric comparison"
  - "Integration tests use TCP probe skip guards (localhost:15432 for Cube, Trino for NL-to-SQL) for clean CI behavior"
  - "CI/CD validates both Cube YAML structure and glossary link integrity on every PR"
  - "Phase 4 deliverables human-approved: all seven requirements confirmed complete"

patterns-established:
  - "Cross-tool validation: compare identical queries across Cube SQL API and direct Trino to detect metric drift"
  - "Integration test skip guards: TCP probe before test execution, skip cleanly when services unavailable"
  - "Glossary-driven governance: every metric measure must reference a valid glossary term"

requirements-completed: [BISEM-01, BISEM-02, BISEM-03, BISEM-04, AISEM-01, AISEM-02, AISEM-03]

# Metrics
duration: 5min
completed: 2026-03-13
---

# Phase 4 Plan 03: Cross-Tool Validation and Phase Sign-Off Summary

**Cross-tool metric validation module, Cube/Trino consistency checks, glossary link verification, integration test stubs, CI/CD validation pipeline, and human-approved Phase 4 sign-off completing all seven semantic layer requirements**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-13T22:33:48Z
- **Completed:** 2026-03-13T22:38:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Cross-tool validation module that compares Cube SQL API results against direct Trino queries with Decimal precision tolerance
- Glossary link validation ensuring all meta.glossary_term values in Cube YAML reference real glossary entries
- Cube YAML structure validation catching definition errors (missing name, sql_table, measures)
- Integration test stubs for Cube SQL API connectivity and NL-to-SQL accuracy (skip-guarded for CI)
- CI/CD pipeline updated with Cube YAML validation and glossary link verification steps
- Human verification and approval of all Phase 4 deliverables

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Cross-tool validation tests** - `fed4ee7` (test)
2. **Task 1 (GREEN): Cross-tool validation, integration stubs, CI, glossary** - `7bf0ae7` (feat)
3. **Task 2: Human verification checkpoint** - approved (no commit, verification only)

_Note: TDD task had RED/GREEN commits. Task 2 was a human-verify checkpoint._

## Files Created/Modified
- `etl/src/semantic/cross_tool_validation.py` - Cross-tool metric validation, glossary link checking, YAML structure validation
- `etl/tests/unit/test_cross_tool_validation.py` - Unit tests for all validation functions (matching, mismatch, decimal precision, glossary, YAML)
- `etl/tests/integration/test_cube_sql_api.py` - Integration tests for Cube SQL API connectivity, query results, decimal precision (TCP skip guard)
- `etl/tests/integration/test_nl_accuracy.py` - Integration tests for NL-to-SQL accuracy by domain and complexity (env-var skip guard)
- `.github/workflows/ci.yml` - Added cube-yaml-validate and glossary-links-validate CI steps
- `etl/src/semantic/__init__.py` - Updated module exports with cross_tool_validation
- `infra/docker/openmetadata/glossary-seed.json` - Glossary seed data with term definitions for validation

## Decisions Made
- Cross-tool validation uses Decimal(38,4) tolerance for financial metric comparison -- avoids floating-point false positives
- Integration tests use TCP probe skip guards for clean CI behavior when Cube or Trino services are unavailable
- CI/CD validates both Cube YAML structure and glossary link integrity on every PR -- catches definition errors pre-merge
- Phase 4 deliverables human-approved: BI connectivity, NL-to-SQL generation, and all seven requirements confirmed complete

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All four phases complete: Foundation, ETL Migration, Governance, and Semantic Layers
- 480 unit tests passing across the full test suite
- Integration test stubs ready for live environment validation (Cube SQL API, NL-to-SQL with Bedrock)
- Pending: Live Teradata OTF validation, Snowflake integration, LDAP auth (require external service access)

## Self-Check: PASSED

All 7 created/modified files verified on disk. Both task commits (fed4ee7, 7bf0ae7) verified in git log.

---
*Phase: 04-semantic-layers-consumer-migration*
*Completed: 2026-03-13*
