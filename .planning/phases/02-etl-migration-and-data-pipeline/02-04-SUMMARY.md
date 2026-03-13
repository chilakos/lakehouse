---
phase: 02-etl-migration-and-data-pipeline
plan: 04
subsystem: etl
tags: [soda-core, sodacl, data-quality, reconciliation, quality-gates, alerting, pyspark]

# Dependency graph
requires:
  - phase: 02-etl-migration-and-data-pipeline
    provides: "BasePipeline ABC with run_quality_checks() placeholder, PipelineConfig, QualityGateError"
provides:
  - "Soda Core scanner utility (run_soda_checks) wrapping soda-core-spark-df"
  - "QualityCheckResult dataclass with JSON serialization for alerting"
  - "SodaCL YAML check definitions for Bronze/Silver/Gold trades"
  - "ReconciliationResult and reconcile_table for source-to-target validation"
  - "BasePipeline.run_quality_checks() wired to Soda Core (replaces placeholder)"
affects: [02-05]

# Tech tracking
tech-stack:
  added: [soda-core-spark-df, soda-core]
  patterns: [quality-gate-between-layers, critical-vs-advisory-checks, yaml-based-quality-checks, reconciliation-framework]

key-files:
  created:
    - etl/src/quality/__init__.py
    - etl/src/quality/scanner.py
    - etl/src/quality/reconciliation.py
    - etl/src/quality/checks/bronze_trades.yml
    - etl/src/quality/checks/silver_trades.yml
    - etl/src/quality/checks/gold_trading_metrics.yml
    - etl/tests/unit/test_reconciliation.py
    - etl/tests/integration/test_quality_checks.py
    - etl/tests/integration/test_quality_alerting.py
  modified:
    - etl/src/pipelines/base.py

key-decisions:
  - "Top-level PySpark F import in reconciliation.py for unittest.mock.patch testability (consistent with base.py pattern)"
  - "Soda scan temp view named __soda_check_target for DataFrame-to-SQL bridge"
  - "Reconciliation uses relative tolerance (abs diff / max(source, 1)) for numeric comparison"
  - "Integration tests override ensure_services fixture to run with local Spark only (no Docker required)"
  - "QualityCheckResult.to_json() uses default=str for safe serialization of any metric type"
  - "BasePipeline falls back to placeholder when soda-core not installed or no checks_path configured"

patterns-established:
  - "Quality gate pattern: critical checks block pipeline, advisory checks warn only"
  - "SodaCL YAML checks use __soda_check_target temp view name (scanner creates from DataFrame)"
  - "Reconciliation tolerance: Decimal-based relative comparison with configurable threshold"
  - "Quality results are structured dicts with QualityCheckResult dataclass items"

requirements-completed: [QUAL-02, QUAL-03, QUAL-04]

# Metrics
duration: 9min
completed: 2026-03-13
---

# Phase 2 Plan 4: Data Quality Framework Summary

**Soda Core quality gates with SodaCL YAML checks for Bronze/Silver/Gold layers, source-to-lakehouse reconciliation framework, and JSON-serializable alerting structure wired into BasePipeline**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-13T15:40:28Z
- **Completed:** 2026-03-13T15:49:35Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Soda Core scanner wraps soda-core-spark-df for programmatic DataFrame quality checks without configuration.yml (QUAL-02)
- SodaCL YAML files define critical (schema, PK null/unique) and advisory (price range, quantity positive) checks per layer
- Critical check failures block pipeline progression; advisory failures produce warnings only (locked decision enforced)
- Source-to-lakehouse reconciliation compares row counts, checksums, and aggregates with configurable tolerance (QUAL-03)
- Quality results are JSON-serializable QualityCheckResult dataclass instances for Grafana/alerting integration (QUAL-04)
- BasePipeline.run_quality_checks() now calls Soda Core scanner (replaces placeholder), with graceful fallback
- 29 tests pass (17 unit + 12 integration) covering all quality framework functionality

## Task Commits

Each task was committed atomically (TDD workflow for Task 1):

1. **Task 1: Soda Core scanner, SodaCL checks, and reconciliation framework**
   - `eb3a542` (test: RED -- failing unit tests for reconciliation framework)
   - `10f8a06` (feat: GREEN -- Soda Core scanner, SodaCL YAML checks, reconciliation)
2. **Task 2: Wire quality gates into BasePipeline and integration tests**
   - `76b9326` (feat: BasePipeline integration, 12 integration tests)

## Files Created/Modified
- `etl/src/quality/__init__.py` - Quality module package init with module docstring
- `etl/src/quality/scanner.py` - Soda Core scan runner with QualityCheckResult dataclass (165 lines)
- `etl/src/quality/reconciliation.py` - ReconciliationResult and reconcile_table for migration validation (249 lines)
- `etl/src/quality/checks/bronze_trades.yml` - SodaCL checks: schema, PK null/unique, price/qty ranges (38 lines)
- `etl/src/quality/checks/silver_trades.yml` - SodaCL checks: PK unique, side valid values (26 lines)
- `etl/src/quality/checks/gold_trading_metrics.yml` - SodaCL checks: symbol not null, trade_count, notional (24 lines)
- `etl/src/pipelines/base.py` - run_quality_checks() updated to call Soda Core scanner (replaces placeholder)
- `etl/tests/unit/test_reconciliation.py` - 17 unit tests for ReconciliationResult and reconcile_table (399 lines)
- `etl/tests/integration/test_quality_checks.py` - 6 integration tests for Soda checks against Spark DataFrames
- `etl/tests/integration/test_quality_alerting.py` - 6 integration tests for alerting structure and JSON serialization

## Decisions Made
- Top-level `from pyspark.sql import functions as F` in reconciliation.py for unittest.mock.patch testability (matches established pattern from base.py)
- Soda scan creates temp view `__soda_check_target` from DataFrame for SodaCL YAML file references
- Reconciliation tolerance uses relative difference: `abs(source - target) / max(abs(source), 1)` to handle varying magnitudes
- Integration tests override `ensure_services` autouse fixture to run with local Spark only (no Docker services required)
- BasePipeline gracefully falls back to passing placeholder when soda-core is not installed or no quality_checks_path is configured

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PySpark F.col() requiring SparkContext in unit tests**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** `F.sum(F.col(col))` in reconcile_table requires active SparkContext, causing unit test failures with mocked Spark
- **Fix:** Moved `from pyspark.sql import functions as F` to module-level import and used `@patch("src.quality.reconciliation.F")` in unit tests
- **Files modified:** etl/src/quality/reconciliation.py, etl/tests/unit/test_reconciliation.py
- **Verification:** All 17 unit tests pass without SparkContext
- **Committed in:** 10f8a06 (Task 1 GREEN commit)

**2. [Rule 3 - Blocking] Installed Java for local Spark integration tests**
- **Found during:** Task 2 (integration test execution)
- **Issue:** Java not installed on machine; local SparkSession creation fails
- **Fix:** Installed default-jre-headless via apt-get
- **Files modified:** None (system package install)
- **Verification:** All 12 integration tests pass with local Spark

**3. [Rule 1 - Bug] Fixed frozen PipelineConfig mutation in integration test**
- **Found during:** Task 2 (test execution)
- **Issue:** Test attempted to assign to frozen PipelineConfig field (`config.target_layer = MagicMock()`)
- **Fix:** Replaced with MagicMock config from the start
- **Files modified:** etl/tests/integration/test_quality_checks.py
- **Verification:** test_base_pipeline_raises_quality_gate_error passes
- **Committed in:** 76b9326 (Task 2 commit)

**4. [Rule 1 - Bug] Fixed PySpark schema inference for null values in alerting test**
- **Found during:** Task 2 (test execution)
- **Issue:** `createDataFrame` with Row containing `trade_id=None` fails type inference
- **Fix:** Provided explicit StructType schema to createDataFrame
- **Files modified:** etl/tests/integration/test_quality_alerting.py
- **Verification:** test_failed_critical_check_produces_alertable_result passes
- **Committed in:** 76b9326 (Task 2 commit)

**5. [Rule 3 - Blocking] Overrode ensure_services fixture for quality tests**
- **Found during:** Task 2 (integration test execution)
- **Issue:** Integration conftest autouse `ensure_services` fixture skips all tests when Docker services unavailable
- **Fix:** Added local `ensure_services` fixture override in each quality test module
- **Files modified:** etl/tests/integration/test_quality_checks.py, etl/tests/integration/test_quality_alerting.py
- **Verification:** All 12 integration tests run with local Spark only
- **Committed in:** 76b9326 (Task 2 commit)

---

**Total deviations:** 5 auto-fixed (3 bugs, 2 blocking)
**Impact on plan:** All auto-fixes necessary for test correctness and execution. No scope creep.

## Issues Encountered
- soda-core-spark-df installation downgraded PySpark from 4.1.1 to 3.5.8 due to soda-core's compatibility constraints. This is acceptable since the project pins `pyspark>=3.5.0,<3.6.0` in pyproject.toml.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Quality framework is complete and ready for Plan 05 (Grafana dashboard integration)
- BasePipeline.run_quality_checks() is wired to Soda Core -- all pipelines automatically get quality gates
- QualityCheckResult.to_json() provides structured output for Grafana/alerting dashboards
- Reconciliation framework is ready for parallel-run validation of migrated DataStage jobs
- SodaCL YAML files can be extended with additional checks per table as new pipelines are added

## Self-Check: PASSED

All 10 created/modified files verified present. All 3 task commits verified in git log.

---
*Phase: 02-etl-migration-and-data-pipeline*
*Completed: 2026-03-13*
