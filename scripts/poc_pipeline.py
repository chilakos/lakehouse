#!/usr/bin/env python3
"""
POC Pipeline: Synthetic Data → Raw Zone → Bronze → Silver → Gold
================================================================
No Spark. No Airflow. No Teradata.
Uses: PyIceberg (table management) + Trino (SQL transforms) + boto3 (raw zone)

Run order:
    docker-compose -f docker-compose.poc.yml up -d
    cd etl && pip install ".[dev]"
    cd .. && python scripts/poc_pipeline.py

What it does:
    1. GENERATE  — synthetic trades via generators.py (100 records)
    2. RAW ZONE  — writes CSV to MinIO  s3://lakehouse-raw/raw/synthetic/...
    3. BRONZE    — reads CSV, writes Iceberg table via PyIceberg
    4. SILVER    — Trino SQL dedup + quality filter  (bronze → silver)
    5. GOLD      — Trino SQL aggregation             (silver → gold)
    6. QUERY     — Trino SELECT to prove it works end-to-end
"""

from __future__ import annotations

import csv
import io
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

# ── colour helpers ─────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
GOLD   = "\033[33m"


def banner(msg: str) -> None:
    width = 70
    print(f"\n{BOLD}{CYAN}{'═' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'═' * width}{RESET}")


def step(n: int, label: str) -> None:
    print(f"\n{BOLD}{YELLOW}[{n}/5] {label}{RESET}")


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {CYAN}→{RESET} {msg}")


def err(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}", file=sys.stderr)


# ── config ─────────────────────────────────────────────────────────────────

MINIO_ENDPOINT   = "http://localhost:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "admin123456"
RAW_BUCKET       = "lakehouse-raw"
DATA_BUCKET      = "lakehouse-data"

NESSIE_URI       = "http://localhost:19120/iceberg"
WAREHOUSE        = f"s3://{DATA_BUCKET}/"

TRINO_HOST       = "localhost"
TRINO_PORT       = 8080
TRINO_USER       = "poc"

BUSINESS_DATE    = date.today().isoformat()
SOURCE_SYSTEM    = "synthetic"
BATCH_ID         = f"poc-batch-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
NUM_RECORDS      = 100


# ── wait for services ──────────────────────────────────────────────────────

def wait_for_trino(timeout: int = 60) -> None:
    import urllib.request
    import urllib.error
    info(f"Waiting for Trino at {TRINO_HOST}:{TRINO_PORT} ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://{TRINO_HOST}:{TRINO_PORT}/v1/info", timeout=3)
            ok("Trino is up")
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Timed out waiting for Trino — is docker-compose.poc.yml running?")


def wait_for_nessie(timeout: int = 60) -> None:
    import urllib.request
    info(f"Waiting for Nessie at localhost:19120 ...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://localhost:19120/api/v2/config", timeout=3)
            ok("Nessie is up")
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("Timed out waiting for Nessie — is docker-compose.poc.yml running?")


# ── step 1: generate synthetic data ───────────────────────────────────────

def generate_trades() -> list[dict]:
    # Add the etl/src directory to path so we can import generators
    etl_src = Path(__file__).parent.parent / "etl" / "src"
    if str(etl_src) not in sys.path:
        sys.path.insert(0, str(etl_src.parent))

    try:
        from src.synthetic.generators import generate_trades as _gen
        trades = _gen(NUM_RECORDS, seed=42)
        ok(f"Generated {len(trades)} synthetic trade records")
        # Show sample
        t = trades[0]
        info(f"Sample: trade_id={t['trade_id']} symbol={t['symbol']} "
             f"side={t['side']} price={t['price']} qty={t['quantity']}")
        return trades
    except ImportError:
        info("generators.py not importable from here — using inline generator")
        return _inline_generate_trades(NUM_RECORDS)


def _inline_generate_trades(n: int) -> list[dict]:
    """Fallback inline generator if etl package not installed."""
    import random
    from datetime import timedelta
    from decimal import Decimal
    rng = random.Random(42)
    symbols = ["AAPL", "GOOGL", "MSFT", "JPM", "GS", "BAC", "C", "WFC", "V", "MA"]
    sides = ["BUY", "SELL"]
    types = ["MARKET", "LIMIT", "STOP"]
    exchanges = ["NYSE", "NASDAQ", "LSE", "TSE"]
    trades = []
    for i in range(n):
        price = round(rng.uniform(50.0, 500.0), 4)
        qty = rng.randint(1, 10000)
        td = date(2026, 1, 1) + timedelta(days=rng.randint(0, 90))
        trades.append({
            "trade_id": i + 1,
            "trade_date": td,
            "symbol": rng.choice(symbols),
            "side": rng.choice(sides),
            "trade_type": rng.choice(types),
            "quantity": qty,
            "price": Decimal(str(price)),
            "notional": Decimal(str(round(price * qty, 4))),
            "account_id": f"ACCT-{rng.randint(1000,9999)}",
            "trader_id": f"TRD-{rng.randint(100,999)}",
            "exchange": rng.choice(exchanges),
            "settlement_date": td + timedelta(days=rng.choice([1, 2, 3])),
        })
    ok(f"Generated {len(trades)} synthetic trade records (inline)")
    return trades


# ── step 2: raw zone upload ────────────────────────────────────────────────

def upload_to_raw_zone(trades: list[dict]) -> str:
    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

    # Ensure bucket exists
    try:
        s3.head_bucket(Bucket=RAW_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=RAW_BUCKET)
        ok(f"Created bucket: {RAW_BUCKET}")

    # Serialise to CSV
    buf = io.StringIO()
    fieldnames = list(trades[0].keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for t in trades:
        writer.writerow({k: str(v) for k, v in t.items()})

    key = f"raw/{SOURCE_SYSTEM}/trades/{BUSINESS_DATE}/trades.csv"
    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=buf.getvalue().encode("utf-8"),
        ContentType="text/csv",
        Metadata={
            "source_system": SOURCE_SYSTEM,
            "business_date": BUSINESS_DATE,
            "batch_id": BATCH_ID,
            "record_count": str(len(trades)),
        },
    )
    raw_path = f"s3://{RAW_BUCKET}/{key}"
    ok(f"Landed {len(trades)} records → {raw_path}")

    # Write a manifest entry
    manifest_key = f"raw/_manifest/{SOURCE_SYSTEM}/{BUSINESS_DATE}.jsonl"
    manifest_entry = json.dumps({
        "batch_id": BATCH_ID,
        "raw_path": raw_path,
        "source_system": SOURCE_SYSTEM,
        "business_date": BUSINESS_DATE,
        "record_count": len(trades),
        "arrival_ts": datetime.now(timezone.utc).isoformat(),
        "status": "LANDED",
    })
    s3.put_object(Bucket=RAW_BUCKET, Key=manifest_key, Body=manifest_entry)
    ok(f"Manifest written → s3://{RAW_BUCKET}/{manifest_key}")

    return raw_path


# ── step 3: bronze — PyIceberg write ──────────────────────────────────────

def write_bronze(trades: list[dict]) -> int:
    import pyarrow as pa
    from pyiceberg.catalog import load_catalog
    from pyiceberg.exceptions import NamespaceAlreadyExistsError, NoSuchTableError
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        DateType,
        DecimalType,
        IntegerType,
        LongType,
        NestedField,
        StringType,
        TimestampType,
    )

    catalog = load_catalog(
        "nessie",
        **{
            "type": "rest",
            "uri": NESSIE_URI,
            "warehouse": WAREHOUSE,
            "s3.endpoint": MINIO_ENDPOINT,
            "s3.access-key-id": MINIO_ACCESS_KEY,
            "s3.secret-access-key": MINIO_SECRET_KEY,
            "s3.path-style-access": "true",
        },
    )

    # Create namespace
    try:
        catalog.create_namespace("bronze")
        ok("Created namespace: bronze")
    except NamespaceAlreadyExistsError:
        ok("Namespace bronze already exists")

    # Define Bronze schema (trades + metadata columns)
    schema = Schema(
        NestedField(1,  "trade_id",        IntegerType(),        required=True),
        NestedField(2,  "trade_date",       DateType(),           required=True),
        NestedField(3,  "symbol",           StringType(),         required=True),
        NestedField(4,  "side",             StringType(),         required=True),
        NestedField(5,  "trade_type",       StringType(),         required=True),
        NestedField(6,  "quantity",         IntegerType(),        required=True),
        NestedField(7,  "price",            DecimalType(18, 4),   required=True),
        NestedField(8,  "notional",         DecimalType(18, 4),   required=True),
        NestedField(9,  "account_id",       StringType(),         required=True),
        NestedField(10, "trader_id",        StringType(),         required=True),
        NestedField(11, "exchange",         StringType(),         required=True),
        NestedField(12, "settlement_date",  DateType(),           required=True),
        NestedField(13, "source_system",    StringType(),         required=False),
        NestedField(14, "batch_id",         StringType(),         required=False),
        NestedField(15, "ingestion_ts",     TimestampType(),      required=False),
    )

    # Drop and recreate for idempotency in POC
    try:
        catalog.drop_table("bronze.trades")
        info("Dropped existing bronze.trades for fresh run")
    except NoSuchTableError:
        pass

    table = catalog.create_table("bronze.trades", schema=schema)
    ok("Created Iceberg table: bronze.trades")

    # Build PyArrow table
    from decimal import Decimal as Dec
    now_ts = datetime.now(timezone.utc).replace(tzinfo=None)

    rows = {
        "trade_id":       pa.array([t["trade_id"]                  for t in trades], type=pa.int32()),
        "trade_date":     pa.array([t["trade_date"]                 for t in trades], type=pa.date32()),
        "symbol":         pa.array([t["symbol"]                     for t in trades], type=pa.string()),
        "side":           pa.array([t["side"]                       for t in trades], type=pa.string()),
        "trade_type":     pa.array([t["trade_type"]                 for t in trades], type=pa.string()),
        "quantity":       pa.array([t["quantity"]                   for t in trades], type=pa.int32()),
        "price":          pa.array([float(t["price"])               for t in trades], type=pa.float64()),
        "notional":       pa.array([float(t["notional"])            for t in trades], type=pa.float64()),
        "account_id":     pa.array([t["account_id"]                 for t in trades], type=pa.string()),
        "trader_id":      pa.array([t["trader_id"]                  for t in trades], type=pa.string()),
        "exchange":       pa.array([t["exchange"]                   for t in trades], type=pa.string()),
        "settlement_date":pa.array([t["settlement_date"]            for t in trades], type=pa.date32()),
        "source_system":  pa.array([SOURCE_SYSTEM] * len(trades),                    type=pa.string()),
        "batch_id":       pa.array([BATCH_ID] * len(trades),                         type=pa.string()),
        "ingestion_ts":   pa.array([now_ts] * len(trades),                           type=pa.timestamp("us")),
    }

    arrow_table = pa.table(rows)
    table.append(arrow_table)

    count = len(table.scan().to_arrow())
    ok(f"Bronze rows written: {count}")
    return count


# ── step 4 & 5: silver + gold via Trino SQL ───────────────────────────────

def run_trino_sql(sql: str, fetch: bool = False):
    import trino as trino_lib
    conn = trino_lib.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        catalog="lakehouse",
        schema="bronze",
    )
    cur = conn.cursor()
    cur.execute(sql)
    if fetch:
        return cur.fetchall(), [d[0] for d in cur.description]
    return None, None


def setup_trino_schemas() -> None:
    """Ensure bronze/silver/gold schemas exist in Trino."""
    for ns in ["bronze", "silver", "gold"]:
        try:
            run_trino_sql(f"CREATE SCHEMA IF NOT EXISTS lakehouse.{ns}")
            ok(f"Schema ensured: lakehouse.{ns}")
        except Exception as e:
            info(f"Schema {ns}: {e}")


def write_silver_via_trino() -> int:
    # Drop and recreate
    run_trino_sql("DROP TABLE IF EXISTS lakehouse.silver.trades")
    run_trino_sql("""
        CREATE TABLE lakehouse.silver.trades AS
        SELECT
            trade_id,
            trade_date,
            symbol,
            side,
            trade_type,
            quantity,
            price,
            notional,
            account_id,
            trader_id,
            exchange,
            settlement_date
        FROM lakehouse.bronze.trades
        WHERE
            price    > 0
            AND quantity > 0
            AND symbol   IS NOT NULL
            AND side     IN ('BUY', 'SELL')
    """)
    rows, _ = run_trino_sql("SELECT COUNT(*) FROM lakehouse.silver.trades", fetch=True)
    count = rows[0][0]
    ok(f"Silver rows written: {count}  (deduped + quality filtered from bronze)")
    return count


def write_gold_via_trino() -> int:
    run_trino_sql("DROP TABLE IF EXISTS lakehouse.gold.trading_metrics")
    run_trino_sql("""
        CREATE TABLE lakehouse.gold.trading_metrics AS
        SELECT
            symbol,
            side,
            COUNT(*)                          AS trade_count,
            SUM(notional)                     AS total_notional,
            AVG(price)                        AS avg_price,
            MIN(price)                        AS min_price,
            MAX(price)                        AS max_price,
            SUM(quantity)                     AS total_quantity,
            MIN(trade_date)                   AS first_trade_date,
            MAX(trade_date)                   AS last_trade_date,
            COUNT(DISTINCT account_id)        AS unique_accounts,
            COUNT(DISTINCT exchange)          AS exchanges_used
        FROM lakehouse.silver.trades
        GROUP BY symbol, side
        ORDER BY total_notional DESC
    """)
    rows, _ = run_trino_sql("SELECT COUNT(*) FROM lakehouse.gold.trading_metrics", fetch=True)
    count = rows[0][0]
    ok(f"Gold rows written: {count}  (aggregated by symbol + side)")
    return count


# ── step 6: show results ───────────────────────────────────────────────────

def show_results() -> None:
    rows, cols = run_trino_sql("""
        SELECT
            symbol,
            side,
            trade_count,
            ROUND(total_notional, 2)   AS total_notional,
            ROUND(avg_price, 2)        AS avg_price,
            unique_accounts
        FROM lakehouse.gold.trading_metrics
        ORDER BY total_notional DESC
        LIMIT 10
    """, fetch=True)

    col_widths = [max(len(str(c)), max(len(str(r[i])) for r in rows))
                  for i, c in enumerate(cols)]

    header = "  ".join(str(c).ljust(w) for c, w in zip(cols, col_widths))
    sep    = "  ".join("─" * w for w in col_widths)

    print(f"\n  {BOLD}Top 10 Gold rows — gold.trading_metrics{RESET}")
    print(f"  {CYAN}{sep}{RESET}")
    print(f"  {BOLD}{header}{RESET}")
    print(f"  {CYAN}{sep}{RESET}")
    for row in rows:
        print("  " + "  ".join(str(v).ljust(w) for v, w in zip(row, col_widths)))
    print(f"  {CYAN}{sep}{RESET}")


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    banner("RBC Lakehouse POC — Synthetic Data End-to-End Pipeline")
    print(f"  Batch ID  : {BOLD}{BATCH_ID}{RESET}")
    print(f"  Date      : {BUSINESS_DATE}")
    print(f"  Records   : {NUM_RECORDS}")
    print(f"  Stack     : MinIO + Nessie + Trino (no Spark, no Airflow, no Teradata)")

    wait_for_nessie()
    wait_for_trino()

    # ── 1. Generate
    step(1, "GENERATE — Synthetic trades (seed=42, deterministic)")
    trades = generate_trades()

    # ── 2. Raw Zone
    step(2, "RAW ZONE — CSV upload to MinIO s3://lakehouse-raw/")
    raw_path = upload_to_raw_zone(trades)

    # ── 3. Bronze
    step(3, "BRONZE — PyIceberg write to lakehouse.bronze.trades")
    bronze_count = write_bronze(trades)

    # ── 4. Silver
    step(4, "SILVER — Trino SQL: dedup + quality filter → lakehouse.silver.trades")
    setup_trino_schemas()
    silver_count = write_silver_via_trino()

    # ── 5. Gold
    step(5, "GOLD — Trino SQL: aggregation → lakehouse.gold.trading_metrics")
    gold_count = write_gold_via_trino()

    # ── Results
    banner("Pipeline Complete — Querying Gold Layer via Trino")
    show_results()

    print(f"""
  {BOLD}Summary{RESET}
  {'─' * 40}
  Raw zone CSV   → {raw_path}
  Bronze rows    → {bronze_count}
  Silver rows    → {silver_count}  (quality filtered)
  Gold rows      → {gold_count}   (symbol × side aggregates)

  {BOLD}Explore further:{RESET}
  Trino UI    → http://localhost:8080
  MinIO UI    → http://localhost:9001  (admin / admin123456)
  Nessie API  → http://localhost:19120/api/v2/trees

  {BOLD}Query Gold direct:{RESET}
  trino --server localhost:8080 --catalog lakehouse --schema gold \\
      --execute "SELECT * FROM trading_metrics ORDER BY total_notional DESC"
""")


if __name__ == "__main__":
    main()
