# Lakehouse Architecture Transformation

A data architecture transformation converting a legacy Teradata/DataStage data warehouse into a modern lakehouse built on **Apache Iceberg** and **Trino**. Designed for a financial services organization with 1.5 PB of data across 300+ sources, supporting both cloud (AWS S3) and on-premises (MinIO) consumers with BI and AI semantic layers.

## The Problem

| Pain Point | Detail |
|-----------|--------|
| **Data duplication** | Same data copied across Teradata, Cloudera, and Snowflake with no single source of truth |
| **Cost & complexity** | Four platforms (Teradata, DataStage, Cloudera, Snowflake) to maintain |
| **Modernization gap** | Current stack can't serve AI/ML workloads or modern query patterns |

## Target Architecture

Per ADR-011, the access and semantic layer is delivered in two phases. Phase 1 ships Snowflake Cortex now; Phase 2 adds Fabric as a parallel BI/AI surface when the Power BI migration completes.

```
     ┌──────────────────────────────────────────────────────────────┐
     │                    Consumption Layer                         │
     │  RBC Assist · Borealis · Power BI · Tableau                  │
     └───────────────────────────┬──────────────────────────────────┘
                                  │
     ┌───────────────────────────┴──────────────────────────────────┐
     │              FastAPI Trust Boundary (router)                 │
     │  OBO auth · guardrails · PII masking · audit logging         │
     │  Routes NL queries to Snowflake Cortex (P1) or Fabric (P2)   │
     └───────┬──────────────────────────────────────┬───────────────┘
             │                                      │
     ┌───────┴────────────┐                ┌───────┴─────────────┐
     │ Snowflake Cortex   │                │ Fabric Data Agent   │
     │ Analyst + Agents   │                │ (Phase 2)           │
     │ Semantic Views     │                │ Import Semantic     │
     │ (CREATE SEMANTIC   │                │ Model · NL2DAX      │
     │  VIEW DDL)         │                │                     │
     └───────┬────────────┘                └───────┬─────────────┘
             │  Iceberg external volumes           │  Python ETL copy
             │  (zero-copy)                        │  Gold → Delta in OneLake
             │                                      │
             └──────────────┬───────────────────────┘
                            │
         ┌──────────────────┴──────────────────────┐
         │     Gold — Apache Iceberg V2            │
         │     Nessie Catalog (REST)               │
         │     FSDM-conformed, Ranger-governed     │
         └──────────────────┬──────────────────────┘
                            │  Bronze → Silver → Gold (Python ETL)
         ┌──────────────────┴──────────────────────┐
         │          Source Systems                 │
         │   Teradata · Mainframe · APIs           │
         └─────────────────────────────────────────┘
```

**Core principle:** Gold Iceberg V2 is the single source of truth. Written once by the on-prem medallion pipeline; read by multiple engines via external volumes (Snowflake, zero-copy) or Delta copy (Fabric, Phase 2). The FastAPI trust boundary is the single entry point for all AI agent queries — no agent or consumer app queries backends directly.

The semantic model itself is defined once in GitHub as YAML and translated by CI/CD to Snowflake semantic views (Phase 1) and Fabric Import semantic models (Phase 2). One definition, two deployments.

See [ADR-011](docs/adr/011-snowflake-cortex-semantic-layer.md) for the full phased approach and [ADR-010](docs/adr/010-fabric-import-semantic-layer.md) for the prior Fabric-only decision it supersedes.

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Table Format | Apache Iceberg | V2 spec |
| Catalog | Nessie | 0.107.4 |
| Query Engine | Trino | 479 |
| Object Storage | AWS S3 / MinIO | latest |
| ETL | Python (PySpark + PyIceberg) | 3.11+ |
| Orchestration | Apache Airflow | 3.1.x |
| Lineage | OpenLineage + Marquez | — |
| Data Quality | Soda Core (SodaCL) | 3.5+ |
| Governance | Apache Ranger | 2.8.0 |
| Data Catalog | OpenMetadata | 1.6.0 |
| Semantic Layer (NL-to-SQL) | Cube | 0.36.0 |
| Access & Semantic Layer — Phase 1 | Snowflake Cortex Analyst + Semantic Views | GA |
| BI/AI Semantic Layer — Phase 2 | Microsoft Fabric (Import mode) | — |
| AI Chatbot Integration — Phase 1 | Snowflake Cortex Analyst REST API | GA |
| AI Chatbot Integration — Phase 2 | Fabric Data Agent (on-behalf-of auth) | — |
| Trust Boundary | FastAPI (OBO, guardrails, audit) | — |
| AI/NL-to-SQL | Claude on AWS Bedrock | Sonnet |
| Monitoring | Grafana + Prometheus | — |
| IaC | Terraform | — |
| CI/CD | GitHub Actions | — |

## Repository Structure

```
lakehouse/
├── etl/                        # Python ETL framework
│   ├── src/
│   │   ├── pipelines/          # Medallion layer pipelines (Bronze/Silver/Gold)
│   │   │   ├── base.py         # BasePipeline ABC -- all pipelines extend this
│   │   │   ├── bronze/         # Raw ingestion (trades, positions, mainframe)
│   │   │   ├── silver/         # Cleaned & validated
│   │   │   └── gold/           # Business-level aggregates (trading metrics, risk)
│   │   ├── ingestion/          # Raw zone file management & ingestion manifest
│   │   │   ├── raw_zone.py     # RawZoneManager -- SFTP drop → S3/MinIO raw zone
│   │   │   └── manifest.py     # IngestionManifest -- LANDED/PROCESSING/PROCESSED/FAILED
│   │   ├── governance/         # Ranger policies, classification, audit, freshness
│   │   ├── quality/            # Soda Core scanner, reconciliation, SodaCL checks
│   │   ├── semantic/           # Cube metric context, NL-to-SQL, evaluation
│   │   ├── lineage/            # OpenLineage configuration
│   │   ├── inventory/          # Job inventory & catalog
│   │   ├── iceberg_utils/      # Catalog helpers, maintenance
│   │   └── config/             # Shared settings
│   ├── dags/                   # Airflow DAGs (Bronze/Silver/Gold + governance)
│   ├── tests/
│   │   ├── unit/               # 480+ unit tests
│   │   └── integration/        # Service-dependent integration tests
│   └── pyproject.toml          # Project config (hatchling, ruff, pytest)
│
├── semantic/                   # Cube semantic layer
│   └── model/
│       ├── cubes/              # YAML metric definitions (trading, risk exposure)
│       └── views/              # Cube views for BI consumption
│
├── infra/                      # Infrastructure
│   ├── docker/                 # Service configs (Trino, Airflow, Grafana, Ranger, etc.)
│   └── terraform/              # IaC modules & environments (dev/staging/prod)
│       ├── modules/            # nessie, trino, s3, minio, networking
│       └── environments/       # dev, staging, prod variable sets
│
├── ci/                         # CI/CD source of truth
│   └── .github/workflows/      # ci.yml, deploy-{dev,staging,prod}.yml, infra.yml
│
├── docs/                       # Project documentation
│   ├── adr/                    # Architecture Decision Records
│   ├── swot/                   # SWOT analyses for leadership
│   ├── benchmarks/             # Performance benchmark templates
│   └── etl-patterns.md         # ETL standards & onboarding guide
│
├── dbt/                        # dbt project (placeholder)
├── docker-compose.yml          # Full local dev environment
├── docker-compose.test.yml     # Test-focused compose (lighter)
└── .planning/                  # GSD project planning artifacts
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Git

### 1. Clone and set up

```bash
git clone https://github.com/chilakos/lakehouse.git
cd lakehouse
```

### 2. Start the local dev environment

```bash
docker compose up -d
```

This starts: PostgreSQL, MinIO, Nessie, Trino, Airflow, Marquez, Grafana, Prometheus, OpenMetadata, Cube, and Ranger.

| Service | URL |
|---------|-----|
| Trino | http://localhost:8080 |
| MinIO Console | http://localhost:9001 |
| Nessie API | http://localhost:19120 |
| Airflow UI | http://localhost:8081 |
| Marquez UI | http://localhost:3000 |
| Grafana | http://localhost:3001 |
| Cube SQL API | localhost:15432 (Postgres wire) |

### 3. Install Python dependencies

```bash
cd etl
pip install -e ".[dev]"
```

### 4. Run tests

```bash
# Unit tests (no services needed)
pytest tests/unit -m unit

# Integration tests (requires Docker services running)
pytest tests/integration -m integration
```

## ETL Pipeline Architecture

The ETL framework follows a **medallion architecture** with three layers:

| Layer | Purpose | Example |
|-------|---------|---------|
| **Bronze** | Raw ingestion, schema validation, metadata tagging | `trades_ingest.py`, `mainframe_ingest.py` |
| **Silver** | Cleaning, deduplication, type coercion | `trades_clean.py`, `positions_clean.py` |
| **Gold** | Business aggregates, cross-source joins | `trading_metrics.py`, `risk_exposure.py` |

All pipelines extend `BasePipeline` (see [`etl/src/pipelines/base.py`](etl/src/pipelines/base.py)) and follow the patterns documented in [`docs/etl-patterns.md`](docs/etl-patterns.md).

### Raw Zone & Ingestion

Before mainframe data reaches the Bronze Iceberg tables, original binary files are preserved in a
**raw zone** on S3/MinIO for 7-year regulatory retention:

```
SFTP / Connect:Direct drop zone  (local staging)
         │
         │  RawZoneManager.upload_to_raw_zone()
         ▼
s3://lakehouse-raw/raw/mainframe/{source_system}/{YYYY-MM-DD}/{filename}
         │
         │  IngestionManifest.register_file()  →  status: LANDED
         │
         │  MainframeBronzePipeline.execute()  →  status: PROCESSED
         ▼
lakehouse.bronze.{table}  (Apache Iceberg via Cobrix)
```

Key components in `etl/src/ingestion/`:

| Module | Class | Purpose |
|--------|-------|---------|
| `raw_zone.py` | `RawZoneManager` | Upload files to S3/MinIO, compute MD5, list raw files |
| `raw_zone.py` | `RawZoneConfig` | Bucket, prefix, region, MinIO endpoint override |
| `manifest.py` | `IngestionManifest` | JSON Lines lifecycle tracking per source/date |
| `manifest.py` | `ManifestEntry` | Single file record: LANDED → PROCESSING → PROCESSED/FAILED |

See [`docs/mainframe-ingestion.md`](docs/mainframe-ingestion.md) for the full guide.

## Governance & Security

- **Apache Ranger** -- Column-level masking, row-level filtering, tag-driven classification
- **OpenMetadata** -- Data catalog, business glossary, freshness tracking
- **BCBS 239 Compliance** -- End-to-end lineage dashboards in Grafana
- **Cross-engine Audit Trail** -- Unified audit records across Trino, Teradata, and Snowflake

## Semantic & AI Layer

Per [ADR-011](docs/adr/011-snowflake-cortex-semantic-layer.md) (supersedes ADR-010):

- **Phase 1 — Snowflake Cortex** -- Cortex Analyst serves NL-to-SQL over Snowflake semantic views, reading Gold Iceberg V2 via external volumes (zero-copy). Cortex Agents orchestrate across Analyst (structured) and Search (unstructured). Configurable orchestration model including Claude Sonnet.
- **Phase 2 — Microsoft Fabric (Import mode)** -- Adds Fabric as a parallel BI/AI surface for Power BI and Fabric Data Agent consumption when OBIEE → Power BI migration completes. Gold is copied to Delta in OneLake via Python ETL.
- **FastAPI Trust Boundary** -- Single entry point for all AI agent queries. Handles OBO auth, PII masking, prompt injection guardrails, audit logging, and routes to Snowflake Cortex or Fabric Data Agent.
- **Semantic model as code** -- Defined once in GitHub YAML (`docs/architecture/semantic-model-template.yaml`), translated by CI/CD to Snowflake `CREATE SEMANTIC VIEW` DDL (Phase 1) and Fabric Import semantic model TMDL (Phase 2).
- **Cube** -- YAML-defined metrics served via SQL API (Postgres wire protocol); legacy NL-to-SQL path retained for specific use cases (ADR-006). Retiring as Cortex and Fabric Data Agent take over primary NL workloads.
- **Evaluation Framework** -- Golden datasets (trading + risk exposure) with execution accuracy scoring against both Snowflake Cortex and Fabric Data Agent output.

## Key Documentation

| Document | Description |
|----------|-------------|
| [`docs/adr/001-teradata-otf-nessie-feasibility.md`](docs/adr/001-teradata-otf-nessie-feasibility.md) | Teradata OTF + Nessie integration decision |
| [`docs/swot/nessie-catalog-swot.md`](docs/swot/nessie-catalog-swot.md) | Nessie catalog SWOT analysis for leadership |
| [`docs/etl-patterns.md`](docs/etl-patterns.md) | ETL standards & team onboarding guide |
| [`docs/mainframe-ingestion.md`](docs/mainframe-ingestion.md) | Mainframe ingestion: raw zone, manifest, SFTP transfer |
| [`docs/benchmarks/benchmark_template.md`](docs/benchmarks/benchmark_template.md) | Query performance benchmark template |
| [`ci/README.md`](ci/README.md) | CI/CD workflow conventions |

## CI/CD

Workflows are authored in `ci/.github/workflows/` and copied to `.github/workflows/` (see [`ci/README.md`](ci/README.md)).

```
feature branch ──> PR to dev ──> merge to dev (auto-deploy)
                                       │
                                 PR to staging ──> merge (deploy + approval)
                                                        │
                                                  PR to main ──> merge (deploy + smoke tests)
```

## Environment Promotion

| Environment | Trigger | Notes |
|-------------|---------|-------|
| dev | Push to `dev` branch | Auto-deploy |
| staging | Push to `staging` branch | Requires approval |
| prod | Push to `main` branch | Approval + smoke tests |

## Project Status

All four phases of the v1.0 milestone are complete:

| Phase | Description | Status |
|-------|-------------|--------|
| 1. Foundation | Mono-repo, Docker, Terraform, multi-engine validation | Complete |
| 2. ETL Migration | Python pipelines, Airflow, data quality, lineage | Complete |
| 3. Governance | Ranger security, OpenMetadata, BCBS 239 dashboards | Complete |
| 4. Semantic Layers | Cube metrics, NL-to-SQL, cross-tool validation | Complete |

### Open Items

- Teradata OTF REST catalog support -- unconfirmed, ADR drafted with fallback strategy
- MinIO replacement decision -- RustFS vs Ceph vs AIStor commercial
- Live integration tests pending: Teradata instance, Snowflake account, LDAP/AD server

## License

Proprietary. Internal use only.
