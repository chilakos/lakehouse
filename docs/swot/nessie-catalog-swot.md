# Nessie as Iceberg Catalog -- SWOT Analysis

**Prepared for:** Leadership Review
**Date:** 2026-03-13
**Phase:** 1 -- Foundation and Feasibility Validation
**Status:** Based on Phase 1 feasibility validation results

## Executive Summary

Nessie is an open-source transactional catalog for Apache Iceberg that implements the Iceberg REST catalog specification. It provides Git-like branching for schema management, supports multiple query engines (Trino, Spark, Flink), and uses PostgreSQL as its backing store. This SWOT analysis evaluates Nessie's suitability as the unified Iceberg catalog for our lakehouse architecture.

**Recommendation:** Nessie is the recommended catalog choice for this project. Its REST catalog compliance, multi-engine support, and branching capabilities align with our architecture requirements. The identified threats are manageable with the mitigations outlined below.

---

## Strengths

### S1: Open-Source with No License Cost
Nessie is Apache 2.0 licensed with no vendor lock-in or per-query pricing. Total cost of ownership is infrastructure + engineering time only. This contrasts with commercial options (Unity Catalog requires Databricks, Polaris SaaS has consumption pricing).

### S2: REST Catalog Specification Compliance
Nessie implements the Apache Iceberg REST catalog specification, which is becoming the industry standard for catalog interoperability. This means any engine that supports REST catalog can connect to Nessie without custom integration code.

### S3: Git-Like Branching for Schema Changes
Nessie provides branching and tagging semantics (similar to Git) for catalog metadata. This enables:
- **Zero-downtime schema migrations:** Test schema changes on a branch before merging to main
- **Reproducible queries:** Tag a catalog state for regulatory reporting
- **Rollback capability:** Revert schema changes without data loss
- **Audit trail:** Full history of metadata changes with timestamps

### S4: Multi-Engine Support (Trino, Spark, Flink)
Nessie serves as a single catalog for multiple query engines. Our Phase 1 feasibility validation confirmed:
- PySpark reads and writes Iceberg tables through Nessie REST catalog
- Trino reads Spark-created tables and writes back through the same catalog
- Cross-engine metadata consistency is maintained (same schema, same row counts)
- Both MinIO (on-prem) and S3 (cloud) storage backends work through one catalog

### S5: PostgreSQL Backing Store
Nessie uses PostgreSQL for metadata storage, providing:
- Enterprise-grade durability and ACID transactions
- Familiar operational model for DBAs
- Well-understood backup, replication, and HA patterns
- No dependency on cloud-specific storage (DynamoDB, etc.)

### S6: Single Catalog Serving Multiple Storage Backends
One Nessie instance serves tables across both S3 (cloud) and MinIO (on-premises), enabling the hybrid architecture without catalog duplication or synchronization.

---

## Weaknesses

### W1: Smaller Community Than Hive Metastore
Hive Metastore has decades of production deployment history across thousands of organizations. Nessie's community, while growing, is significantly smaller. This means:
- Fewer Stack Overflow answers and community resources
- Smaller pool of engineers with production Nessie experience
- Less third-party tooling integration

### W2: No Native High Availability Without External Orchestration
Nessie does not include built-in clustering or leader election. HA requires:
- Kubernetes deployment with multiple replicas
- PostgreSQL HA (e.g., Patroni, RDS Multi-AZ)
- Load balancer in front of Nessie instances
This is achievable but adds operational complexity compared to managed services.

### W3: Limited Vendor Support
Unlike commercial catalogs (Unity Catalog backed by Databricks, AWS Glue backed by Amazon), Nessie relies on community support and Dremio's stewardship. Enterprise support contracts are available through Dremio but at additional cost.

### W4: Teradata OTF Does Not Natively Support REST Catalog
As documented in ADR-001, Teradata's Open Table Format feature supports AWS Glue and HMS but not REST catalog. This requires either:
- Trino query federation as a fallback (validated in Phase 1)
- Future Teradata OTF update to add REST catalog support

### W5: Learning Curve for Branching Semantics
While branching is a strength, teams unfamiliar with Git-like catalog management need training. Incorrect branch management could lead to metadata divergence or confusion.

---

## Opportunities

### O1: REST Catalog Spec Becoming Industry Standard
The Apache Iceberg REST catalog specification is gaining rapid adoption:
- Snowflake added ICEBERG_REST catalog integration
- AWS Lake Formation is adding REST catalog support
- Confluent, Tabular, and others are implementing the spec
As REST catalog becomes the standard, Nessie's position strengthens.

### O2: Zero-Downtime Schema Migrations via Branching
Nessie branching enables a schema migration workflow not possible with traditional catalogs:
1. Create branch `schema-v2`
2. Apply schema changes on the branch
3. Run validation queries against the branch
4. Merge to `main` when verified
This eliminates the downtime window for schema changes in production.

### O3: Snowflake ICEBERG_REST Integration
Snowflake's native support for ICEBERG_REST catalog type allows direct integration with Nessie. This eliminates the need for data copy or ETL to provide Snowflake access to the lakehouse data.

### O4: Growing Ecosystem Adoption
The Nessie project is actively developed with regular releases. The Dremio-backed governance model provides stability while the Apache Iceberg ecosystem grows.

### O5: Regulatory Compliance via Catalog Versioning
Nessie's full audit trail of metadata changes supports:
- BCBS 239 data lineage requirements
- Point-in-time query reproducibility for regulatory reporting
- Change management documentation for audits

---

## Threats

### T1: Apache Polaris Gaining Momentum
Apache Polaris (incubating) is a competing REST catalog implementation backed by Snowflake. If Polaris gains broader adoption, Nessie may face community fragmentation.

**Mitigation:** Both Nessie and Polaris implement the same REST catalog spec. Migration between them is possible because the REST API is standardized. Our code uses `catalog.type=rest` (not Nessie-specific), enabling catalog switching without application changes.

### T2: Vendor Lock-In Risk if Migrating to Managed Catalog
If we later decide to move to a managed catalog (AWS Glue, Polaris SaaS), migration effort includes:
- Metadata export/import
- Connection string changes across all engines
- Testing and validation

**Mitigation:** The REST catalog spec provides a standard API. Migration effort is primarily operational, not architectural. Our infrastructure-as-code approach means connection configuration changes are automated through Terraform.

### T3: REST Catalog Specification Still Evolving
The Iceberg REST catalog spec is not yet fully finalized. Breaking changes, while unlikely, could require Nessie updates.

**Mitigation:** Pin Nessie to a specific version in production. Test upgrades in staging before promotion. Our Docker Compose and Helm chart configurations lock the version.

### T4: Nessie Project Governance Changes
Nessie is primarily maintained by Dremio. A change in Dremio's strategy (acquisition, pivot) could affect project maintenance.

**Mitigation:**
1. Nessie is Apache 2.0 licensed -- the code can be forked if necessary
2. Multiple organizations contribute to Nessie beyond Dremio
3. The REST catalog spec ensures our architecture is not Nessie-specific
4. Maintain the ability to switch to Polaris with < 1 week of engineering effort

### T5: Scale Limitations Under Extreme Load
Nessie's performance characteristics at extreme scale (millions of tables, thousands of concurrent connections) are less proven than AWS Glue or Hive Metastore.

**Mitigation:** Our lakehouse has hundreds of tables, not millions. Benchmark harness established in Phase 1 will track catalog response times. PostgreSQL backing store scales well for our volume. If needed, caching layer can be added.

---

## Decision Matrix

| Criteria | Nessie | Polaris | AWS Glue | Hive Metastore |
|----------|--------|---------|----------|----------------|
| License cost | Free | Free (OSS) / Paid (SaaS) | Per-request pricing | Free |
| REST catalog spec | Yes | Yes | Partial | No |
| Multi-engine support | Trino, Spark, Flink | Trino, Spark | Spark, Athena | Trino, Spark, Hive |
| Branching | Yes (unique) | No | No | No |
| Teradata OTF | Via Trino federation | Unknown | Yes (Glue) | Yes |
| Snowflake integration | Yes (ICEBERG_REST) | Yes (ICEBERG_REST) | No | No |
| Cloud-agnostic | Yes | Yes | AWS only | Yes |
| HA complexity | Medium (K8s) | Medium (K8s) | Low (managed) | High (HMS HA) |
| Community size | Growing | Emerging | Large (AWS) | Largest |

## Recommendation

**Nessie is recommended as the Iceberg catalog for the lakehouse architecture** based on:

1. REST catalog compliance for multi-engine interoperability
2. Git-like branching for safe schema evolution (unique differentiator)
3. Successful Phase 1 feasibility validation (Spark + Trino confirmed working)
4. Cloud-agnostic design supporting our hybrid S3/MinIO architecture
5. No license cost and open-source governance
6. Manageable risk profile with documented mitigations for each threat

The primary risk (Teradata OTF REST catalog gap) has a validated fallback (Trino query federation) that meets performance requirements.

---

*Prepared by: Lakehouse Architecture Team*
*Review cycle: Quarterly (next review: 2026-Q2)*
