# Lakehouse Architecture Transformation

A data architecture transformation converting a legacy Teradata/DataStage data warehouse into a modern lakehouse built on **Apache Iceberg** and **Trino**. Designed for a financial services organization with 1.5 PB of data across 300+ sources, supporting both cloud (AWS S3) and on-premises (MinIO) consumers with BI and semantic layers.

> This README is intentionally implementation-focused: it describes what is present in the repository today. Some documents under [`docs/`](docs/) explore future-state options that are not fully represented in the current source tree.

## The Problem

| Pain Point | Detail |
|-----------|--------|
| **Data duplication** | Same data copied across Teradata, Cloudera, and Snowflake with no single source of truth |
| **Cost & complexity** | Four platforms (Teradata, DataStage, Cloudera, Snowflake) to maintain |
| **Modernization gap** | Current stack can't serve AI/ML workloads or modern query patterns |

## Current Repository Architecture

```
     ┌──────────────────────────────────────────────────────────────┐
     │                Consumers & Validation Paths                 │
     │        Trino SQL · Cube SQL API · Airflow DAGs             │
     │             Unit tests · Integration tests                 │
     └───────────────────────────┬──────────────────────────────────┘
                                  │
     ┌───────────────────────────┴──────────────────────────────────┐
     │              Governance & Semantic Components                │
     │ Ranger policies · OpenMetadata configs · Soda quality        │
     │ Lineage helpers · Cube YAML models · NL-to-SQL utilities     │
     └───────────────────────────┬──────────────────────────────────┘
                                  │
     ┌───────────────────────────┴──────────────────────────────────┐
     │                    Python ETL Application                    │
     │ Bronze ingestion · Silver cleaning · Gold aggregates         │
     │ Raw-zone retention · Manifest tracking · Synthetic data      │
     └───────────────────────────┬──────────────────────────────────┘
                                  │
                     ┌────────────┴────────────┐
                     │ Apache Iceberg + Nessie │
                     │   lakehouse catalog     │
                     └────────────┬────────────┘
                                  │
                     ┌────────────┴────────────┐
                     │     AWS S3 / MinIO      │
                     │      object storage     │
                     └─────────────────────────┘
```

**Current implementation focus:** the source tree centers on Nessie-backed Iceberg tables, Python ETL pipelines, Airflow orchestration, Ranger/OpenMetadata governance helpers, Cube semantic models, and Terraform/Docker assets for local and environment deployment. Architectural explorations for additional consumers and governance products are documented under [`docs/`](docs/), but are not all implemented as runnable source code in this repository.

## Repository Tech Stack

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
| Monitoring | Grafana + Prometheus | — |
| IaC | Terraform | — |
| CI/CD | GitHub Actions | — |

## What Exists in the Current Source Code

| Area | Present in repo today | Evidence |
|------|------------------------|----------|
| ETL framework | Base pipeline contract, incremental loading support, Bronze/Silver/Gold pipeline modules | [`etl/src/pipelines/`](etl/src/pipelines/) |
| Ingestion controls | Raw-zone upload/retention helpers and manifest lifecycle tracking | [`etl/src/ingestion/raw_zone.py`](etl/src/ingestion/raw_zone.py), [`etl/src/ingestion/manifest.py`](etl/src/ingestion/manifest.py) |
| Governance utilities | Ranger policy builders, classification, freshness, audit, anomaly detection | [`etl/src/governance/`](etl/src/governance/) |
| Semantic assets | Cube YAML cubes/views plus cross-tool validation, metric context, prompt building, and evaluation helpers | [`semantic/model/`](semantic/model/), [`etl/src/semantic/`](etl/src/semantic/) |
| Orchestration | Airflow DAGs for Bronze, Gold, quality, maintenance, and governance flows | [`etl/dags/`](etl/dags/) |
| Infrastructure | Docker service definitions and Terraform modules for networking, S3, MinIO, Nessie, and Trino | [`infra/docker/`](infra/docker/), [`infra/terraform/`](infra/terraform/) |
| Test coverage | Unit and integration test suites for ETL, governance, semantic, and infra expectations | [`etl/tests/`](etl/tests/) |
| Placeholder / design-led areas | `dbt/` remains a placeholder; some HTML docs capture evaluated or future-state options | [`dbt/`](dbt/), [`docs/`](docs/) |

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
│   │   ├── unit/               # Unit test suite for ETL, governance, semantic, and docs checks
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
│   ├── architecture/           # HTML architecture diagrams and decision reviews
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
# Lint + format checks used in CI
ruff check .
ruff format --check .

# Unit tests used in CI (no services needed)
pytest tests/unit/ -x --tb=short

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

- **Cube** -- YAML-defined metrics served via SQL API (Postgres wire protocol); NL-to-SQL schema linking (ADR-006)
- **Microsoft Fabric (Import mode)** -- BI and AI surface layer for Gold data; DAX semantic model serving Power BI, Tableau (XMLA), and RBC Assist via Fabric Data Agent (ADR-010)
- **NL-to-SQL** -- Natural language query engine using Claude on AWS Bedrock with Cube YAML context
- **Evaluation Framework** -- Golden datasets (trading + risk exposure) with execution accuracy scoring

## Key Documentation

| Document | Description |
|----------|-------------|
| [`docs/architecture/outstanding-questions.md`](docs/architecture/outstanding-questions.md) | Judge-style repo review questions and architecture/documentation gaps to resolve |
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

## Current Repository Status

| Area | Current state | Notes |
|------|---------------|-------|
| ETL application | Implemented in source | Python package, medallion pipelines, ingestion helpers, governance/quality/semantic modules |
| Local platform | Implemented in config | Docker definitions exist for Airflow, Cube, Grafana, OpenMetadata, Prometheus, Ranger, and Trino |
| Environment deployment | Implemented in config | Terraform modules and environment tfvars exist for dev/staging/prod |
| Automated validation | Implemented in CI | CI runs Ruff, unit tests, Terraform validate, and Terraform fmt checks |
| External system readiness | Partial / environment-dependent | Some integration paths require live services or credentials outside the repo |
| Roadmap / decision areas | Still open | See [`docs/architecture/outstanding-questions.md`](docs/architecture/outstanding-questions.md) for the review backlog |

## License

Proprietary. Internal use only.
