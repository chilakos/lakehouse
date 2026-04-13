# Outstanding Questions for Repo Review

This is a **judge-style review list** for the repository as it exists today.

For each question, answer with evidence:
- the file or directory that proves the claim
- the test, workflow, or manual runbook that validates it
- the owner who will close the gap if the answer is still "planned"

## 1. Architecture Source of Truth

| Priority | Question | Why this is being challenged |
|---|---|---|
| High | Is the committed platform direction **Nessie + Ranger + MinIO**, or **Polaris + Privacera + MinIO**? | The source code centers on Nessie and Ranger, while some HTML docs discuss Polaris and Privacera as decided choices. |
| High | Which documents should a new engineer trust first: the README, ADRs, or the architecture HTML pages? | The repo currently contains both implementation-oriented docs and future-state exploration docs. |
| Medium | Which parts of the "target architecture" are implemented, and which are still strategic design only? | This repo includes runnable ETL/infrastructure assets plus strategy documents for additional consumers and governance tooling. |

## 2. Delivery Completeness

| Priority | Question | Why this is being challenged |
|---|---|---|
| High | Which Bronze, Silver, and Gold pipelines are considered production-ready versus reference implementations? | The repo has concrete pipeline modules, but not every business domain or migration path is represented in code. |
| High | Which Airflow DAGs are mandatory for the core platform, and which are examples or supporting jobs? | There are DAGs for medallion layers, governance, maintenance, and examples; the operational minimum is not stated clearly. |
| Medium | Is `dbt/` intentionally a placeholder, or is there a planned handoff between Python ETL and dbt? | The directory exists, but there is no active dbt project implementation in the current tree. |

## 3. Operability and Developer Experience

| Priority | Question | Why this is being challenged |
|---|---|---|
| High | Can a new contributor run `pip install -e ".[dev]"` in `etl/` successfully today? If not, what is the pinned working setup? | The current editable install path needs to be dependable if the README is the onboarding entry point. |
| High | What is the minimum local stack required to run a meaningful integration test pass? | Docker assets exist for many services, but the smallest supported developer workflow is not explicit. |
| Medium | Which integration tests are expected to run in CI, and which are intentionally manual because they require external credentials or systems? | The repo contains integration coverage for S3, Snowflake, Ranger, Trino, and more, but not all can run everywhere. |

## 4. Governance and Auditability

| Priority | Question | Why this is being challenged |
|---|---|---|
| High | What is the authoritative source for data classification, glossary terms, and policy ownership? | Governance logic exists in code, but the operational source of truth and approval path are not obvious from the repo root. |
| Medium | How are Ranger policies promoted across environments and reviewed for change control? | Policy builders exist in Python, while Terraform manages platform infrastructure; the handoff between them is not documented. |
| Medium | What evidence proves end-to-end auditability from ingestion through query access? | The repo includes audit, lineage, and freshness utilities, but the expected control evidence set is not summarized in one place. |

## 5. Consumer and Semantic Strategy

| Priority | Question | Why this is being challenged |
|---|---|---|
| High | Are Fabric, Teradata, and Snowflake current delivery commitments in this repository, or external integration targets documented for planning? | The README and docs mention them, but the executable source in this repo primarily implements Iceberg/Nessie/Trino/Cube-centered flows. |
| Medium | What is the acceptance bar for the NL-to-SQL path: accuracy threshold, approved datasets, and human review requirements? | Prompt-building, evaluation, and metric-context utilities exist, but the release criteria are not captured in the repo root docs. |
| Medium | Is Cube the long-term semantic system of record, or a validation layer on the way to another serving model? | Cube YAML models and validators exist, but broader semantic ownership is still a strategic question. |

## Suggested Review Ritual

Use this file during architecture or delivery review and answer each item with:
1. **Decision**
2. **Evidence**
3. **Owner**
4. **Due date**
5. **Next repo/doc update required**
