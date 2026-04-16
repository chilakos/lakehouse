# RBC Assist × Fabric Data Agent — Architecture Options

**File:** `RBC_Assist_Fabric_Architecture.pptx`
**Author:** George Chilakos, VP Enterprise Data
**Date:** April 2026
**Status:** Working draft — for discussion with Vinh Tran and Rex Davis

---

## Purpose

This deck frames two related architectural decisions that need to be made as we evaluate exposing Fabric Data Agent and Fabric IQ to RBC Assist:

1. **Agent consumption surface** — how does RBC Assist actually reach Fabric Data Agent? Three patterns are viable:
   - **Pattern 1** — Custom Python app with FastAPI trust boundary (symmetric with Borealis/Teradata pattern)
   - **Pattern 3** — Foundry agent between RBC Assist and Fabric Data Agent (adds Azure Policy model governance and Entra Agent ID inventory)
   - **Pattern 2** — Copilot Studio in Teams/M365 (future surface, can reuse a Foundry backend)

2. **Data access pattern** — should every structured data source accessible to AI agents be exposed via a Fabric semantic model, regardless of whether the underlying source is Iceberg or Teradata? This extends ADR-010 (Fabric Import semantic model as BI/AI surface) from the lakehouse domain to cover Teradata-sourced FSDM data as well.

---

## Key takeaways

- **Foundry is not strictly required** to expose Fabric Data Agent to RBC Assist. The Fabric Data Agent Python SDK supports On-Behalf-Of (OBO) identity passthrough natively. Foundry's value is governance and orchestration — Azure Policy model allowlist, Entra Agent ID inventory, Content Safety, and multi-source orchestration — not connectivity.
- **The Fabric Data Agent internal NL2DAX model is Microsoft-managed and opaque.** RBC does not get to choose this model. This applies equally in all three patterns — Foundry does not change it.
- **Service Principal Name (SPN) authentication is not supported** by Fabric Data Agent. Every call requires a human user's Entra token in the chain. This rules out agentic background jobs against Fabric Data Agent; those workflows need an alternate path (direct XMLA or direct Delta read with service identity).
- **The thin FastAPI trust boundary does not go away** even if Foundry is adopted. It still owns RBC-specific PII rules (SIN, account numbers, BCBS-flagged fields), RBC audit format / SIEM forwarding, cost attribution per user and use-case, and pre-flight request validation. It becomes thinner, not absent.
- **The unified semantic layer decision is architecturally bigger than the agent surface decision.** If we commit to "every source behind a semantic model," the agent consumption pattern simplifies because Fabric Data Agent becomes the single agent-facing interface regardless of source.

---

## Slide-by-slide summary

| # | Slide | Purpose |
|---|---|---|
| 1 | Title | Session framing |
| 2 | Executive summary | Side-by-side view of the two decisions |
| 3 | Pattern 3 architecture | Foundry + Fabric Data Agent call flow with FDA internals expanded |
| 4 | Governance breakdown | What FastAPI owns, what Foundry takes over, what stays Microsoft-managed |
| 5 | Target state | Unified semantic layer over Iceberg + Teradata |
| 6 | Tradeoffs & open questions | Benefits, risks, and the three questions to close with owners |
| 7 | Next steps | Two parallel execution tracks |

---

## Open questions to close before ADRs are written

1. **Is Foundry RBC's enterprise AI agent runtime?**
   - Owner: Rex Davis / Vinh Tran / Borealis
   - Determines whether Pattern 3 replaces Pattern 1 or is additive.

2. **What is RBC Assist built on today?**
   - Owner: RBC Assist product team
   - Python custom / Foundry / Copilot Studio — dictates the integration pattern.

3. **Do we commit to FSDM-in-Fabric as the semantic contract?**
   - Owner: Enterprise Data (George Chilakos)
   - If yes, JoAnn's DA team and Sam (Teradata) lead the semantic model design; POC a bounded domain first.

---

## Related ADRs and follow-on work

- **ADR-010** — Fabric Import semantic model as BI/AI surface layer (established)
- **ADR-011** — Snowflake Cortex as access + semantic layer (supersedes ADR-010) — **note:** this deck was drafted before ADR-011 landed; the Fabric Data Agent direction here may need reconciliation against the Snowflake Cortex decision
- **Next ADR** (to be drafted) — RBC Assist × Fabric Data Agent consumption pattern (or reconciled against Snowflake Cortex)
- **Next ADR** (to be drafted) — Teradata agent access via semantic model (deprecates FastAPI-direct-Teradata as an agent surface)
- **Architectural principle** (to be drafted) — All agent-accessible structured data shall be exposed via a governed semantic layer (Fabric or Snowflake Cortex per ADR-011)

---

## Proposed execution tracks

**Track A — Agent consumption surface**
1. Confirm RBC Assist tech stack with product team
2. Raise Foundry-as-runtime question with Rex / Vinh
3. POC Fabric Data Agent via Python SDK with OBO against a low-sensitivity semantic model
4. Draft ADR-011

**Track B — Unified semantic layer**
1. Write the architectural principle statement
2. Pick a bounded FSDM domain for POC (e.g. Customer)
3. Early Teradata licensing conversation with Sam
4. Draft ADR-012

---

## Notes on the deck format

- 16:9 widescreen, RBC brand palette (`#003068` primary dark blue, `#3068FF` primary blue, `#2AD2C9` teal accent)
- Arial font (Inter fallback), `Confidential — Internal Use Only` header on every slide
- No gradients, no drop shadows, no decorative bars — RBC design system compliant
