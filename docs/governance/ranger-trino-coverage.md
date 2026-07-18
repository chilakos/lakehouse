# Apache Ranger + Trino: Governance Coverage Map

**Scope:** What Ranger governs, what it doesn't, and the open gaps during the
Teradata migration transition period.

---

## How Ranger Works with Trino

Ranger operates as a **System Access Control plugin** inside Trino. Every query
submitted to Trino — by a human analyst, a DataStage job, a Python pipeline, Borealis,
or an AI agent — is evaluated against Ranger policies before execution.

```
User / Service Account
        │
        ▼
   Trino Coordinator
        │
        ├── Parse query → extract resource list
        │   (catalog.schema.table.column for every object referenced)
        │
        ├── Call Ranger plugin: isAccessAllowed(user, resource, action)?
        │   │
        │   ├── DENY → query rejected, audit event logged
        │   └── ALLOW → query continues
        │
        ├── Apply column masking (if Ranger masking policy exists)
        │   e.g. MASK(sin_number) → 'XXX-XX-XXXX' for non-PII-authorized users
        │
        ├── Apply row filtering (if Ranger row filter policy exists)
        │   e.g. WHERE region = current_user_region()
        │
        └── Execute query → return results
                │
                └── Audit event logged to Solr
                    (user, timestamp, query, tables accessed, allow/deny)
```

Ranger policies are cached in Trino and refreshed every 30 seconds. If Ranger Admin
is temporarily unavailable, Trino continues enforcing the last-known policy cache —
it does not fail open.

---

## What Ranger Governs (Covered)

| Access path | Governed by Ranger? | Notes |
|---|---|---|
| Trino query → Iceberg Bronze | ✅ Yes | Full table/column/row policy |
| Trino query → Iceberg Silver | ✅ Yes | Full table/column/row policy |
| Trino query → Iceberg Gold | ✅ Yes | Full table/column/row policy |
| Cube SQL API → Trino → Gold | ✅ Yes | Trino is the execution layer; Ranger evaluates |
| AI agents (Borealis) via Cube | ✅ Yes | Same Trino path, same policies |
| Trino JDBC → Teradata (federation) | ✅ Partial | Ranger governs the Trino side; Teradata governs internally |
| Python ETL via Trino JDBC | ✅ Yes | Service account governed by Ranger policy |
| Airflow DAGs via Trino | ✅ Yes | Airflow service account governed by Ranger policy |

---

## What Ranger Does NOT Govern (Gaps)

| Access path | Governed? | Risk | Mitigation |
|---|---|---|---|
| Direct S3/Pure Storage reads (boto3, PyArrow) | ❌ No | Ungoverned data access; no audit trail | S3 bucket policies + IAM; block direct reads at infra layer (ADR-002) |
| Teradata internal queries (direct JDBC to TD) | ❌ No — Teradata native | Separate audit trail; not in OpenLineage | Teradata query logs must be ingested to BCBS 239 audit store separately |
| Teradata OTF direct to Nessie (if bypasses Trino) | ❌ No | Full Ranger bypass | Do not permit OTF direct reads until confirmed to route through Trino (ADR-001, ADR-002) |
| Cloudera Hive tables (during migration) | ❌ No | Shadow data accessible without Ranger | Deprecate shadow copies before decommissioning governance gap |
| Raw HDFS reads on Cloudera | ❌ No | Ungoverned | HDFS data decommissioned with Cloudera |
| Snowflake (during migration) | ❌ No — Snowflake native | Separate governance model | Snowflake decommissioned per migration plan |

---

## BCBS 239 Audit Trail Coverage

BCBS 239 requires a complete, unbroken audit trail of all data access from ingestion
to consumption. During the transition period, this trail has a gap:

```
FULL COVERAGE (target state):
Ingestion → Bronze (Ranger ✅) → Silver (Ranger ✅) → Gold (Ranger ✅) → BI/AI (Ranger ✅)

CURRENT GAP (transition period):
Teradata direct queries → Teradata native logs only (not in OpenLineage)
Cloudera shadow reads  → No audit trail at all

REQUIRED ACTION:
1. Ingest Teradata DBQL query logs into the central audit store
2. Deprecate all Cloudera shadow copies (eliminate ungoverned reads)
3. Enforce Trino-only access to Iceberg from day one
```

> ⚠️ **UNRESOLVED**: A process for correlating Teradata DBQL logs with OpenLineage
> events has not been defined. Both audit trails exist but are not linked. Owner:
> governance team. Required for full BCBS 239 coverage during transition.

---

## Policy Design Principles

### Least privilege by default

No user or service account has access to any Iceberg table by default. Access must
be explicitly granted via a Ranger policy. Denying by default means new tables are
automatically protected the moment they are registered in Nessie.

### Layer-based access tiers

| Role | Bronze | Silver | Gold | Vector Store |
|---|---|---|---|---|
| `data_engineer` | Read/Write | Read/Write | Read/Write | None |
| `data_analyst` | None | None | Read | None |
| `bi_tool_svc` | None | None | Read | None |
| `ai_agent_svc` | None | None | Read (via Cube) | Read |
| `pipeline_svc` | Read/Write | Read/Write | Read/Write | Write |
| `admin` | Full | Full | Full | Full |

Direct Bronze/Silver access by analysts or BI tools is explicitly denied. All
analytical consumption happens via Gold tables, enforced by Ranger policy.

### Column masking for PII

Sensitive columns (SIN, date of birth, full account numbers) are masked by default
for all roles except `pii_authorized`:

```
Policy: mask_pii_default
  Resources: iceberg.silver.*, iceberg.gold.*
  Columns: sin_number, date_of_birth, full_account_number
  Users/Groups: ALL except pii_authorized
  Masking: MASK (replace with 'XXXXXXXX')
```

### Automated Column Classification Pipeline (ADR-007)

> **Status:** Approved (2026-03-30). Addresses the manual classification bottleneck
> identified in `bootstrap-policies.py` (`seed_classification_tags()` deferral).

The manual gap between table creation and PII masking is closed by an automated pipeline:

```
Table lands in Nessie → Ranger deny-by-default (immediate)
    ↓
OpenMetadata Trino connector discovers table (existing)
    ↓
OpenMetadata Auto-Classification workflow scans columns
    (spaCy NLP + Microsoft Presidio: SSN, email, phone, credit card, etc.)
    ↓
Tag Sync Bridge (Airflow DAG) reads classified columns
    ↓
Maps to Ranger tag taxonomy:
    PII.Sensitive (SSN/SIN patterns)  → RESTRICTED  → MASK_NULL / SHOW_LAST_4
    PII.Sensitive (email/phone)       → CONFIDENTIAL → MASK_HASH / SHOW_LAST_4
    No PII tag (gold schema)          → INTERNAL     → MASK_NONE
    No PII tag (public schema)        → PUBLIC       → MASK_NONE
    ↓
Pushes tag-resource associations to Ranger TagREST API
    (POST /service/tags/tagresourceassoc — no Atlas required)
    ↓
Existing Ranger tag-based masking policies activate automatically
```

**Classification latency:** New tables have PII tags applied within 6 hours of ingestion
(target: near real-time via OpenMetadata webhook in Phase 1.3).

**Row-level filters:** Tables with a `business_unit` column are automatically given
row-filter policies following the same pattern as `build_row_filter_policies()` in
`bootstrap-policies.py`.

See ADR-007 for full architecture and implementation phases.

### Service account identity passthrough

Python ETL pipelines, Airflow DAGs, and AI agents authenticate to Trino using
dedicated service accounts. Ranger logs these identities — every audit event is
attributable to a specific service account, not a generic system user.

```python
# Service account authentication in Python pipeline
conn = connect(
    host="trino.lakehouse.rbc.internal",
    port=8080,
    user="svc_etl_pipeline",          # Service account — logged by Ranger
    auth=KerberosAuthentication(),     # Kerberos from RBC AD
    http_scheme="https",
)
```

---

## Ranger Admin — Key Operational Notes

**Policy refresh interval:** Trino plugins poll Ranger every 30 seconds. Policy
changes take up to 30 seconds to propagate to all Trino coordinators and workers.

**Audit storage:** Ranger audit events are written to Solr
(`ranger-solr:8983/solr/ranger_audits`). Solr must be monitored for disk capacity.
Audit log retention: minimum 7 years for BCBS 239 compliance.

**High availability:** Ranger Admin can be deployed HA. The Trino plugin functions
during temporary Ranger unavailability using its cached policy set. The cache file
is written to local disk on each Trino node on every policy refresh.

**Ranger version:** The native Trino plugin requires Ranger 2.3.0+ (for the Ranger
side) and Trino 466+ (for the Trino side). Confirm versions with Platform Engineering
before deployment.
