# Phase 3: Governance, Security Hardening, and Platform - Research

**Researched:** 2026-03-13
**Domain:** Data governance (Ranger security, data catalog, lineage compliance, audit trail)
**Confidence:** MEDIUM-HIGH

## Summary

Phase 3 adds production-grade security enforcement via Apache Ranger for Trino (column masking and row-level filtering), a data catalog platform for self-service discovery, BCBS 239 regulatory compliance dashboards built on Marquez/OpenLineage lineage data, and a centralized audit trail aggregating query access from Trino, Teradata, and Snowflake. The phase builds on existing Phase 2 infrastructure: Marquez 0.50.0 as the OpenLineage backend, Grafana for dashboards, Prometheus for metrics, and Airflow for orchestration.

The primary technologies are Apache Ranger 2.8.0 (with official Docker images and Trino plugin), OpenMetadata 1.12.x (recommended as the data catalog -- simpler architecture, native glossary approval workflow, built-in data profiling, OpenLineage event consumption via Kafka), the Grafana Infinity plugin for querying the Marquez REST API to build compliance dashboards, and Trino's built-in HTTP event listener for audit capture. The audit aggregation layer will use Airflow DAGs to ETL audit logs from all three engines into a common schema stored in PostgreSQL (hot) with S3 archival (cold).

**Primary recommendation:** Use OpenMetadata as the data catalog (simpler deployment, native glossary with approval workflow, built-in profiling, direct OpenLineage consumption). Deploy Apache Ranger 2.8.0 with official Docker images. Build BCBS 239 compliance dashboards in Grafana using the Infinity data source plugin against the Marquez REST API. Use Trino HTTP event listener plus Airflow ETL DAGs for the centralized audit trail.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Apache Ranger for Trino column-level masking and row-level filtering
- Engine-native masking for Teradata (view-based) and Snowflake (dynamic masking policies)
- Row-level security via business-unit attribute filtering with Ranger policies filtering based on user BU membership from LDAP groups
- Tag-driven data classification with sensitivity levels: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED -- masking rules keyed to tags, not specific columns
- Nested identity mapping: AD groups define team membership -> Ranger roles define data access policies
- Existing Phase 1 file-based RBAC (rules.json) replaced by Ranger policies for production
- Full lineage visualization with data quality overlay -- not just WHERE data came from but HOW HEALTHY it was at each transformation step
- BCBS 239 focus on the big three principles: Accuracy, Completeness, Timeliness
- Dual format: interactive Grafana dashboards + scheduled PDF/HTML export for audit evidence archives
- Lineage scope: full instrumented lineage for lakehouse + manually-registered lineage stubs for legacy systems (Teradata, Snowflake)
- Build on existing Marquez/OpenLineage infrastructure from Phase 2
- Business glossary: collaborative wiki-style with business user proposals and data steward approval
- Data freshness tracking: freshness timeline graph + SLA badges per table, traffic-light status
- Deep-linked integration between Grafana and catalog
- Per-engine native audit logging + ETL aggregation into common schema
- Full column-level access auditing: user, timestamp, query text, tables, columns, rows returned, masked vs unmasked
- Retention: 3 years hot storage, 7 years cold archive (S3 Glacier)
- Batch daily anomaly reports for suspicious patterns

### Claude's Discretion
- Data catalog platform selection (DataHub vs OpenMetadata vs other)
- Ranger deployment topology and HA configuration
- Audit log storage technology (Elasticsearch vs S3+Athena vs dedicated audit DB)
- Grafana dashboard layout and panel design for compliance views
- PDF/HTML report generation tooling
- Legacy lineage stub registration approach
- Anomaly detection heuristics for daily audit reports

### Deferred Ideas (OUT OF SCOPE)
- Real-time anomaly alerting on audit events -- batch daily reports for Phase 3
- Full BCBS 239 coverage (all 11 principles) -- Phase 3 covers big three only
- Nessie branching for schema governance -- explore after Ranger is operational
- Data contracts between producer and consumer domains -- v2 scope (PLAT-V2-03)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SEC-03 | Column-level security (masking PII and sensitive financial fields) via Apache Ranger | Ranger 2.8.0 Trino plugin supports column masking with types: MASK, MASK_SHOW_LAST_4, MASK_SHOW_FIRST_4, MASK_HASH, MASK_NULL, MASK_NONE, custom. Tag-based policies scale across tables. |
| SEC-04 | Row-level security for multi-business-unit data access via Apache Ranger | Ranger row-level filtering supports SQL predicates using Trino session variables like current_user(), enabling `business_unit = ${current_user_bu}` filters |
| GOVN-02 | Lineage visualization available for regulatory reporting (BCBS 239, SOX compliance) | Marquez REST API `/api/v1-beta/lineage?nodeId=` returns graph (nodes+edges). Grafana Infinity plugin queries this. Quality scores overlay from Soda Core. |
| GOVN-03 | Data classification and sensitivity labeling applied to PII and regulated financial data | Ranger tag-based policies: create `tag` service, define classification tags (PII, CONFIDENTIAL, etc.), attach to columns. Tag sync via Ranger TagSync or REST API. |
| GOVN-04 | Business glossary with data definitions accessible to business users | OpenMetadata native glossary with approval workflow (Draft->In Review->Approved states). Reviewers approve/reject terms. FSDM terms as seed data. |
| GOVN-05 | Audit trail capturing all data access across Trino, Teradata, and Snowflake | Trino HTTP event listener -> audit service; Teradata DBQL tables (DBC.QryLogV); Snowflake ACCESS_HISTORY view. Airflow DAG aggregates into common schema. |
| PLAT-01 | Data catalog deployed for self-service data discovery (search, profiling, glossary) | OpenMetadata: Trino connector ingests metadata + profiling + lineage. Elasticsearch-powered search. Built-in data profiler. Business glossary. |
| PLAT-03 | Data freshness tracking visible to business users | OpenMetadata system metrics track INSERT/UPDATE/DELETE operations per table. Freshness timeline graphs in profiler UI. Supplement with Grafana SLA badges. |
</phase_requirements>

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| Apache Ranger | 2.8.0 | Access control, column masking, row filtering, tag-based policies | Official Docker images (apache/ranger:2.8.0). Native Trino plugin. Tag-based policies scale to 300+ sources. Python client (apache-ranger PyPI). |
| OpenMetadata | 1.12.x | Data catalog, search, profiling, glossary, lineage display | Simpler architecture (MySQL/PostgreSQL + Elasticsearch only, no Kafka/graph DB). Native glossary approval workflow. Built-in data profiling. OpenLineage consumer via Kafka. Trino connector for metadata. |
| Grafana (existing) | latest | Compliance dashboards, data freshness SLA badges | Already deployed on port 3001. Infinity plugin for REST API queries. Provisioning pattern established. |
| Marquez (existing) | 0.50.0 | OpenLineage backend, lineage graph API | Already deployed. REST API provides lineage graph for compliance dashboards. |
| Trino (existing) | 479 | Query engine with Ranger plugin and HTTP event listener | Already deployed. Ranger access control plugin available. HTTP event listener for audit. |

### Supporting

| Library/Tool | Version | Purpose | When to Use |
|-------------|---------|---------|-------------|
| apache-ranger (Python) | latest (PyPI) | Programmatic policy management | Seeding Ranger policies, tag creation, automated classification |
| Grafana Infinity Plugin | latest | REST API data source for Grafana | Querying Marquez API for lineage visualization in compliance dashboards |
| grafana-reporter (IzakMarais) | latest | PDF export of Grafana dashboards | Scheduled PDF/HTML export for audit evidence archives |
| Apache Solr | (bundled with Ranger) | Ranger audit log storage | Ranger's native audit backend -- stores policy access audit events |
| PostgreSQL (existing) | 15 | Audit trail hot storage, OpenMetadata backend | Already deployed. Extend for audit aggregation tables and OpenMetadata metadata. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OpenMetadata | DataHub | DataHub has richer API and streaming architecture, but requires Kafka + graph DB (JanusGraph/Neo4j) -- significantly more operational complexity. DataHub's Iceberg REST catalog feature is interesting but not needed since we have Nessie. OpenMetadata's simpler stack (MySQL/PG + ES) is better for this project's infrastructure footprint. |
| OpenMetadata | Apache Atlas | Atlas is tightly coupled to Hadoop ecosystem, limited community momentum, no native data profiling or glossary approval workflow. |
| PostgreSQL for audit | Elasticsearch | ES provides better full-text search on query text, but adds another stateful service. PostgreSQL is already deployed (3 instances). For 3-year hot storage with daily anomaly queries, PostgreSQL with proper indexing is sufficient. If query text search becomes critical, add ES later. |
| PostgreSQL for audit | S3 + Athena | Better for cold analytics but slower for daily operational queries. Use S3 for the 7-year cold archive tier, PostgreSQL for the 3-year hot tier. |
| grafana-reporter | Skedler | Commercial product. grafana-reporter is open source and sufficient for scheduled PDF export. |

**Installation (new dependencies):**
```bash
# Python client for Ranger policy management
pip install apache-ranger

# Docker images (added to docker-compose.yml)
# apache/ranger:2.8.0
# apache/ranger-db:2.8.0
# apache/ranger-solr:2.8.0
# apache/ranger-zk:2.8.0 (Zookeeper for Solr)
# docker.getcollate.io/openmetadata/server:1.12.0
# docker.getcollate.io/openmetadata/ingestion:1.12.0
# docker.elastic.co/elasticsearch/elasticsearch:8.x (for OpenMetadata)
# mysql:8 (for OpenMetadata, or reuse existing PostgreSQL)
```

## Architecture Patterns

### Recommended Project Structure
```
infra/docker/
  ranger/
    ranger-trino-security.xml       # Ranger plugin config for Trino
    ranger-trino-audit.xml          # Audit routing config
    ranger-policymgr-ssl.xml        # SSL config (if needed)
    install.properties              # Trino plugin installation config
    bootstrap-policies.py           # Seed Ranger policies using apache-ranger client
  openmetadata/
    docker-compose-override.yml     # OM-specific service definitions
    connectors/
      trino-ingestion.yaml          # Trino metadata ingestion config
      airflow-lineage.yaml          # Airflow/OpenLineage ingestion config
  grafana/
    dashboards/
      pipeline_observability.json   # (existing)
      bcbs239_compliance.json       # BCBS 239 compliance dashboard
      data_freshness.json           # Data freshness SLA dashboard
      audit_overview.json           # Audit trail overview dashboard
    provisioning/
      datasources.yml               # Add Infinity datasource for Marquez API
      dashboards.yml                # (existing, auto-discovers dashboard JSON)
etl/
  src/
    governance/
      __init__.py
      classification.py             # Tag classification logic (PII detection, sensitivity labeling)
      ranger_policies.py            # Ranger policy seeding and management
      audit_schema.py               # Common audit schema definition
      audit_aggregator.py           # Cross-engine audit ETL logic
      anomaly_detector.py           # Daily anomaly detection heuristics
      lineage_stubs.py              # Legacy system lineage stub registration
      freshness_tracker.py          # Data freshness SLA tracking
  dags/
    governance/
      dag_audit_aggregation.py      # Daily audit ETL from all engines
      dag_anomaly_report.py         # Daily anomaly detection report
      dag_classification_scan.py    # Periodic data classification scanning
      dag_freshness_check.py        # Freshness SLA monitoring
  tests/
    unit/
      test_classification.py
      test_audit_schema.py
      test_anomaly_detector.py
      test_ranger_policies.py
    integration/
      test_ranger_masking.py        # Ranger column masking integration tests
      test_ranger_row_filter.py     # Ranger row-level filtering tests
      test_audit_pipeline.py        # Audit aggregation integration tests
      test_catalog_ingestion.py     # OpenMetadata ingestion tests
```

### Pattern 1: Tag-Based Data Classification
**What:** Assign sensitivity tags (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED) to columns via Ranger's tag service. Masking policies are defined on tags, not individual columns.
**When to use:** Always -- this is the locked decision for scaling to 300+ sources.
**Example:**
```python
# Source: Apache Ranger Python client (PyPI apache-ranger)
from apache_ranger.client.ranger_client import RangerClient
from apache_ranger.model.ranger_policy import RangerPolicy, RangerPolicyItem, RangerPolicyResource

ranger = RangerClient("http://ranger-admin:6080", ("admin", "rangerR0cks!"))

# Create a tag-based masking policy for CONFIDENTIAL data
policy = RangerPolicy()
policy.service = "trino_tag"  # tag service name
policy.name = "confidential_column_masking"
policy.policyType = 1  # 1 = datamask policy
policy.resources = {"tag": RangerPolicyResource({"values": ["CONFIDENTIAL"]})}

# Define masking: show last 4 chars for data_readers group
mask_item = RangerPolicyItem()
mask_item.groups = ["data_readers"]
mask_item.dataMaskInfo = {"dataMaskType": "MASK_SHOW_LAST_4"}
policy.dataMaskPolicyItems = [mask_item]

ranger.create_policy(policy)
```

### Pattern 2: Grafana + Marquez Lineage Dashboard
**What:** Use Grafana Infinity data source plugin to query Marquez REST API and visualize lineage graphs with quality overlay.
**When to use:** For BCBS 239 compliance dashboards.
**Example:**
```json
// Grafana Infinity data source configuration (provisioning/datasources.yml)
// Source: Grafana Infinity plugin docs
{
  "name": "Marquez-API",
  "type": "yesoreyeram-infinity-datasource",
  "access": "proxy",
  "url": "http://marquez:5000",
  "jsonData": {
    "auth_method": "",
    "global_queries": []
  }
}

// Panel query to fetch lineage for a dataset:
// URL: /api/v1-beta/lineage?nodeId=dataset:lakehouse:gold.risk_report
// Parser: JSONPath
// Root: $.graph.nodes[*]
// Columns: type, id, data.latestRun.state
```

### Pattern 3: Cross-Engine Audit Aggregation
**What:** Each engine emits audit logs natively. An Airflow DAG runs daily to extract, transform, and load audit data into a common schema.
**When to use:** For GOVN-05 centralized audit trail.
**Example:**
```python
# Common audit schema (normalized across engines)
AUDIT_SCHEMA = {
    "audit_id": "UUID",
    "timestamp": "TIMESTAMP WITH TIME ZONE",
    "engine": "VARCHAR",        # trino | teradata | snowflake
    "user_name": "VARCHAR",
    "query_id": "VARCHAR",
    "query_text": "TEXT",
    "tables_accessed": "JSONB",  # [{schema, table}]
    "columns_accessed": "JSONB", # [{schema, table, column}]
    "rows_returned": "BIGINT",
    "bytes_scanned": "BIGINT",
    "masked_columns": "JSONB",   # columns where masking was applied
    "access_granted": "BOOLEAN",
    "source_engine_audit_id": "VARCHAR",
}

# Trino: HTTP event listener POSTs to audit service endpoint
# Teradata: Query DBC.QryLogV + DBC.DBQLObjTbl daily
# Snowflake: Query SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY daily
```

### Pattern 4: OpenMetadata + OpenLineage Integration
**What:** OpenMetadata consumes OpenLineage events via Kafka to ingest pipeline lineage alongside catalog metadata.
**When to use:** For PLAT-01 catalog + lineage integration.
**Architecture:**
```
Airflow/Spark --> OpenLineage events --> Kafka topic --> OpenMetadata OpenLineage connector
                                     |
                                     --> Marquez (existing, receives via HTTP)

OpenMetadata Trino connector --> Trino metadata + profiling
OpenMetadata UI --> Search, glossary, lineage, profiling, freshness
```

### Anti-Patterns to Avoid
- **Column-by-column masking rules:** Do NOT create individual masking policies per column. Use tag-based policies keyed to classification tags (CONFIDENTIAL, PII, etc.). Column-by-column does not scale to 300+ sources.
- **Querying Marquez DB directly:** Do NOT bypass the Marquez REST API to query its PostgreSQL database. The API provides stable lineage graph traversal; the DB schema is an implementation detail.
- **Single monolithic audit table:** Do NOT dump raw audit logs from all engines into one denormalized table. Use a normalized common schema with engine-specific extraction logic.
- **Building a custom data catalog:** Do NOT hand-roll search, profiling, or glossary features. OpenMetadata provides all of these out of the box.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Column masking | Custom Trino UDFs for masking | Ranger column masking policies | Ranger handles dynamic masking per user/group with multiple mask types. Custom UDFs cannot enforce per-user visibility. |
| Data catalog search | Custom Elasticsearch indexing of table metadata | OpenMetadata search | OpenMetadata indexes table, column, tag, and glossary metadata automatically with relevance ranking. |
| Business glossary | Custom wiki/database for term definitions | OpenMetadata glossary with approval workflow | Native Draft->Review->Approved workflow, hierarchical terms, related terms, tag linkage -- extensive feature set. |
| Data profiling | Custom PySpark jobs to compute column stats | OpenMetadata data profiler | Built-in profiler computes null rates, unique counts, distributions, histograms, min/max. Scheduled via UI. |
| Lineage graph traversal | Custom graph queries on Marquez DB | Marquez REST API /lineage endpoint | API returns proper graph structure (nodes + edges) with upstream/downstream traversal built in. |
| PDF report generation | Custom PDF rendering from dashboard data | grafana-reporter or Grafana Enterprise reporting | Handles dashboard screenshot rendering, pagination, scheduling. |
| Audit log parsing | Custom parsers for each engine's audit format | Engine-specific extractors with common schema | Teradata DBQL, Snowflake ACCESS_HISTORY, and Trino event listener each have well-documented formats. |

**Key insight:** This phase integrates mature, battle-tested governance tools. The engineering effort should focus on configuration, integration, and policy definition -- not building custom governance infrastructure.

## Common Pitfalls

### Pitfall 1: Ranger Plugin Version Mismatch with Trino
**What goes wrong:** The Ranger Trino plugin version must match the Trino server version closely. The community demo targets Trino 433; our stack uses Trino 479.
**Why it happens:** The Ranger Trino plugin is compiled against specific Trino SPI versions. Mismatches cause ClassNotFoundException or NoSuchMethodError at runtime.
**How to avoid:** Use Ranger 2.8.0 which includes Trino plugin support. Verify the plugin is built for Trino 479 or build from source targeting the correct Trino version. Test plugin loading before configuring policies.
**Warning signs:** Trino fails to start or logs `SystemAccessControl` loading errors.

### Pitfall 2: Ranger Policy Cache Stale After Updates
**What goes wrong:** Policy changes in Ranger Admin do not take effect immediately. The Trino plugin polls Ranger Admin at configured intervals (default can be 30 seconds).
**Why it happens:** The Ranger plugin caches policies locally in `/etc/ranger/<service>/policycache`. Cache refresh depends on poll interval configuration.
**How to avoid:** Configure `ranger.plugin.trino.policy.pollIntervalMs` to an appropriate value (e.g., 5000ms for dev, 30000ms for production). Understand that policy changes are eventually consistent.
**Warning signs:** Policy change in Ranger UI has no effect; tests fail intermittently after policy updates.

### Pitfall 3: OpenMetadata Memory Requirements
**What goes wrong:** OpenMetadata server and ingestion containers fail to start or OOM-kill.
**Why it happens:** OpenMetadata requires minimum 2 vCPU + 6 GiB for server and 2 vCPU + 8 GiB for ingestion container. Docker default memory limits are often too low.
**How to avoid:** Set explicit memory limits in docker-compose.yml: `mem_limit: 6g` for server, `mem_limit: 8g` for ingestion. Ensure the host has sufficient RAM (16+ GiB total recommended for the full stack).
**Warning signs:** Container restarts, Java OutOfMemoryError in logs.

### Pitfall 4: Marquez Lineage API Returns Empty Graph
**What goes wrong:** The `/api/v1-beta/lineage?nodeId=` endpoint returns empty nodes/edges even though lineage events were captured.
**Why it happens:** The nodeId format must exactly match: `dataset:{namespace}:{name}` or `job:{namespace}:{name}`. Namespace and name are case-sensitive and must match what OpenLineage emitters send.
**How to avoid:** First query `/api/v1/namespaces/{namespace}/datasets` to get exact dataset names. Use those names in lineage queries. The namespace for this project is "lakehouse" (set in Phase 2).
**Warning signs:** 200 OK response but empty graph structure.

### Pitfall 5: Trino HTTP Event Listener Performance Impact
**What goes wrong:** HTTP event listener adds latency to every query completion because it makes a synchronous POST.
**Why it happens:** The HTTP event listener POSTs to the configured endpoint on every query completion event. If the endpoint is slow or down, it can block Trino.
**How to avoid:** Point the HTTP event listener at a fast, local endpoint (e.g., a lightweight audit receiver service that writes to a queue/buffer). Configure retry count low (0 or 1) to avoid blocking. Consider using the MySQL event listener as an alternative if latency is a concern -- it writes to a MySQL table asynchronously.
**Warning signs:** Increased query latency after enabling event listener; Trino coordinator logs show connection timeouts.

### Pitfall 6: OpenMetadata Airflow Port Conflict
**What goes wrong:** OpenMetadata ships with its own Airflow instance on port 8080. The project already has Airflow on port 8081 (mapped from internal 8080).
**Why it happens:** OpenMetadata bundles Airflow for ingestion workflow management.
**How to avoid:** Use OpenMetadata's external Airflow ingestion option: run OpenMetadata ingestion pipelines from the existing Airflow instance rather than the bundled one. This avoids running two Airflow instances. Alternatively, remap the OpenMetadata Airflow to a different port (e.g., 8082).
**Warning signs:** Port binding conflicts on Docker startup.

### Pitfall 7: Snowflake ACCESS_HISTORY Enterprise Requirement
**What goes wrong:** ACCESS_HISTORY view is empty or inaccessible.
**Why it happens:** The Snowflake ACCESS_HISTORY view is only available on Enterprise edition or higher. Standard edition does not include it.
**How to avoid:** Verify the Snowflake account is Enterprise edition. If not, fall back to QUERY_HISTORY view (available in all editions) which provides query-level but not column-level access tracking.
**Warning signs:** "Object does not exist" error when querying SNOWFLAKE.ACCOUNT_USAGE.ACCESS_HISTORY.

## Code Examples

### Ranger Trino Plugin Configuration
```xml
<!-- infra/docker/ranger/ranger-trino-security.xml -->
<!-- Source: Trino 479 Ranger documentation -->
<configuration>
  <property>
    <name>ranger.plugin.trino.service.name</name>
    <value>trino</value>
  </property>
  <property>
    <name>ranger.plugin.trino.policy.rest.url</name>
    <value>http://ranger-admin:6080</value>
  </property>
  <property>
    <name>ranger.plugin.trino.policy.pollIntervalMs</name>
    <value>5000</value>
  </property>
  <property>
    <name>ranger.plugin.trino.use.rangerGroups</name>
    <value>true</value>
  </property>
  <property>
    <name>ranger.plugin.trino.access.cluster.name</name>
    <value>lakehouse</value>
  </property>
</configuration>
```

### Trino Access Control Properties
```properties
# infra/docker/trino/etc/access-control.properties
# Source: Trino 479 documentation
access-control.name=ranger
ranger.service.name=trino
ranger.plugin.config.resource=/etc/trino/ranger/ranger-trino-security.xml,/etc/trino/ranger/ranger-trino-audit.xml
ranger.hadoop.config.resource=
```

### Trino HTTP Event Listener for Audit
```properties
# infra/docker/trino/etc/event-listener.properties
# Source: Trino 479 documentation
event-listener.name=http
http-event-listener.log-created=false
http-event-listener.log-completed=true
http-event-listener.connect-ingest-uri=http://audit-receiver:8090/api/v1/audit
http-event-listener.connect-retry-count=1
http-event-listener.connect-retry-delay=1s
http-event-listener.connect-max-delay=5s
```

### Ranger Row-Level Filter Policy
```python
# Source: Apache Ranger Python client + Ranger policy model docs
from apache_ranger.client.ranger_client import RangerClient
from apache_ranger.model.ranger_policy import (
    RangerPolicy, RangerPolicyItem, RangerPolicyResource, RangerRowFilterPolicyItem
)

ranger = RangerClient("http://ranger-admin:6080", ("admin", "rangerR0cks!"))

# Row-level filter: users in 'wealth_mgmt' group only see wealth_mgmt rows
policy = RangerPolicy()
policy.service = "trino"
policy.name = "gold_trades_bu_filter"
policy.policyType = 2  # 2 = row filter policy
policy.resources = {
    "catalog": RangerPolicyResource({"values": ["iceberg"]}),
    "schema": RangerPolicyResource({"values": ["gold"]}),
    "table": RangerPolicyResource({"values": ["trades"]}),
}

filter_item = RangerRowFilterPolicyItem()
filter_item.groups = ["wealth_mgmt"]
filter_item.rowFilterInfo = {"filterExpr": "business_unit = 'WEALTH_MGMT'"}
policy.rowFilterPolicyItems = [filter_item]

ranger.create_policy(policy)
```

### Marquez Lineage API Query for Compliance Dashboard
```python
# Source: Marquez REST API / OpenLineage blog
import requests

MARQUEZ_URL = "http://marquez:5000"
NAMESPACE = "lakehouse"

# Get lineage graph for a regulated report dataset
response = requests.get(
    f"{MARQUEZ_URL}/api/v1-beta/lineage",
    params={"nodeId": f"dataset:{NAMESPACE}:gold.bcbs239_risk_report", "depth": 10}
)
lineage = response.json()

# Extract nodes (jobs + datasets) and edges
nodes = lineage.get("graph", [])
for node in nodes:
    node_type = node.get("type")  # "DATASET" or "JOB"
    node_id = node.get("id")
    # For datasets: check latest run facets for quality scores
    if node_type == "DATASET":
        facets = node.get("data", {}).get("facets", {})
        quality = facets.get("dataQualityMetrics", {})
```

### OpenMetadata Trino Ingestion Configuration
```yaml
# Source: OpenMetadata v1.12.x documentation
source:
  type: trino
  serviceName: lakehouse-trino
  serviceConnection:
    config:
      type: Trino
      hostPort: trino:8080
      username: admin
      catalog: iceberg
      databaseSchema: ""
  sourceConfig:
    config:
      type: DatabaseMetadata
      markDeletedTables: true
      includeTables: true
      includeViews: true
      schemaFilterPattern:
        includes:
          - "bronze.*"
          - "silver.*"
          - "gold.*"

sink:
  type: metadata-rest
  config: {}

workflowConfig:
  openMetadataServerConfig:
    hostPort: http://openmetadata-server:8585/api
    authProvider: openmetadata
    securityConfig:
      jwtToken: "<ingestion-bot-jwt-token>"
```

### Legacy Lineage Stub Registration
```python
# Register Teradata/Snowflake as lineage stubs in Marquez
# Source: Marquez REST API
import requests

MARQUEZ_URL = "http://marquez:5000"

# Register a Teradata source dataset as an OpenLineage dataset
def register_legacy_lineage_stub(namespace, source_name, dataset_name, description):
    """Register a manually-defined dataset in Marquez for legacy system lineage."""
    payload = {
        "type": "DB_TABLE",
        "physicalName": f"{source_name}.{dataset_name}",
        "description": description,
        "sourceName": source_name,
        "fields": [],  # Schema can be populated if known
        "tags": ["legacy", source_name.lower()],
    }
    response = requests.put(
        f"{MARQUEZ_URL}/api/v1/namespaces/{namespace}/datasets/{source_name}.{dataset_name}",
        json=payload,
    )
    return response.json()

# Example: Register Teradata trade source
register_legacy_lineage_stub(
    "lakehouse", "teradata", "dw.trades_history",
    "Legacy Teradata trade history table - source for bronze.trades"
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| File-based RBAC (rules.json) | Apache Ranger policies (tag-based, dynamic) | Phase 3 migration | Dynamic policy updates without Trino restart. Tag-based scales to 300+ sources. |
| Marquez Web UI only for lineage | Grafana dashboards + Marquez API for compliance | Phase 3 new | Compliance-oriented views with quality overlay, SLA tracking, PDF export. |
| No data catalog | OpenMetadata for discovery, profiling, glossary | Phase 3 new | Self-service data discovery. Business users can find and understand data. |
| No audit trail | Centralized cross-engine audit in common schema | Phase 3 new | Regulatory compliance. Column-level access tracking. Anomaly detection. |
| OpenLineage -> Marquez only | OpenLineage -> Marquez + OpenMetadata (dual) | Phase 3 | Lineage visible in both compliance dashboards and data catalog. |

**Deprecated/outdated:**
- **Phase 1 rules.json RBAC**: Replaced by Ranger policies. Keep rules.json as documentation reference only.
- **Marquez Web UI (port 3000)**: Still available for debugging but compliance users should use Grafana dashboards. OpenMetadata will also show lineage.

## Open Questions

1. **Ranger Trino Plugin Compatibility with Trino 479**
   - What we know: Ranger 2.8.0 includes Trino plugin. Community demos target Trino 433.
   - What's unclear: Whether the 2.8.0 plugin binary works out-of-the-box with Trino 479 or requires a rebuild.
   - Recommendation: Plan a Wave 0 task to verify plugin loading with Trino 479. If incompatible, build plugin from Ranger source against Trino 479 SPI.

2. **OpenMetadata PostgreSQL vs MySQL Backend**
   - What we know: OpenMetadata supports both PostgreSQL and MySQL. The project already runs PostgreSQL 15 (3 instances).
   - What's unclear: Whether the PostgreSQL backend has full feature parity with MySQL in OpenMetadata 1.12.x.
   - Recommendation: Use PostgreSQL to avoid adding MySQL to the stack. The docker-compose-postgres.yml variant is officially provided.

3. **Kafka for OpenLineage Event Routing**
   - What we know: OpenMetadata's OpenLineage connector consumes events from Kafka. Currently, OpenLineage events go directly to Marquez via HTTP.
   - What's unclear: Whether adding Kafka solely for this purpose is worth the complexity.
   - Recommendation: Configure Airflow/Spark to emit OpenLineage events to both HTTP (Marquez) and Kafka (OpenMetadata), or use Marquez as the single source and have OpenMetadata ingest lineage from Marquez via its Trino connector's lineage extraction feature rather than a separate Kafka path.

4. **LDAP/AD Integration for Ranger Group Sync**
   - What we know: The design requires AD groups -> Ranger roles mapping. Phase 1 noted LDAP auth connection needs AD server access.
   - What's unclear: Whether LDAP/AD connectivity will be available in the dev environment.
   - Recommendation: Implement with mock LDAP groups for dev/test. Use Ranger's UserSync module for production. Plan the abstraction so LDAP can be swapped in when available.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `etl/pyproject.toml` ([tool.pytest.ini_options]) |
| Quick run command | `cd etl && python -m pytest tests/unit -x -q` |
| Full suite command | `cd etl && python -m pytest tests/ -x -q --strict-markers` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-03 | Column masking applied for unauthorized roles | integration | `cd etl && python -m pytest tests/integration/test_ranger_masking.py -x` | No -- Wave 0 |
| SEC-04 | Row-level filtering restricts by business unit | integration | `cd etl && python -m pytest tests/integration/test_ranger_row_filter.py -x` | No -- Wave 0 |
| GOVN-02 | Lineage visible for regulated report end-to-end | integration | `cd etl && python -m pytest tests/integration/test_compliance_lineage.py -x` | No -- Wave 0 |
| GOVN-03 | Classification tags applied to PII columns | unit + integration | `cd etl && python -m pytest tests/unit/test_classification.py -x` | No -- Wave 0 |
| GOVN-04 | Business glossary terms searchable and have definitions | integration | `cd etl && python -m pytest tests/integration/test_catalog_glossary.py -x` | No -- Wave 0 |
| GOVN-05 | Audit trail captures access across all three engines | unit + integration | `cd etl && python -m pytest tests/unit/test_audit_schema.py tests/integration/test_audit_pipeline.py -x` | No -- Wave 0 |
| PLAT-01 | Data catalog search returns datasets with profiling | integration | `cd etl && python -m pytest tests/integration/test_catalog_ingestion.py -x` | No -- Wave 0 |
| PLAT-03 | Data freshness visible per table with SLA status | unit + integration | `cd etl && python -m pytest tests/unit/test_freshness_tracker.py -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd etl && python -m pytest tests/unit -x -q`
- **Per wave merge:** `cd etl && python -m pytest tests/ -x -q --strict-markers`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `etl/tests/unit/test_classification.py` -- covers GOVN-03 tag classification logic
- [ ] `etl/tests/unit/test_audit_schema.py` -- covers GOVN-05 common audit schema validation
- [ ] `etl/tests/unit/test_anomaly_detector.py` -- covers GOVN-05 anomaly detection heuristics
- [ ] `etl/tests/unit/test_ranger_policies.py` -- covers SEC-03, SEC-04 policy definition structure
- [ ] `etl/tests/unit/test_freshness_tracker.py` -- covers PLAT-03 freshness logic
- [ ] `etl/tests/integration/test_ranger_masking.py` -- covers SEC-03 column masking with Ranger
- [ ] `etl/tests/integration/test_ranger_row_filter.py` -- covers SEC-04 row filtering with Ranger
- [ ] `etl/tests/integration/test_compliance_lineage.py` -- covers GOVN-02 lineage visualization data
- [ ] `etl/tests/integration/test_catalog_glossary.py` -- covers GOVN-04 glossary functionality
- [ ] `etl/tests/integration/test_audit_pipeline.py` -- covers GOVN-05 audit aggregation
- [ ] `etl/tests/integration/test_catalog_ingestion.py` -- covers PLAT-01 catalog discovery
- [ ] `etl/src/governance/__init__.py` -- governance module package init
- [ ] Docker Compose additions: Ranger (admin + db + solr + zk), OpenMetadata (server + ingestion + elasticsearch)

## Sources

### Primary (HIGH confidence)
- [Trino 479 Ranger access control docs](https://trino.io/docs/current/security/ranger-access-control.html) -- Ranger plugin configuration, properties, policy requirements
- [Trino 479 HTTP event listener docs](https://trino.io/docs/current/admin/event-listeners-http.html) -- Audit event listener configuration and data captured
- [OpenMetadata v1.12.x Trino connector docs](https://docs.open-metadata.org/v1.12.x/connectors/database/trino) -- Trino metadata ingestion, profiling, lineage
- [OpenMetadata v1.12.x OpenLineage connector](https://docs.open-metadata.org/v1.12.x/connectors/pipeline/openlineage) -- OpenLineage event consumption via Kafka
- [OpenMetadata v1.12.x glossary approval workflow](https://docs.open-metadata.org/latest/how-to-guides/data-governance/glossary/approval) -- Draft/review/approved states, reviewer assignment
- [OpenMetadata Docker deployment](https://docs.open-metadata.org/v1.12.x/quick-start/local-docker-deployment) -- Docker Compose setup, ports, requirements
- [OpenMetadata minimum requirements](https://docs.open-metadata.org/latest/deployment/minimum-requirements) -- 2 vCPU + 6 GiB server, 2 vCPU + 8 GiB ingestion
- [Apache Ranger Docker Hub images](https://hub.docker.com/r/apache/ranger) -- Official images: ranger, ranger-db, ranger-solr, ranger-zk
- [Apache Ranger Docker setup wiki](https://cwiki.apache.org/confluence/display/RANGER/Run+Ranger+in+Docker+using+DockerHub+Images) -- Docker run commands, service dependencies
- [Apache Ranger policy model](https://ranger.apache.org/blogs/policy_model.html) -- Tag-based policies, resource-based policies, data masking types
- [Apache Ranger REST APIs](https://cwiki.apache.org/confluence/display/RANGER/REST+APIs+for+Policy+Management) -- Policy CRUD operations
- [Apache Ranger tag-based policies](https://cwiki.apache.org/confluence/display/RANGER/Tag+Based+Policies) -- Tag service, tag-based masking, classification-driven authorization
- [apache-ranger PyPI](https://pypi.org/project/apache-ranger/) -- Python client for Ranger REST API
- [Marquez REST API blog](https://openlineage.io/blog/explore-lineage-api/) -- Lineage API endpoints, graph traversal
- [Snowflake ACCESS_HISTORY docs](https://docs.snowflake.com/en/sql-reference/account-usage/access_history) -- Column-level access audit view
- [Grafana Infinity plugin](https://grafana.com/grafana/plugins/yesoreyeram-infinity-datasource/) -- REST API data source for JSON/CSV/GraphQL

### Secondary (MEDIUM confidence)
- [OpenMetadata profiler metrics](https://docs.open-metadata.org/v1.12.x/how-to-guides/data-quality-observability/profiler/metrics) -- Freshness tracking via system metrics (INSERT/UPDATE/DELETE operations)
- [Trino Ranger demo (nil1729)](https://github.com/nil1729/trino-ranger-demo) -- Docker Compose reference for Ranger+Trino integration
- [Trino Ranger demo (aakashnand)](https://github.com/aakashnand/trino-ranger-demo) -- Another Docker Compose reference
- [Cloudera Ranger column masking docs](https://docs.cloudera.com/data-warehouse/1.5.5/dw-securing/topics/dw-trino-ranger-column-masking.html) -- Masking types: MASK, MASK_SHOW_LAST_4, MASK_SHOW_FIRST_4, MASK_HASH, MASK_NULL, MASK_NONE, custom
- [grafana-reporter](https://github.com/IzakMarais/reporter) -- PDF export service for Grafana OSS dashboards
- [Teradata DBQL documentation](https://www.dwhpro.com/teradata-query-logging-dbql/) -- DBQL tables, query logging configuration

### Tertiary (LOW confidence)
- OpenMetadata data freshness for Trino: documentation confirms INSERT/UPDATE/DELETE tracking for BigQuery/Redshift/Snowflake. For Trino/Iceberg, freshness may need custom implementation via Iceberg snapshot timestamps. Needs validation.
- Ranger 2.8.0 Trino plugin compatibility with Trino 479: community demos use older Trino versions. Binary compatibility needs runtime verification.
- OpenMetadata PostgreSQL backend feature parity with MySQL: officially supported but less commonly documented in community examples.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All tools have official Docker images, documented APIs, and active communities. OpenMetadata recommendation is MEDIUM-HIGH (strong evidence for simpler deployment + native features, but final validation needed for Trino/Iceberg freshness tracking).
- Architecture: HIGH -- Patterns follow documented integration paths. Grafana Infinity + Marquez API is well-supported. Ranger tag-based policies are a core feature.
- Pitfalls: MEDIUM-HIGH -- Most pitfalls sourced from official docs and community issues. Ranger/Trino version compatibility is the main uncertainty.

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (30 days -- stable ecosystem, no fast-moving changes expected)
