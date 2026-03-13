# Architecture Research

**Domain:** Financial Services Lakehouse (Teradata/DataStage to Iceberg/Trino transformation)
**Researched:** 2026-03-13
**Confidence:** MEDIUM-HIGH (core patterns well-documented; Teradata OTF + Nessie/Polaris interop is LOW confidence due to limited direct evidence)

## System Overview

```
                         +-----------------------------------------+
                         |         CONSUMPTION LAYER                |
                         |                                         |
                         |  +--------+  +--------+  +-----------+  |
                         |  |Tableau |  |Power BI|  |NL-to-SQL  |  |
                         |  +---+----+  +---+----+  |AI Agent   |  |
                         |      |           |       +-----+-----+  |
                         +------+-----------+-------------+--------+
                                |           |             |
                         +------+-----------+-------------+--------+
                         |         SEMANTIC LAYER                   |
                         |                                         |
                         |  +-----------------------------------+  |
                         |  | BI Semantic Layer (dbt Metrics /   |  |
                         |  | AtScale / Cube)                    |  |
                         |  +-----------------------------------+  |
                         |  +-----------------------------------+  |
                         |  | AI Semantic Layer (NL-to-SQL with  |  |
                         |  | LLM + semantic context)            |  |
                         |  +-----------------------------------+  |
                         +-----------------------------------------+
                                          |
                         +----------------+------------------------+
                         |         QUERY ENGINE LAYER               |
                         |                                         |
                         |  +-----------+  +-----------+           |
                         |  | Teradata  |  |   Trino   |           |
                         |  | (OTF R/W) |  | (Iceberg  |           |
                         |  |           |  |  R/W)     |           |
                         |  +-----+-----+  +-----+-----+          |
                         |        |              |                 |
                         |  +-----+-----+        |                 |
                         |  | Snowflake |        |                 |
                         |  | (Iceberg  +--------+                 |
                         |  |  ext tbl) |                          |
                         |  +-----------+                          |
                         +-----------------------------------------+
                                          |
                         +----------------+------------------------+
                         |         CATALOG LAYER                    |
                         |                                         |
                         |  +-----------------------------------+  |
                         |  |  Iceberg Catalog                  |  |
                         |  |  (REST protocol: Polaris or       |  |
                         |  |   Nessie, backed by AWS Glue      |  |
                         |  |   for Teradata compatibility)     |  |
                         |  +-----------------------------------+  |
                         +-----------------------------------------+
                                          |
                         +----------------+------------------------+
                         |         TABLE FORMAT LAYER               |
                         |                                         |
                         |  +-----------------------------------+  |
                         |  | Apache Iceberg                    |  |
                         |  | (Parquet data files, Avro metadata|  |
                         |  |  manifest lists, snapshots)       |  |
                         |  +-----------------------------------+  |
                         +-----------------------------------------+
                                          |
                         +----------------+------------------------+
                         |         STORAGE LAYER (S3 API)           |
                         |                                         |
                         |  +---------------+  +----------------+  |
                         |  | AWS S3        |  | MinIO (on-prem)|  |
                         |  | (cloud        |  | (S3-compatible |  |
                         |  |  workloads)   |  |  workloads)    |  |
                         |  +---------------+  +----------------+  |
                         +-----------------------------------------+
                                          ^
                                          |
                         +----------------+------------------------+
                         |         INGESTION LAYER                  |
                         |                                         |
                         |  +-----------------------------------+  |
                         |  | Python ETL Framework              |  |
                         |  | (PySpark + Airflow/Dagster)       |  |
                         |  | Replacing DataStage               |  |
                         |  +-----------------------------------+  |
                         |  +-----------------------------------+  |
                         |  | Medallion: Bronze -> Silver -> Gold|  |
                         |  +-----------------------------------+  |
                         +-----------------------------------------+
                                          ^
                                          |
                         +----------------+------------------------+
                         |         SOURCE LAYER                     |
                         |                                         |
                         |  +-----------+  +--------+  +---------+ |
                         |  | Mainframe |  |Internal|  |External | |
                         |  | (primary) |  |Sources |  |Sources  | |
                         |  | ~100 src  |  | 150+   |  | 50+    | |
                         |  +-----------+  +--------+  +---------+ |
                         +-----------------------------------------+
                                          ^
                         +----------------+------------------------+
                         |         CROSS-CUTTING CONCERNS            |
                         |                                         |
                         |  +----------+  +---------+  +--------+  |
                         |  |Governance|  | CI/CD   |  |Lineage |  |
                         |  |& Access  |  | GitHub  |  |OpenLine|  |
                         |  |Control   |  | Actions |  |age     |  |
                         |  +----------+  +---------+  +--------+  |
                         +-----------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Talks To | Implementation |
|-----------|---------------|----------|----------------|
| **Source Systems** | Generate raw operational data | Ingestion Layer (outbound only) | Mainframe (COBOL/VSAM), databases, APIs, file drops |
| **Python ETL Framework** | Extract from sources, transform through medallion layers, load to Iceberg | Source Systems (read), Storage Layer (write), Catalog (register) | PySpark jobs orchestrated by Airflow or Dagster |
| **AWS S3** | Cloud object storage for Iceberg data and metadata files | All engines via S3 API | Managed AWS service |
| **MinIO** | On-premises S3-compatible object storage | All on-prem engines via S3 API | Self-hosted MinIO cluster |
| **Apache Iceberg** | Open table format providing ACID transactions, schema evolution, time travel | Storage Layer (data files), Catalog (metadata pointers) | Iceberg libraries embedded in each engine |
| **Iceberg Catalog** | Central metadata registry: table locations, schemas, snapshots, partitions | All query engines, ETL framework | See Catalog Strategy section below |
| **Teradata** | Enterprise query engine with OTF read/write on Iceberg tables | Catalog (AWS Glue/HMS), Storage (S3) | VantageCloud Lake or on-prem with OTF license |
| **Trino** | Open-source distributed SQL query engine for interactive analytics | Catalog (Nessie/Polaris/Glue REST), Storage (S3/MinIO) | Self-managed Trino cluster |
| **Snowflake** | Optional compute engine via Iceberg external tables | Catalog (REST/Glue), Storage (S3) | Snowflake account with Iceberg external table support |
| **BI Semantic Layer** | Business metric definitions, consistent query interface for BI tools | Trino/Teradata (query), Tableau/Power BI (serve) | dbt Semantic Layer or AtScale |
| **AI Semantic Layer** | NL-to-SQL translation with business context | BI Semantic Layer (metadata), Trino (query execution) | LLM + semantic model (custom or AtScale) |
| **Governance & Lineage** | Access control, audit trails, regulatory compliance, data lineage | All components (metadata collection) | OpenLineage + Marquez, catalog-level access control |
| **CI/CD** | Version control, automated testing, deployment of ETL and infrastructure | GitHub (source), Airflow/Dagster (deploy), Trino (schema migrations) | GitHub Actions |

---

## Recommended Project Structure

```
lakehouse/
├── etl/                           # Python ETL framework (DataStage replacement)
│   ├── sources/                   # Source-specific extractors
│   │   ├── mainframe/             # COBOL copybook parsers, VSAM readers
│   │   ├── database/              # JDBC/ODBC extractors
│   │   ├── api/                   # REST/SOAP API extractors
│   │   └── file/                  # CSV, XML, flat file loaders
│   ├── bronze/                    # Raw landing zone transformations
│   │   ├── schemas/               # Bronze schema definitions (Iceberg)
│   │   └── jobs/                  # PySpark jobs: extract -> bronze
│   ├── silver/                    # Cleansed/conformed transformations
│   │   ├── schemas/               # Silver schema definitions
│   │   └── jobs/                  # PySpark jobs: bronze -> silver
│   ├── gold/                      # Business-ready aggregations
│   │   ├── schemas/               # Gold schema definitions
│   │   └── jobs/                  # PySpark/dbt: silver -> gold
│   ├── shared/                    # Common utilities
│   │   ├── iceberg_utils.py       # Catalog interaction, table management
│   │   ├── quality.py             # Data quality checks
│   │   └── config.py              # Environment-aware config (cloud vs on-prem)
│   └── tests/                     # Unit and integration tests
│       ├── unit/                  # Pure logic tests
│       └── integration/           # Tests against test Iceberg catalog
├── orchestration/                 # Pipeline orchestration
│   ├── dags/                      # Airflow DAGs (or Dagster pipelines)
│   ├── schedules/                 # Cron definitions
│   └── sensors/                   # Source availability sensors
├── catalog/                       # Iceberg catalog configuration
│   ├── polaris/                   # Polaris server config (if chosen)
│   │   ├── docker-compose.yml     # Local dev deployment
│   │   └── k8s/                   # Kubernetes manifests for prod
│   └── migrations/                # Catalog schema migrations
├── trino/                         # Trino cluster configuration
│   ├── catalog/                   # Trino catalog properties files
│   │   ├── iceberg.properties     # Iceberg connector config
│   │   └── teradata.properties    # Teradata connector (if needed)
│   ├── config/                    # Trino server config
│   └── k8s/                       # Kubernetes deployment
├── semantic/                      # Semantic layers
│   ├── bi/                        # BI semantic layer (dbt metrics / AtScale)
│   │   ├── models/                # dbt models for Gold layer
│   │   ├── metrics/               # Metric definitions
│   │   └── tests/                 # Metric validation tests
│   └── ai/                        # AI semantic layer
│       ├── schema_context/        # Table/column descriptions for LLM
│       ├── examples/              # Few-shot SQL examples
│       └── api/                   # NL-to-SQL API service
├── governance/                    # Data governance configuration
│   ├── lineage/                   # OpenLineage integration config
│   ├── access/                    # Access control policies
│   └── quality/                   # Data quality rule definitions
├── infrastructure/                # IaC for deployment
│   ├── terraform/                 # AWS infrastructure (S3, IAM, networking)
│   ├── ansible/                   # On-prem MinIO/Trino provisioning
│   └── k8s/                       # Shared Kubernetes resources
├── ci/                            # CI/CD pipeline definitions
│   └── .github/
│       └── workflows/             # GitHub Actions workflows
│           ├── etl-test.yml       # Test ETL jobs on PR
│           ├── etl-deploy.yml     # Deploy ETL to orchestrator
│           ├── trino-deploy.yml   # Deploy Trino config changes
│           └── semantic-deploy.yml # Deploy semantic layer changes
├── docs/                          # Architecture decision records, runbooks
│   ├── adr/                       # Architecture Decision Records
│   └── runbooks/                  # Operational runbooks
└── tests/                         # End-to-end integration tests
    └── e2e/                       # Full pipeline tests
```

### Structure Rationale

- **etl/sources/**: Isolates source-specific complexity (especially mainframe COBOL copybook parsing) from transformation logic. Each source type has unique connectivity and format challenges.
- **etl/bronze|silver|gold/**: Maps directly to medallion layers. Each layer owns its schemas and transformation jobs, making it clear which code produces which layer.
- **catalog/**: Catalog is infrastructure, not application code. Separating it allows catalog choice to evolve independently of ETL logic.
- **trino/**: Trino configuration as code enables version-controlled, reproducible cluster deployments.
- **semantic/bi vs semantic/ai**: These serve different consumers with different requirements (latency, accuracy, interface) and should evolve independently.

---

## Architectural Patterns

### Pattern 1: Multi-Engine Iceberg (Core Pattern)

**What:** Multiple query engines (Teradata, Trino, Snowflake) read and write the same Iceberg tables through a shared catalog, with Iceberg's optimistic concurrency handling conflicts.

**When to use:** Always -- this is the foundational pattern for the entire architecture.

**How it works:**
1. All engines connect to the same Iceberg catalog (or catalog-compatible endpoints)
2. Each engine reads the current metadata pointer from the catalog before any operation
3. Writers stage new metadata files, then perform an atomic compare-and-swap commit
4. If another writer committed first, the operation retries against the latest snapshot
5. Readers always see a consistent snapshot (snapshot isolation)

**Trade-offs:**
- PRO: Single copy of data, no ETL between engines, vendor flexibility
- PRO: Each engine optimized for different workloads (Teradata for complex analytics, Trino for ad-hoc, Snowflake for external consumers)
- CON: Catalog must support all engines -- this is the critical constraint (see Catalog Strategy)
- CON: Write-heavy concurrent workloads from multiple engines can cause retry storms

**Critical constraint for this project:** Teradata OTF currently supports AWS Glue, Hive Metastore, and Unity Catalog. Trino supports Glue, HMS, Nessie, Polaris (REST), and JDBC catalogs. Snowflake supports REST catalogs, Glue, and Snowflake Open Catalog. The **catalog choice must be the intersection** of what all three engines support.

```
Engine Catalog Support Matrix (verified):

                  | AWS Glue | HMS  | Nessie | Polaris/REST | Unity |
Teradata OTF      |    Y     |  Y   |   ?    |      ?       |   Y   |
Trino             |    Y     |  Y   |   Y    |      Y       |   N   |
Snowflake         |    Y     |  N   |   N*   |      Y*      |   N   |
PySpark           |    Y     |  Y   |   Y    |      Y       |   Y   |

Y = confirmed supported
N = not supported
? = not documented, needs validation
* = via REST catalog protocol (Snowflake supports Iceberg REST catalogs)
```

### Pattern 2: Medallion Architecture (Bronze/Silver/Gold)

**What:** Data flows through three progressive quality layers, each with distinct guarantees.

**When to use:** For all batch ETL pipelines replacing DataStage.

**Layer definitions for this project:**

| Layer | Purpose | Schema | Quality | Retention | Typical Consumers |
|-------|---------|--------|---------|-----------|-------------------|
| **Bronze** | Raw landing zone. 1:1 copy of source data in Iceberg/Parquet | Source schema (preserve as-is), add ingestion metadata columns | No quality enforcement; append-only | Long (years) for audit/replay | Data engineers only |
| **Silver** | Cleansed, deduplicated, conformed | Standardized types, nullable rules, FK relationships | Quality checks enforced (nulls, ranges, referential integrity) | Medium-long | Data engineers, advanced analysts |
| **Gold** | Business-ready aggregations and dimensional models | Star schema / FSDM-aligned entities | Business rules applied, metrics pre-computed | Long (regulatory) | BI tools, AI layer, business users |

**Iceberg namespace convention:**
```
bronze.{source_name}.{table_name}    e.g. bronze.mainframe.customer_master
silver.{domain}.{entity_name}        e.g. silver.customer.customer_profile
gold.{business_area}.{metric_name}   e.g. gold.risk.daily_var_summary
```

**Trade-offs:**
- PRO: Clear data lineage path (source -> bronze -> silver -> gold)
- PRO: Bronze enables replay/reprocessing without re-extracting from source
- PRO: Silver is reusable across multiple Gold models
- CON: Three copies of data (mitigated by Iceberg's efficient Parquet columnar storage)
- CON: Latency increases with each layer (acceptable for batch-first strategy)

### Pattern 3: Write Engine Separation

**What:** Designate specific engines for write operations vs. read operations to avoid concurrency conflicts and optimize for each engine's strengths.

**When to use:** In multi-engine environments to prevent write conflicts and leverage engine strengths.

**Recommended ownership for this project:**

| Operation | Primary Engine | Rationale |
|-----------|---------------|-----------|
| Bronze writes (source extraction) | PySpark (ETL framework) | Best for batch extraction, mainframe connectors, schema inference |
| Silver writes (transformation) | PySpark (ETL framework) | Complex transformations, data quality checks |
| Gold writes (aggregation) | dbt on Trino or PySpark | dbt for SQL-based transforms; PySpark for complex logic |
| Interactive queries (read) | Trino | Sub-second interactive queries, federation |
| Complex analytics (read) | Teradata | Existing workloads, complex joins on large datasets |
| BI queries (read) | Trino (primary), Teradata (migration period) | BI tools connect via JDBC/ODBC to Trino |
| Ad-hoc external (read) | Snowflake | External consumers, Iceberg external tables |
| Table compaction | PySpark | Trino uses merge-on-read (defers compaction); Spark handles copy-on-write compaction efficiently |

**Trade-offs:**
- PRO: Eliminates write conflicts between engines
- PRO: Each engine does what it does best
- CON: Requires discipline and governance to enforce ownership
- CON: Compaction must be scheduled separately (PySpark) since Trino defers it

### Pattern 4: Hybrid Cloud Storage with Unified Catalog

**What:** Same Iceberg catalog serves tables stored on both AWS S3 (cloud) and MinIO (on-prem), with engines deployed in both environments.

**When to use:** When regulatory, latency, or data sovereignty requirements demand on-premises data copies.

**Topology:**

```
    CLOUD (AWS)                          ON-PREMISES
    ===========                          ============

    +----------+                         +----------+
    |  Trino   |---+                 +---|  Trino   |
    | (cloud)  |   |                 |   | (on-prem)|
    +----------+   |                 |   +----------+
                   |                 |
    +----------+   |   +---------+   |   +----------+
    |Snowflake |---+---|Iceberg  |---+---|Teradata  |
    |(compute) |   |   |Catalog  |   |   |(on-prem) |
    +----------+   |   |(shared) |   |   +----------+
                   |   +---------+   |
    +----------+   |       |         |   +----------+
    | PySpark  |---+       |         +---| PySpark  |
    | (cloud)  |           |             | (on-prem)|
    +----------+           |             +----------+
                           |
              +------------+-------------+
              |                          |
         +----+-----+            +------+------+
         |  AWS S3   |            |    MinIO    |
         |  (cloud   |            |  (on-prem   |
         |   storage)|            |   storage)  |
         +----------+            +-------------+
```

**Key decisions:**
- The Iceberg catalog must be network-accessible from both environments
- AWS Glue works natively for cloud but requires VPN/Direct Connect for on-prem access
- Polaris or Nessie (self-hosted) works in both environments natively
- Data does NOT replicate between S3 and MinIO -- tables are stored in one location
- Each table's storage location is declared at creation time

**Trade-offs:**
- PRO: Data sovereignty compliance (sensitive data stays on-prem)
- PRO: Reduced egress costs for on-prem-heavy workloads
- CON: Network latency for cross-environment catalog access
- CON: Operational complexity managing two storage environments
- CON: Disaster recovery planning becomes more complex

---

## Data Flow

### Primary Data Flow: Source to Consumer

```
[300+ Sources]
      |
      | Extract (Python ETL / PySpark)
      v
[BRONZE Layer]  ──────  Iceberg tables on S3/MinIO
      |                 Raw data, append-only
      | Transform (PySpark)
      | Cleanse, deduplicate, conform
      v
[SILVER Layer]  ──────  Iceberg tables on S3/MinIO
      |                 Standardized, quality-checked
      | Aggregate (dbt on Trino / PySpark)
      | Business rules, dimensional modeling
      v
[GOLD Layer]    ──────  Iceberg tables on S3/MinIO
      |                 Business-ready, FSDM-aligned
      |
      +─────────> [Teradata OTF] ──> Complex analytics (existing workloads)
      |
      +─────────> [Trino] ──> Interactive queries, BI semantic layer
      |                        |
      |                        +──> [dbt Semantic Layer] ──> Tableau, Power BI
      |                        |
      |                        +──> [AI Semantic Layer] ──> NL-to-SQL API
      |
      +─────────> [Snowflake] ──> External consumers (Iceberg external tables)
```

### Teradata OTF + Trino Coexistence Flow

This is the critical coexistence pattern. Both engines operate on the same Iceberg tables:

```
                    +------------------+
                    | Iceberg Catalog  |
                    | (AWS Glue or     |
                    |  REST catalog)   |
                    +--------+---------+
                             |
                    metadata | pointers
                             |
              +--------------+--------------+
              |                             |
     +--------+--------+          +--------+--------+
     |   Teradata OTF   |          |     Trino       |
     |                   |          |                 |
     | - Reads Iceberg   |          | - Reads Iceberg |
     |   via NOS/OTF     |          |   via connector |
     | - Writes Iceberg  |          | - Writes Iceberg|
     |   via OTF         |          |   (merge-on-    |
     | - Uses AMP        |          |    read)        |
     |   parallelism     |          | - Uses MPP      |
     | - Catalog: Glue   |          |   workers       |
     |   or HMS          |          | - Catalog: any  |
     +--------+----------+          +--------+--------+
              |                              |
              |     S3 API (read/write)      |
              |                              |
              +----------+---+---+-----------+
                         |   |   |
                    +----+---+---+----+
                    |    Parquet       |
                    |    Data Files    |
                    |    on S3/MinIO   |
                    +-----------------+
```

**How coexistence works in practice:**

1. **Shared catalog is mandatory.** Both Teradata and Trino must point to the same catalog so they see the same table metadata. AWS Glue is the safest common denominator (both support it natively). If using Polaris/Nessie for Trino, a Glue-sync bridge may be needed for Teradata.

2. **Snapshot isolation protects readers.** When Teradata reads a table, it pins to a snapshot. A concurrent Trino write creates a new snapshot without affecting Teradata's read.

3. **Write ownership prevents conflicts.** Designate one engine as the writer for each table (typically PySpark for ETL writes). Both Teradata and Trino should primarily be readers of the medallion layers, not writers. If both must write, they write to different tables.

4. **Compaction is a separate concern.** Trino writes use merge-on-read (positional delete files). PySpark should run scheduled compaction (rewrite_data_files / rewrite_manifests) to maintain query performance for all engines.

5. **Schema evolution flows from catalog.** Schema changes made by any engine are visible to all engines through the catalog. Use Iceberg's schema evolution (add column, rename, widen type) to avoid breaking consumers.

**Practical coexistence timeline:**
- **Phase 1:** Teradata reads Iceberg tables written by PySpark. Trino reads same tables. No engine conflicts.
- **Phase 2:** Both engines read/write, with table-level ownership rules. PySpark handles compaction.
- **Phase 3:** Teradata workloads progressively shift to Trino. Teradata becomes a read-only consumer.

### Lineage Flow

```
[Source] ──extract──> [Bronze] ──transform──> [Silver] ──aggregate──> [Gold]
   |                    |                       |                      |
   +----OpenLineage-----+-------OpenLineage-----+------OpenLineage-----+
                                    |
                              +-----v------+
                              |  Marquez   |
                              | (lineage   |
                              |  store)    |
                              +-----+------+
                                    |
                              +-----v------+
                              | Governance |
                              | Dashboard  |
                              | (audit +   |
                              |  compliance|
                              |  reports)  |
                              +------------+
```

---

## Catalog Strategy (Critical Decision)

The catalog is the single most critical architectural decision because it determines which engines can participate and how governance is enforced.

### Recommendation: Dual-Catalog with REST Bridge

Given Teradata's limited catalog support (Glue, HMS, Unity) vs. Trino and Snowflake's broader support (including REST catalogs), the recommended approach is:

**Option A (Simplest -- AWS-primary deployments): AWS Glue as primary catalog**

| Criterion | Assessment |
|-----------|------------|
| Teradata support | Native (confirmed) |
| Trino support | Native (confirmed) |
| Snowflake support | Native (confirmed) |
| PySpark support | Native (confirmed) |
| On-prem access | Requires VPN/Direct Connect to AWS |
| Branching/versioning | Not supported |
| Multi-table transactions | Not supported |
| Cost | Pay-per-request (cheap at low scale, scales with usage) |
| Operational burden | None (serverless) |
| Governance | Via Lake Formation (IAM-based) |

**Best for:** Cloud-primary deployments where on-prem is secondary. Lowest risk for Phase 1.

**Option B (Most capable -- hybrid deployments): Polaris (REST) + Glue sync for Teradata**

| Criterion | Assessment |
|-----------|------------|
| Teradata support | NOT native -- requires Glue/HMS sync or REST catalog adapter (UNVERIFIED) |
| Trino support | Native via REST catalog |
| Snowflake support | Native via REST catalog |
| PySpark support | Native via REST catalog |
| On-prem access | Self-hosted, works anywhere |
| Branching/versioning | Not built-in (add Nessie for this) |
| Multi-table transactions | Not built-in |
| Cost | Self-hosted infrastructure |
| Operational burden | Medium (requires PostgreSQL backend, monitoring) |
| Governance | OIDC/OPA integration for fine-grained access |

**Best for:** Hybrid deployments needing vendor-neutral, self-hosted catalog. Requires validation of Teradata REST catalog support.

**Option C (Most advanced -- if Teradata supports REST): Nessie as primary catalog**

| Criterion | Assessment |
|-----------|------------|
| Teradata support | NOT documented -- needs validation |
| Trino support | Native (both Nessie API and REST) |
| Snowflake support | Via REST catalog protocol |
| PySpark support | Native |
| On-prem access | Self-hosted, works anywhere |
| Branching/versioning | Core feature (Git-like branches, tags) |
| Multi-table transactions | Supported |
| Cost | Self-hosted infrastructure |
| Operational burden | Medium (requires backing store) |
| Governance | Branch-level access control |

**Best for:** Teams needing branching (dev/test/prod data isolation) and multi-table transactions. Highest capability but highest risk due to Teradata compatibility uncertainty.

### Recommended Strategy

**Start with AWS Glue (Option A) for Phase 1.** This is the only catalog confirmed to work with all four engines (Teradata, Trino, Snowflake, PySpark). Accept the limitations (no branching, no multi-table transactions, requires network path from on-prem to AWS).

**Validate Teradata REST catalog support in Phase 1.** If Teradata supports the Iceberg REST catalog protocol, Option B (Polaris) or Option C (Nessie) becomes viable for Phase 2+, enabling self-hosted hybrid catalog with advanced features.

**For on-prem MinIO workloads during Phase 1:** Use Glue via VPN/Direct Connect. If network latency is unacceptable, deploy a local HMS as a secondary catalog for on-prem tables only, with a sync process to keep Glue as the authoritative source.

---

## Scaling Considerations

| Concern | Current (Teradata-era) | At Lakehouse Phase 1 | At Full Lakehouse |
|---------|------------------------|-----------------------|-------------------|
| **Data volume** | 1.5 PB in Teradata | ~200 TB in Iceberg (pilot domains) | 1.5 PB+ in Iceberg |
| **Query concurrency** | Teradata handles all queries | Teradata + Trino split workloads | Trino primary, Teradata reduced |
| **ETL throughput** | DataStage (limited parallelism) | PySpark (horizontal scaling) | PySpark at full scale (300+ jobs) |
| **Catalog pressure** | N/A | Low (pilot tables) | High (thousands of tables, frequent commits) |
| **Storage cost** | Teradata storage pricing | S3/MinIO (10-50x cheaper per TB) | S3/MinIO at petabyte scale |

### Scaling Priorities

1. **First bottleneck: Catalog throughput.** At thousands of tables with frequent ETL commits, the catalog becomes a bottleneck. AWS Glue handles this well (serverless scaling). HMS requires careful capacity planning. Nessie/Polaris need horizontal scaling configuration.

2. **Second bottleneck: Trino cluster sizing.** As BI workloads migrate from Teradata to Trino, the Trino cluster needs to scale. Use autoscaling workers and separate clusters for ETL-write vs. interactive-read workloads.

3. **Third bottleneck: Small file problem.** Frequent writes to Iceberg tables create many small Parquet files. Without scheduled compaction, query performance degrades for all engines. PySpark compaction jobs must be part of the architecture from day one.

---

## Anti-Patterns

### Anti-Pattern 1: Letting Multiple Engines Write the Same Table

**What people do:** Both PySpark and Trino write to the same Iceberg table concurrently.
**Why it is wrong:** Optimistic concurrency causes retry storms under load. Different engines use different write strategies (Trino: merge-on-read; Spark: copy-on-write by default), leading to inconsistent file layouts and degraded read performance.
**Do this instead:** Designate a single write-owner per table. Use PySpark for ETL writes. Use Trino for read-heavy interactive queries. If Trino must write (e.g., Gold layer via dbt), ensure no other engine writes to those same tables.

### Anti-Pattern 2: Skipping Bronze and Loading Directly to Silver

**What people do:** Transform data during extraction and write directly to Silver layer to "save time."
**Why it is wrong:** Loses the ability to replay/reprocess from raw data when requirements change. In financial services, regulatory auditors may require access to raw source data. When a Silver transformation has a bug, there is no Bronze to replay from.
**Do this instead:** Always land raw data in Bronze first. Bronze writes should be fast (minimal transformation -- just format conversion and metadata addition). Accept the storage cost; Parquet on S3/MinIO is cheap.

### Anti-Pattern 3: Using Hive Metastore for New Deployments

**What people do:** Deploy HMS because "it's what we know" from Hadoop days.
**Why it is wrong:** HMS is a single-table-at-a-time catalog with no branching, no multi-table transactions, requires infrastructure management (MySQL/PostgreSQL backing store, Thrift server), and is increasingly legacy. AWS Glue is serverless and strictly better for AWS deployments.
**Do this instead:** Use AWS Glue for cloud-primary, Polaris for self-hosted/hybrid. Only use HMS if an existing, well-managed HMS deployment already exists and engines require it.

### Anti-Pattern 4: Building NL-to-SQL Directly Against Raw Database Schemas

**What people do:** Point an LLM at the Gold layer schema and ask it to generate SQL.
**Why it is wrong:** Enterprise schemas have hundreds of tables with cryptic names, complex joins, and business logic embedded in column names that LLMs cannot infer. Accuracy drops to 50-70% without semantic context.
**Do this instead:** Build a semantic layer (BI layer with metric definitions) first. Point the AI semantic layer at the semantic model, not the raw schema. The LLM generates queries against simplified, well-documented entities. The semantic layer engine handles the translation to physical SQL.

### Anti-Pattern 5: Replicating Data Between S3 and MinIO

**What people do:** Copy/sync tables between cloud S3 and on-prem MinIO to "make data available everywhere."
**Why it is wrong:** Creates the exact same data duplication problem the lakehouse architecture is designed to eliminate. Introduces consistency issues, doubles storage cost, and requires complex sync logic.
**Do this instead:** Each table lives in one storage location (S3 OR MinIO). Engines in both environments access tables through the shared catalog. Use network connectivity (VPN/Direct Connect) for cross-environment access. Only replicate for disaster recovery, with clear ownership semantics.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Mainframe (source)** | COBOL copybook → Python parser → PySpark extract | Primary source system. Connectivity via MQ, Connect:Direct, or SFTP. COBOL copybook libraries (e.g., `cobrix` for Spark) parse EBCDIC formats. |
| **AWS S3** | S3 API (native) | Standard `s3a://` or `s3://` paths in all engines. IAM role-based access. |
| **MinIO** | S3 API (compatible) | Configure endpoint URL override in each engine. TLS required for production. Same IAM-style access keys. |
| **Tableau** | JDBC to Trino (or Teradata during migration) | Trino JDBC driver. Consider Trino connection pooling for BI query patterns. |
| **Power BI** | ODBC to Trino, or dbt Semantic Layer integration | dbt Semantic Layer provides native Power BI connector for governed metrics. |
| **GitHub** | Git for source control, GitHub Actions for CI/CD | All ETL code, dbt models, Trino configs, infrastructure as code version controlled. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **ETL Framework <-> Iceberg Catalog** | Iceberg client library (PySpark) | PySpark embeds Iceberg runtime. Catalog connection via catalog properties in SparkSession config. |
| **Trino <-> Iceberg Catalog** | Iceberg connector (catalog properties file) | `/etc/trino/conf/catalog/iceberg.properties` defines catalog type, URI, credentials. |
| **Teradata <-> Iceberg Catalog** | OTF bridge (Teradata-managed) | Teradata handles catalog interaction internally. Configure via `CREATE FOREIGN TABLE` or OTF SQL extensions. |
| **Snowflake <-> Iceberg** | External volume + catalog integration | External volume defines S3 credentials. Catalog integration defines Glue/REST endpoint. |
| **BI Semantic Layer <-> Trino** | JDBC connection | dbt connects to Trino via `dbt-trino` adapter. Semantic Layer serves metrics via its own API. |
| **AI Semantic Layer <-> BI Semantic Layer** | Metadata API | AI layer reads metric definitions, entity relationships, and business glossary from BI semantic layer to provide context for NL-to-SQL. |
| **OpenLineage <-> ETL/Trino** | OpenLineage API (HTTP events) | PySpark and Airflow emit OpenLineage events automatically via integrations. Marquez collects and stores. |

---

## Suggested Build Order

Based on component dependencies, risk, and value delivery:

```
Phase 1: Foundation                     Phase 2: Core Platform
(Months 1-3)                            (Months 3-6)
====================                    ====================
[S3/MinIO storage]                      [Silver layer ETL]
       |                                       |
[AWS Glue catalog]                      [Gold layer (dbt on Trino)]
       |                                       |
[Iceberg table format]                  [BI Semantic Layer]
       |                                       |
[PySpark ETL: Bronze]                   [Tableau/Power BI migration]
       |                                       |
[Trino cluster (read)]                  [Snowflake Iceberg ext tables]
       |                                       |
[Teradata OTF (read)]                  [OpenLineage integration]
       |
[CI/CD pipeline (GitHub)]

Phase 3: Advanced                       Phase 4: Optimization
(Months 6-9)                            (Months 9-12)
====================                    ====================
[AI Semantic Layer]                     [Teradata workload migration]
       |                                       |
[NL-to-SQL API]                         [Catalog upgrade (Polaris?)]
       |                                       |
[Advanced governance]                   [On-prem MinIO expansion]
       |                                       |
[Mainframe source expansion]            [Performance tuning]
       |                                       |
[Lineage dashboards]                    [Full DataStage retirement]
```

**Build order rationale:**

1. **Storage + Catalog + Table Format first** because everything depends on them. No engine can operate without storage and metadata.
2. **Bronze ETL before engines** because engines have nothing to query without data.
3. **Trino before Snowflake** because Trino is the primary open query engine. Snowflake is additive.
4. **Teradata OTF reads early** to prove coexistence and de-risk the approach. Existing Teradata workloads continue while validating Iceberg.
5. **Silver/Gold before BI** because BI tools need business-ready data, not raw Bronze.
6. **BI semantic layer before AI semantic layer** because the AI layer depends on BI metric definitions for accuracy.
7. **Governance throughout** but formal lineage dashboards can follow the initial ETL build.

---

## Sources

### Teradata OTF
- [Teradata Open Table Formats](https://www.teradata.com/platform/open-table-formats) - Official OTF capabilities page (HIGH confidence)
- [Teradata Embraces Open Table Formats (press release)](https://www.teradata.com/press-releases/2024/teradata-embraces-open-table-formats-iceberg) - Confirmed catalogs: Glue, HMS, Unity (HIGH confidence)
- [Teradata OTF Introduction Demos](https://github.com/Teradata/OTF_Introduction_Demos) - GitHub repo with working examples (MEDIUM confidence)

### Trino + Iceberg
- [Trino Iceberg Connector Documentation](https://trino.io/docs/current/connector/iceberg.html) - Official docs, catalog types, operations (HIGH confidence)
- [Working with Iceberg tables by using Trino - AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/apache-iceberg-on-aws/iceberg-trino.html) - AWS production patterns (HIGH confidence)
- [Apache Iceberg and Trino: Powering Data Lakehouse Architecture](https://www.opensourceforu.com/2026/01/apache-iceberg-and-trino-powering-data-lakehouse-architecture/) - Architecture patterns (MEDIUM confidence)

### Snowflake + Iceberg
- [Snowflake Iceberg Tables Documentation](https://docs.snowflake.com/en/user-guide/tables-iceberg) - Official, externally managed tables and REST catalog support (HIGH confidence)
- [Snowflake Write Support for Externally Managed Iceberg Tables (GA)](https://docs.snowflake.com/en/release-notes/2025/other/2025-10-17-iceberg-external-writes-cld-ga) - Full DML on external Iceberg as of Oct 2025 (HIGH confidence)

### Iceberg Catalogs
- [Iceberg Catalogs 2025: Emerging Metadata Solutions](https://www.e6data.com/blog/iceberg-catalogs-2025-emerging-catalogs-modern-metadata-management) - Catalog comparison with adoption data (MEDIUM confidence)
- [2025 State of the Apache Iceberg Ecosystem](https://datalakehousehub.com/blog/2026-02-state-of-the-apache-iceberg-ecosystem/) - Survey: Glue 39.3%, Nessie 28.6%, Polaris 21.4% adoption (MEDIUM confidence)
- [Nessie + Iceberg + Trino](https://projectnessie.org/iceberg/trino/) - Official Nessie-Trino configuration (HIGH confidence)
- [Apache Polaris](https://polaris.apache.org/) - Official Polaris project page, REST catalog (HIGH confidence)

### Hybrid Cloud / MinIO
- [The Definitive Guide to Lakehouse Architecture with Iceberg and MinIO](https://blog.min.io/lakehouse-architecture-iceberg-minio/) - MinIO + Iceberg architecture (MEDIUM confidence)
- [Hybrid Iceberg Lakehouse Storage Solutions: MinIO](https://www.dremio.com/blog/hybrid-lakehouse-storage-solutions-minio/) - Hybrid deployment patterns (MEDIUM confidence)

### Semantic Layer
- [The Semantic Lakehouse for AI/BI](https://www.atscale.com/blog/semantic-lakehouse-for-ai-bi/) - BI + AI semantic layer architecture (MEDIUM confidence)
- [dbt Semantic Layer + Trino + Power BI](https://docs.getdbt.com/docs/cloud-integrations/semantic-layer/power-bi) - Official dbt docs (HIGH confidence)
- [NL2SQL System Design Guide 2025](https://medium.com/@adityamahakali/nl2sql-system-design-guide-2025-c517a00ae34d) - NL-to-SQL architecture patterns (LOW confidence)

### Governance
- [OpenLineage](https://github.com/OpenLineage/OpenLineage) - Open standard for lineage (HIGH confidence)
- [BCBS 239 Data Lineage Compliance](https://www.ovaledge.com/blog/bcbs-239-data-lineage) - Financial services regulatory requirements (MEDIUM confidence)
- [Regulatory Data Lineage Tracking](https://atlan.com/regulatory-data-lineage-tracking/) - Compliance patterns (MEDIUM confidence)

### Medallion Architecture
- [Medallion Architecture - Databricks](https://www.databricks.com/glossary/medallion-architecture) - Reference definition (HIGH confidence)
- [Handling Schema Drift in Medallion Architecture with Iceberg](https://nexla.com/blog/handling-schema-drift-in-medallion-architecture-with-apache-iceberg/) - Iceberg-specific medallion patterns (MEDIUM confidence)

---
*Architecture research for: Financial Services Lakehouse Transformation*
*Researched: 2026-03-13*
