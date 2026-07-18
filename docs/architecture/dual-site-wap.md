# Dual-Site WAP — Architecture and Sequence Reference

Companion to [ADR-019](../adr/019-dual-site-data-hub-hosting.md). Every data hub has one
designated writer site; the opposite site hosts a read-only Iceberg replica synchronized
per WAP publish. The WAP contract and the replicator codepath are identical in both
directions — only the cast changes.

## Architecture

```mermaid
flowchart LR
    subgraph ONPREM["On-prem site"]
        ETL1["Airflow + Python ETL<br/>WAP writer, Soda gates"]
        GRAV["Gravitino<br/>Iceberg REST, WAP branches"]
        TRINO["Trino<br/>Ranger-enforced reads"]
        PURE["Pure Storage<br/>Parquet + metadata files"]
        ETL1 --> GRAV
        GRAV --> PURE
        TRINO --> GRAV
    end
    subgraph CLOUD["Cloud site (AWS)"]
        ETL2["Airflow + Python ETL<br/>WAP writer, Soda gates"]
        POLARIS["Snowflake Open Catalog<br/>Polaris, RBAC read-only"]
        SNOW["Snowflake<br/>Cortex + warehouses"]
        S3["Amazon S3<br/>Parquet + metadata files"]
        ETL2 --> POLARIS
        POLARIS --> S3
        SNOW --> POLARIS
    end
    REPL["Hub Replicator<br/>diff, copy, rewrite, commit"]
    GRAV <-->|snapshots| REPL
    REPL <-->|snapshots| POLARIS
    PURE <-->|data files| REPL
    REPL <-->|data files| S3
```

## Sequence — on-prem writer hub

```mermaid
sequenceDiagram
    participant ETL as ETL (on-prem)
    participant GRAV as Gravitino
    participant PURE as Pure Storage
    participant REPL as Replicator
    participant S3 as Amazon S3
    participant POL as Polaris

    ETL->>GRAV: create branch wap_<run_id>
    ETL->>PURE: write Parquet delta files
    ETL->>GRAV: commit snapshot to branch
    ETL->>GRAV: Soda audit reads (via Trino)
    alt audit fails
        ETL->>GRAV: drop branch, alert — no publish
    else audit passes
        ETL->>GRAV: fast-forward main (atomic publish)
    end
    ETL->>REPL: publish event (Airflow / OpenLineage)
    REPL->>GRAV: read snapshot diff since last sync
    REPL->>PURE: read delta data + manifest files
    REPL->>S3: copy files, verify checksums, rewrite URIs
    REPL->>POL: Iceberg REST commit (read-only namespace)
    Note over POL: Snowflake / Cortex readers flip atomically
```

## Sequence — cloud writer hub

```mermaid
sequenceDiagram
    participant ETL as ETL (cloud)
    participant POL as Polaris
    participant S3 as Amazon S3
    participant REPL as Replicator
    participant PURE as Pure Storage
    participant GRAV as Gravitino

    ETL->>POL: create branch wap_<run_id>
    ETL->>S3: write Parquet delta files
    ETL->>POL: commit snapshot to branch
    ETL->>POL: Soda audit reads (cloud compute)
    alt audit fails
        ETL->>POL: drop branch, alert — no publish
    else audit passes
        ETL->>POL: fast-forward main (atomic publish)
    end
    ETL->>REPL: publish event (Airflow / OpenLineage)
    REPL->>POL: read snapshot diff since last sync
    REPL->>S3: read delta data + manifest files
    REPL->>PURE: copy files, verify checksums, rewrite URIs
    REPL->>GRAV: Iceberg REST commit (read-only namespace)
    Note over GRAV: Trino readers flip atomically
```

## Replicator internals

```mermaid
flowchart LR
    LIS["Publish listener<br/>events + reconciliation sweep"]
    ST["State store<br/>last synced snapshot ID"]
    DIFF["Snapshot differ<br/>manifest diff → file list"]
    COPY["File copier<br/>parallel, checksum verify"]
    URI["URI rewriter<br/>endpoint path translation"]
    COMMIT["Catalog committer<br/>idempotent Iceberg REST"]
    LIS --> ST --> DIFF --> COPY --> URI --> COMMIT
```

Design properties:

- **Commit-last ordering.** All side effects visible to readers happen in the final step.
  A crash anywhere earlier leaves only orphaned files on the replica object store (swept
  by a cleanup job) and zero visible change.
- **Idempotent.** Re-running a partially completed replication resumes from state and
  lands the same snapshot; committing an already-present snapshot is a no-op.
- **State is a cache, not a correctness dependency.** The replica catalog's current
  snapshot lineage is the ground truth; the state store can be rebuilt from it.
- **Multi-snapshot catch-up.** The differ spans the full lineage range between last-synced
  and the current main head, so a lagging replica catches up in one run.
- **Three URI locations.** Absolute paths live in `metadata.json`, the manifest list, and
  each manifest file — the rewriter must translate all three for the target endpoint.
- **Dual-mode triggering.** Event-driven per publish, plus a periodic reconciliation sweep
  comparing writer main heads against replica state, so a dropped event degrades to
  bounded lag rather than silent divergence.
- **Symmetric.** One codepath serves both directions; direction is a property of the hub
  registry, not the platform.
