# Trino Deployment Reference

Covers all three deployment forms: Docker Compose (local dev), Helm (Kubernetes),
and Terraform (infrastructure provisioning). Explains the coordinator/worker split,
workload isolation via resource groups, LDAP auth, TLS, and the three-phase access
control migration path.

---

## Architecture Overview

Trino is a **distributed SQL query engine with no storage of its own.** It translates
SQL into parallel reads from Iceberg Parquet files on S3/Pure Storage, executes joins and
aggregations in-memory across worker nodes, and returns results. It never holds data
between queries.

```
Consumers (Python ETL / Soda / Power BI / AI agents)
                    │  SQL over HTTP / JDBC
                    ▼
            TRINO COORDINATOR
            ├─ Parses SQL
            ├─ Checks RBAC (file rules or Ranger)
            ├─ Applies column masking (Ranger Phase 3)
            ├─ Routes query to resource group
            ├─ Distributes work to workers
            └─ Logs query to audit receiver
                    │
           ┌────────┴────────┐
           ▼                 ▼
       WORKER 1 ... WORKER N          ← scales horizontally
       Read Parquet from S3 in parallel
                    │
          asks "where is this table?"
                    ▼
                 NESSIE              ← returns S3 path + snapshot + schema
                    │
                    ▼
             S3 / Pure Storage             ← actual Parquet files
```

---

## Form 1 — Docker Compose (Local Dev / POC)

Single Trino container. Coordinator and worker run in the same JVM process.
2GB heap. No auth, no TLS. Full 18-service stack starts with:

```bash
docker compose up
```

Config files are volume-mounted read-only:

```yaml
volumes:
  - ./infra/docker/trino/etc/config.properties:/etc/trino/config.properties:ro
  - ./infra/docker/trino/etc/catalog/iceberg.properties:/etc/trino/catalog/iceberg.properties:ro
  - ./infra/docker/trino/etc/resource-groups:/etc/trino/resource-groups:ro
  - ./infra/docker/trino/etc/event-listener.properties:/etc/trino/event-listener.properties:ro
  - ./infra/docker/trino/etc/access-control:/etc/trino/access-control:ro
```

To change config: edit the file, `docker compose restart trino`.

Startup dependency order (all health-checked before next service starts):
```
postgres → minio → minio-init → nessie → trino → cube-api
                                                → airflow → soda
```

---

## Form 2 — Kubernetes via Helm

In production Trino runs as two separate Kubernetes Deployments:

**Coordinator pod** — query planning and distribution only.
- 1–4 CPU cores, `${coordinator_memory}` RAM (8GB in prod)
- Does not execute query work in production (`node-scheduler.include-coordinator=false`)
- Exposes port 8443 (HTTPS) via ClusterIP Service

**Worker pods (N)** — parallel data reading and computation.
- 2–8 CPU cores each, `${worker_memory}` RAM (32GB in prod)
- Scale horizontally: add workers to increase throughput and memory
- Workers register with coordinator via `discovery.uri`

Scale workers by changing one Terraform variable:
```hcl
# prod.tfvars
trino_workers = 8   # increase for higher throughput
```

### Resource sizing guide

| Environment | Workers | Worker RAM | Use case |
|---|---|---|---|
| dev | 1 | 8 GB | Local development, single-user |
| staging | 2 | 16 GB | Integration testing, team shared |
| prod (initial) | 4–6 | 32 GB | 300+ sources, concurrent BI + ETL |
| prod (scaled) | 8–12 | 32 GB | Peak load, large Silver rebuilds |

---

## Form 3 — Terraform

Terraform's `modules/trino` does three things on `terraform apply`:

### 1. Deploys the Helm release
```hcl
resource "helm_release" "trino" {
  repository = "https://trinodb.github.io/charts"
  chart      = "trino"
  version    = var.trino_chart_version
  values     = [templatefile("values.yaml.tpl", { ... })]
}
```
`values.yaml.tpl` is rendered with environment-specific variables injected at plan
time. Dev, staging, and prod share the same template — only the variable values differ.

### 2. Creates the RBAC ConfigMap
```hcl
resource "kubernetes_config_map" "trino_access_rules" {
  data = { "rules.json" = var.access_control_rules }
}
```
Trino hot-reloads this file every 60 seconds. Update access policy with
`terraform apply` — no pod restart, no downtime.

### 3. Provisions TLS via cert-manager
```hcl
resource "kubernetes_manifest" "trino_certificate" {
  # cert-manager Certificate → Let's Encrypt → JKS keystore → K8s Secret
  # Mounted into Trino pod at /tls/keystore.jks
  # Auto-renewed before expiry — zero manual rotation
}
```

---

## Workload Isolation — Resource Groups

Every Trino query is assigned to a resource group that limits its memory and
concurrency. Groups are defined in `infra/docker/trino/etc/resource-groups/rules.json`.

### Memory allocation (% of total cluster memory)

```
engineering  60%
  etl_pipelines  40%   ← Bronze→Silver→Gold transforms, Airflow DAGs
  soda_quality   15%   ← Soda quality gate checks
  schema_ops      5%   ← CREATE/ALTER TABLE

bi           35%
  cube_semantic  20%   ← AI middleware + Cube REST/SQL API
  power_bi       10%   ← Power BI DirectQuery
  tableau         5%   ← Tableau

ai_agents     5%       ← Borealis, RBC Assist, FastAPI middleware
```

Memory limits are **soft** — groups burst freely when headroom exists. Under
contention the scheduler enforces ratios. Timeouts are **hard** — queries exceeding
their limit are killed.

| Group | Memory | Concurrent | Timeout |
|---|---|---|---|
| etl_pipelines | 40% | 15 | 4 hours |
| soda_quality | 15% | 5 | 30 min |
| schema_ops | 5% | 3 | 10 min |
| cube_semantic | 20% | 20 | 5 min |
| power_bi | 10% | 15 | 10 min |
| tableau | 5% | 10 | 10 min |
| ai_agents | 5% | 5 | **2 min** |

### Routing

Routing uses the connection's `user` (service account) and `source` tag. Use the
named constructors in `etl/src/iceberg_utils/trino.py`:

```python
conn = get_etl_connection()          # → engineering.etl_pipelines
conn = get_soda_connection()         # → engineering.soda_quality
conn = get_schema_ops_connection()   # → engineering.schema_ops
conn = get_ai_connection()           # → ai_agents
conn = get_nessie_branch_connection( # → engineering.soda_quality (branch-scoped)
    "ingest/account-master-20260320"
)
```

Cube and Power BI set their `source` tag automatically — no code change needed.

---

## Three-Phase Access Control

### Phase 1 — File-based RBAC (active now in local dev)

`infra/docker/trino/etc/access-control/rules.json`

Three roles: `data_admin` (full), `data_engineers` (read/write except sensitive_ns),
`data_readers` (SELECT only, no sensitive_ns). Schema-level only — no column masking.

Active via `config.properties`:
```properties
access-control.name=file
security.config-file=/etc/trino/access-control/rules.json
```

Hot-reloads every 60 seconds. Update the file, Trino picks it up automatically.

### Phase 2 — LDAP Authentication (staging/prod)

Activate by uncommenting in `config.properties`:
```properties
http-server.authentication.type=PASSWORD
http-server.https.enabled=true
http-server.https.port=8443
```

Set env vars: `LDAP_URL`, `LDAP_USER_BASE_DN`, `LDAP_BIND_PATTERN`.

User identity is now the LDAP principal — logged in every audit event and evaluated
by Ranger in Phase 3.

### Phase 3 — Apache Ranger (column masking + row filters)

Replace file-based access control:
```properties
access-control.name=ranger
ranger.service.name=trino
ranger.plugin.config.resource=/etc/trino/ranger/ranger-trino-security.xml, \
  /etc/trino/ranger/ranger-trino-audit.xml
```

⚠️ **Compatibility check required**: Ranger Trino plugin targets Trino 433.
Current deployment is Trino 479. Verify JAR compatibility or build plugin from
source before enabling in production.

Layer-based access tiers (define as Ranger policies):

| Role | Bronze | Silver | Gold | Vector Store |
|---|---|---|---|---|
| `data_engineer` | R/W | R/W | R/W | — |
| `data_analyst` | ❌ | ❌ | Read | — |
| `bi_tool_svc` | ❌ | ❌ | Read | — |
| `pipeline_svc` | R/W | R/W | R/W | Write |
| `ai_agent_svc` | ❌ | ❌ | Read (via Cube) | Read |
| `admin` | Full | Full | Full | Full |

Column masking policies:

| Column | Roles masked | Mask type |
|---|---|---|
| `cust_sin`, `full_name`, `email` | all except `pii_authorized` | MASK_HASH |
| `avail_bal_amt`, `ledger_bal_amt` | `data_analyst`, `bi_tool_svc` | NULLIFY |
| `acct_nbr` | `data_analyst` | LAST_4 |

Ranger policy refresh: 30 seconds. Policies function from local cache if Ranger Admin
is temporarily unavailable (does not fail open).

---

## Observability

Resource group utilisation via Trino system tables:

```sql
-- Running queries by group + memory usage
SELECT resource_group_id,
       COUNT(*)                              AS running,
       SUM(total_memory_reservation) / 1e9  AS memory_gb,
       MAX(elapsed_time)                     AS longest
FROM   system.runtime.queries
WHERE  state = 'RUNNING'
GROUP  BY 1
ORDER  BY memory_gb DESC;

-- Queued queries (waiting for concurrency slot)
SELECT resource_group_id, query_id, queued_time, query
FROM   system.runtime.queries
WHERE  state = 'QUEUED'
ORDER  BY queued_time DESC;
```

Add both queries as panels in `infra/docker/grafana/dashboards/pipeline_observability.json`.

Prometheus metrics via Trino JMX connector:
```sql
SELECT *
FROM   jmx.current."trino.execution:name=QueryManager"
-- Exposes: queuedQueries, runningQueries, completedQueries, failedQueries
```

---

## Key Files

| File | Purpose |
|---|---|
| `infra/docker/trino/etc/config.properties` | Main config: coordinator, auth, access control, resource groups |
| `infra/docker/trino/etc/catalog/iceberg.properties` | Nessie REST catalog wiring |
| `infra/docker/trino/etc/resource-groups/rules.json` | Workload isolation — group definitions and selectors |
| `infra/docker/trino/etc/resource-groups/resource-groups.properties` | Activates resource groups |
| `infra/docker/trino/etc/access-control/rules.json` | Phase 1 file-based RBAC |
| `infra/docker/trino/etc/event-listener.properties` | Query audit → audit-receiver HTTP |
| `infra/docker/trino/etc/jvm.config` | Heap size, GC settings |
| `infra/terraform/modules/trino/main.tf` | Helm release + ConfigMap + cert-manager cert |
| `infra/terraform/modules/trino/values.yaml.tpl` | Helm values template (env-parameterised) |
| `etl/src/iceberg_utils/trino.py` | Python connection factory with named workload constructors |
| `docs/adr/002-trino-as-mandatory-query-gateway.md` | Why Trino is the only read/write path |
| `docs/adr/004-trino-workload-isolation.md` | Why resource groups, allocation rationale |
