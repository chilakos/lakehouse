# The Two-Type Data Product Model — Why It Matters Now

**For:** Vinh Tran, Martin
**From:** George Chilakos, VP Enterprise Data
**Date:** May 2026
**Companion to:** ADR-017 (full technical decision), ADR-016 reconciliation note

---

## The problem in one paragraph

Most data mesh programmes — at RBC and across the industry — fail in the same way. They improve the technology and leave the governance untouched. The team that builds the pipeline becomes accountable for the accuracy of attributes they neither produce nor have authority to fix. Business owners of source systems remain disconnected from the downstream impact of their data quality decisions. The result is a more complex data warehouse rather than a data mesh, with the same fundamental defect: nobody who can fix a problem feels they own it.

Lumina is reaching the point where this matters. With the Fabric semantic plane (ADR-014) about to expose data to RBC Assist and Borealis through AI agents, an attribute that is wrong at source is no longer just a wrong number on a dashboard. It is a confidently asserted answer that strips the consumer's ability to apply their own context. We need the governance model fixed before the AI consumption surface is wide open, not after.

## What we are proposing

A two-type model for every data product in Lumina:

**Operational Data Products (ODPs)** are owned by the business leader of the operational area that transacts on the subject. They are deliberately rich (typically 80%+ of the source system's attribute surface) because the operational team needs operational depth. The owner has both the accountability for accuracy and the authority to fix issues at source. Consumers fit the ODP's model, not the reverse.

**Collaborative Data Products (CDPs)** are the cross-domain views assembled from multiple ODPs for use by the rest of the organization. They are narrow and purpose-fit (typically 10–20% of the union of contributing ODPs). They are *managed* by a Data Product Manager who is responsible for construction, monitoring, and SLAs — but accountability for the accuracy of each attribute remains with the contributing ODP owner. The Customer 360 surface, the counterparty exposure view, and most FSDM-derived enterprise tables are CDPs.

The structural change is a single artefact called the **attribute accountability map**: for every attribute in a CDP, the contributing ODP and the accountable business owner are recorded. No CDP enters production without it.

## Why this is uncomfortable, and why we should do it anyway

The Customer record at RBC is contributed to by P&CB, Capital Markets, Wealth, Risk, and Finance. Under the single-owner model that has been tacit until now, no business leader has accepted accountability for the Customer 360 surface, because no single business leader can credibly claim authority over all of it. The pipeline team — Lumina platform engineering — becomes the de facto accountable party. They cannot fix the data, only the pipeline. So defects accumulate, and the asset degrades.

The two-type model says the truth out loud: the Customer 360 surface is a *collaborative* product, no single business owner controls it, and accountability is therefore distributed at the attribute level. This requires a series of conversations with LOB heads to agree which attributes their ODP supplies and what they will be on the hook for. Those are the conversations we have been deferring. The model makes them unavoidable, but it also makes them tractable — because what is being asked of each LOB is bounded and specific, not open-ended.

The FSDM is the largest case in point. As it stands, it is a single conformed model with no attribute-level accountability map. Under this model, FSDM-derived tables that are exposed for cross-domain use are CDPs and require the map to be populated retroactively. This is a 6–9 month programme of work, not a one-time exercise. It is also the work that converts the FSDM from a 35-year-old asset that nobody is fully accountable for into one that has a defensible governance frame.

## What changes if we adopt this

For Lumina engineering: the Fabric semantic models we are building become CDPs by definition, owned by Data Product Managers in our team. Our accountability is for structure, SLAs, and lineage — not for whether the underlying source attribute is correct. That accountability flows to the contributing ODP owner, with the attribute accountability map as the routing record.

For LOB business leaders: explicit accountability for a defined set of attributes, with a clear escalation path when a defect is raised on a downstream CDP. This is more accountability than they have today, but it is also better-defined and more defensible than what they have informally been pulled into.

For RBC Assist and Borealis: when an AI-mediated answer is challenged, the attribute accountability map tells us who investigates. Today there is no such record, and the default landing pad is whoever owns the platform.

For the Lumina programme overall: a governance model that makes the EDW investment defensible and the AI consumption story credible. Without this, the AI ambition outruns the data quality foundation, and the first wrong-but-confident answer from RBC Assist becomes a much larger problem than it needs to be.

## What I am asking for

Three things, in the next 4–6 weeks:

1. **Endorsement of the model.** I am asking for sign-off on ADR-017 as the governance frame for Lumina, with the understanding that it implies a programme of attribute accountability mapping work that runs through 2026 and into 2027.

2. **Two pilot CDPs.** I am proposing `cdp.customer_360_lite` (P&CB) and `cdp.counterparty_exposure` (Capital Markets) as Phase 1 pilots. These are chosen for political tractability and business value — visible enough to matter, contained enough to complete in 12 weeks. I will need your support in the conversations with the relevant LOB heads to nominate ODP owners.

3. **Air cover on the FSDM framing.** Calling the FSDM a "legacy collaborative data product without an accountability map" is accurate but politically loaded. The framing is what makes the ADR useful as a forcing function with the LOB heads, but it will land harder if it is read as an EDW critique rather than as a governance modernization. Your endorsement of the framing — privately and publicly — is what makes the work happen at the pace required.

## What this is not

This is not a re-platforming. The Iceberg lakehouse, Trino, Fabric, Snowflake Cortex, and the Lumina Gateway all stand exactly as decided in ADR-002, ADR-011, ADR-014, and ADR-015. This is a governance overlay on the technology stack, not a replacement for any of it.

This is not a request for additional headcount in 2026. The Phase 1 pilot work is absorbable within the existing Lumina platform team. The FSDM mapping programme in 2027 will require LOB business analyst time more than platform engineering time, and that conversation is for later.

This is not novel. The two-type model is established in the data mesh literature (originating in Steve Jones's Feb 2022 piece on operational vs collaborative data products and reinforced in his subsequent writing) and is being adopted at scale by other large financial institutions facing the same multi-source-composite problem. We are not pioneering; we are catching up.

---

## Recommendation

Endorse the model, sponsor the two pilots, and commit to the FSDM framing. The cost of doing this now is a programme of accountability conversations that we have been deferring. The cost of not doing it is the AI consumption surface going live on a governance foundation that will not hold.
