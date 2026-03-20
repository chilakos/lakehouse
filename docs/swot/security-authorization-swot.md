# Data Security & Authorization -- SWOT Analysis

**Prepared for:** Leadership Review
**Date:** 2026-03-20
**Phase:** 3 -- Governance, Security Hardening & Platform
**Status:** Evaluation of cross-engine authorization options

## Executive Summary

Apache Ranger is our current authorization engine, providing column-level masking, row-level filtering, and tag-based classification for Trino. However, Ranger only enforces policies natively on Hadoop-ecosystem engines (Trino, Spark, Hive). This forces engine-native security workarounds for Teradata (view-based masking) and Snowflake (dynamic masking policies), creating governance fragmentation that conflicts with Principle 3 ("Own Your Destiny") and Principle 4 ("Bring Your Own Compute").

This SWOT evaluates whether to stay with Ranger or adopt a cross-engine authorization platform that supports our full compute landscape -- including engines we may add in the future.

**Recommendation:** Retain Apache Ranger for Trino/Spark enforcement today, but begin evaluating **Privacera** (commercial, Ranger-compatible) or **Unity Catalog OSS** (open-source, Iceberg REST native) as a cross-engine governance layer. The choice between them depends on budget appetite and whether Teradata support is a hard requirement.

---

## Current State

| Engine | Current Security Approach | Policy Source | Gap |
|--------|--------------------------|---------------|-----|
| **Trino** | Apache Ranger plugin | Ranger policies | None -- full support |
| **Spark** | Apache Ranger plugin | Ranger policies | None -- full support |
| **Teradata** | View-based masking (engine-native) | Manual DDL | Policies not synced with Ranger |
| **Snowflake** | Dynamic masking policies (engine-native) | Snowflake-native | Policies not synced with Ranger |

**Core problem:** Two separate policy systems. Changes to masking rules require updating Ranger *and* each engine-native policy set independently. This creates drift risk, audit gaps, and operational overhead that scales with each new compute engine added.

---

## Option Comparison

| Criteria | Apache Ranger | OPA (Trino Plugin) | Privacera | Immuta | Unity Catalog OSS | Gravitino |
|----------|--------------|---------------------|-----------|--------|-------------------|-----------|
| **License** | Free (Apache 2.0) | Free (Apache 2.0) | Commercial | Commercial | Free (Apache 2.0) | Free (Apache 2.0) |
| **Trino support** | Yes (native plugin) | Yes (native plugin) | Yes (via Ranger) | Yes (Starburst plugin) | Yes (Iceberg REST) | Yes (native connector) |
| **Spark support** | Yes (native plugin) | No | Yes (via Ranger) | Yes (Databricks) | Yes (native) | Yes (native connector) |
| **Snowflake support** | No | No | Yes (PolicySync) | Yes (native) | Partial (Iceberg REST reads) | Partial (Iceberg REST reads) |
| **Databricks support** | No | No | Yes (native) | Yes (Unity Catalog) | Yes (native) | Yes (connector) |
| **Teradata support** | No | No | Unknown (verify) | No | No | No |
| **Column masking** | Yes | Yes | Yes | Yes | Commercial only (not in OSS) | Planned (ABAC roadmap) |
| **Row filtering** | Yes | Yes | Yes | Yes | Commercial only (not in OSS) | Planned (ABAC roadmap) |
| **Tag-based policies** | Yes (Atlas integration) | No (custom Rego) | Yes (discovery + tags) | Yes (attribute-based) | Yes (governed tags) | Yes (tag system, ABAC 2026) |
| **Policy-as-code** | XML/JSON policies | Rego policies | UI + API | UI + API | SQL + API | API + Ranger push-down |
| **Iceberg REST catalog** | No | No | No | No | Yes (native) | Yes (native) |
| **Audit aggregation** | Per-engine only | Per-engine only | Unified cross-engine | Unified cross-engine | Unified (UC-managed) | Unified (built-in) |
| **Maturity** | Very high (10+ years) | High (CNCF graduated) | High (enterprise) | High (enterprise) | Medium (OSS since 2024) | Medium (Apache TLP 2025) |

---

## SWOT: Apache Ranger (Current State)

### Strengths

#### S1: Proven at Enterprise Scale
Ranger has 10+ years of production deployments across thousands of organizations. It is the de facto standard for Hadoop-ecosystem access control, natively integrated by AWS EMR, Starburst, Confluent, and all major cloud Hadoop distributions.

#### S2: Deep Trino/Spark Integration
Native plugins for column masking, row filtering, and tag-based classification with no performance overhead. Our Phase 3 implementation is already operational.

#### S3: Policy-as-Code in Source Control
Ranger policies are JSON/XML, versionable in Git, deployable via CI/CD. This aligns with Principle 6 ("Enterprise Governance as Code") and Principle 9 ("Guardrails, Not Gates").

#### S4: No License Cost
Apache 2.0 licensed. No per-query pricing or commercial agreements required.

### Weaknesses

#### W1: Hadoop-Ecosystem Only
Ranger cannot enforce policies on Snowflake, Databricks, Teradata, BigQuery, Redshift, or any non-Hadoop engine. This directly conflicts with Principle 4 ("Bring Your Own Compute") -- adding a new compute engine requires building a separate security integration from scratch.

#### W2: Governance Fragmentation
Two separate policy systems (Ranger for Trino/Spark, engine-native for everything else) create:
- **Drift risk:** Masking rules diverge between engines over time
- **Audit gaps:** No single view of who accessed what across all engines
- **Operational overhead:** Every policy change must be applied in multiple places
- **Compliance risk:** BCBS 239 requires demonstrable consistency across all access paths

#### W3: Forces Engine Deprecation
If security must be consistent and Ranger only covers Trino/Spark, the path of least resistance is to deprecate engines Ranger cannot reach (Snowflake, Databricks). This reduces the organization's compute flexibility and contradicts the "Bring Your Own Compute" principle.

#### W4: No Iceberg REST Catalog Integration
Ranger operates at the engine level, not the catalog level. It cannot enforce policies through the Iceberg REST catalog API, meaning engines that access Iceberg tables via REST (without a Ranger plugin) bypass all governance.

### Opportunities

#### O1: Privacera as a Commercial Ranger Extension
Privacera (founded by Ranger's creators) extends Ranger with PolicySync connectors for Snowflake, Databricks, Redshift, and more. Existing Ranger policies can be lift-and-shifted to Privacera without rewriting. This is the lowest-friction path to cross-engine governance.

#### O2: Unity Catalog OSS as Catalog-Level Governance
Unity Catalog enforces access control at the Iceberg REST catalog layer via scan planning -- policies travel with the data regardless of which engine reads it. Since our architecture already uses REST catalog (Nessie), this approach aligns naturally.

#### O3: Gravitino Authorization Push-Down
Gravitino (now Apache TLP) pushes privileges down to underlying permission systems, including Ranger. As Gravitino's ABAC engine matures (2026 roadmap), it could serve as a unified policy layer that delegates to Ranger for Trino/Spark while handling other engines natively.

### Threats

#### T1: Ranger Becomes a Ceiling on Architecture Evolution
If Ranger remains the sole authorization system, every future compute engine decision is gated by "does it have a Ranger plugin?" This inverts the architecture -- the security tool dictates compute choices instead of compute being pluggable.

#### T2: Compliance Exposure from Policy Fragmentation
Auditors and regulators (BCBS 239, GDPR, SOX) expect demonstrable proof that the same access controls apply regardless of how data is accessed. Two separate policy systems are harder to defend under audit than one unified system.

#### T3: Operational Scaling Risk
Each new engine-native security integration adds operational burden: separate policy authoring, separate testing, separate audit collection, separate incident response procedures. This cost grows linearly with each compute engine added.

---

## SWOT: Cross-Engine Alternatives

### Privacera (Commercial, Ranger-Compatible)

| Dimension | Assessment |
|-----------|-----------|
| **Strengths** | Built by Ranger creators; lift-and-shift existing policies; PolicySync for Snowflake, Databricks, Redshift, BigQuery; unified audit; enterprise support |
| **Weaknesses** | Commercial license (cost); Teradata support unconfirmed; documentation noted as incomplete by users; smaller engineering team |
| **Opportunities** | Fastest path from current Ranger to cross-engine; no architecture rewrite needed; maintains all existing Trino/Spark integrations |
| **Threats** | Vendor dependency on Privacera; commercial pricing may not align with "Own Your Destiny" principle |

### Unity Catalog OSS (Open-Source, Catalog-Level)

| Dimension | Assessment |
|-----------|-----------|
| **Strengths** | Apache 2.0; Iceberg REST catalog native; credential vending for S3/GCS/ADLS; 700+ companies using commercial UC; 1M+ SDK downloads/month |
| **Weaknesses** | **Critical: row filtering, column masking, and ABAC are commercial Databricks-only features -- NOT available in the open-source version.** OSS UC provides only basic table/schema/catalog-level grants. Tables with row filters or column masks **cannot be accessed via the Iceberg REST API**, undermining the multi-engine governance story. Trino OAuth2/multi-tenant still maturing; would require catalog migration from Nessie; no Teradata support |
| **Opportunities** | If Databricks opens governance features to OSS, this becomes the strongest option. Iceberg REST native means any engine can discover tables. Active community and LF AI sandbox project |
| **Threats** | Databricks controls which features are open-sourced; most valuable governance features may remain commercial indefinitely; catalog migration from Nessie has operational risk; losing Nessie branching (unique differentiator) |

### OPA (Open-Source, Trino-Only)

| Dimension | Assessment |
|-----------|-----------|
| **Strengths** | CNCF graduated; Rego policy language is powerful; column masking + row filtering in Trino; universal policy engine beyond data |
| **Weaknesses** | Trino-only for data access control (same limitation as Ranger); no Snowflake/Databricks/Teradata; no tag-based classification built in; custom Rego development required |
| **Opportunities** | Could replace Ranger for Trino if policy-as-code in Rego is preferred over Ranger XML |
| **Threats** | Does not solve the core cross-engine problem; lateral move from Ranger, not an upgrade |

### Gravitino (Open-Source, Federation Layer)

| Dimension | Assessment |
|-----------|-----------|
| **Strengths** | Apache TLP (graduated June 2025); unified metadata + authorization; Ranger push-down today; ABAC engine on 2026 roadmap; multi-engine (Trino, Spark, Flink); tag system built in |
| **Weaknesses** | ABAC/fine-grained enforcement still on roadmap (not GA); 1.0 released recently; limited production references for authorization specifically; no Snowflake/Teradata enforcement today |
| **Opportunities** | Could layer on top of Nessie (preserving branching); authorization push-down to Ranger means zero disruption to current Trino/Spark setup; future ABAC would unify policies |
| **Threats** | Betting on roadmap features; authorization maturity lags catalog maturity; may not deliver cross-engine enforcement in our timeline |

### Immuta (Commercial, Multi-Engine)

| Dimension | Assessment |
|-----------|-----------|
| **Strengths** | Native integrations: Snowflake, Databricks (Unity Catalog), Starburst/Trino, Redshift, BigQuery, S3; attribute-based access control; 4x Trino performance improvements (2025); unified audit |
| **Weaknesses** | Commercial license; no Teradata support; Redshift deprecating Python UDFs affects some masking types; smaller market share than Privacera |
| **Opportunities** | Covers our top 3 engines (Trino, Snowflake, Databricks) natively; attribute-based policies align with our tag classification system |
| **Threats** | Vendor lock-in; commercial dependency conflicts with Principle 3 |

---

## Decision Matrix

| Criteria | Weight | Ranger (current) | Privacera | Unity Catalog OSS | Gravitino | Immuta |
|----------|--------|-------------------|-----------|-------------------|-----------|--------|
| Cross-engine coverage | **High** | Low (2 engines) | High (6+ engines) | Medium (4 engines) | Medium (3 engines) | High (6+ engines) |
| Column masking + row filtering | **High** | Yes | Yes | Yes | Roadmap | Yes |
| Tag-based classification | **High** | Yes | Yes | Yes | Yes (ABAC 2026) | Yes |
| Open-source / no vendor lock-in | **High** | Yes | No | Yes | Yes | No |
| Iceberg REST catalog alignment | **Medium** | No | No | Yes (native) | Yes (native) | No |
| Nessie compatibility | **Medium** | N/A | N/A | Replace or coexist | Layer on top | N/A |
| Teradata support | **Medium** | No | Unknown | No | No | No |
| Migration effort from Ranger | **Medium** | N/A | Low (lift-and-shift) | High (catalog change) | Low (push-down) | High (new platform) |
| Unified audit trail | **Medium** | No | Yes | Yes | Yes | Yes |
| Production maturity | **Medium** | Very high | High | Medium | Medium | High |
| License cost | **Low** | Free | Paid | Free | Free | Paid |

---

## Recommendation

### Short-Term (Now): Keep Ranger, Stop Deprecating Engines

Do not deprecate Snowflake or Databricks for lack of Ranger support. Instead, acknowledge that Ranger is our Trino/Spark authorization layer, not our universal governance platform. Continue engine-native security for Snowflake/Teradata with documented policy sync procedures.

### Medium-Term (Q3 2026): Evaluate Privacera or Unity Catalog OSS

Run a 4-week proof-of-concept for one of:

1. **Privacera** -- if budget allows and cross-engine coverage is the priority. Fastest path: existing Ranger policies transfer directly. Best for organizations that need Snowflake + Databricks + Trino governance immediately.

2. **Unity Catalog OSS** -- if open-source and catalog-level governance is the priority. **Caveat:** Row filtering, column masking, and ABAC are commercial Databricks-only features not available in the OSS version. Tables with these policies cannot be accessed via Iceberg REST API. Evaluate only if Databricks opens these features to OSS, or if basic catalog-level grants are sufficient.

### Long-Term (2027): Monitor Gravitino ABAC

Gravitino's authorization push-down to Ranger and planned ABAC engine could provide unified governance while preserving our Nessie catalog investment. Monitor the 1.x releases for production-ready cross-engine enforcement. If Gravitino delivers on its 2026 ABAC roadmap, it becomes a compelling open-source alternative that layers on top of our existing architecture rather than replacing it.

### What This Means for "Bring Your Own Compute"

| Approach | Compute engines supported | Principle 4 alignment |
|----------|--------------------------|----------------------|
| Ranger only (current) | Trino, Spark | Low -- forces engine deprecation |
| Ranger + engine-native (current workaround) | Trino, Spark, Teradata, Snowflake | Medium -- fragmented governance |
| Privacera | Trino, Spark, Snowflake, Databricks, Redshift, BigQuery | High -- unified governance |
| Unity Catalog OSS | Any Iceberg REST client | High -- catalog-level governance |
| Gravitino (future) | Trino, Spark, Flink + ABAC targets | Medium-High -- depends on roadmap |

---

*Prepared by: Lakehouse Architecture Team*
*Review cycle: Quarterly (next review: 2026-Q3)*
*Sources: Apache Ranger docs, Privacera blog & PDF, Trino OPA docs, Immuta 2025.1 docs, Unity Catalog blog, Gravitino 2025 summary*
