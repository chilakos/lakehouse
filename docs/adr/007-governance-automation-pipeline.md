# ADR-007: Automated Governance Pipeline — OpenMetadata Classification to Ranger TagREST

**Status:** Accepted
**Date:** 2026-03-30
**Authors:** George Chilakos, VP Enterprise Data (Lumina / RBC)
**Raised by:** Governance scalability review (March 2026)

---

## Context

The lakehouse governance stack has an elegant enforcement layer but a manual classification
bottleneck:

**What works (automated):**
- New tables in Nessie are immediately protected by Ranger's deny-by-default policy
- Tag-based masking policies in Ranger work correctly (RESTRICTED → MASK_NULL/SHOW_LAST_4,
  CONFIDENTIAL → MASK_HASH, etc.) — see `bootstrap-policies.py`
- Access policies use wildcards (`iceberg.gold.*`) — new tables are covered automatically

**What is broken (manual):**
- Column sensitivity classification is manual. `bootstrap-policies.py` attempts to seed
  classification tags but defers with a log message: "requires Atlas integration"
- Row-level filter policies (business_unit filtering) are manual per table
- No automated pipeline: table appears → columns classified → tags pushed to Ranger

At 2 tables, manual tagging is fine. At thousands of tables (the Teradata migration target),
this is a compliance risk: new tables with PII columns sit unmasked until someone manually
classifies them. This is a BCBS 239 audit finding waiting to happen.

---

## Decision

**We will build an automated classification pipeline using OpenMetadata's built-in
auto-classification engine and Ranger's TagREST API. No Apache Atlas. No Gravitino.**

The pipeline:

```
Table lands in Nessie (Gold/Silver)
    ↓
OpenMetadata ingestion discovers table (existing Trino connector)
    ↓
OpenMetadata Auto-Classification workflow scans columns
    (spaCy NLP + Presidio recognizers: SSN, email, phone, credit card, etc.)
    ↓
Tag sync bridge (Airflow DAG) reads classified columns from OpenMetadata API
    ↓
Maps OpenMetadata PII tags to Ranger tag taxonomy:
    PII.Sensitive (SSN/SIN patterns) → RESTRICTED
    PII.Sensitive (email/phone)      → CONFIDENTIAL
    No PII tag                       → INTERNAL or PUBLIC (by schema)
    ↓
Pushes tag-resource associations to Ranger TagREST API
    (POST /service/tags/tagresourceassoc)
    ↓
Existing Ranger masking policies activate automatically
```

---

## Rationale

### 1. OpenMetadata has production-ready auto-classification

OpenMetadata uses spaCy NLP and Microsoft Presidio recognizers to scan column names and
sample data. Built-in detectors cover: email, phone, SSN, credit card, address, IP address,
date of birth, passport number, driver's license. Confidence threshold is configurable
(0-100). Custom classifiers (regex, column name patterns) are available from v1.12+.

The current `trino-ingestion.yaml` only runs `DatabaseMetadata` ingestion. A second workflow
of type `AutoClassification` is needed targeting Gold and Silver schemas.

### 2. Ranger's TagREST API works without Atlas

The `bootstrap-policies.py` deferred tag seeding because it assumed Atlas was required.
Research confirms Ranger has a full TagREST API that supports programmatic tag management
without Atlas:

- `POST /service/tags/tagdefs` — create tag definitions
- `POST /service/tags/tags` — create tag instances
- `POST /service/tags/serviceresources` — register column-level resources
- `POST /service/tags/tagresourceassoc` — associate tags with resources

This is the API path that replaces the deferred `seed_classification_tags()` function.

### 3. Gravitino does not solve this problem

Gravitino (Apache TLP, v1.2.0) provides RBAC push-down to Ranger — which we already have.
It does NOT offer:
- PII auto-classification
- Tag-based (ABAC) policy management (on roadmap, not shipped)
- Business glossary, data quality profiling, or discovery portal

Gravitino is complementary to Nessie + OpenMetadata, not a replacement (confirmed by our
SWOT analysis in `docs/swot/data/open-metadata.yml`). Its multi-catalog federation has
marginal value here since Trino already federates at the query layer. Gravitino should be
monitored for ABAC maturity but not added to the stack now.

### 4. Apache Atlas is not needed

Atlas is the traditional tag source for Ranger's tag-sync daemon. However:
- Atlas adds significant infrastructure (HBase + Solr + Kafka)
- The same outcome is achieved via Ranger's TagREST API with a lightweight Python bridge
- RANGER-4978 (native OpenMetadata tag source for Ranger tagsync) is an open PR but not
  merged as of March 2026 — we cannot depend on it

### 5. Row-level filters can be convention-generated

For tables with a `business_unit` column (detectable via OpenMetadata schema metadata),
the tag sync bridge auto-generates Ranger row-filter policies using the same pattern as
`build_row_filter_policies()` in `bootstrap-policies.py`.

---

## Implementation

### Phase 1: Auto-Classification (build now)

1. Add `auto-classification.yaml` alongside existing `trino-ingestion.yaml`:
   - Type: `AutoClassification`
   - Confidence threshold: 80
   - Schema filter: `gold.*`, `silver.*`
   - Classification filter: `PII`
   - Schedule: After each metadata ingestion cycle or daily

2. Build tag sync bridge as an Airflow DAG:
   - Query OpenMetadata API: `GET /api/v1/tables?fields=columns,tags`
   - Map PII classifications → Ranger tag taxonomy (RESTRICTED/CONFIDENTIAL/INTERNAL/PUBLIC)
   - Push to Ranger TagREST API
   - Generate row-filter policies for tables with `business_unit` column
   - Schedule: Every 6 hours or triggered after classification completes

3. Configure OpenMetadata webhook for real-time triggers on tag assignment events

### Phase 2: Harden (Q3 2026)

- Add custom classifiers for domain-specific columns (`account_id`, `trader_id`, `sin_number`)
  using OpenMetadata's custom recognizer framework
- Drift detection CI check: compare OpenMetadata classifications against Ranger tag
  associations, alert on gaps
- Monitor RANGER-4978: if merged, replace custom bridge with native tagsync

### Phase 3: Evaluate (2027)

- Gravitino ABAC: re-evaluate if Gravitino ships production-ready tag-based policy push-down
- Privacera: evaluate if cross-engine enforcement (Teradata + Trino + future engines)
  becomes a hard requirement

---

## Consequences

- `bootstrap-policies.py` `seed_classification_tags()` will be replaced by the automated
  pipeline (the function currently logs a deferral message)
- New Airflow DAG: `governance_tag_sync`
- New OpenMetadata workflow config: `auto-classification.yaml`
- The glossary-seed.json claim that "PII columns are automatically classified via regex rules"
  will become true (it is currently aspirational)
- Classification latency: new tables will have tags applied within 6 hours of first ingestion
  (real-time via webhook in Phase 1.3)
- No new infrastructure services — uses existing OpenMetadata, Ranger, Airflow, and PostgreSQL
