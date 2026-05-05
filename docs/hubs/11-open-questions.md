# 11 — Open questions for review

Decisions still open. These need to close before Phase 1 build starts.

## 11.1 Snowflake-only or hybrid hub compute?

**Question:** Are all hubs going to run on Snowflake long-term, or do
we need to support Iceberg-on-Trino / Fabric / Databricks for some
hubs?

**Why it matters:** The framework is portable in principle (dbt Core
adapters), but the first hub's patterns set defaults. If we know a
second compute target is coming, Phase 1 should include adapter
abstraction.

**Recommendation:** Start Snowflake-only for Phase 1–4. Revisit before
Phase 5.

## 11.2 Which catalog?

**Question:** What is the canonical catalog for hub-certified
products? Candidates:

- Microsoft Fabric / OneLake catalog
- Atlan
- Collibra
- Snowflake Horizon
- Internal/in-house

**Why it matters:** The framework's catalog registration hook needs a
target. The hook is thin, but the choice affects what governance
metadata flows downstream.

**Recommendation:** Need direction from Vinh / Rex. Build the hook as
a thin abstraction in Phase 1; specific tool integration in Phase 2.

## 11.3 Federated read governance from Teradata

**Question:** ADR-014 amendment covers the gateway pattern for AI
traffic, but the hub's read path from Teradata views via Trino needs
explicit Ranger policy. Who owns it — Platform Engineering, Enterprise
Data, or the LOB DMO?

**Why it matters:** Without clear ownership, federated reads will
either be over-permissive (security risk) or under-permissive (DMOs
cannot get their work done).

**Recommendation:** Platform Engineering owns the policy framework.
LOB DMOs declare entitlement requests. Enterprise Data approves
sensitive ones. Need to formalize.

## 11.4 Hub Steward role definition

**Question:** This role does not exist formally today. What is the
job description, reporting line, and time commitment?

**Why it matters:** The Hub Steward is the approver for prod
promotions and rehydrate requests. Without a clear role, approvals
will bottleneck on a few overloaded individuals.

**Recommendation:** One Hub Steward per hub, reporting line into the
LOB DMO leadership, ~25% of role. Need to agree with Vinh and the LOB
heads before Phase 2.

## 11.5 dbt Core or dbt Cloud?

**Question:** Run dbt Core on our own runners, or use dbt Cloud?

**Why it matters:** dbt Cloud adds a vendor in the path. dbt Core on
our runners reuses the Helios pattern.

**Recommendation:** dbt Core. Confirm with Saurabh.

## 11.6 Sigma Computing fit

**Question:** Sigma was floated as a possible authoring layer for the
DMO tier. How does it fit?

**Why it matters:** Sigma is an authoring tool, not a framework. If
it produces SQL that gets imported into the dbt project, it can fit.
If it runs as a parallel authoring path with its own deployment, it
duplicates the framework.

**Recommendation:** Evaluate Sigma as a *front-end* to `product.yml`
for DMO-tier users — Sigma generates the SQL, framework wraps it.
Worth a separate evaluation in Phase 4.

## 11.7 Snowflake-native dbt (Workspaces)

**Question:** The Snowflake team is exploring dbt-on-Snowflake. Are
we taking a position?

**Why it matters:** If the Snowflake team adopts the native pattern
and the hub program adopts dbt-Core-on-our-runners, we will have two
parallel patterns at RBC and DMOs will get conflicting guidance.

**Recommendation:** Take a clear position in an ADR
(see [`07-cicd-pattern.md`](/lakehouse/hubs/07-cicd-pattern/) for the case
against dbt-on-Snowflake). Walk the position through with the
Snowflake team and Vinh. Get to one pattern.
