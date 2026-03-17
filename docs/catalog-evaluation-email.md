## Subject: Iceberg Catalog Evaluation — Comparison Summary, Polaris Limitations & Gravitino vs Nessie Analysis

Hi team,

Following our evaluation of Iceberg catalog options for the lakehouse architecture, please find the full comparison below.

### 1. Catalog Comparison (All Options)

| Criteria | Nessie | Polaris | AWS Glue | Hive Metastore | Gravitino |
|---|---|---|---|---|---|
| **License cost** | Free | Free (OSS) / Paid (SaaS) | Per-request pricing | Free | Free |
| **REST catalog spec** | Yes | Yes | Partial | No | Yes |
| **Multi-engine support** | Trino, Spark, Flink | Trino, Spark | Spark, Athena | Trino, Spark, Hive | Trino, Spark, Flink |
| **Branching** | Yes (unique) | No | No | No | No |
| **Teradata OTF** | Via Trino federation | Unknown | Yes (Glue) | Yes | Unknown |
| **Snowflake integration** | Yes (ICEBERG_REST) | Yes (ICEBERG_REST) | No | No | Yes (ICEBERG_REST) |
| **Cloud-agnostic** | Yes | Yes | AWS only | Yes | Yes |
| **HA complexity** | Medium (K8s) | Medium (K8s) | Low (managed) | High (HMS HA) | Medium (K8s) |
| **Community size** | Growing | Emerging | Large (AWS) | Largest | Emerging (incubating) |

### 2. Polaris — Identified Limitations

| Area | Polaris Limitation | Notes |
|---|---|---|
| **Maturity** | Apache Incubating project | Still emerging; not yet a top-level Apache project |
| **Community** | Emerging / smaller community | Fewer production deployments and community resources |
| **Branching** | No branching support | Cannot do Git-like schema migrations, rollbacks, or catalog versioning |
| **Multi-engine support** | Trino, Spark only | No documented Flink support |
| **Teradata OTF** | Unknown compatibility | Not documented whether Teradata OTF works with Polaris |
| **Licensing** | Free (OSS) / Paid (SaaS) | Snowflake-managed SaaS has consumption pricing |
| **HA complexity** | Medium (K8s required) | Same operational overhead as Nessie — no advantage |
| **Vendor backing** | Snowflake-backed | Risk of steering toward Snowflake ecosystem priorities |

### 3. Gravitino vs Nessie — Detailed Analysis

| Dimension | Nessie | Gravitino | Verdict |
|---|---|---|---|
| **Project status** | Established open-source project (Dremio-backed) | Apache Incubating (Datastrato-backed) | Nessie — more mature and battle-tested |
| **Core purpose** | Transactional Iceberg catalog | Unified metadata lake across multiple catalog types | Different — Gravitino is broader in scope |
| **REST catalog spec** | Yes | Yes | Tie |
| **Branching / versioning** | Git-like branching, tagging, rollback, audit trail | No branching support | Nessie — unique differentiator |
| **Multi-catalog federation** | No — single Iceberg catalog only | Yes — federate Hive, Iceberg, JDBC, and more | Gravitino — can manage multiple catalog types |
| **Access control** | Relies on external auth (Trino RBAC, K8s) | Centralized access control with tag-based governance | Gravitino — richer built-in governance |
| **Multi-engine support** | Trino, Spark, Flink | Trino, Spark, Flink | Tie |
| **Snowflake integration** | Yes (ICEBERG_REST) | Yes (ICEBERG_REST) | Tie |
| **Teradata OTF** | Via Trino federation (validated) | Unknown | Nessie — fallback is proven |
| **Backing store** | PostgreSQL (enterprise-grade, familiar ops) | Multiple backends supported | Nessie — PostgreSQL is well-understood |
| **Production footprint** | Growing; multiple production deployments documented | Smaller; still in incubation with limited production references | Nessie — more proven in production |
| **Community & support** | Growing community; Dremio enterprise support available | Emerging; Datastrato-backed | Nessie — larger community today |
| **Migration risk** | N/A (current choice) | Low — same REST catalog API; Gravitino can layer on top of Nessie | Low risk either way |
| **Future potential** | Strong as a standalone Iceberg catalog | Could serve as a federation layer *on top of* Nessie | Complementary — not necessarily a replacement |

**Key takeaway:** Gravitino is the closest feature match to Nessie, but they serve slightly different purposes. Nessie is a focused Iceberg catalog with unique branching capabilities. Gravitino is a broader unified metadata layer with multi-catalog federation and built-in governance. Gravitino's incubation status and smaller production footprint make it premature for our primary catalog today. However, Gravitino could be evaluated as a **federation layer on top of Nessie** once it reaches 1.0 — our REST catalog API usage makes this a low-risk future option.

### Recommendation

**Nessie** remains our recommended choice. The deciding factors are:
1. Git-like branching for zero-downtime schema evolution (no other catalog offers this)
2. Validated in Phase 1 feasibility testing (Spark + Trino confirmed working)
3. Cloud-agnostic design for our hybrid S3/MinIO architecture
4. Proven Teradata OTF fallback via Trino federation
5. Migration to Polaris or Gravitino remains < 1 week effort if needed

Happy to walk through the full SWOT analysis in our next sync.

Best regards
