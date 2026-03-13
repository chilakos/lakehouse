---
phase: 03-governance-security-hardening-and-platform
plan: "02"
subsystem: catalog
tags: [openmetadata, trino, elasticsearch, freshness, lineage, marquez, docker]

# Dependency graph
requires:
  - phase: 03-governance-security-hardening-and-platform
    provides: Ranger Docker deployment and governance classification module (03-01)
  - phase: 02-etl-migration-and-data-pipeline
    provides: Marquez lineage backend, Trino/Iceberg bronze/silver/gold schemas

provides:
  - OpenMetadata data catalog (server, ingestion, Elasticsearch, PostgreSQL) in docker-compose.yml
  - Trino connector ingestion YAML targeting bronze/silver/gold schemas
  - FSDM business glossary seed data with 10 terms and approval workflow states
  - FreshnessStatus/FreshnessSLA modules with SLA-based traffic-light monitoring (GREEN/YELLOW/RED)
  - DEFAULT_SLAS: gold 24h/48h, silver 12h/24h, bronze 6h/12h
  - register_legacy_lineage_stub() for Marquez REST API stub registration
  - register_teradata_sources(): 3 Teradata tables (trades_history, positions_daily, counterparty_master)
  - register_snowflake_sources(): 2 Snowflake datasets (risk_metrics, trading_summary)
  - Integration test stubs for OpenMetadata catalog and glossary (auto-skip when OM not running)

affects:
  - 03-03-audit-trail (can query freshness status for audit reporting)
  - 03-04-platform (catalog ready for self-service data discovery)

# Tech tracking
tech-stack:
  added:
    - docker.getcollate.io/openmetadata/server:1.6.0
    - docker.getcollate.io/openmetadata/ingestion:1.6.0
    - docker.elastic.co/elasticsearch/elasticsearch:8.15.0
    - freshness_tracker.py (pure stdlib, no new deps)
    - lineage_stubs.py (uses requests, already available)
  patterns:
    - TDD Red-Green for config file validation and module implementation
    - Traffic-light SLA status (GREEN/YELLOW/RED) for freshness monitoring
    - Marquez REST API stub registration for legacy source lineage
    - Integration tests with auto-skip TCP probe for optional service dependencies

key-files:
  created:
    - docker-compose.yml (openmetadata services section)
    - infra/docker/openmetadata/connectors/trino-ingestion.yaml
    - infra/docker/openmetadata/glossary-seed.json
    - infra/docker/openmetadata/docker-compose-override.yml
    - etl/src/governance/freshness_tracker.py
    - etl/src/governance/lineage_stubs.py
    - etl/tests/unit/test_openmetadata_config.py
    - etl/tests/unit/test_freshness_tracker.py
    - etl/tests/integration/test_catalog_ingestion.py
    - etl/tests/integration/test_catalog_glossary.py
  modified:
    - etl/src/governance/__init__.py

key-decisions:
  - "OpenMetadata ingestion port 8086 (not default 8080) to avoid conflicts with Trino:8080 and Airflow:8081"
  - "OpenMetadata 1.6.0 used as known stable release (research specified 1.12.x but Docker Hub tags unverified)"
  - "Elasticsearch 8.15.0 with xpack.security.enabled=false for local dev simplicity"
  - "Freshness SLA logic: within warning_threshold -> GREEN (allows grace period past expected_interval); within critical_threshold -> YELLOW; past critical -> RED"
  - "Lineage stubs use HTTP PUT to Marquez /api/v1/namespaces/{ns}/datasets/{src}.{name} endpoint"
  - "Integration tests auto-skip via TCP probe to localhost:8585 when OpenMetadata not running"

patterns-established:
  - "Traffic-light SLA pattern: GREEN/YELLOW/RED with get_freshness_badge() returning {status, label, icon} for UI consumption"
  - "Legacy system lineage: register once as DB_TABLE stub in Marquez so lineage graphs are complete before full migration"
  - "Integration test guard: _is_openmetadata_reachable() TCP probe + module-level autouse fixture = zero-config skip"

requirements-completed: [PLAT-01, GOVN-04, PLAT-03]

# Metrics
duration: 8min
completed: 2026-03-13
---

# Phase 3 Plan 02: OpenMetadata Catalog, Freshness Tracker, and Legacy Lineage Summary

**OpenMetadata 1.6.0 data catalog with Trino ingestion for bronze/silver/gold schemas, SLA-based traffic-light freshness tracker (GREEN/YELLOW/RED per medallion layer), and Marquez REST stub registration for legacy Teradata and Snowflake lineage sources**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-13T17:44:45Z
- **Completed:** 2026-03-13T17:52:19Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 11

## Accomplishments

- OpenMetadata 4-service stack (server, ingestion, Elasticsearch, PostgreSQL) added to docker-compose.yml with correct port assignments (8585/8086/9200/5436), memory limits (6g server / 8g ingestion), health checks, and no port conflicts with existing 20+ services
- Trino ingestion YAML connector targeting bronze.*, silver.*, gold.* schemas via lakehouse-trino service; glossary-seed.json with 10 FSDM terms (Trade, Position, PII, BCBS 239, SLA, Bronze/Silver/Gold Layers, Data Freshness, Business Unit) all in Draft status for approval workflow
- Freshness tracker module with FreshnessSLA dataclass, FreshnessStatus enum (GREEN="On time"/YELLOW="Warning"/RED="Stale"), check_table_freshness() (None->RED, within warning->GREEN, within critical->YELLOW, else->RED), DEFAULT_SLAS (gold 24h/48h, silver 12h/24h, bronze 6h/12h), and batch get_all_freshness()
- Legacy lineage stub registration for 3 Teradata tables (trades_history, positions_daily, counterparty_master) and 2 Snowflake datasets (risk_metrics, trading_summary) via Marquez REST API

## Task Commits

Each task was committed atomically (TDD = 2 commits per task):

1. **Task 1 RED: OpenMetadata config tests** - `38d94fb` (test: failing tests for docker and Trino ingestion config)
2. **Task 1 GREEN: OpenMetadata Docker deployment** - `3b8e07b` (feat: all 4 OM services, Trino ingestion YAML, glossary seed)
3. **Task 2 RED: Freshness tracker tests** - `c9480bc` (test: 51 failing unit tests for freshness tracker)
4. **Task 2 GREEN: Freshness tracker + lineage stubs** - `4c9c02c` (feat: all modules + integration tests)

**Plan metadata:** (final commit with SUMMARY.md, STATE.md, ROADMAP.md)

_Note: TDD tasks have multiple commits (test -> feat)_

## Files Created/Modified

- `docker-compose.yml` - Added om-db, elasticsearch, openmetadata-server, openmetadata-ingestion services + om-db-data/es-data volumes
- `infra/docker/openmetadata/connectors/trino-ingestion.yaml` - Trino -> OpenMetadata ingestion config targeting bronze/silver/gold schemas
- `infra/docker/openmetadata/glossary-seed.json` - 10 FSDM business glossary terms (Trade, Position, PII, BCBS 239, SLA, layers, etc.)
- `infra/docker/openmetadata/docker-compose-override.yml` - Environment-specific tuning override file
- `etl/src/governance/freshness_tracker.py` - FreshnessStatus, FreshnessSLA, DEFAULT_SLAS, check_table_freshness(), get_freshness_badge(), get_all_freshness()
- `etl/src/governance/lineage_stubs.py` - register_legacy_lineage_stub(), register_teradata_sources(), register_snowflake_sources()
- `etl/src/governance/__init__.py` - Updated to export freshness_tracker and lineage_stubs symbols
- `etl/tests/unit/test_openmetadata_config.py` - 39 tests for docker-compose OpenMetadata services, Trino ingestion YAML, glossary seed
- `etl/tests/unit/test_freshness_tracker.py` - 51 tests for freshness SLA logic and badge rendering
- `etl/tests/integration/test_catalog_ingestion.py` - Integration tests for catalog search (auto-skip if OM down)
- `etl/tests/integration/test_catalog_glossary.py` - Integration tests for glossary term search and workflow states

## Decisions Made

- **OpenMetadata ingestion port 8086**: Avoids conflict with Trino (8080) and Airflow (8081). The ingestion container internally runs on 8080 but is mapped to 8086 on the host.
- **OpenMetadata 1.6.0**: Research mentions 1.12.x but Docker Hub image tags needed verification. 1.6.0 is a known stable release available from docker.getcollate.io.
- **Freshness SLA grace period logic**: `hours_since <= warning_threshold -> GREEN` (not `<= expected_interval`). This gives a grace window between expected interval and warning before alarming, matching operational reality.
- **Lineage stubs via HTTP PUT**: Marquez API uses PUT for idempotent dataset registration; re-running register functions is safe.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Import path discovery: Existing tests use `from src.governance...` (run from etl/ dir) not `from etl.src.governance...`. Updated test import paths to match established project convention.

## User Setup Required

None - no external service configuration required for unit tests. Integration tests auto-skip when OpenMetadata not running.

To run OpenMetadata stack and trigger Trino ingestion:
1. `docker compose up -d openmetadata-server openmetadata-ingestion elasticsearch om-db`
2. Wait for health checks: `docker compose ps`
3. Generate INGESTION_BOT_JWT in OpenMetadata UI -> Settings -> Bots -> ingestion-bot
4. Replace `<INGESTION_BOT_JWT>` in `infra/docker/openmetadata/connectors/trino-ingestion.yaml`
5. `docker compose exec openmetadata-ingestion metadata ingest -c /home/airflow/connectors/trino-ingestion.yaml`

## Next Phase Readiness

- OpenMetadata catalog infrastructure ready for 03-03 (audit trail) and 03-04 (platform hardening)
- Freshness tracker can be wired to Grafana dashboards for SLA visibility panels
- Lineage stubs give Marquez complete upstream lineage picture from Teradata/Snowflake sources
- 318 unit tests passing (90 new in this plan, 228 from prior plans)

## Self-Check: PASSED

All files present and all commits verified:
- freshness_tracker.py: FOUND
- lineage_stubs.py: FOUND
- trino-ingestion.yaml: FOUND
- glossary-seed.json: FOUND
- test_freshness_tracker.py: FOUND
- test_catalog_ingestion.py: FOUND
- test_catalog_glossary.py: FOUND
- Commit 38d94fb: FOUND
- Commit 3b8e07b: FOUND
- Commit c9480bc: FOUND
- Commit 4c9c02c: FOUND

---
*Phase: 03-governance-security-hardening-and-platform*
*Completed: 2026-03-13*
