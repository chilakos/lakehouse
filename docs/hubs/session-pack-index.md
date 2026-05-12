---
title: Hub Design Session Pack
---

# Hub Design Session Pack

A focused set of artifacts produced ahead of the cloud hub design session. Use these to open the conversation with the design team; longer-form reference docs live alongside (see [the main hubs index](/lakehouse/hubs/)).

## Read in this order

| # | Doc | Purpose | Time |
| --- | --- | --- | --- |
| 1 | [Opening bullets](/lakehouse/hubs/session-01-opening-bullets/) | The talking points for the session — frame, principles, open questions | 5 min |
| 2 | [One-pager handout](/lakehouse/hubs/session-02-one-pager/) | Pre-read for the room; what a DMO touches and what they don't | 90 sec |
| 3 | [`product.yml` spec](/lakehouse/hubs/session-03-product-yml-spec/) | The single declarative artifact a DMO authors per data product | 10 min |
| 4 | [UX flow diagram](/lakehouse/hubs/session-04-ux-flow/) | End-to-end DMO journey with mermaid diagram and failure-modes table | 8 min |

## What this pack establishes

The four docs together commit to a specific UX shape for the hubs:

- **One file per data product** — `product.yml` is the contract; everything else is generated.
- **Bronze is the architectural floor** — immutable, append-only, Iceberg snapshots ARE the change history. Silver and Gold are always rehydratable from Bronze.
- **DMOs declare, the platform generates** — Helios extracts, dbt projects, CI workflows, Snowflake DDL, OPA policies, catalog entries — all generated from `product.yml`.
- **One physical Gold, three read paths** — Snowflake secure view, Fabric mirror, Iceberg external volume. No copies, no drift.
- **Promotion is gated by tests and certification, not by tickets** — dev → UAT → prod with explicit, automated gates.

## Open questions to close in the session

1. Hide dbt behind `product.yml` + `hub-cli`, or expose it directly to advanced DMOs?
2. One orchestration plane (Helios) for both Bronze extracts and Silver/Gold dbt runs, or split?
3. Where does rehydration run — DMO dev warehouse, or a platform-owned rehydration warehouse?
4. Is Iceberg external volume the canonical Gold storage so BI, AI, and on-prem Trino all read the same bytes?

These are the live design decisions. Everything else in the pack is a strawman around them.

## Where this lands

The decisions out of this session feed into ADR-016 (Hub Self-Service Authoring Framework) and tighten ADR-013, ADR-014, ADR-015. The architectural commitments in the session pack are intentionally bolder than the existing 00–11 hub reference docs — they're the position to negotiate against, not the consensus.

[← Back to Hubs](/lakehouse/hubs/) · [← Back to Lakehouse]({{ '/' | relative_url }})
