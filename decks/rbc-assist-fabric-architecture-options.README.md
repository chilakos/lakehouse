# RBC Assist × Fabric Data Agent — Architecture Options

**File:** `rbc-assist-fabric-architecture-options.pptx`
**Author:** George Chilakos, VP Enterprise Data
**Date:** April 2026
**Status:** Working draft — for Phase 2 planning alongside ADR-011

---

## Reconciliation with ADR-011 (important)

This deck was drafted before ADR-011 (Snowflake Cortex as Access and Semantic Layer) landed. ADR-011 establishes a phased approach — Snowflake Cortex in Phase 1 (ship now), Fabric as a parallel BI/AI surface in Phase 2 (when OBIEE → Power BI migration completes). The deck's framing assumes Fabric Data Agent as the primary path, which is now the Phase 2 question rather than the immediate one.

**How to read this deck today:**
- The three consumption patterns (custom Python + FastAPI, Foundry-mediated, Copilot Studio) remain valid design options for the **Phase 2 Fabric Data Agent integration**
- The FastAPI trust boundary pattern described here aligns with and reinforces the trust boundary established in ADR-011
- The "unified semantic layer" argument is subsumed by ADR-011's "one definition, two deployments" principle — the YAML semantic model template deploys to Snowflake semantic views (P1) and Fabric Import semantic models (P2)
- The Foundry-as-orchestration question remains open and applies to Phase 2

The newly drafted ADR-012 formalizes the Phase 2 Fabric Data Agent consumption pattern and should be read as the authoritative follow-on to this deck.

---

## Purpose

This deck frames design options for connecting RBC Assist to Fabric Data Agent as part of the Phase 2 extension described in ADR-011. Three patterns are evaluated:

1. **Pattern 1** — Custom Python app with FastAPI trust boundary (direct SDK integration, symmetric with existing ADR-011 pattern)
2. **Pattern 3** — Foundry agent between RBC Assist and Fabric Data Agent (adds Azure Policy model governance and Entra Agent ID inventory)
3. **Pattern 2** — Copilot Studio in Teams/M365 (future surface, can reuse a Foundry backend)

---

## Key takeaways

- **Foundry is not strictly required** to expose Fabric Data Agent to RBC Assist. The Fabric Data Agent Python SDK supports On-Behalf-Of (OBO) identity passthrough natively. Foundry's value is governance and orchestration — Azure Policy model allowlist, Entra Agent ID inventory, Content Safety, and multi-source orchestration — not connectivity.
- **The Fabric Data Agent internal NL2DAX model is Microsoft-managed and opaque.** RBC does not get to choose this model. This applies equally in all three patterns — Foundry does not change it.
- **Service Principal Name (SPN) authentication is not supported** by Fabric Data Agent. Every call requires a human user's Entra token in the chain. This rules out agentic background jobs against Fabric Data Agent; those workflows need an alternate path (direct XMLA or direct Delta read with service identity).
- **The FastAPI trust boundary (per ADR-011) is the single agent entry point.** It does not go away — it gains a second backend route for Fabric Data Agent alongside the existing Snowflake Cortex route.

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

## Open questions to close

1. **Is Foundry RBC's enterprise AI agent runtime?**
   - Owner: Rex Davis / Vinh Tran / Borealis
   - Applies to Phase 2. Determines whether Pattern 3 replaces Pattern 1 or is additive. ADR-012 documents the options but does not resolve this strategic question.

2. **What is RBC Assist built on today?**
   - Owner: RBC Assist product team
   - Python custom / Foundry / Copilot Studio — dictates the integration pattern.

3. **Phase 1 vs Phase 2 user routing**
   - Owner: Enterprise Data (George Chilakos) + Borealis
   - Which workloads stay on Snowflake Cortex (P1) vs. move to Fabric Data Agent (P2) once Fabric is live? FastAPI routing rules need to be defined before Phase 2.

---

## Related ADRs and follow-on work

- **ADR-010** — Fabric Import semantic model as BI/AI surface layer (superseded by ADR-011)
- **ADR-011** — Snowflake Cortex as access + semantic layer (current authoritative direction)
- **ADR-012** — RBC Assist × Fabric Data Agent consumption pattern (Phase 2 extension to ADR-011)

---

## Notes on the deck format

- 16:9 widescreen, RBC brand palette (`#003068` primary dark blue, `#3068FF` primary blue, `#2AD2C9` teal accent)
- Arial font (Inter fallback), `Confidential — Internal Use Only` header on every slide
- No gradients, no drop shadows, no decorative bars — RBC design system compliant
