# Mainframe Data Ingestion Guide

This guide covers the end-to-end process for ingesting mainframe batch files
into the lakehouse — from the SFTP/Connect:Direct drop zone through the raw
zone, ingestion manifest, and into the Bronze Iceberg table.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│  Mainframe (z/OS)                                              │
│  DB2 unloads · VSAM extracts · batch job outputs              │
└────────────────────────┬───────────────────────────────────────┘
                         │  SFTP / Connect:Direct / NDM
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  Local Staging Directory  (SFTP drop zone)                     │
│  /sftp/drop/{source_system}/                                   │
└────────────────────────┬───────────────────────────────────────┘
                         │  RawZoneManager.upload_to_raw_zone()
                         │  • MD5 checksum computed before upload
                         │  • File stored binary-exact (no conversion)
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  Raw Zone  (S3 / MinIO)                                        │
│  s3://lakehouse-raw/raw/mainframe/{source}/{YYYY-MM-DD}/{file} │
│                                                                │
│  _manifest/{source}/{YYYY-MM-DD}.jsonl  ← IngestionManifest   │
└────────────────────────┬───────────────────────────────────────┘
                         │  MainframeBronzePipeline.execute()
                         │  Cobrix: EBCDIC → Spark DataFrame
                         ▼
┌────────────────────────────────────────────────────────────────┐
│  Bronze Layer  (Apache Iceberg via Nessie)                     │
│  lakehouse.bronze.{table}                                      │
└────────────────────────────────────────────────────────────────┘
```

---

## Raw Zone Architecture

### Bucket Structure

```
s3://lakehouse-raw/
├── raw/
│   ├── mainframe/
│   │   ├── mainframe_db2/
│   │   │   ├── 2026-03-15/
│   │   │   │   ├── accounts.dat
│   │   │   │   └── positions.dat
│   │   │   └── 2026-03-16/
│   │   │       └── accounts.dat
│   │   └── vsam_cics/
│   │       └── 2026-03-15/
│   │           └── transactions.dat
│   └── _manifest/
│       ├── mainframe_db2/
│       │   ├── 2026-03-15.jsonl
│       │   └── 2026-03-16.jsonl
│       └── vsam_cics/
│           └── 2026-03-15.jsonl
```

### Key Design Principles

| Principle | Detail |
|-----------|--------|
| **Binary-exact preservation** | Files are never modified — original EBCDIC bytes are stored as-is |
| **Date partitioning** | Each business date gets its own prefix for efficient lifecycle management |
| **Source isolation** | Each source system has its own prefix to simplify access control |
| **Manifest co-location** | The `_manifest/` prefix sits alongside raw data for easy correlation |

### Configuration

```python
from src.ingestion.raw_zone import RawZoneConfig

# AWS S3 (production)
s3_config = RawZoneConfig(
    bucket="lakehouse-raw",
    region="us-east-1",
)

# MinIO (on-premises / local dev)
minio_config = RawZoneConfig(
    bucket="lakehouse-raw",
    endpoint_url="http://minio:9000",
    region="us-east-1",
)
```

---

## File Transfer Patterns

### SFTP (SSH File Transfer Protocol)

Most mainframe shops use SFTP to drop files from z/OS to a Linux landing server.
The typical flow is:

1. Mainframe batch job completes and writes output to a GDG (Generation Data Group)
2. An FTP/SFTP job step copies the file to the Linux SFTP server
3. `RawZoneManager.upload_to_raw_zone()` picks up the file and moves it to S3

```python
import os
from src.ingestion.raw_zone import RawZoneConfig, RawZoneManager

SFTP_DROP = "/sftp/drop/mainframe_db2"
SOURCE_SYSTEM = "mainframe_db2"
BUSINESS_DATE = "2026-03-15"

config = RawZoneConfig(bucket="lakehouse-raw")
manager = RawZoneManager(config=config)

for filename in os.listdir(SFTP_DROP):
    local_path = os.path.join(SFTP_DROP, filename)
    raw_file = manager.upload_to_raw_zone(
        local_path=local_path,
        source_system=SOURCE_SYSTEM,
        business_date=BUSINESS_DATE,
    )
    print(f"Landed: {raw_file.raw_path} ({raw_file.file_size_bytes} bytes)")
```

### Connect:Direct / NDM

IBM Connect:Direct (formerly NDM) is the standard for bank-to-bank and
mainframe-to-server file transfer. The process file executes on the mainframe
and deposits the file at a server-side path.

From the lakehouse perspective, Connect:Direct deposits the file at a local
path just like SFTP — the upload step is identical:

```python
raw_file = manager.upload_to_raw_zone(
    local_path="/data/ndm/drop/accounts.dat",
    source_system="mainframe_db2",
    business_date="2026-03-15",
)
```

### Path Construction

Use `RawZoneManager.get_raw_zone_path()` to build canonical paths without
instantiating a full manager:

```python
from src.ingestion.raw_zone import RawZoneManager

# Returns: "raw/mainframe/mainframe_db2/2026-03-15/accounts.dat"
key = RawZoneManager.get_raw_zone_path("mainframe_db2", "2026-03-15", "accounts.dat")

# Full S3 URI
uri = f"s3://lakehouse-raw/{key}"
```

---

## Manifest Lifecycle

The ingestion manifest tracks every file from first arrival to Bronze write
completion.  Each manifest is stored as a **JSON Lines** file — one JSON object
per line — in the `_manifest/` prefix.

### Status Transitions

```
                ┌──────────────────────────────────────┐
  File arrives  │                                      │
       ↓        │  register_file()                     │
   LANDED   ────┤                                      │
       ↓        │  mark_processing(file_id, batch_id)  │
  PROCESSING ───┤                                      │
       │        └──────────────────────────────────────┘
       ├──► PROCESSED  (mark_processed)
       └──► FAILED     (mark_failed)
```

### ManifestEntry Fields

| Field | Type | Description |
|-------|------|-------------|
| `file_id` | `str` | UUID generated at registration |
| `raw_path` | `str` | Full S3 URI |
| `source_system` | `str` | e.g. `"mainframe_db2"` |
| `business_date` | `str` | `"YYYY-MM-DD"` |
| `file_size_bytes` | `int` | File size at landing |
| `md5_checksum` | `str` | Hex MD5 digest |
| `arrival_ts` | `str` | ISO 8601 UTC timestamp |
| `status` | `str` | `LANDED \| PROCESSING \| PROCESSED \| FAILED` |
| `batch_id` | `str \| None` | ETL batch identifier |
| `bronze_table` | `str \| None` | Fully-qualified Iceberg table |
| `row_count` | `int \| None` | Rows written to Bronze |
| `processed_ts` | `str \| None` | ISO 8601 UTC completion time |
| `error_message` | `str \| None` | Error description if FAILED |

### Manifest File Format

The manifest is append-friendly JSON Lines.  Because status updates append new
records, `load_manifest()` returns the *last* entry per `file_id`:

```jsonl
{"file_id": "abc-123", "status": "LANDED", ...}
{"file_id": "abc-123", "status": "PROCESSING", "batch_id": "batch-001", ...}
{"file_id": "abc-123", "status": "PROCESSED", "row_count": 50000, ...}
```

---

## Step-by-Step: Onboarding a New Mainframe Source

### 1. Define the Source System

Pick a snake_case identifier for the source system.  This becomes part of
every raw zone path and manifest key:

```
mainframe_db2      # DB2 z/OS extracts
vsam_cics          # VSAM files via CICS
mainframe_cobol    # Custom COBOL programs
```

### 2. Obtain the COBOL Copybook

Request the record layout (copybook `.cpy` file) from the mainframe team.
Store it in `etl/tests/fixtures/` for testing and alongside the Airflow DAG
config for production runs.

```cobol
       01  ACCOUNT-RECORD.
           05  ACCOUNT-ID         PIC X(10).
           05  ACCOUNT-NAME       PIC X(50).
           05  BALANCE             PIC S9(13)V99 COMP-3.
           05  ACCOUNT-TYPE       PIC X(3).
           05  OPEN-DATE          PIC X(8).
```

### 3. Configure the Raw Zone

```python
from src.ingestion.raw_zone import RawZoneConfig, RawZoneManager

config = RawZoneConfig(bucket="lakehouse-raw")
manager = RawZoneManager(config=config)
```

### 4. Create a Manifest Instance

```python
from src.ingestion.manifest import IngestionManifest

manifest = IngestionManifest(bucket="lakehouse-raw")
```

### 5. Upload the File and Register It

```python
raw_file = manager.upload_to_raw_zone(
    local_path="/sftp/drop/accounts.dat",
    source_system="mainframe_db2",
    business_date="2026-03-15",
)
entry = manifest.register_file(
    raw_path=raw_file.raw_path,
    source_system=raw_file.source_system,
    business_date=raw_file.business_date,
    file_size_bytes=raw_file.file_size_bytes,
    md5_checksum=raw_file.md5_checksum,
    arrival_ts=raw_file.arrival_ts,
)
batch_id = "batch-mf-20260315-001"
manifest.mark_processing(entry.file_id, batch_id, "mainframe_db2", "2026-03-15")
```

### 6. Run the Pipeline

```python
from src.iceberg_utils.catalog import get_spark_session
from src.pipelines.bronze.mainframe_ingest import MainframeBronzePipeline

spark = get_spark_session()
pipeline = MainframeBronzePipeline(
    spark=spark,
    copybook_path="/opt/airflow/copybooks/accounts.cpy",
    data_path=raw_file.raw_path,
    source_system="mainframe_db2",
    batch_id=batch_id,
    raw_zone_config=config,
    manifest=manifest,
    manifest_entry=entry,
)
result = pipeline.execute()
# Manifest entry is now PROCESSED automatically
print(f"Wrote {result['rows_written']} rows to Bronze")
```

### 7. Add Quality Checks

Create `etl/src/quality/checks/bronze_accounts.yml` following the SodaCL
pattern in [`docs/etl-patterns.md`](etl-patterns.md#3-quality-checks).

### 8. Create an Airflow DAG

Wrap steps 5 and 6 in a DAG following the pattern in
[`docs/etl-patterns.md`](etl-patterns.md#4-dag-patterns).

---

## Regulatory Retention

### Why Raw Zone Files Are Never Deleted

Financial regulators (SEC Rule 17a-4, FINRA 4370, Basel III, BCBS 239) require
firms to retain source records for **7 years** in their original form.
The raw zone satisfies this requirement because:

1. **Binary-exact copies** — EBCDIC bytes are stored as-is; no encoding conversion
2. **Immutable storage** — S3 Object Lock (compliance mode) prevents modification or deletion
3. **Independent of Bronze** — Raw files exist even if Iceberg tables are rebuilt

### Recommended S3 Lifecycle Policy

```json
{
  "Rules": [
    {
      "ID": "raw-zone-tiering",
      "Filter": { "Prefix": "raw/mainframe/" },
      "Status": "Enabled",
      "Transitions": [
        { "Days": 90,   "StorageClass": "STANDARD_IA" },
        { "Days": 365,  "StorageClass": "GLACIER_IR" },
        { "Days": 1095, "StorageClass": "DEEP_ARCHIVE" }
      ]
    }
  ]
}
```

### S3 Object Lock (Compliance Mode)

Enable Object Lock on the raw zone bucket with a 7-year retention period:

```bash
aws s3api put-object-lock-configuration \
  --bucket lakehouse-raw \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Years": 7
      }
    }
  }'
```

---

## Troubleshooting

### CobrixNotAvailableError

**Symptom:** `MainframeBronzePipeline.extract()` raises `CobrixNotAvailableError`.

**Cause:** The Cobrix JAR is not on the Spark classpath.

**Fix:** Add the JAR to `spark.jars.packages` in your Spark config:

```python
spark_conf = {
    "spark.jars.packages": "za.co.absa.cobrix:spark-cobol_2.12:2.9.2",
}
```

Or download and reference locally:

```python
spark_conf = {
    "spark.jars": "/opt/spark/jars/spark-cobol_2.12-2.9.2.jar",
}
```

### FileNotFoundError During extract()

**Symptom:** `extract()` raises `FileNotFoundError: File 'accounts.dat' not found in raw zone`.

**Cause:** `raw_zone_config` was provided but the file has not been uploaded yet
(or was uploaded to a different `source_system` / `business_date`).

**Fix:**

1. Verify the file was uploaded: `manager.list_raw_files(source_system, business_date)`
2. Check the `source_system` and `business_date` match exactly
3. Confirm the S3 key follows the canonical pattern: `raw/mainframe/{source}/{date}/{filename}`

### Manifest Entry Not Found (KeyError)

**Symptom:** `manifest.mark_processing()` raises `KeyError: file_id not found`.

**Cause:** The `file_id` does not exist in the manifest for the given date.

**Fix:**

1. Confirm `register_file()` was called before `mark_processing()`
2. Check `source_system` and `business_date` match the `register_file()` call
3. Inspect the manifest: `manifest.load_manifest(source_system, business_date)`

### Checksum Mismatch

**Symptom:** The MD5 in the manifest does not match a recomputed hash of the raw file.

**Cause:** File corruption during transfer or accidental overwrite.

**Fix:**

1. Re-download the original from the mainframe source
2. Upload a fresh copy: `manager.upload_to_raw_zone(...)` with a new manifest entry
3. If Object Lock is enabled, create a new object version rather than overwriting

### Large Files / Timeouts

**Symptom:** `upload_to_raw_zone()` times out for files > 5 GB.

**Fix:** The boto3 `upload_file` method uses multipart upload automatically
for large files.  Increase the `multipart_threshold` via a `TransferConfig`:

```python
import boto3
from boto3.s3.transfer import TransferConfig

s3 = boto3.client("s3")
config = TransferConfig(multipart_threshold=1024 * 25, max_concurrency=10)
s3.upload_file("large_file.dat", "bucket", "key", Config=config)
```
