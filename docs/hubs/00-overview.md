# 00 — Overview

## The design problem

Once data lands in Bronze, what does a DMO actually touch to take it from
Bronze through Silver into Gold, in a way that is reproducible, governed,
and reruns end-to-end without a platform engineer in the loop?

This is not a question about Helios. Helios solves landing — DataStage
jobs migrated to Python, deployed via GitHub Actions, run on Kubernetes,
land into Teradata and into Bronze. That pattern is in production and
working.

The hub self-service question is the next layer up: how the LOB-owned
authoring experience should look on top of that, given Snowflake as the
hub compute and the existing enterprise control plane.

## The commitment

Bronze is immutable and append-only. Silver and Gold are pure functions
of Bronze plus the methodology in Git. Together these two properties make
"rerun" a real feature instead of a nice idea — and they make
point-in-time rehydration a single command.

If anyone has `UPDATE` or `DELETE` on Bronze, ever, the whole architecture
collapses. This is enforced by Snowflake RBAC, not by policy. The
framework's load service principal is the only identity with INSERT;
DMOs get SELECT only.

## The wrap

DMOs do not author dbt projects. They author one structured artifact per
data product — `product.yml` — and write the SQL for the Silver and Gold
transforms. The framework compiles the artifact into a runnable dbt
project, executes it on the platform's existing GitHub Actions / OpenShift
infrastructure (the Helios pattern), emits lineage, runs the tests, and
registers the output as a certified data product.

dbt is the engine. The wrapper is what makes it self-service.

## Operating model at a glance

```mermaid
flowchart TB

classDef source fill:#E8F1FA,stroke:#0051A5,stroke-width:1.5px,color:#002F6C
classDef bronze fill:#FCE4B6,stroke:#B07A1F,stroke-width:1.5px,color:#5C3B00
classDef silver fill:#E5E5E5,stroke:#6B6B6B,stroke-width:1.5px,color:#1F1F1F
classDef gold   fill:#FFE38A,stroke:#A37800,stroke-width:1.5px,color:#4A3500
classDef author fill:#E1F0DC,stroke:#3F7A2A,stroke-width:1.5px,color:#1F4012
classDef plat   fill:#F2E1F4,stroke:#7A2C8E,stroke-width:1.5px,color:#3D154A

subgraph SRC["Sources the team pulls from"]
  direction LR
  TD["Teradata views<br/>(EDW)"]:::source
  HIVE["EDL Hive tables<br/>(on-prem lake)"]:::source
end

subgraph HUB["Hub (Snowflake)"]
  direction TB
  subgraph BRZ["Bronze — Immutable, append-only"]
    direction LR
    B1["bronze.td_extract"]:::bronze
    B2["bronze.hive_extract"]:::bronze
  end
  subgraph SLV["Silver — Cleansed & conformed"]
    direction LR
    S1["clients_clean"]:::silver
    S2["positions_clean"]:::silver
  end
  subgraph GLD["Gold — Certified product"]
    direction LR
    G1["household_exposure"]:::gold
  end
end

subgraph AUTH["DMO authoring"]
  direction TB
  PYL["product.yml"]:::author
  SQL["silver/*.sql<br/>gold/*.sql"]:::author
  CLI["hub-cli"]:::author
end

subgraph PLAT["Platform (invisible to DMO)"]
  direction TB
  GIT["GitHub repo"]:::plat
  CI["GitHub Actions<br/>on OpenShift<br/>(Helios pattern)"]:::plat
  DBT["dbt Core<br/>generated from<br/>product.yml"]:::plat
  ORCH["Scheduler"]:::plat
end

TD ==>|"1. scheduled extract<br/>via Trino → Snowpipe"| B1
HIVE ==>|"1. scheduled extract<br/>via Trino → Snowpipe"| B2
BRZ -.->|"INSERT only<br/>no UPDATE / DELETE"| BRZ

PYL --> CLI
SQL --> CLI
CLI ==>|"2. commit & PR"| GIT
GIT ==>|"3. trigger"| CI
CI ==>|"4. generate &<br/>execute"| DBT

DBT ==>|"5a. read"| BRZ
DBT ==>|"5b. write"| SLV
SLV ==>|"6. aggregate"| GLD
ORCH ==>|"nightly"| DBT

CLI -.->|"R1. rehydrate<br/>--as-of date"| ORCH
ORCH -.->|"R2. Time Travel pin"| BRZ
DBT -.->|"R3. rebuild<br/>Silver → Gold<br/>for window"| SLV
```

## Personas

| Persona | Approx % of users | Authoring tool | What they own |
| --- | --- | --- | --- |
| Analytics engineer | 5–15% | dbt Core, Git, full PR flow | The certified backbone of the hub: complex Silver and Gold models, framework extensions |
| DMO analyst / BI dev | 40–50% | Hub portal + `product.yml` + SQL files | The bulk of data products: Silver cleansing, Gold aggregates, tests, ownership metadata |
| Business user | 30–40% | Power BI, Fabric Data Agent, certified Gold tables | Consumes published products. Authors analyses, not data products. |

The wrapper is designed for the middle tier. The other two tiers fall
out naturally — analytics engineers can drop down into raw dbt for
escape cases (in `framework/` only), and business users only see Gold.

## What this design is not

It is not a replacement for the EDW pipelines. Helios continues to land
data into Teradata and into Bronze unchanged.

It is not a new orchestrator. Scheduled hub runs use the same GitHub
Actions self-hosted runners on OpenShift that Helios uses.

It is not a vendor lock-in. dbt Core runs on the platform's own
infrastructure, against Snowflake. The same pattern would run against
Iceberg-on-Trino or Fabric with only the dbt adapter changing.

It is not a free pass on governance. Every product passes through the
same enterprise control plane — classification, lineage, audit,
catalog certification — wired into CI, not bolted on after.

## Design philosophy in one sentence

**dbt under the hood, product definition on top, immutable Bronze as
the foundation, and the same CI/CD pattern as Helios so the platform
team supports one model instead of two.**

## Read next

- [01 — Experience flow](01-experience-flow) — day-by-day from scaffold to rehydrate
- [04 — Source selection](04-source-selection) — how a DMO picks a Teradata view or Hive table
- [05 — Rehydration](05-rehydration) — how point-in-time rebuild works
- [11 — Open questions](11-open-questions) — what still needs to close before Phase 1
