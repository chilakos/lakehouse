# Phase 1: Foundation and Feasibility Validation - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove that Trino, Teradata OTF, and Snowflake can all read the same Iceberg tables through a shared Nessie catalog on AWS S3 (cloud) and MinIO (on-prem), with CI/CD pipelines and baseline security (SSO/RBAC, encryption) in place. This phase validates the multi-engine architecture before committing to full data migration.

</domain>

<decisions>
## Implementation Decisions

### Iceberg Catalog
- Nessie as the centralized Iceberg catalog (REST catalog spec)
- Single-region HA deployment with replicas (not multi-region)
- PostgreSQL as the Nessie metadata backing store
- Main branch only for Phase 1 — Nessie branching capability explored in later phases once foundation is proven
- Nessie must serve Trino, Teradata OTF, and Snowflake from the same catalog instance

### On-prem Storage
- Keep MinIO as the on-prem S3-compatible storage (team already operates it)
- Small proof dataset (< 100 GB) sufficient for Phase 1 feasibility
- On-prem storage serves both regulatory/data residency requirements AND performance/latency needs for on-prem consumers
- MinIO deployment should mirror S3 bucket structure for consistency

### Repository Structure & IaC
- Mono-repo with top-level folders: /infra, /etl, /dbt, /ci
- Terraform for all infrastructure-as-code (Trino, Nessie, Airflow, storage config)
- Branch-based environment promotion: feature branches → PR to dev → merge to staging → merge to main (prod)
- GitHub Actions as the CI/CD engine
- Separate Trino cluster and Nessie catalog per environment (dev/staging/prod) — full isolation, no shared infrastructure

### Feasibility Proof Strategy
- Synthetic financial dataset (trades, positions, risk metrics) — no compliance overhead, fully controlled
- Feasibility deliverable: live demo to leadership + written benchmark report (latency, throughput, resource usage)
- Teradata OTF validation in week 1 — if OTF REST catalog support is blocked, pivot to Trino query federation to Teradata as the bridge and document the gap
- Schema evolution testing (add column, widen type) included in feasibility proof — validates FNDTN-04 and demonstrates Iceberg's core value

### Claude's Discretion
- Trino cluster sizing and worker configuration
- Nessie deployment method (Docker, Kubernetes, bare metal)
- TLS certificate management approach
- Synthetic data generation tooling
- Benchmark test harness design
- MinIO cluster topology for Phase 1

</decisions>

<specifics>
## Specific Ideas

- Leadership needs a compelling demo + numbers to greenlight Phase 2 — the feasibility proof is the gate
- Teradata OTF is the highest-risk item — validate first, have a fallback ready
- SWOT analyses for catalog choice, Snowflake strategy, data model, and semantic layer are required by leadership (noted in PROJECT.md) — Phase 1 should produce at least the catalog SWOT
- The 40+ engineer team needs a clear repo structure they can onboard to quickly

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None — patterns will be established by this phase

### Integration Points
- AWS S3 buckets (cloud storage target)
- MinIO on-prem cluster (on-prem storage target)
- Teradata existing instance (OTF integration point)
- Snowflake existing account (external table integration)
- SSO/LDAP/Active Directory (authentication source)
- GitHub (code hosting and CI/CD)

</code_context>

<deferred>
## Deferred Ideas

- Nessie branching for schema change management — explore after Phase 1 proves the basics
- Multi-region catalog HA — revisit if workloads expand across regions
- Data mesh domain-based repo structure — premature for Phase 1, consider for v2
- Real production data for testing — requires governance approvals, use synthetic first

</deferred>

---

*Phase: 01-foundation-and-feasibility-validation*
*Context gathered: 2026-03-13*
