---
phase: 1
slug: foundation-and-feasibility-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + PySpark integration tests |
| **Config file** | etl/pyproject.toml (Wave 0 creates) |
| **Quick run command** | `cd etl && pytest tests/unit/ -x --tb=short` |
| **Full suite command** | `cd etl && pytest tests/ -x --tb=short` |
| **Estimated runtime** | ~120 seconds (integration tests require Docker services) |

---

## Sampling Rate

- **After every task commit:** Run `cd etl && pytest tests/unit/ -x --tb=short`
- **After every plan wave:** Run `cd etl && pytest tests/ -x --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green + manual Teradata OTF + Snowflake validations
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | FNDTN-01 | integration | `pytest tests/integration/test_iceberg_s3.py -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | FNDTN-02 | integration | `pytest tests/integration/test_iceberg_minio.py -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | FNDTN-03 | integration | `pytest tests/integration/test_nessie_dual_storage.py -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | FNDTN-04 | integration | `pytest tests/integration/test_schema_evolution.py -x` | ❌ W0 | ⬜ pending |
| 01-01-05 | 01 | 1 | FNDTN-05 | integration | `pytest tests/integration/test_partition_evolution.py -x` | ❌ W0 | ⬜ pending |
| 01-01-06 | 01 | 1 | FNDTN-06 | integration | `pytest tests/integration/test_table_maintenance.py -x` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | QUERY-01 | integration | `pytest tests/integration/test_trino_reads.py -x` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | QUERY-02 | integration | `pytest tests/integration/test_trino_writes.py -x` | ❌ W0 | ⬜ pending |
| 01-02-03 | 02 | 1 | QUERY-03 | manual-only | Manual: Teradata OTF + Nessie validation | N/A | ⬜ pending |
| 01-02-04 | 02 | 1 | QUERY-04 | integration | `pytest tests/integration/test_snowflake_reads.py -x` | ❌ W0 | ⬜ pending |
| 01-02-05 | 02 | 1 | QUERY-05 | integration | `pytest tests/integration/test_metadata_consistency.py -x` | ❌ W0 | ⬜ pending |
| 01-02-06 | 02 | 1 | QUERY-06 | integration | `pytest tests/integration/test_benchmarks.py -x` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 1 | CICD-01 | unit | `pytest tests/unit/test_repo_structure.py -x` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 1 | CICD-02 | smoke | `act --dry-run` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 1 | CICD-03 | smoke | `terraform plan -var-file=environments/dev/terraform.tfvars` | ❌ W0 | ⬜ pending |
| 01-03-04 | 03 | 1 | CICD-04 | smoke | `terraform validate && terraform plan` | ❌ W0 | ⬜ pending |
| 01-03-05 | 03 | 1 | SEC-01 | manual-only | Manual: LDAP login to Trino | N/A | ⬜ pending |
| 01-03-06 | 03 | 1 | SEC-02 | integration | `pytest tests/integration/test_rbac.py -x` | ❌ W0 | ⬜ pending |
| 01-03-07 | 03 | 1 | SEC-05 | smoke | `aws s3api get-bucket-encryption --bucket lakehouse-data` | ❌ W0 | ⬜ pending |
| 01-03-08 | 03 | 1 | SEC-06 | smoke | `openssl s_client -connect nessie:19120` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `etl/pyproject.toml` — project configuration with pytest, pyspark, pyiceberg dependencies
- [ ] `etl/tests/conftest.py` — shared fixtures (Spark session, Nessie client, Trino connection, MinIO client)
- [ ] `etl/tests/unit/` — unit test directory structure
- [ ] `etl/tests/integration/` — integration test directory structure
- [ ] `docker-compose.test.yml` — Nessie + PostgreSQL + MinIO + Trino for local integration testing
- [ ] Framework install: `pip install pytest pyspark pyiceberg trino[sqlalchemy]`

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Teradata OTF reads Iceberg via Nessie | QUERY-03 | Requires live Teradata instance with OTF license; no documented REST catalog support | 1. Configure Teradata OTF with Nessie REST endpoint 2. Attempt CREATE FOREIGN TABLE 3. If fails, test Trino JDBC federation from Teradata 4. Document result |
| LDAP authentication on Trino | SEC-01 | Requires live LDAP/AD server connection | 1. Configure password-authenticator.properties with LDAP 2. Attempt login with LDAP user 3. Verify group-based access control |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
