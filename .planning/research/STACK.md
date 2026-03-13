# Technology Stack

**Project:** Lakehouse Architecture Transformation
**Researched:** 2026-03-13
**Overall Confidence:** MEDIUM-HIGH (most recommendations verified via multiple sources; some emerging tools have lower certainty)

---

## Recommended Stack

### Table Format

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Apache Iceberg | 1.10.x (V2 spec; V3 when engines catch up) | Open table format for all data | Industry standard for multi-engine lakehouse. Supported by Teradata OTF, Trino, Snowflake, Spark. V2 is production-stable; V3 spec (deletion vectors, default values) ratified but engine support still rolling out. Netflix, Apple, LinkedIn battle-tested at PB scale. | HIGH |

**Rationale:** Iceberg is the only OTF with first-class support across all four engines in this architecture (Teradata, Trino, Snowflake, Spark). Delta Lake is Databricks-centric; Hudi is ingestion-focused. This is not a close decision.

### Iceberg Catalog

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Apache Polaris | 1.2.x | Primary Iceberg REST catalog | Graduated to Apache TLP Feb 2026. Implements Iceberg REST spec. PostgreSQL-backed persistence. RBAC, fine-grained permissions, event logging. S3-compatible (MinIO) support since v1.1.0. Vendor-neutral. | MEDIUM-HIGH |
| Project Nessie | 0.9x+ | Git-branching catalog layer (optional, Phase 2+) | Git-style branching, tags, and multi-table atomic commits. Ideal for dev/test isolation and data versioning. REST catalog support experimental. Layer on top of Polaris when branching is needed. | MEDIUM |

**SWOT: Apache Polaris**

| | Positive | Negative |
|---|---------|----------|
| **Internal** | **Strengths:** Apache TLP (governance stability). REST spec compliant (any engine works). PostgreSQL persistence (ops-friendly). RBAC built-in. MinIO support since 1.1.0. | **Weaknesses:** Young project (first release July 2025). Smaller community than Glue/HMS. No managed service offering. Self-hosted operational burden. |
| **External** | **Opportunities:** REST catalog becoming the standard. Snowflake catalog-linked databases support REST. Positions for future engine additions. Growing contributor base. | **Threats:** AWS Glue is free-tier for AWS users. Nessie may subsume Polaris features. Lakekeeper (Rust-based) rising fast. Snowflake may push proprietary catalog. |

**Why NOT the alternatives:**

| Alternative | Why Not |
|-------------|---------|
| AWS Glue Data Catalog | AWS-locked. No on-prem MinIO support. Breaks hybrid cloud/on-prem requirement. Fine for AWS-only shops, not for this architecture. |
| Hive Metastore (HMS) | Legacy. No REST spec. No branching. No RBAC. Requires Hadoop infrastructure. Being replaced industry-wide. |
| Nessie standalone | REST support still experimental. Better as a complement to Polaris than a replacement. More complex to operate as primary catalog. |
| Lakekeeper | Rust-based, very fast, but even younger than Polaris (21.4% adoption vs Polaris 21.4%). Less proven at enterprise scale. Worth monitoring. |

**Decision:** Use Polaris as the primary catalog. Evaluate Nessie for dev/test branching in Phase 2. This gives REST-spec compliance for Trino + Snowflake + Spark while supporting both AWS S3 and MinIO.

---

### Query Engines

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Trino | 479+ | Primary open query engine | Federation across Iceberg + Teradata. Iceberg connector supports V1/V2, REST/Nessie/Glue/JDBC catalogs. Full DML (UPDATE, DELETE, MERGE). Add-files procedure for migration. 100+ connectors. | HIGH |
| Teradata VantageCloud (DB-e 20+) | DB-e 20 | Legacy warehouse with OTF bridge | Cross-read/write/query of Iceberg tables via OTF. Supports Glue and HMS catalogs natively. Validates Iceberg feasibility without migration risk. Keep during transition. | HIGH |
| Snowflake | Current | Optional compute over Iceberg external tables | Catalog-linked databases (GA Oct 2025) enable full DML on externally-managed Iceberg tables via REST catalog. Write support to external Iceberg tables is GA. Billing for catalog-linked DBs started Dec 2025. | HIGH |

**Trino Configuration for Iceberg + Polaris + MinIO:**
```properties
# catalog/iceberg.properties
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri=http://polaris:8181/api/catalog
iceberg.rest-catalog.warehouse=lakehouse
fs.native-s3.enabled=true
s3.endpoint=https://minio.internal:9000
s3.region=us-east-1
s3.path-style-access=true
```

**Teradata OTF Catalog Note:** Teradata OTF currently supports AWS Glue and HMS catalogs. REST catalog (Polaris) support is not yet confirmed. This means Teradata may need a Glue or HMS facade, or Polaris may need to expose HMS-compatible endpoints. **This is a critical integration risk to validate in Phase 1.**

---

### Storage

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| AWS S3 | Current | Cloud object storage | Production standard. Native Iceberg support. Lifecycle policies, versioning, encryption at rest. | HIGH |
| MinIO AIStor | Enterprise | On-premises S3-compatible storage | S3 API compatible with Iceberg. Note: open-source MinIO repo archived early 2026; enterprise AIStor is the path forward. 11 nines durability. S3 Express API support. | MEDIUM-HIGH |

**Critical Note on MinIO:** The open-source MinIO community edition was archived in early 2026. For production on-prem storage, MinIO AIStor (commercial) is required. Budget accordingly. If budget is constrained, evaluate Ceph with S3 gateway as a fully open-source alternative.

**Storage Layout:**
```
s3://lakehouse-raw/          # Bronze: raw ingested data
s3://lakehouse-curated/      # Silver: cleansed, conformed
s3://lakehouse-analytics/    # Gold: business-ready aggregates
s3://lakehouse-sandbox/      # Dev/test scratch space
```

---

### Python ETL Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PySpark | 3.5.x (Spark 3.5) | Primary ETL engine for heavy transforms | Required for 1.5 PB scale. Native Iceberg write support. Distributed processing. Team of 40 engineers likely has Spark skills. Battle-tested at PB scale by Netflix, Apple. | HIGH |
| PyIceberg | 0.11.x | Lightweight Iceberg table operations | Python-native Iceberg access without JVM. Schema evolution, metadata ops, small-to-medium reads/writes. Integrates with Pandas, DuckDB, Polars, Arrow. Use for utility scripts, metadata operations, testing. | MEDIUM-HIGH |
| DuckDB | 1.2.x | Local analytics, testing, small transforms | In-process OLAP. Zero-config. Iceberg read support. Ideal for CI/CD test queries, developer local testing, small dataset transformations. Not for PB-scale production ETL. | HIGH |
| Polars | 1.x | DataFrame operations where Pandas is too slow | 10-100x faster than Pandas for single-node transforms. Lazy evaluation. Arrow-native. Use for medium-scale transforms that don't need Spark distribution. | MEDIUM |

**ETL Framework Decision:**

Use **PySpark** as the primary ETL engine (replaces DataStage). At 1.5 PB with 300+ sources, distributed processing is non-negotiable. Supplement with **PyIceberg** for metadata-only operations and **DuckDB** for testing/development.

**Why NOT the alternatives:**

| Alternative | Why Not |
|-------------|---------|
| DuckDB as primary ETL | Single-node. Cannot handle 1.5 PB distributed processing. Great for dev/test, not production at this scale. |
| Polars as primary ETL | Single-node (though distributed Polars is emerging). Not mature enough for PB-scale production. |
| Daft | Distributed Python DataFrame, but immature. Worth watching for 2027. |
| Pandas | Memory-bound. Slow. No Iceberg-native support. Legacy choice. |

**PySpark + Iceberg Configuration:**
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("lakehouse-etl") \
    .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.lakehouse.type", "rest") \
    .config("spark.sql.catalog.lakehouse.uri", "http://polaris:8181/api/catalog") \
    .config("spark.sql.catalog.lakehouse.warehouse", "lakehouse") \
    .config("spark.sql.catalog.lakehouse.io-impl", "org.apache.iceberg.aws.s3.S3FileIO") \
    .config("spark.sql.catalog.lakehouse.s3.endpoint", "https://minio.internal:9000") \
    .getOrCreate()
```

---

### Data Transformation Layer

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| dbt-core + dbt-trino | dbt 1.9.x / dbt-trino latest | SQL transformations, Silver-to-Gold modeling | Industry standard for SQL-based transforms. Trino adapter supports Iceberg materializations, MERGE for incremental models. Semantic Layer integration (Trino joined dbt Semantic Layer July 2025). Model contracts. Massive community. | HIGH |

**Why dbt over SQLMesh:**

SQLMesh offers compelling features (9x faster execution in benchmarks, virtual environments, built-in state tracking, column-level lineage). However, for this project:

1. **Team size (40 engineers):** dbt's massive community means easier hiring and onboarding
2. **Ecosystem integration:** dbt integrates with Airflow, Snowflake, Tableau, every governance tool
3. **Semantic Layer:** dbt Semantic Layer + MetricFlow is more mature for BI integration
4. **Risk profile:** Financial services org transforming 1.5 PB -- choose the battle-tested option
5. **Trino adapter maturity:** dbt-trino is production-proven; SQLMesh Trino support is newer

**Reconsider SQLMesh if:** dbt-trino performance becomes a bottleneck, or if virtual environments prove critical for the team's workflow.

---

### Semantic Layer (BI)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Cube | 1.6.x (Core) | Universal semantic layer for BI tools | API-first (REST, GraphQL, SQL). Trino integration. Pre-aggregation caching (sub-second P95). Multi-tenant security. Tableau and Power BI connectors. AI API for LLM integration. | MEDIUM-HIGH |

**SWOT: Cube as Semantic Layer**

| | Positive | Negative |
|---|---------|----------|
| **Internal** | **Strengths:** API-first fits headless/multi-BI pattern. Native Trino integration. Pre-aggregation handles concurrency. Multi-tenant RBAC. AI API built-in. Both OSS core and cloud offering. | **Weaknesses:** Requires learning Cube schema language. Another service to operate. Not as widely adopted as dbt in analytics engineering circles. |
| **External** | **Opportunities:** Semantic layer is Gartner "essential infrastructure" (2025 Hype Cycle). AI/LLM integration trending. Governs metrics centrally for Tableau + Power BI + NL-to-SQL. | **Threats:** dbt Semantic Layer improving rapidly. AtScale targets enterprise harder. Tableau/Power BI building native semantic layers. |

**Why NOT the alternatives:**

| Alternative | Why Not |
|-------------|---------|
| dbt Semantic Layer alone | Requires dbt Cloud for full features. MetricFlow is SQL-push-down only (no caching). Weaker API story for embedding. Less mature for high-concurrency BI. |
| AtScale | Enterprise-grade but expensive. Proprietary. Heavier to operate. Better fit if you have >500 BI users with complex cubes. Evaluate if Cube proves insufficient. |
| No semantic layer | Leads to metric inconsistency across Tableau and Power BI. Each team defines revenue differently. Governance nightmare for financial services. |

**Architecture:** dbt models define the transformation logic (Silver to Gold). Cube sits on top of Trino, consuming dbt-built Gold tables, and serves consistent metrics to Tableau, Power BI, and the NL-to-SQL layer.

---

### Semantic Layer (AI / NL-to-SQL)

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Wren AI | Latest (OSS) | NL-to-SQL semantic engine | Open-source, semantic-first design. Built-in modeling language for business context. Apache DataFusion engine (decoupled from any warehouse). Self-hosted enterprise option. 13K+ GitHub stars. Hybrid LLM approach for data privacy. | MEDIUM |
| Vanna AI | 2.0 | Alternative/complement NL-to-SQL | RAG-based architecture that learns from org usage. Agent-based (Vanna 2.0). Row-level security. Audit logs. MIT licensed. 20K+ GitHub stars. Production-ready with user-aware security. | MEDIUM |

**SWOT: NL-to-SQL Layer**

| | Positive | Negative |
|---|---------|----------|
| **Internal** | **Strengths:** Both open-source with self-hosted options (data sovereignty for financial services). RAG/semantic approaches push accuracy to 86-95%. Audit trail capabilities. | **Weaknesses:** Frontier LLMs still 70-85% raw accuracy on complex queries. Requires semantic model curation effort. Both relatively young projects. Enterprise production deployments limited. |
| **External** | **Opportunities:** LLM accuracy improving rapidly. Cube AI API can feed business context. Financial services users desperate for self-service analytics. | **Threats:** Hallucinated SQL on financial data is high-risk. Regulatory scrutiny of AI-generated analytics. Vendor solutions (Thoughtspot, etc.) more polished. |

**Recommendation:** Start with **Cube's AI API** as the first NL-to-SQL layer (it already has your semantic model and Trino connection). Evaluate **Wren AI** as a dedicated NL-to-SQL engine if Cube's AI API proves insufficient. Deploy **Vanna AI** only if you need a standalone, RAG-trained solution with deeper learning from user behavior.

**Critical constraint for financial services:** Any NL-to-SQL system MUST have:
1. Query review/approval workflow before execution
2. Audit trail of all generated SQL
3. Row-level security enforcement
4. Ability to restrict to pre-approved query patterns
5. Human-in-the-loop for financial reporting queries

---

### Orchestration

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Apache Airflow | 3.0.x+ | Workflow orchestration | De facto standard. 80K+ orgs. 30M+ monthly downloads. Airflow 3.0 (April 2025) adds asset-aware scheduling, DAG versioning, React UI. Massive operator library (Snowflake, Spark, Trino, dbt, Kubernetes). AWS MWAA managed option. | HIGH |

**Why Airflow over Dagster:**

Dagster offers genuine advantages (asset-centric, 2x productivity claims, better local dev, built-in lineage). However:

1. **Scale:** 40 engineers, 300+ sources, 1.5 PB. Airflow is battle-tested at this scale. Dagster less so.
2. **Airflow 3.0 closes the gap:** Asset-aware scheduling, event-driven triggers, and data assets address Dagster's key differentiators.
3. **Managed services:** AWS MWAA provides managed Airflow. No equivalent managed Dagster on AWS (Dagster Cloud exists but is separate).
4. **Ecosystem integration:** Every data tool has an Airflow operator. DataStage migration scripts can wrap in BashOperator/PythonOperator incrementally.
5. **Hiring:** Airflow skills are ubiquitous. Dagster skills are rarer.
6. **Financial services conservatism:** Battle-tested > cutting-edge for regulated environments.

**Reconsider Dagster if:** Starting fresh with a small team, or if asset-centric lineage becomes a primary requirement that Airflow 3.0 assets don't satisfy.

**Why NOT Prefect:** Smaller ecosystem. Less operator coverage. Better for ML workflows than ETL orchestration. Cloud-first pricing model.

---

### Data Quality

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Soda Core | 4.1.x | Primary data quality framework | Data Contracts as first-class concept (v4). SodaCL (YAML-based checks). Missing/invalid/duplicate/aggregate checks. Reconciliation checks (critical for Teradata-to-Iceberg validation). Plugin architecture. Lighter-weight than Great Expectations. | MEDIUM-HIGH |
| Great Expectations | 1.x (GX Core) | Complex validation rules, profiling | Python-native. Extensive expectation library. Data profiling. Auto-generated expectations via Data Assistants. Spark + SQLAlchemy integration. Use for complex statistical validations where Soda's YAML is insufficient. | MEDIUM-HIGH |

**Decision:** Use **Soda Core** as the primary quality framework. Its Data Contracts model aligns with the lakehouse medallion architecture (define contracts at each layer boundary). Use **Great Expectations** for complex statistical profiling during the initial Teradata-to-Iceberg migration validation.

**Why Soda over GX as primary:**
1. YAML-based checks (SodaCL) are more accessible to 40 engineers than Python-heavy GX
2. Data Contracts in v4 map cleanly to Bronze/Silver/Gold layer boundaries
3. Reconciliation checks are purpose-built for migration validation (Teradata vs Iceberg)
4. Lighter operational footprint

**dbt tests** (schema tests, data tests) complement both -- use for transformation-layer validation within dbt models.

---

### Data Governance, Lineage, and Catalog

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| OpenMetadata | 1.12.x | Data catalog, lineage, governance | Unified platform: discovery + lineage + quality + governance. 90+ connectors. Column-level lineage. PII auto-classification. Git-based metadata versioning (CI/CD friendly). Natural language agents. Open-source. | MEDIUM-HIGH |
| OpenLineage | Latest spec | Lineage event standard | Open framework for lineage collection. Integrates with Airflow (native), Spark, dbt. Produces lineage events consumed by OpenMetadata or Marquez. Industry standard. | HIGH |

**Why OpenMetadata over alternatives:**

| Alternative | Why Not |
|-------------|---------|
| Collibra | Best-in-class but expensive ($500K+/year enterprise). Overkill for Phase 1. Consider if OpenMetadata hits governance ceiling. |
| Atlan | Strong product but SaaS-only. Financial services may need on-prem option. Expensive. |
| DataHub (LinkedIn) | Modular but requires assembly. Less unified than OpenMetadata. Community fragmented. |
| Apache Atlas | Legacy. Tied to Hadoop ecosystem. Limited modern integrations. |

**Lineage Architecture:**
```
Airflow (OpenLineage producer) --> OpenLineage events --> OpenMetadata (consumer)
Spark (OpenLineage producer)   --> OpenLineage events --> OpenMetadata (consumer)
dbt (artifact producer)        --> dbt artifacts       --> OpenMetadata (ingestion)
Trino (query logs)             --> log parsing          --> OpenMetadata (ingestion)
```

**Financial Services Governance Requirements Addressed:**

| Requirement | Solution |
|-------------|----------|
| BCBS 239 data lineage | OpenLineage + OpenMetadata column-level lineage |
| BCBS 239 data quality | Soda Core data contracts + quality metrics in OpenMetadata |
| BCBS 239 data ownership | OpenMetadata ownership assignment + review workflows |
| DORA operational resilience | Airflow monitoring + infrastructure as code + audit trails |
| Audit trail | OpenMetadata change history + Git-based metadata versioning |
| PII classification | OpenMetadata auto-classification agents |
| Access control | Polaris RBAC + Trino access control + Cube row-level security |

---

### BI Tools

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Tableau | Current | Primary BI (existing investment) | Already in use. Connects to Trino via JDBC. Cube connector available for semantic layer. Keep existing dashboards during migration. | HIGH |
| Power BI | Current | Secondary BI (existing investment) | Already in use. Connects to Trino via ODBC. Cube connector available. Import and DirectQuery modes. | HIGH |

**Connection Path:** Tableau/Power BI --> Cube (semantic layer, caching, security) --> Trino (query federation) --> Iceberg tables (S3/MinIO)

**Fallback Path:** Tableau/Power BI --> Trino directly (bypass Cube for ad-hoc exploration)

---

### CI/CD and DevOps

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| GitHub | Enterprise | Source control, collaboration | Already specified as requirement. Branch protection, PR reviews, CODEOWNERS. | HIGH |
| GitHub Actions | Current | CI/CD pipelines | Native GitHub integration. dbt slim CI (run only changed models). Python linting/testing. Infrastructure validation. Cost-efficient for data engineering workflows. | HIGH |
| Terraform | 1.9.x+ | Infrastructure as code | AWS resources (S3, IAM, networking). MinIO configuration. Polaris deployment. Trino cluster management. State management for audit trail. | HIGH |
| Docker / Kubernetes | Current | Container orchestration | Polaris, Trino, Airflow, Cube, OpenMetadata all containerized. Helm charts available for most. K8s for scaling Spark and Trino workers. | HIGH |
| pre-commit | Latest | Code quality gates | Python linting (ruff), SQL formatting (sqlfluff), secret scanning, YAML validation. Runs before every commit. | HIGH |

**CI/CD Pipeline Architecture:**
```
PR Created/Updated:
  1. pre-commit hooks (ruff, sqlfluff, yaml-lint, secret-scan)
  2. Python unit tests (pytest)
  3. dbt compile + dbt test (slim CI - changed models only)
  4. Soda contract validation (against dev environment)
  5. Terraform plan (infrastructure changes)
  6. DuckDB integration tests (query correctness on sample data)

Merge to main:
  7. dbt run (deploy to staging)
  8. Soda quality checks (staging)
  9. Terraform apply (infrastructure)
  10. Airflow DAG deployment
  11. Promotion to production (manual gate for financial services)
```

---

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyArrow | 17.x+ | Arrow-native data interchange | Data format for PyIceberg, DuckDB, Polars interop. In-memory columnar format. |
| SQLAlchemy + Trino dialect | 2.0.x + trino[sqlalchemy] | Trino connection from Python | Application-level Trino queries. Soda Core Trino connectivity. |
| sqlfluff | 3.x | SQL linting and formatting | CI/CD SQL quality gate. Enforces consistent SQL style across 40 engineers. |
| ruff | 0.9.x | Python linting and formatting | Replaces flake8 + black + isort. Fastest Python linter (Rust-based). |
| pytest | 8.x | Python testing | Unit tests for ETL functions. Integration tests with DuckDB. |
| Pydantic | 2.x | Data validation, config models | ETL pipeline configuration. API request/response models. Type-safe configs. |
| boto3 | 1.x | AWS SDK | S3 operations. IAM management. Direct AWS service interaction. |

---

## Version Pinning Strategy

For a financial services environment, pin **major.minor** versions and allow patch updates:

```
# requirements.txt pattern
pyspark>=3.5.0,<3.6.0
pyiceberg>=0.11.0,<0.12.0
duckdb>=1.2.0,<1.3.0
soda-core>=4.1.0,<4.2.0
great-expectations>=1.0.0,<2.0.0
dbt-core>=1.9.0,<1.10.0
dbt-trino>=1.9.0,<1.10.0
polars>=1.0.0,<2.0.0
```

---

## Alternatives Considered (Full Matrix)

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Table Format | Apache Iceberg | Delta Lake | Databricks-centric. Less multi-engine support. |
| Table Format | Apache Iceberg | Apache Hudi | Ingestion-focused. Weaker query engine support. |
| Catalog | Apache Polaris | AWS Glue | No on-prem/MinIO support. AWS lock-in. |
| Catalog | Apache Polaris | Hive Metastore | Legacy. No REST. No RBAC. |
| Catalog | Apache Polaris | Gravitino | Too early. Federated approach adds complexity. |
| Query Engine | Trino | Presto | Trino is the active fork. Larger community. |
| Query Engine | Trino | Dremio | Proprietary. Adds vendor dependency. |
| ETL Engine | PySpark | Databricks | Vendor lock-in. Expensive. Already have Spark capability. |
| ETL Engine | PySpark | AWS Glue ETL | AWS-locked. Less control. |
| Transformation | dbt | SQLMesh | Smaller community. Higher risk for 40-person team. |
| Orchestration | Airflow 3.0 | Dagster | Less battle-tested at scale. Smaller ecosystem. |
| Orchestration | Airflow 3.0 | Prefect | ML-focused. Less ETL ecosystem. |
| Semantic Layer | Cube | AtScale | Expensive. Heavier. |
| Semantic Layer | Cube | dbt Semantic Layer | Cloud-required for full features. No caching. |
| NL-to-SQL | Wren AI / Cube AI | ThoughtSpot | Proprietary. Expensive. Vendor lock-in. |
| Data Quality | Soda Core | Monte Carlo | Proprietary. Expensive. |
| Data Quality | Soda Core | Elementary | dbt-native only. Less standalone capability. |
| Governance | OpenMetadata | Collibra | $500K+/year. Overkill for Phase 1. |
| Governance | OpenMetadata | Atlan | SaaS-only. Data sovereignty concerns. |
| Storage (on-prem) | MinIO AIStor | Ceph | Harder to operate. Weaker S3 compatibility. But fully open-source. |

---

## Installation

```bash
# Core Python ETL
pip install "pyspark>=3.5.0,<3.6.0" \
    "pyiceberg[s3fs,glue,rest]>=0.11.0,<0.12.0" \
    "duckdb>=1.2.0,<1.3.0" \
    "polars>=1.0.0,<2.0.0" \
    "pyarrow>=17.0.0"

# dbt
pip install "dbt-core>=1.9.0,<1.10.0" \
    "dbt-trino>=1.9.0,<1.10.0"

# Data Quality
pip install "soda-core-trino>=4.1.0" \
    "great-expectations>=1.0.0,<2.0.0"

# Orchestration (managed via Helm/Docker, not pip in prod)
pip install "apache-airflow>=3.0.0,<3.1.0"  # for local dev only

# Dev dependencies
pip install "pytest>=8.0.0" \
    "ruff>=0.9.0" \
    "sqlfluff>=3.0.0" \
    "pre-commit>=4.0.0" \
    "pydantic>=2.0.0" \
    "boto3>=1.35.0"

# Infrastructure (via Helm charts)
# Apache Polaris: docker pull apache/polaris:1.2.0
# Trino: helm install trino trino/trino --version 479
# Cube: docker pull cubejs/cube:v1.6
# OpenMetadata: helm install openmetadata open-metadata/openmetadata
# Airflow: helm install airflow apache-airflow/airflow --version 1.15.0
```

---

## Architecture Integration Summary

```
                        +------------------+
                        |   GitHub Actions  |
                        |   (CI/CD)        |
                        +--------+---------+
                                 |
                    +------------+------------+
                    |                         |
              +-----v------+          +------v-------+
              |  Airflow   |          |  Terraform   |
              |  3.0       |          |  (IaC)       |
              +-----+------+          +--------------+
                    |
        +-----------+-----------+
        |           |           |
  +-----v----+ +---v-----+ +--v-------+
  | PySpark  | | dbt     | | Soda     |
  | ETL      | | Trino   | | Core     |
  +-----+----+ +---+-----+ +--+-------+
        |           |           |
        +-----+-----+-----+----+
              |           |
        +-----v----+ +---v----------+
        |  Trino   | | Teradata     |
        |  479     | | OTF          |
        +-----+----+ +---+----------+
              |           |
        +-----v-----------v-----+
        |    Apache Polaris     |
        |    (Iceberg Catalog)  |
        +-----------+-----------+
                    |
        +-----------+-----------+
        |                       |
  +-----v------+        +------v-------+
  |  AWS S3    |        |  MinIO       |
  |  (cloud)   |        |  (on-prem)   |
  +------------+        +--------------+

  Consumers:
  Tableau / Power BI --> Cube --> Trino --> Iceberg
  NL-to-SQL (Cube AI / Wren AI) --> Trino --> Iceberg
  Snowflake --> Iceberg REST catalog --> Iceberg tables on S3
```

---

## Open Questions and Risks

### Critical (Must resolve in Phase 1)

1. **Teradata OTF + Polaris REST catalog compatibility:** Teradata OTF currently documents support for Glue and HMS. Does it support Iceberg REST catalog (Polaris)? If not, you need either: (a) HMS facade over Polaris, (b) dual catalog sync, or (c) Glue for Teradata + Polaris for everything else.

2. **MinIO AIStor licensing costs:** Open-source MinIO is archived. Enterprise AIStor pricing for 1.5 PB on-prem must be budgeted. Get quotes early.

3. **Snowflake catalog-linked database billing:** Billing started Dec 2025. Model costs for Snowflake reading Iceberg via REST catalog at expected query volumes.

### Important (Resolve by Phase 2)

4. **NL-to-SQL accuracy on financial data:** 70-85% raw LLM accuracy is insufficient for financial reporting. Semantic layer context pushes to 86-95%, but remaining errors on financial data could be costly. Requires human-in-the-loop workflow.

5. **Polaris operational maturity:** As a self-hosted service, who operates Polaris? What's the HA/DR story? PostgreSQL backend needs its own HA.

6. **Spark cluster sizing:** 1.5 PB migration + ongoing ETL requires significant Spark infrastructure. AWS EMR vs self-managed vs Kubernetes (spark-on-k8s-operator).

---

## Sources

### Iceberg & Catalogs
- [Apache Iceberg Releases](https://iceberg.apache.org/releases/) -- Iceberg 1.10.1, Dec 2025
- [Apache Polaris GitHub](https://github.com/apache/polaris) -- Polaris TLP graduation Feb 2026
- [Apache Polaris TLP Announcement](https://www.globenewswire.com/news-release/2026/02/19/3240735/0/en/apache-polaris-graduates-to-top-level-apache-project.html)
- [Iceberg Catalogs 2025: Emerging Metadata Solutions](https://www.e6data.com/blog/iceberg-catalogs-2025-emerging-catalogs-modern-metadata-management)
- [2025 State of the Apache Iceberg Ecosystem](https://datalakehousehub.com/blog/2026-02-state-of-the-apache-iceberg-ecosystem/)
- [Project Nessie](https://projectnessie.org/)
- [Iceberg V3 Spec](https://opensource.googleblog.com/2025/08/whats-new-in-iceberg-v3.html)

### Teradata & Snowflake
- [Teradata Open Table Formats](https://www.teradata.com/platform/open-table-formats)
- [Teradata OTF Press Release](https://www.teradata.com/press-releases/2024/teradata-embraces-open-table-formats-iceberg)
- [Snowflake Iceberg Tables Documentation](https://docs.snowflake.com/en/user-guide/tables-iceberg)
- [Snowflake External Managed Iceberg Writes GA](https://docs.snowflake.com/en/release-notes/2025/other/2025-10-17-iceberg-external-writes-cld-ga)

### Query & Compute Engines
- [Trino 479 Iceberg Connector](https://trino.io/docs/current/connector/iceberg.html)
- [Trino S3 File System Support](https://trino.io/docs/current/object-storage/file-system-s3.html)
- [PyIceberg on PyPI](https://pypi.org/project/pyiceberg/) -- v0.11.1, Mar 2026
- [PyIceberg Documentation](https://py.iceberg.apache.org/)

### Transformation & Semantic Layer
- [dbt-trino Configurations](https://docs.getdbt.com/reference/resource-configs/trino-configs)
- [dbt Semantic Layer + Trino (July 2025)](https://www.getdbt.com/blog/whats-new-in-dbt-july-2025)
- [Cube Trino Integration](https://cube.dev/docs/product/configuration/data-sources/trino)
- [Cube AI and Semantic Layer](https://cube.dev/blog/semantic-layer-and-ai-the-future-of-data-querying-with-natural-language)
- [Semantic Layer Architectures 2025](https://www.typedef.ai/resources/semantic-layer-architectures-explained-warehouse-native-vs-dbt-vs-cube)

### NL-to-SQL
- [Enterprise NL-to-SQL with LLMs (AWS)](https://aws.amazon.com/blogs/machine-learning/enterprise-grade-natural-language-to-sql-generation-using-llms-balancing-accuracy-latency-and-scale/)
- [NL-to-SQL Complete 2026 Guide](https://www.blazesql.com/blog/natural-language-to-sql)
- [Text-to-SQL LLM Accuracy Comparison 2026](https://research.aimultiple.com/text-to-sql/)
- [Wren AI OSS](https://www.getwren.ai/oss)
- [Wren AI 2025 Year in Review](https://www.getwren.ai/post/wren-ai-2025-year-in-review-from-open-source-to-agentic-bi-in-production)
- [Vanna AI 2.0](https://vanna.ai/)

### Orchestration
- [Apache Airflow 3.0 Release](https://airflow.apache.org/blog/airflow-three-point-oh-is-here/)
- [Airflow 3.0 Asset-Aware Scheduling](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html)
- [Dagster vs Airflow Comparison](https://dagster.io/vs/dagster-vs-airflow)

### Data Quality
- [Soda Core v4 Release Notes](https://docs.soda.io/soda-v4/release-notes/soda-core-release-notes) -- v4.1.0, Feb 2026
- [Great Expectations for Lakehouses](https://greatexpectations.io/blog/data-quality-for-your-lakehouse-lakehouse-engine-gx/)
- [2026 Open-Source Data Quality Landscape](https://datakitchen.io/the-2026-open-source-data-quality-and-data-observability-landscape/)

### Governance & Lineage
- [OpenMetadata Documentation](https://docs.open-metadata.org/v1.12.x)
- [OpenLineage](https://openlineage.io/)
- [BCBS 239 Compliance Guide 2025](https://www.alation.com/blog/bcbs-239-guide-compliance-best-practices-2025/)
- [BCBS 239 and Lakehouse (Databricks)](https://www.databricks.com/blog/bcbs-239-compliance-age-ai-turning-regulatory-burden-strategic-advantage)

### Storage
- [MinIO Lakehouse Architecture Guide](https://blog.min.io/lakehouse-architecture-iceberg-minio/)
- [MinIO AIStor](https://www.min.io/)
- [Polaris + Trino + MinIO Walkthrough](https://medium.com/@gilles.philippart/build-a-data-lakehouse-with-apache-iceberg-polaris-trino-minio-349c534ecd98)

### CI/CD
- [dbt CI/CD with GitHub Actions](https://www.datafold.com/blog/accelerating-dbt-core-ci-cd-with-github-actions-a-step-by-step-guide)
- [GitHub Actions for Data Engineering](https://dev.to/alexmercedcoder/a-deep-dive-into-github-actions-from-software-development-to-data-engineering-bki)
