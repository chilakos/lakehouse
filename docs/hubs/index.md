---
title: Hub Self-Service — Design Docs
---

# Hub self-service — design docs

This folder holds the design for the Lumina hub self-service authoring
experience. The intent is to give each LOB a building zone where DMOs can
compose data products from EDW (Teradata) and EDL (Hive) sources without
going through Enterprise Data engineering for every change.

Status: **Draft for review with Vinh Tran.** Not yet an ADR — this is the design
intent that will produce ADR-016 (Hub self-service authoring framework) once
the open questions in [11 — Open questions](11-open-questions) are closed.

## Start here

| Doc | Purpose |
| --- | --- |
| [00 — Overview](00-overview) | Executive summary, personas, operating-model diagram, architectural commitment |
| [01 — Experience flow](01-experience-flow) | Day-by-day flow from scaffold to prod promotion to rehydration |
| [04 — Source selection](04-source-selection) | **Deep dive** — how a DMO picks a Teradata view or Hive table |
| [05 — Rehydration](05-rehydration) | **Deep dive** — how point-in-time rehydration works end to end |

## Reference

| Doc | Purpose |
| --- | --- |
| [02 — Repo structure](02-repo-structure) | Folder layout and what is hand-authored vs generated |
| [03 — `product.yml` schema](03-product-yml-schema) | The single authoring artifact — annotated example and field reference |
| [06 — CLI and portal](06-cli-and-portal) | The CLI surface and portal equivalents |
| [07 — CI/CD pattern](07-cicd-pattern) | CI/CD reference architecture (Helios pattern) |
| [08 — Governance hooks](08-governance-hooks) | Where enterprise controls plug in |
| [09 — Failure modes](09-failure-modes) | Three patterns that sink hub self-service |
| [10 — Build plan](10-build-plan) | Phased plan to MVP and beyond |
| [11 — Open questions](11-open-questions) | Decisions still open for review |

## Related

- ADR-013 — EDLH conformance layer
- ADR-014 + amendment — Gateway and landing zone
- ADR-015 — RBC Data Gateway
- Data Hub Architecture v2

[← Back to Lakehouse Hub]({{ '/' | relative_url }})
