# First Principles

These are the non-negotiable beliefs that guide every architectural and engineering decision in the Lakehouse project. Use them to settle debates, evaluate tradeoffs, and onboard new team members.

---

## 1. Single Copy, Many Readers

Data is written once in Apache Iceberg and read by any engine — Trino, Teradata, Snowflake, BI tools, AI models. We never create additional copies to serve a new consumer.

**Test:** If a proposed design requires duplicating data into another platform, it violates this principle.

---

## 2. Reuse Over Rebuild

Pipelines, schemas, metric definitions, and governance rules are built once and shared across layers. The medallion architecture (Bronze → Silver → Gold) exists to maximise reuse at every stage.

**Test:** Before building something new, ask: "Does this already exist in another layer or pipeline?"

---

## 3. Own Your Destiny

We use open formats (Iceberg), open catalogs (Nessie), and open protocols (REST) so the organization is never locked into a single vendor's proprietary platform for its data layer.

**Test:** If removing a vendor would require re-writing the data layer, we have a dependency problem.

---

## 4. Bring Your Own Compute

The data layer does not dictate the compute layer. Consumers choose the engine that fits their workload — Trino for federated queries, Teradata for existing workloads, Snowflake for external consumers — all reading the same Iceberg tables.

**Test:** Can a new compute engine be added without changing how data is stored or cataloged?

---

## 5. BI & AI Ready by Default

Every dataset is modeled, documented, and served through a semantic layer (Cube) so it is immediately consumable for dashboards, reports, and ML workloads. Data that can't be consumed is waste.

**Test:** Can a BI analyst or AI model use this dataset today without additional transformation?

---

## 6. Enterprise Governance as Code

Security policies (Ranger), data quality checks (Soda), lineage (OpenLineage), and data classification are automated, version-controlled, and auditable. Governance is not an afterthought — it ships with the data.

**Test:** Is every governance rule in source control, testable in CI, and enforceable without manual intervention?

---

## 7. Lineage & Traceability

Every record's origin, transformation, and destination is tracked end-to-end. This is non-negotiable for BCBS 239 compliance, operational trust, and debugging production issues.

**Test:** Given any Gold-layer record, can we trace it back to its raw source and every transformation it passed through?

---

## 8. Quality at the Gate

Data quality is validated at ingestion (Bronze), transformation (Silver), and aggregation (Gold). Bad data does not propagate downstream. SodaCL checks are first-class citizens in every pipeline.

**Test:** If a quality check fails at Bronze, does the pipeline halt before writing to Silver?

---

## 9. Guardrails, Not Gates

Developers move fast within well-defined boundaries — pre-commit hooks, CI checks, policy-as-code, automated tests — rather than waiting for manual approvals. Speed and safety are not opposites.

**Test:** Can a developer ship a compliant change without waiting for a human gatekeeper?

---

## How to Use These Principles

| Context | How to Apply |
|---------|-------------|
| **Architecture Decision Records (ADRs)** | Reference the principle(s) that support or challenge a proposed decision |
| **Code Reviews** | Call out violations — "This creates a second copy of the dataset (violates Principle 1)" |
| **Onboarding** | New team members read this document in their first week |
| **Tradeoff Debates** | When two valid approaches exist, the one that better aligns with these principles wins |