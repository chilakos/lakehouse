# Phase 1: Foundation and Feasibility Validation - Research

**Researched:** 2026-03-13
**Domain:** Multi-engine Iceberg lakehouse with Nessie catalog, hybrid storage (S3 + MinIO), CI/CD, and baseline security
**Confidence:** MEDIUM-HIGH

## Summary

Phase 1 proves the core architectural premise: can Trino, Teradata OTF, and Snowflake all read the same Iceberg tables through a shared Nessie catalog on both AWS S3 (cloud) and MinIO (on-prem)? The user has locked Nessie as the catalog choice, which differs from the project-level research recommendation of AWS Glue. This creates a known risk: Teradata OTF has NO documented support for Nessie or any REST catalog -- only AWS Glue, Hive Metastore, and Unity Catalog are confirmed. The CONTEXT.md explicitly plans for this: "Teradata OTF validation in week 1 -- if OTF REST catalog support is blocked, pivot to Trino query federation to Teradata as the bridge and document the gap."

The phase also establishes the mono-repo structure (/infra, /etl, /dbt, /ci), Terraform IaC, GitHub Actions CI/CD with branch-based environment promotion, and baseline security (SSO/LDAP for Trino, RBAC via file-based access control, S3 SSE-KMS encryption, TLS everywhere). A synthetic financial dataset (trades, positions, risk metrics) avoids compliance overhead while providing realistic test data. The feasibility deliverable is a live demo to leadership plus a written benchmark report.

Nessie 0.107.4 is the latest release (March 9, 2026), with mature Iceberg REST catalog support, PostgreSQL backend, and Helm chart deployment. Trino 479 supports Nessie natively via both the Nessie catalog type and REST catalog protocol. Snowflake supports Iceberg REST catalogs via CREATE CATALOG INTEGRATION (ICEBERG_REST). The technology stack is well-documented, but the Teradata-Nessie integration gap is the single highest-risk item in this phase.

**Primary recommendation:** Validate Teradata OTF + Nessie interoperability in the first week. Deploy Nessie on Kubernetes with PostgreSQL backend. Use Trino's native Nessie catalog type. Configure Snowflake via REST catalog integration. Establish CI/CD and security in parallel.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Nessie as the centralized Iceberg catalog (REST catalog spec)
- Single-region HA deployment with replicas (not multi-region)
- PostgreSQL as the Nessie metadata backing store
- Main branch only for Phase 1 -- Nessie branching capability explored in later phases once foundation is proven
- Nessie must serve Trino, Teradata OTF, and Snowflake from the same catalog instance
- Keep MinIO as the on-prem S3-compatible storage (team already operates it)
- Small proof dataset (< 100 GB) sufficient for Phase 1 feasibility
- On-prem storage serves both regulatory/data residency requirements AND performance/latency needs for on-prem consumers
- MinIO deployment should mirror S3 bucket structure for consistency
- Mono-repo with top-level folders: /infra, /etl, /dbt, /ci
- Terraform for all infrastructure-as-code (Trino, Nessie, Airflow, storage config)
- Branch-based environment promotion: feature branches -> PR to dev -> merge to staging -> merge to main (prod)
- GitHub Actions as the CI/CD engine
- Separate Trino cluster and Nessie catalog per environment (dev/staging/prod) -- full isolation, no shared infrastructure
- Synthetic financial dataset (trades, positions, risk metrics) -- no compliance overhead, fully controlled
- Feasibility deliverable: live demo to leadership + written benchmark report (latency, throughput, resource usage)
- Teradata OTF validation in week 1 -- if OTF REST catalog support is blocked, pivot to Trino query federation to Teradata as the bridge and document the gap
- Schema evolution testing (add column, widen type) included in feasibility proof -- validates FNDTN-04 and demonstrates Iceberg's core value

### Claude's Discretion
- Trino cluster sizing and worker configuration
- Nessie deployment method (Docker, Kubernetes, bare metal)
- TLS certificate management approach
- Synthetic data generation tooling
- Benchmark test harness design
- MinIO cluster topology for Phase 1

### Deferred Ideas (OUT OF SCOPE)
- Nessie branching for schema change management -- explore after Phase 1 proves the basics
- Multi-region catalog HA -- revisit if workloads expand across regions
- Data mesh domain-based repo structure -- premature for Phase 1, consider for v2
- Real production data for testing -- requires governance approvals, use synthetic first
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FNDTN-01 | Iceberg tables created and queryable on AWS S3 | Nessie + Trino Iceberg connector with S3 file system; PySpark with Iceberg REST catalog |
| FNDTN-02 | Iceberg tables created and queryable on MinIO (on-prem S3-compatible) | Nessie S3 object store config with path-style-access; Trino s3.endpoint override; MinIO bucket mirroring |
| FNDTN-03 | Centralized Iceberg catalog deployed supporting both S3 and MinIO storage backends | Nessie supports multiple warehouse configurations and per-bucket S3 overrides |
| FNDTN-04 | Iceberg schema evolution works without data rewrites across all engines | Iceberg metadata-only schema changes (add column, widen type) verified for Trino and Snowflake |
| FNDTN-05 | Iceberg partition evolution supported for query performance optimization | Iceberg hidden partitioning supported by Trino; partition evolution is metadata-only |
| FNDTN-06 | Automated Iceberg table maintenance (compaction, snapshot expiration, orphan file cleanup) | PySpark procedures: rewrite_data_files, expire_snapshots, remove_orphan_files |
| QUERY-01 | Trino reads Iceberg tables from both S3 and MinIO via shared catalog | Trino Nessie catalog type with S3 native file system config; endpoint override for MinIO |
| QUERY-02 | Trino writes Iceberg tables (ETL output, Silver/Gold transformations) | Trino Iceberg connector supports full DML: INSERT, UPDATE, DELETE, MERGE |
| QUERY-03 | Teradata OTF reads Iceberg tables from S3 via shared catalog (feasibility validated) | HIGH RISK: Teradata OTF does NOT document REST/Nessie support; fallback to Trino federation |
| QUERY-04 | Snowflake reads Iceberg tables via external tables (compute-only, no data copies) | Snowflake CREATE CATALOG INTEGRATION (ICEBERG_REST) connects to Nessie REST endpoint |
| QUERY-05 | All three engines see consistent table metadata from shared catalog | Nessie provides snapshot isolation; all engines read same metadata via REST protocol |
| QUERY-06 | Query performance benchmarked: Trino vs Teradata OTF vs direct Teradata | Synthetic dataset + benchmark harness; measure latency, throughput, resource usage |
| CICD-01 | GitHub repository structure established for ETL code, dbt models, and infrastructure | Mono-repo: /infra, /etl, /dbt, /ci with branch-based promotion |
| CICD-02 | CI/CD pipeline deployed via GitHub Actions for automated testing and deployment | GitHub Actions workflows for terraform plan/apply, Python tests, deployment |
| CICD-03 | Environment promotion workflow (dev -> staging -> production) | Branch-based: feature -> dev -> staging -> main (prod) with separate infrastructure per env |
| CICD-04 | Infrastructure as Code for lakehouse components | Terraform modules for Nessie, Trino, S3 buckets, MinIO config, IAM, networking |
| SEC-01 | SSO/LDAP/Active Directory authentication integrated with Trino | Trino LDAP authentication via password-authenticator.properties; HTTPS required |
| SEC-02 | Role-based access control (RBAC) enforced on catalogs, schemas, and tables | Trino file-based access control (rules.json) + Nessie authorization policies |
| SEC-05 | Encryption at rest (S3 SSE-KMS, MinIO equivalent) for all Iceberg data | S3 SSE-KMS with AWS KMS keys; MinIO SSE-KMS with KES + external KMS |
| SEC-06 | Encryption in transit (TLS) for all data movement and query traffic | TLS for Trino coordinator, Nessie API, MinIO, S3 endpoints |
</phase_requirements>

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| Apache Iceberg | 1.10.x (V2 spec) | Open table format | Only OTF with first-class support across Trino, Teradata, Snowflake, Spark |
| Project Nessie | 0.107.4 | Iceberg REST catalog with Git-like versioning | User decision. Supports REST spec, PostgreSQL backend, multi-warehouse, S3+MinIO |
| Trino | 479+ | Primary query engine | Iceberg connector with full DML, native Nessie support, LDAP auth, file-based RBAC |
| PySpark | 3.5.x | ETL engine for Iceberg writes and table maintenance | Native Iceberg write support, compaction procedures, distributed at PB scale |
| Terraform | 1.9.x+ | Infrastructure as Code | AWS resources, Kubernetes manifests, state management for audit trail |
| GitHub Actions | Current | CI/CD engine | Native GitHub integration, branch-based workflows, OIDC for AWS auth |
| PostgreSQL | 15+ | Nessie metadata backing store | User decision. Nessie JDBC2 store type reduces storage overhead |
| MinIO | Current deployment | On-prem S3-compatible storage | User decision. Team already operates it; mirror S3 bucket structure |
| AWS S3 | Current | Cloud object storage | Standard. SSE-KMS encryption, IAM policies, lifecycle management |

### Supporting

| Library/Tool | Version | Purpose | When to Use |
|-------------|---------|---------|-------------|
| PyIceberg | 0.11.x | Python-native Iceberg metadata operations | Schema evolution scripts, table maintenance utilities, CI test queries |
| DuckDB | 1.2.x | Local analytics, CI/CD test queries | Developer local testing, small dataset validation in CI pipelines |
| Faker | Latest | Synthetic data generation | Generate realistic trades, positions, risk metrics for feasibility proof |
| Docker / Kubernetes | Current | Container orchestration | Deploy Nessie, Trino on K8s; local dev with Docker Compose |
| Helm | 3.x | Kubernetes package manager | Nessie Helm chart (Bitnami), Trino Helm chart |
| cert-manager | Latest | TLS certificate automation on K8s | Automate Let's Encrypt or internal CA certificate issuance and renewal |
| pre-commit | Latest | Code quality gates | Python linting (ruff), Terraform fmt, secret scanning |
| pytest | 8.x | Python testing framework | Unit tests for ETL, integration tests with DuckDB |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Nessie | AWS Glue | Glue is confirmed with all engines but is AWS-locked, no on-prem support |
| Nessie | Apache Polaris | Polaris is also REST-spec; Nessie adds Git-like branching (deferred to Phase 2+) |
| MinIO | RustFS | RustFS is 2.3x faster, Apache 2.0, but very new and team has no operational experience |
| MinIO | Ceph RGW | Battle-tested but operationally heavy; overkill for Phase 1 proof dataset |
| Terraform | Pulumi | Pulumi offers real programming languages but smaller community for data infra |
| cert-manager | Manual certs | Manual certs do not scale and are error-prone for multi-environment setup |

**Installation:**
```bash
# Python ETL dependencies
pip install "pyspark>=3.5.0,<3.6.0" \
    "pyiceberg[s3fs,rest]>=0.11.0,<0.12.0" \
    "duckdb>=1.2.0,<1.3.0" \
    "faker>=30.0.0" \
    "pytest>=8.0.0" \
    "ruff>=0.9.0" \
    "pre-commit>=4.0.0" \
    "boto3>=1.35.0"

# Infrastructure tools
# Terraform: https://developer.hashicorp.com/terraform/install
# Helm: https://helm.sh/docs/intro/install/

# Nessie (via Helm)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install nessie bitnami/nessie --set versionStoreType=JDBC_POSTGRESQL

# Trino (via Helm)
helm repo add trino https://trinodb.github.io/charts
helm install trino trino/trino --version 0.31.0

# Nessie (via Docker for local dev)
docker pull ghcr.io/projectnessie/nessie:0.107.4
```

## Architecture Patterns

### Recommended Project Structure
```
lakehouse/
├── infra/                        # Infrastructure as Code
│   ├── terraform/
│   │   ├── modules/
│   │   │   ├── nessie/           # Nessie catalog deployment (K8s + PostgreSQL)
│   │   │   ├── trino/            # Trino cluster deployment (coordinator + workers)
│   │   │   ├── s3/               # S3 buckets, IAM policies, KMS keys
│   │   │   ├── minio/            # MinIO configuration (endpoint, buckets, encryption)
│   │   │   ├── networking/       # VPC, subnets, security groups, VPN/Direct Connect
│   │   │   └── monitoring/       # CloudWatch, Prometheus, Grafana
│   │   ├── environments/
│   │   │   ├── dev/              # Dev environment terraform.tfvars
│   │   │   ├── staging/          # Staging environment terraform.tfvars
│   │   │   └── prod/             # Production environment terraform.tfvars
│   │   ├── backend.tf            # S3 remote state configuration
│   │   ├── main.tf               # Module composition
│   │   ├── variables.tf          # Input variables
│   │   └── outputs.tf            # Output values
│   └── helm/
│       ├── nessie/               # Nessie Helm values overrides
│       └── trino/                # Trino Helm values overrides
├── etl/                          # Python ETL framework
│   ├── src/
│   │   ├── synthetic/            # Synthetic data generators (trades, positions, risk)
│   │   ├── iceberg_utils/        # Catalog interaction, table creation, maintenance
│   │   └── config/               # Environment-aware configuration (S3 vs MinIO)
│   ├── tests/
│   │   ├── unit/                 # Pure logic tests
│   │   └── integration/          # Tests against Nessie + Iceberg
│   ├── pyproject.toml            # Python project config
│   └── requirements.txt          # Pinned dependencies
├── dbt/                          # dbt project (placeholder for Phase 1)
│   └── .gitkeep
├── ci/                           # CI/CD pipeline definitions
│   └── .github/
│       └── workflows/
│           ├── ci.yml            # PR checks: lint, test, terraform plan
│           ├── deploy-dev.yml    # Deploy to dev on merge to dev branch
│           ├── deploy-staging.yml # Deploy to staging on merge to staging branch
│           ├── deploy-prod.yml   # Deploy to prod on merge to main
│           └── infra.yml         # Terraform plan/apply workflow
├── docs/                         # Architecture decisions, runbooks
│   ├── adr/                      # Architecture Decision Records
│   ├── benchmarks/               # Benchmark results and reports
│   └── swot/                     # SWOT analyses (catalog choice required by leadership)
├── .github/
│   └── workflows -> ../ci/.github/workflows  # Symlink for GitHub discovery
├── .pre-commit-config.yaml       # Pre-commit hooks configuration
└── .gitignore
```

### Pattern 1: Nessie as Centralized REST Catalog
**What:** Nessie serves as the single Iceberg catalog for all engines, exposing the Iceberg REST protocol. Each engine connects to Nessie's REST endpoint to discover tables, read metadata, and commit changes.
**When to use:** Always in this architecture -- Nessie is the locked catalog choice.
**Configuration:**

Nessie server (Docker/K8s environment variables):
```properties
# Nessie catalog configuration
nessie.version.store.type=JDBC2
quarkus.datasource.jdbc.url=jdbc:postgresql://postgres:5432/nessie
quarkus.datasource.username=nessie
quarkus.datasource.password=${NESSIE_DB_PASSWORD}

# Warehouse configuration
nessie.catalog.default-warehouse=lakehouse
nessie.catalog.warehouses.lakehouse.location=s3://lakehouse-data/

# S3 configuration (for cloud)
nessie.catalog.service.s3.default-options.region=us-east-1
nessie.catalog.service.s3.default-options.access-key=${AWS_ACCESS_KEY_ID}

# MinIO configuration (per-bucket override for on-prem)
nessie.catalog.service.s3.buckets.lakehouse-onprem.endpoint=https://minio.internal:9000
nessie.catalog.service.s3.buckets.lakehouse-onprem.path-style-access=true
nessie.catalog.service.s3.buckets.lakehouse-onprem.region=us-east-1
nessie.catalog.service.s3.buckets.lakehouse-onprem.access-key=${MINIO_ACCESS_KEY}
```

Trino catalog (etc/catalog/iceberg.properties):
```properties
connector.name=iceberg
iceberg.catalog.type=nessie
iceberg.nessie-catalog.uri=http://nessie:19120/api/v2
iceberg.nessie-catalog.ref=main
iceberg.nessie-catalog.default-warehouse-dir=s3://lakehouse-data/
fs.native-s3.enabled=true
s3.region=us-east-1
# For MinIO tables, Trino uses the location from catalog metadata
# which already points to minio endpoint
```

Alternative -- Trino via REST protocol (recommended for better compatibility):
```properties
connector.name=iceberg
iceberg.catalog.type=rest
iceberg.rest-catalog.uri=http://nessie:19120/iceberg
iceberg.rest-catalog.prefix=main
```

PySpark session configuration:
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("lakehouse-etl") \
    .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.lakehouse.type", "rest") \
    .config("spark.sql.catalog.lakehouse.uri", "http://nessie:19120/iceberg") \
    .config("spark.sql.catalog.lakehouse.warehouse", "lakehouse") \
    .config("spark.sql.catalog.lakehouse.io-impl",
            "org.apache.iceberg.aws.s3.S3FileIO") \
    .getOrCreate()
```

Snowflake catalog integration:
```sql
CREATE OR REPLACE CATALOG INTEGRATION nessie_catalog_int
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = 'default'
  REST_CONFIG = (
    CATALOG_URI = 'https://nessie.yourdomain.com/iceberg'
    PREFIX = 'main'
  )
  REST_AUTHENTICATION = (
    TYPE = BEARER
    BEARER_TOKEN = '<nessie_auth_token>'
  )
  ENABLED = TRUE;
```

### Pattern 2: Teradata OTF Fallback Strategy
**What:** If Teradata OTF cannot connect to Nessie (HIGH probability), use Trino as a federation bridge: Teradata queries Trino via JDBC/ODBC, and Trino reads Iceberg tables from Nessie.
**When to use:** When Teradata OTF lacks REST catalog support (validate in week 1).
**Approach:**

```
Teradata --> (JDBC/ODBC) --> Trino --> (Nessie catalog) --> Iceberg on S3/MinIO
```

Trino provides a Teradata connector for reverse federation too:
```properties
# etc/catalog/teradata.properties
connector.name=teradata
connection-url=jdbc:teradata://teradata-host/DATABASE=mydb
connection-user=${TERADATA_USER}
connection-password=${TERADATA_PASSWORD}
```

This allows Trino to join Iceberg tables with Teradata-native tables in a single query, providing a coexistence path.

### Pattern 3: Hybrid Cloud/On-Prem Storage with Nessie
**What:** Nessie manages tables stored on both AWS S3 and MinIO using per-bucket S3 configuration overrides. Tables are created with location pointing to the appropriate storage backend.
**When to use:** Always -- MinIO is the locked on-prem storage choice.
**Key detail:** Nessie's S3 credential vending means credentials are never exposed to clients. The server handles storage access on behalf of clients.

```python
# Creating a table on S3 (cloud)
spark.sql("""
    CREATE TABLE lakehouse.cloud_ns.trades (
        trade_id BIGINT,
        symbol STRING,
        quantity DECIMAL(18,4),
        price DECIMAL(18,4),
        trade_date DATE
    )
    USING iceberg
    LOCATION 's3://lakehouse-data/cloud_ns/trades'
""")

# Creating a table on MinIO (on-prem)
spark.sql("""
    CREATE TABLE lakehouse.onprem_ns.positions (
        position_id BIGINT,
        account_id STRING,
        symbol STRING,
        quantity DECIMAL(18,4),
        market_value DECIMAL(18,4),
        as_of_date DATE
    )
    USING iceberg
    LOCATION 's3://lakehouse-onprem/onprem_ns/positions'
""")
```

### Pattern 4: Branch-Based Environment Promotion
**What:** Feature branches -> PR to dev -> merge to staging -> merge to main (prod). Each environment has its own Nessie catalog, Trino cluster, and storage buckets -- full isolation.
**Implementation:**

```yaml
# ci/.github/workflows/deploy-dev.yml
name: Deploy to Dev
on:
  push:
    branches: [dev]
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write  # OIDC for AWS
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-arn: arn:aws:iam::role/github-actions-dev
          aws-region: us-east-1
      - uses: hashicorp/setup-terraform@v3
      - run: |
          cd infra/terraform
          terraform init
          terraform workspace select dev
          terraform apply -auto-approve -var-file=environments/dev/terraform.tfvars
```

### Anti-Patterns to Avoid
- **Multiple engines writing the same Iceberg table concurrently:** Causes optimistic concurrency retry storms. Designate one write-owner per table (PySpark for ETL).
- **Skipping table maintenance:** Without automated compaction, tables accumulate small files and query planning degrades to minutes. Compaction is Day 1, not "later."
- **Hardcoding environment-specific values:** Use Terraform variables and workspace-based configuration. Never hardcode S3 endpoints, Nessie URIs, or credentials.
- **Using Nessie native catalog type when REST works:** Trino's REST catalog type (`iceberg.catalog.type=rest`) provides better forward compatibility than the Nessie-specific type. Prefer REST.
- **Sharing infrastructure between environments:** Full isolation (separate Nessie + Trino per env) prevents dev changes from impacting production. This is a locked decision.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Iceberg table compaction | Custom file-merging scripts | PySpark `rewrite_data_files` procedure | Handles manifest rewriting, data file merging, concurrent access safely |
| Snapshot expiration | Manual snapshot deletion | PySpark `expire_snapshots` procedure | Correctly identifies orphaned files, respects retention policies |
| Orphan file cleanup | S3 listing + manual deletion | PySpark `remove_orphan_files` procedure | Avoids deleting files still referenced by active snapshots |
| TLS certificate management | Manual cert generation/renewal | cert-manager on K8s (or AWS ACM) | Auto-renewal, ACME protocol, handles rotation without downtime |
| Secrets management | Config files with credentials | AWS Secrets Manager or HashiCorp Vault | Rotation, audit trail, no secrets in code/git |
| Synthetic data generation | Custom random data scripts | Faker library with financial data providers | Deterministic seeding, realistic names/values, well-tested |
| Terraform remote state | Local state files | S3 backend with DynamoDB locking | Team collaboration, state locking, versioned state history |
| LDAP group resolution for Trino | Custom LDAP query code | Trino's built-in LDAP authenticator + group provider | Handles group caching, connection pooling, failover |

**Key insight:** Every item above has subtle edge cases (concurrent access, partial failure recovery, credential rotation) that mature tools handle correctly. Hand-rolling any of these will consume 2-4 weeks of engineering time and produce inferior results.

## Common Pitfalls

### Pitfall 1: Teradata OTF Cannot Connect to Nessie (HIGHEST RISK)
**What goes wrong:** Teradata OTF only documents support for AWS Glue, Hive Metastore, and Unity Catalog. No REST catalog (Nessie, Polaris) support is documented.
**Why it happens:** Teradata OTF is still maturing and lags the open-source catalog ecosystem. Teams choose a catalog for Trino/Snowflake without validating Teradata compatibility.
**How to avoid:** Validate in week 1. Have the fallback ready: Trino federation (Teradata queries Trino via JDBC, Trino reads Iceberg from Nessie). Document the gap for leadership.
**Warning signs:** No Teradata OTF REST catalog documentation found; Teradata engineering cannot confirm REST support.

### Pitfall 2: Trino-Nessie Configuration Conflicts
**What goes wrong:** Trino's strict interpretation of the Iceberg REST specification can conflict with Nessie's implementation, particularly around warehouse path resolution and S3 credential management, producing "Cannot obtain metadata" errors.
**Why it happens:** Trino 443+ includes fixes for Nessie integration, but edge cases remain around credential vending and path resolution.
**How to avoid:** Use Trino 479+ (latest). Test with the REST catalog type (`iceberg.catalog.type=rest`) rather than the Nessie-specific type. Verify S3 credential vending works end-to-end before proceeding.
**Warning signs:** "Cannot obtain metadata" errors in Trino coordinator logs; tables visible in Nessie UI but not queryable from Trino.

### Pitfall 3: MinIO S3 API Incompatibilities with Iceberg
**What goes wrong:** MinIO has documented issues with Iceberg: S3 signature validation errors after 3 hours of continuous operation (Iceberg issue #13045), HEAD request failures that work fine on AWS S3, and unpatched CVE vulnerabilities.
**Why it happens:** MinIO entered maintenance mode December 2025. Open-source development has effectively stopped.
**How to avoid:** Pin MinIO version. Test all Iceberg operations (create table, write data, compact, expire snapshots) on MinIO specifically. Monitor for signature expiration issues. Have a contingency plan for migration to RustFS or Ceph if issues are blockers.
**Warning signs:** Intermittent "SignatureDoesNotMatch" errors after sustained operations; Iceberg metadata operations that work on S3 but fail on MinIO.

### Pitfall 4: Iceberg Small File Explosion Without Day-1 Maintenance
**What goes wrong:** Every write creates new metadata and data files. Without compaction, tables accumulate thousands of small files and query planning degrades.
**Why it happens:** Teams treat Iceberg as "write and forget" without scheduling compaction, snapshot expiration, or orphan file cleanup.
**How to avoid:** Implement automated table maintenance from the first table creation. Target 100-256 MB file sizes. Run compaction after each batch write. Expire snapshots daily (retain 7-14 days minimum).
**Warning signs:** Query planning exceeds 5 seconds; `SELECT * FROM "table$files"` shows thousands of files under 100 MB.

### Pitfall 5: Environment Isolation Gaps Break Production
**What goes wrong:** Dev changes to Nessie catalog metadata or Trino configurations leak into production because environments share infrastructure.
**Why it happens:** Cost-saving by sharing catalog instances or storage buckets across environments.
**How to avoid:** Full isolation is a locked decision. Separate Nessie instances, separate Trino clusters, separate S3 buckets, separate MinIO buckets per environment. Use Terraform workspaces to manage.
**Warning signs:** A table created in dev appears in production queries; a schema change in staging breaks a production query.

### Pitfall 6: Snowflake REST Catalog Read-Only Limitation
**What goes wrong:** Snowflake's catalog integration for external REST catalogs provides read-only access. Teams assume full DML is available on day one.
**Why it happens:** Snowflake documentation mentions write support for externally managed Iceberg tables, but this requires specific configuration (external volumes, access delegation) and has restrictions.
**How to avoid:** For Phase 1, treat Snowflake as a read-only consumer of Iceberg tables. Validate read access first. Write support via external volumes can be explored in Phase 2 if needed.
**Warning signs:** Snowflake users encounter "permission denied" or "unsupported operation" errors when attempting INSERT/UPDATE.

## Code Examples

Verified patterns from official sources:

### Nessie Server Deployment (Docker Compose for local dev)
```yaml
# Source: Nessie official documentation
version: '3'
services:
  nessie:
    image: ghcr.io/projectnessie/nessie:0.107.4
    ports:
      - "19120:19120"
    environment:
      - NESSIE_VERSION_STORE_TYPE=JDBC2
      - QUARKUS_DATASOURCE_JDBC_URL=jdbc:postgresql://postgres:5432/nessie
      - QUARKUS_DATASOURCE_USERNAME=nessie
      - QUARKUS_DATASOURCE_PASSWORD=nessie123
      - NESSIE_CATALOG_DEFAULT_WAREHOUSE=lakehouse
      - NESSIE_CATALOG_WAREHOUSES_LAKEHOUSE_LOCATION=s3://lakehouse-data/
      - NESSIE_CATALOG_SERVICE_S3_DEFAULT_OPTIONS_REGION=us-east-1
      - NESSIE_CATALOG_SERVICE_S3_DEFAULT_OPTIONS_PATH_STYLE_ACCESS=true
      - NESSIE_CATALOG_SERVICE_S3_DEFAULT_OPTIONS_ENDPOINT=http://minio:9000
    depends_on:
      - postgres
      - minio

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: nessie
      POSTGRES_USER: nessie
      POSTGRES_PASSWORD: nessie123
    volumes:
      - pgdata:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: admin123456
    volumes:
      - miniodata:/data

volumes:
  pgdata:
  miniodata:
```

### Trino LDAP Authentication Configuration
```properties
# Source: Trino 479 Documentation
# etc/config.properties (coordinator)
http-server.authentication.type=PASSWORD
http-server.https.enabled=true
http-server.https.port=8443
http-server.https.keystore.path=/etc/trino/tls/keystore.jks
http-server.https.keystore.key=<keystore_password>

# etc/password-authenticator.properties
password-authenticator.name=ldap
ldap.url=ldaps://ldap.company.com:636
ldap.user-bind-pattern=uid=${USER},ou=people,dc=company,dc=com
ldap.group-auth-pattern=(&(objectClass=groupOfNames)(member=uid=${USER},ou=people,dc=company,dc=com))
ldap.user-base-dn=ou=people,dc=company,dc=com
```

### Trino File-Based RBAC
```json
// Source: Trino 479 Documentation
// etc/access-control/rules.json
{
  "catalogs": [
    {
      "catalog": "iceberg",
      "allow": "all"
    }
  ],
  "schemas": [
    {
      "catalog": "iceberg",
      "schema": ".*",
      "owner": true
    }
  ],
  "tables": [
    {
      "catalog": "iceberg",
      "schema": "sensitive_ns",
      "table": ".*",
      "privileges": ["SELECT"],
      "groups": ["data_readers"]
    },
    {
      "catalog": "iceberg",
      "schema": ".*",
      "table": ".*",
      "privileges": ["SELECT", "INSERT", "DELETE", "UPDATE"],
      "groups": ["data_engineers"]
    }
  ]
}
```

```properties
# etc/access-control.properties
access-control.name=file
security.config-file=etc/access-control/rules.json
security.refresh-period=60s
```

### Iceberg Schema Evolution (Trino)
```sql
-- Source: Trino Iceberg connector docs / Iceberg schema evolution docs
-- Add a column (metadata-only, no data rewrite)
ALTER TABLE iceberg.default_ns.trades ADD COLUMN settlement_date DATE;

-- Widen a type (metadata-only, int -> bigint)
ALTER TABLE iceberg.default_ns.trades ALTER COLUMN quantity SET DATA TYPE DECIMAL(20,4);

-- Verify schema is visible from all engines
-- Trino:
DESCRIBE iceberg.default_ns.trades;

-- Snowflake (after catalog refresh):
DESCRIBE TABLE my_iceberg_db.default_ns.trades;
```

### Iceberg Table Maintenance (PySpark)
```python
# Source: Apache Iceberg Spark Procedures documentation
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("iceberg-maintenance") \
    .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.lakehouse.type", "rest") \
    .config("spark.sql.catalog.lakehouse.uri", "http://nessie:19120/iceberg") \
    .config("spark.sql.catalog.lakehouse.warehouse", "lakehouse") \
    .getOrCreate()

# 1. Compact data files (target 256 MB)
spark.sql("""
    CALL lakehouse.system.rewrite_data_files(
        table => 'default_ns.trades',
        options => map('target-file-size-bytes', '268435456')
    )
""")

# 2. Expire old snapshots (retain 7 days)
spark.sql("""
    CALL lakehouse.system.expire_snapshots(
        table => 'default_ns.trades',
        older_than => TIMESTAMP '2026-03-06 00:00:00',
        retain_last => 10
    )
""")

# 3. Remove orphan files
spark.sql("""
    CALL lakehouse.system.remove_orphan_files(
        table => 'default_ns.trades',
        older_than => TIMESTAMP '2026-03-10 00:00:00'
    )
""")

# 4. Rewrite manifests for faster planning
spark.sql("""
    CALL lakehouse.system.rewrite_manifests(
        table => 'default_ns.trades'
    )
""")
```

### Synthetic Financial Data Generation
```python
# Using Faker for synthetic financial data
from faker import Faker
from datetime import date, timedelta
import random
import decimal

fake = Faker()
Faker.seed(42)  # Deterministic for reproducibility

def generate_trades(num_records: int) -> list[dict]:
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'JPM', 'GS', 'BAC', 'C', 'WFC',
               'BRK.B', 'V', 'MA', 'AXP', 'BLK', 'SCHW', 'MS']
    sides = ['BUY', 'SELL']
    trade_types = ['MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT']

    trades = []
    for i in range(num_records):
        symbol = random.choice(symbols)
        price = round(random.uniform(50.0, 500.0), 4)
        quantity = random.randint(1, 10000)
        trades.append({
            'trade_id': i + 1,
            'trade_date': fake.date_between(
                start_date=date(2024, 1, 1),
                end_date=date(2026, 3, 13)
            ),
            'symbol': symbol,
            'side': random.choice(sides),
            'trade_type': random.choice(trade_types),
            'quantity': quantity,
            'price': decimal.Decimal(str(price)),
            'notional': decimal.Decimal(str(price * quantity)),
            'account_id': f'ACCT-{random.randint(1000, 9999)}',
            'trader_id': f'TRD-{random.randint(100, 999)}',
            'exchange': random.choice(['NYSE', 'NASDAQ', 'LSE', 'TSE']),
            'settlement_date': fake.date_between(
                start_date=date(2024, 1, 3),
                end_date=date(2026, 3, 16)
            ),
        })
    return trades

# Similar generators for positions and risk_metrics tables
```

### Terraform Module for Nessie on EKS
```hcl
# infra/terraform/modules/nessie/main.tf
resource "helm_release" "nessie" {
  name       = "nessie-${var.environment}"
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "nessie"
  namespace  = "lakehouse-${var.environment}"

  set {
    name  = "versionStoreType"
    value = "JDBC_POSTGRESQL"
  }

  set {
    name  = "postgresql.enabled"
    value = "true"
  }

  set {
    name  = "replicaCount"
    value = var.nessie_replicas
  }

  set_sensitive {
    name  = "postgresql.auth.password"
    value = var.nessie_db_password
  }

  values = [
    templatefile("${path.module}/values.yaml.tpl", {
      environment      = var.environment
      s3_bucket        = var.s3_bucket
      s3_region        = var.s3_region
      minio_endpoint   = var.minio_endpoint
      minio_bucket     = var.minio_bucket
    })
  ]
}

variable "environment" {
  type = string
}

variable "nessie_replicas" {
  type    = number
  default = 2
}

variable "nessie_db_password" {
  type      = string
  sensitive = true
}

variable "s3_bucket" {
  type = string
}

variable "s3_region" {
  type    = string
  default = "us-east-1"
}

variable "minio_endpoint" {
  type = string
}

variable "minio_bucket" {
  type = string
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hive Metastore as Iceberg catalog | REST catalogs (Nessie, Polaris) | 2024-2025 | REST is the standard; HMS is legacy |
| Nessie native protocol only | Nessie supports Iceberg REST protocol | Nessie 0.95+ (2025) | Any Iceberg REST client works with Nessie |
| MinIO open-source for on-prem S3 | MinIO effectively abandoned (Dec 2025) | Dec 2025 | RustFS/Ceph are alternatives; MinIO AIStor (commercial) is the vendor path |
| Trino Nessie catalog type only | Trino supports Nessie via REST catalog type too | Trino 443+ | Better forward compatibility via REST |
| Snowflake read-only Iceberg external tables | Snowflake full DML on external Iceberg (GA Oct 2025) | Oct 2025 | Snowflake can write to externally managed tables |
| Manual TLS cert management | cert-manager on K8s with automated renewal | 2023+ | Eliminates certificate expiry incidents |
| GitHub Actions long-lived AWS credentials | OIDC-based short-lived tokens | 2023+ | No stored secrets, reduced security risk |
| Nessie JDBC store type | Nessie JDBC2 store type | 2025-2026 | Reduced PostgreSQL storage overhead |

**Deprecated/outdated:**
- MinIO open-source: archived early 2026, no new features, security patches "case by case"
- Hive Metastore for new deployments: no REST spec, no RBAC, no branching, requires Thrift infrastructure
- Trino versions before 443: missing critical Nessie integration bug fixes

## Open Questions

1. **Teradata OTF + Nessie REST catalog support**
   - What we know: Teradata documents Glue, HMS, Unity only. No REST catalog mentioned.
   - What's unclear: Whether Teradata has undocumented REST support, or plans to add it.
   - Recommendation: Test in week 1. Contact Teradata engineering if possible. Fallback to Trino federation is ready.

2. **Nessie HA with multiple replicas**
   - What we know: Nessie supports multiple replicas with PostgreSQL backend. Bitnami Helm chart supports replicaCount.
   - What's unclear: Exactly how Nessie handles concurrent catalog commits across replicas -- does PostgreSQL provide sufficient locking?
   - Recommendation: Deploy with 2 replicas for Phase 1 dev/staging, validate concurrent writes from Trino + PySpark.

3. **MinIO stability for sustained Iceberg operations**
   - What we know: Documented issues with S3 signature validation after 3 hours (Iceberg issue #13045). MinIO in maintenance mode.
   - What's unclear: Whether the team's current MinIO version is affected. Whether the issue is fixed in their deployment.
   - Recommendation: Run a 24-hour sustained read/write test on MinIO before trusting it for the proof. Have a RustFS contingency plan.

4. **Snowflake credential vending from Nessie**
   - What we know: Snowflake supports REST catalog integration. Nessie supports S3 credential vending.
   - What's unclear: Whether Snowflake's `ACCESS_DELEGATION_MODE=VENDED_CREDENTIALS` works with Nessie's credential vending. Snowflake may require an external volume instead.
   - Recommendation: Test with both `VENDED_CREDENTIALS` and `EXTERNAL_VOLUME_CREDENTIALS` modes. Document which works.

5. **Trino cluster sizing for Phase 1 proof**
   - What we know: Phase 1 dataset is < 100 GB synthetic data. Workload is benchmark queries, not production.
   - What's unclear: Optimal coordinator/worker configuration for mixed read/write workload.
   - Recommendation: Start with 1 coordinator + 2 workers (r5.xlarge or equivalent). Scale up if benchmark results show resource contention.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + PySpark integration tests |
| Config file | etl/pyproject.toml (to be created in Wave 0) |
| Quick run command | `cd etl && pytest tests/unit/ -x --tb=short` |
| Full suite command | `cd etl && pytest tests/ -x --tb=short` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FNDTN-01 | Iceberg table CRUD on S3 | integration | `pytest tests/integration/test_iceberg_s3.py -x` | No - Wave 0 |
| FNDTN-02 | Iceberg table CRUD on MinIO | integration | `pytest tests/integration/test_iceberg_minio.py -x` | No - Wave 0 |
| FNDTN-03 | Nessie catalog serves both S3 and MinIO | integration | `pytest tests/integration/test_nessie_dual_storage.py -x` | No - Wave 0 |
| FNDTN-04 | Schema evolution across engines | integration | `pytest tests/integration/test_schema_evolution.py -x` | No - Wave 0 |
| FNDTN-05 | Partition evolution metadata-only | integration | `pytest tests/integration/test_partition_evolution.py -x` | No - Wave 0 |
| FNDTN-06 | Automated table maintenance | integration | `pytest tests/integration/test_table_maintenance.py -x` | No - Wave 0 |
| QUERY-01 | Trino reads from S3 and MinIO | integration | `pytest tests/integration/test_trino_reads.py -x` | No - Wave 0 |
| QUERY-02 | Trino writes Iceberg tables | integration | `pytest tests/integration/test_trino_writes.py -x` | No - Wave 0 |
| QUERY-03 | Teradata OTF reads Iceberg | manual-only | Manual: connect Teradata OTF to Nessie; if fails, test Trino federation | No - Wave 0 |
| QUERY-04 | Snowflake reads via REST catalog | integration | `pytest tests/integration/test_snowflake_reads.py -x` | No - Wave 0 |
| QUERY-05 | Cross-engine metadata consistency | integration | `pytest tests/integration/test_metadata_consistency.py -x` | No - Wave 0 |
| QUERY-06 | Performance benchmarks | integration | `pytest tests/integration/test_benchmarks.py -x` | No - Wave 0 |
| CICD-01 | Repo structure valid | unit | `pytest tests/unit/test_repo_structure.py -x` | No - Wave 0 |
| CICD-02 | GitHub Actions workflows valid | smoke | `act --dry-run` (act tool) | No - Wave 0 |
| CICD-03 | Environment promotion works | smoke | `terraform plan -var-file=environments/dev/terraform.tfvars` | No - Wave 0 |
| CICD-04 | Terraform IaC valid | smoke | `terraform validate && terraform plan` | No - Wave 0 |
| SEC-01 | LDAP authentication works | manual-only | Manual: login to Trino with LDAP credentials | N/A |
| SEC-02 | RBAC restricts access | integration | `pytest tests/integration/test_rbac.py -x` | No - Wave 0 |
| SEC-05 | Encryption at rest enabled | smoke | `aws s3api get-bucket-encryption --bucket lakehouse-data` | No - Wave 0 |
| SEC-06 | TLS enabled on all endpoints | smoke | `openssl s_client -connect nessie:19120` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd etl && pytest tests/unit/ -x --tb=short`
- **Per wave merge:** `cd etl && pytest tests/ -x --tb=short`
- **Phase gate:** Full suite green + manual Teradata OTF validation + Snowflake read validation

### Wave 0 Gaps
- [ ] `etl/pyproject.toml` -- project configuration with pytest settings
- [ ] `etl/tests/conftest.py` -- shared fixtures (Spark session, Nessie client, Trino connection)
- [ ] `etl/tests/unit/` -- directory structure
- [ ] `etl/tests/integration/` -- directory structure
- [ ] Framework install: `pip install pytest pyspark pyiceberg duckdb`
- [ ] Docker Compose for test infrastructure: Nessie + PostgreSQL + MinIO

## Sources

### Primary (HIGH confidence)
- [Nessie + Iceberg + Trino configuration](https://projectnessie.org/iceberg/trino/) -- Trino catalog properties, version requirements
- [Nessie Iceberg REST configuration](https://projectnessie.org/guides/iceberg-rest/) -- Server config, warehouse setup, S3 options, client connection URIs
- [Nessie releases](https://projectnessie.org/releases/) -- v0.107.4 (March 9, 2026), latest stable
- [Trino 479 Iceberg connector](https://trino.io/docs/current/connector/iceberg.html) -- Full DML, catalog types, S3 config
- [Trino 479 LDAP authentication](https://trino.io/docs/current/security/ldap.html) -- LDAP config, group-based auth
- [Trino 479 file-based access control](https://trino.io/docs/current/security/file-system-access-control.html) -- JSON rules, catalog/schema/table level
- [Trino metastores docs](https://trino.io/docs/current/object-storage/metastores.html) -- Nessie metastore configuration
- [Snowflake CREATE CATALOG INTEGRATION (REST)](https://docs.snowflake.com/en/sql-reference/sql/create-catalog-integration-rest) -- SQL syntax, auth types, examples
- [Snowflake catalog integration configuration](https://docs.snowflake.com/en/user-guide/tables-iceberg-configure-catalog-integration) -- Catalog integration setup
- [Apache Iceberg schema evolution](https://iceberg.apache.org/docs/latest/evolution/) -- Metadata-only changes, type widening rules
- [Apache Iceberg Spark procedures](https://iceberg.apache.org/docs/latest/spark-procedures/) -- Compaction, snapshot expiration, orphan cleanup
- [Apache Iceberg maintenance](https://iceberg.apache.org/docs/latest/maintenance/) -- Table maintenance best practices
- [AWS S3 SSE-KMS encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/specifying-kms-encryption.html) -- Server-side encryption configuration
- [MinIO SSE-KMS](https://min.io/docs/minio/linux/administration/server-side-encryption/server-side-encryption-sse-kms.html) -- KES + external KMS setup
- [HashiCorp Terraform GitHub Actions](https://developer.hashicorp.com/terraform/tutorials/automation/github-actions) -- Official tutorial

### Secondary (MEDIUM confidence)
- [Building Production-Ready Data Lakehouse with Iceberg, Nessie, Trino, Spark on K8s](https://medium.com/@nsalexamy/building-a-production-ready-data-lakehouse-locally-apache-iceberg-nessie-trino-and-spark-on-eea4445888ab) -- March 2026 walkthrough
- [Iceberg + Nessie REST + MinIO + Spark + Trino walkthrough](https://medium.com/@arnab.neogi.86/apache-iceberg-nessie-rest-catalog-minio-spark-trino-and-duckdb-part-2-6f0aee21e8d9) -- Integration patterns
- [Bitnami Nessie Helm chart](https://github.com/bitnami/charts/blob/main/bitnami/nessie/README.md) -- Helm deployment options
- [Nessie Kubernetes guide](https://projectnessie.org/guides/kubernetes/) -- K8s deployment patterns
- [Terraform CI/CD for data engineering](https://terrateam.io/blog/ci-cd-pipeline-for-terraform) -- GitHub Actions patterns
- [Trino on EKS blueprint](https://awslabs.github.io/data-on-eks/docs/blueprints/distributed-databases/trino) -- AWS deployment patterns
- [Iceberg catalogs 2025 survey](https://www.e6data.com/blog/iceberg-catalogs-2025-emerging-catalogs-modern-metadata-management) -- Adoption data

### Tertiary (LOW confidence -- needs validation)
- Teradata OTF REST catalog support -- NO documentation found; assumed unsupported pending week 1 validation
- Snowflake vended credentials with Nessie -- no direct documentation of this specific combination
- MinIO signature validation stability at sustained load -- known issue (#13045) but unclear if current MinIO versions are affected
- Nessie multi-replica consistency under concurrent writes -- PostgreSQL locking should handle it but no production-scale evidence found

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Nessie, Trino, PySpark, Terraform, GitHub Actions are well-documented and production-proven
- Architecture: MEDIUM-HIGH -- Nessie REST catalog pattern is proven for Trino and Spark; Snowflake REST integration is documented; Teradata integration is LOW confidence
- Pitfalls: MEDIUM-HIGH -- Teradata OTF catalog gap is well-documented as a risk; MinIO issues are documented; Iceberg maintenance patterns are proven
- Security: HIGH -- Trino LDAP, file-based RBAC, S3 SSE-KMS, TLS are all well-documented with official examples

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (30 days -- stable technologies except MinIO which may see rapid changes)

---
*Phase: 01-foundation-and-feasibility-validation*
*Research completed: 2026-03-13*
