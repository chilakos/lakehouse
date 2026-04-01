# Lakehouse POC — End-to-End Local Pipeline

Run the full medallion pipeline (Raw → Bronze → Silver → Gold) on your laptop in under 5 minutes. No Spark. No Airflow. No Teradata.

---

## What It Does

```
GENERATE   →   RAW ZONE   →   BRONZE   →   SILVER   →   GOLD
(Python)       (MinIO CSV)    (PyIceberg)  (Trino SQL)  (Trino SQL)
```

| Stage | What happens |
|---|---|
| **Generate** | 100 synthetic trade records (deterministic, seed=42) |
| **Raw Zone** | CSV uploaded to `s3://lakehouse-raw/raw/synthetic/trades/` |
| **Bronze** | CSV written as Iceberg V2 table via PyIceberg — append-only, with metadata columns |
| **Silver** | Trino SQL: dedup + quality filter (price > 0, valid side) → `lakehouse.silver.trades` |
| **Gold** | Trino SQL: aggregation by symbol × side → `lakehouse.gold.trading_metrics` |

---

## Prerequisites

- Docker Desktop (or Docker Engine + Compose)
- Python 3.11+

---

## Run It

### 1. Start the stack (4 services, ~2 min first run)

```bash
docker-compose -f docker-compose.poc.yml up -d
```

Wait for all services to be healthy:

```bash
docker-compose -f docker-compose.poc.yml ps
```

All four should show `healthy` or `Up`:
- `poc-nessie-db` — Postgres (Nessie metadata)
- `poc-minio` — MinIO (object storage)
- `poc-nessie` — Nessie (Iceberg REST catalog)
- `poc-trino` — Trino (query engine)

### 2. Install Python dependencies

```bash
cd etl
pip install ".[dev]"
cd ..
```

### 3. Run the pipeline

```bash
python scripts/poc_pipeline.py
```

Expected output (truncated):

```
══════════════════════════════════════════════════════════════════════
  RBC Lakehouse POC — Synthetic Data End-to-End Pipeline
══════════════════════════════════════════════════════════════════════
  Batch ID  : poc-batch-20260401T123456
  Stack     : MinIO + Nessie + Trino (no Spark, no Airflow, no Teradata)

[1/5] GENERATE — Synthetic trades (seed=42, deterministic)
  ✓ Generated 100 synthetic trade records
  → Sample: trade_id=1 symbol=AAPL side=BUY price=234.5 qty=4821

[2/5] RAW ZONE — CSV upload to MinIO s3://lakehouse-raw/
  ✓ Landed 100 records → s3://lakehouse-raw/raw/synthetic/trades/2026-04-01/trades.csv
  ✓ Manifest written

[3/5] BRONZE — PyIceberg write to lakehouse.bronze.trades
  ✓ Created Iceberg table: bronze.trades
  ✓ Bronze rows written: 100

[4/5] SILVER — Trino SQL: dedup + quality filter
  ✓ Silver rows written: 100

[5/5] GOLD — Trino SQL: aggregation
  ✓ Gold rows written: 30  (symbol × side aggregates)

  Top 10 Gold rows — gold.trading_metrics
  symbol  side  trade_count  total_notional  avg_price  unique_accounts
  MSFT    BUY   4            3245678.12      321.45     4
  ...
```

---

## Explore

| Service | URL | Credentials |
|---|---|---|
| Trino UI | http://localhost:8080 | any username |
| MinIO Console | http://localhost:9001 | admin / admin123456 |
| Nessie API | http://localhost:19120/api/v2/trees | — |

### Query via Trino CLI

```bash
# If you have the Trino CLI:
trino --server localhost:8080 --catalog lakehouse --schema gold \
    --execute "SELECT * FROM trading_metrics ORDER BY total_notional DESC"

# Or via Docker:
docker exec -it poc-trino trino \
    --catalog lakehouse --schema gold \
    --execute "SELECT symbol, side, trade_count, total_notional FROM trading_metrics LIMIT 10"
```

### Query raw CSV in MinIO

```bash
# List what landed in the raw zone
aws s3 ls s3://lakehouse-raw/raw/synthetic/trades/ \
    --endpoint-url http://localhost:9000 \
    --no-sign-request
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  poc_pipeline.py                                                 │
│                                                                  │
│  generators.py                                                   │
│      └─→ 100 synthetic trades (seed=42)                         │
│              │                                                   │
│              ▼  boto3                                            │
│  MinIO   s3://lakehouse-raw/raw/synthetic/trades/YYYY-MM-DD/    │
│              │                                                   │
│              ▼  PyIceberg → Nessie REST catalog                  │
│  Iceberg  lakehouse.bronze.trades  (Parquet on s3://lakehouse-data/)│
│              │                                                   │
│              ▼  Trino SQL (quality filter + dedup)               │
│  Iceberg  lakehouse.silver.trades                                │
│              │                                                   │
│              ▼  Trino SQL (GROUP BY symbol, side)                │
│  Iceberg  lakehouse.gold.trading_metrics  ← query this          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tear Down

```bash
docker-compose -f docker-compose.poc.yml down -v
```

The `-v` flag removes the data volumes so the next run starts fresh.

---

## Extending the POC

| Want to add | Where to look |
|---|---|
| More data types | `etl/src/synthetic/generators.py` — add `generate_positions()` |
| Quality checks | `etl/src/quality/` — run Soda Core checks after Bronze |
| Lineage | `etl/src/lineage/` — add OpenLineage emission to each step |
| Airflow DAG | `etl/dags/` — wrap each step in an Airflow task |
| Full stack | `docker-compose.yml` — adds Airflow, Ranger, Grafana, OpenMetadata |
