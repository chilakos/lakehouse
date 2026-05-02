# Lumina Data Hub — 3-Month MVP Plan for PI Planning

| Field | Value |
| --- | --- |
| **Document type** | Program Increment plan |
| **Date** | 2026-05-02 |
| **Author** | George Chilakos (VP, Enterprise Data) |
| **PI window** | Q3 2026 (13 weeks, 3 months) |
| **Companion to** | Data Hub Architecture v2, ADRs 011/012/013/014/015 |

## Purpose

Deliver the smallest credible end-to-end slice of the Lumina Data Hub Architecture in one PI. The slice must exercise every architectural plane — Raw Zone, EDLH, one LOB hub, semantic plane, gateway, consumption — so that the architecture is *validated* rather than just *agreed to*. Anything not on this plan is explicitly out of scope for this PI.

## The MVP slice in one sentence

**One LOB hub (Capital Markets) reads from the EDLH and a Raw Zone namespace, publishes one certified data product (Counterparty Risk Score), exposes one Fabric semantic model, has one Fabric Data Agent reachable via the RBC Data Gateway, and answers one defined question end-to-end through RBC Assist.**

Everything else — additional hubs, additional products, additional consumers, full LOB rollout — is post-MVP.

## Why this slice

Three reasons it earns its keep:

1. **It exercises every plane.** Storage (Iceberg), Raw Zone (Capital Markets namespace), EDLH (conformed Customer + Counterparty), LOB hub (Capital Markets bronze→silver→gold), semantic plane (Fabric semantic model), gateway (FastAPI on OCP), consumption (RBC Assist). If this slice works, the architecture is validated.

2. **Counterparty Risk Score is genuinely useful.** It is a real Capital Markets data product with real consumers (Risk function primarily), and it is plausibly the first product to be promoted to enterprise scope down the line. It is not a toy.

3. **It is small enough to fit in 13 weeks** with a realistic team. Skipping any plane — say, deferring the gateway — would invalidate the validation. Adding a second hub or product would not fit.

## What the MVP delivers

### Functional outcomes

- A working RBC Assist conversational query: *"What is RBC's exposure to counterparty X in Capital Markets, and what is the counterparty risk score?"* The answer flows through the gateway, hits the Capital Markets Fabric Data Agent, queries the Capital Markets semantic model, executes against Hub Gold (Snowflake), joins to the conformed Counterparty dimension from EDLH, and returns a grounded answer with lineage.
- One certified data product (Counterparty Risk Score) published in the Data Product Registry with a contract in Git, versioned, with a documented SLA.
- One Power BI report on the Capital Markets semantic model, used by the Capital Markets analytics team for daily counterparty review.

### Architectural outcomes

- Raw Zone (Iceberg) operational with Capital Markets namespace and Enterprise namespace.
- One operational source landing live in each namespace (Capital Markets: a representative trading platform; Enterprise: customer master via CDC).
- EDLH bronze→silver pipeline operational with at least Customer and Counterparty conformed dimensions in Silver.
- Capital Markets Hub bronze→silver→gold pipeline operational, reading from both EDLH and Raw Zone.
- Capital Markets Fabric semantic model published, with at least 5 measures and 3 dimensions.
- Capital Markets Fabric Data Agent published.
- RBC Data Gateway MVP deployed on OCP with all seven responsibilities operational at minimum-viable level.
- Data Product Registry MVP deployed (single product registered, lifecycle workflow exercised end-to-end).

### Governance outcomes

- Purview labels propagating end-to-end from Raw Zone through to semantic model.
- Ranger policies enforcing access at the storage layer.
- Lineage visible in OpenLineage from Raw Zone source through to RBC Assist response.
- Audit log entries for every gateway call flowing to RBC SIEM.

## What is explicitly NOT in MVP

To prevent scope creep — these are deferred to subsequent PIs:

- A second LOB hub (P&CB, Wealth, Insurance, Risk).
- A second certified data product.
- The Tier 2 Enterprise Conformance layer (ADR-016) full build — only the Counterparty conformed dimension is in scope.
- The entity-resolution graph (Neptune/Neo4j) — Counterparty conformance is done via standard Iceberg tables in MVP.
- Cross-hub orchestration in the gateway — single-agent routing only in MVP.
- Fabric Mirroring of Snowflake (will be piloted, but not on the critical path).
- DirectQuery to Trino performance optimization — DirectQuery to Snowflake only in MVP (Capital Markets is cloud-primary).
- Promotion path workflow — out of scope; the one MVP product stays in the Capital Markets hub.
- M365 Copilot integration — RBC Assist only.
- LOB self-serve ingestion runtime polishing — Capital Markets Raw Zone landing is platform-team-built in MVP, with LOB self-serve as a fast-follow.
- FSDM CDC into Raw Zone — out of scope for MVP, scheduled for the next PI.

## Team and effort

Estimated 9-10 FTE-equivalent for 13 weeks, organized into five workstreams. PI planning should confirm exact named owners.

| Workstream | FTE | Lead | Scope |
| --- | --- | --- | --- |
| **WS1: Storage & Raw Zone** | 1.5 | Sanjeev (Platform Engineering) | Iceberg, Nessie, Gravitino/Ranger, Raw Zone namespaces, ingestion patterns |
| **WS2: EDLH** | 1.5 | Gautam (Lakehouse Tech Lead) | Enterprise Bronze/Silver, Customer + Counterparty conformed dimensions |
| **WS3: Capital Markets Hub** | 2.0 | Capital Markets data engineering + platform support | Hub Bronze/Silver/Gold, Counterparty Risk Score product, semantic model, Fabric Data Agent |
| **WS4: RBC Data Gateway** | 2.0 | Platform + RBC Assist team | FastAPI on OCP, all 7 responsibilities at MVP level, single-agent routing |
| **WS5: Registry & Governance** | 1.5 | Platform team + Saurabh (PM) | Registry MVP on top of MCS, Purview integration, contract format, lifecycle workflows |
| **Cross-cutting** | 1.0 | George + Saurabh | Architecture review, ADR maintenance, dependency management, demo orchestration |

## PI planning structure — six 2-week iterations (with one buffer iteration)

Iteration cadence: 2 weeks per iteration, 6 iterations + 1 stabilization iteration = 13 weeks. PI demo at end of iteration 6, stabilization iteration before next PI.

### Iteration 1 (Weeks 1–2): Foundations and skeletons

**Theme: stand up the rails so everything else can build in parallel**

- WS1: Iceberg cluster operational; Nessie catalog initialized; Raw Zone bucket structure defined; Capital Markets and Enterprise namespaces created (empty); first Ranger policies authored.
- WS2: EDLH workspace structure defined; Bronze schema for Customer and Counterparty drafted; Airflow DAG skeleton in place.
- WS3: Capital Markets workspace defined; Snowflake account access confirmed; Hub Bronze schema drafted; trading platform source identified and access requested.
- WS4: FastAPI skeleton on OCP; Entra ID auth flow working; first stub endpoint returning a hardcoded response; deployment pipeline operational.
- WS5: Registry data model designed; contract YAML schema defined; Git repo structure for product contracts established.

**Iteration 1 demo:** All five workstreams have a "hello world" running. Nothing useful end-to-end yet, but every plane has a heartbeat.

### Iteration 2 (Weeks 3–4): First data flowing

**Theme: data lands in the Raw Zone and reaches Bronze**

- WS1: Customer master CDC pipeline live, landing in Enterprise namespace; trading platform feed live, landing in Capital Markets namespace; Purview labels applied at landing.
- WS2: Enterprise Bronze populated from Customer master; Bronze→Silver transformation skeleton; first Soda data quality checks running.
- WS3: Capital Markets Hub Bronze populated from Raw Zone trading platform feed; Hub Bronze→Silver transformation skeleton.
- WS4: Gateway Auth + Policy layers complete; first real call to a stub Fabric Data Agent succeeds; audit logging to SIEM working.
- WS5: Registry MVP exposes a contract upload + browse UI; contract validation against schema operational.

**Iteration 2 demo:** A trader's data lands in Iceberg via the platform-mediated path. A test query through the gateway returns "I cannot answer that yet" with full audit. Customer master visible in Enterprise Bronze.

### Iteration 3 (Weeks 5–6): Conformance and silver

**Theme: data becomes meaningful**

- WS1: Self-serve ingestion pattern documented and validated with one Capital Markets pipeline (still operated by platform team, but using the templates Capital Markets will eventually use).
- WS2: Customer dimension conformed in Enterprise Silver; Counterparty dimension conformed in Enterprise Silver; both exposed as governed Iceberg tables consumable by hubs; lineage capture validated.
- WS3: Capital Markets Hub Silver populated; joined to Counterparty conformed dimension from EDLH; first Hub Silver tables accessible via Trino federation.
- WS4: Gateway Orchestrator MVP — single-agent routing logic; Adapters layer with Fabric Data Agent adapter working against a real (empty) Fabric Data Agent.
- WS5: First product contract authored (Counterparty Risk Score); contract review and approval workflow exercised; product registered as "proposed" in registry.

**Iteration 3 demo:** Customer and Counterparty conformed dimensions queryable. Capital Markets analyst can run a Trino query joining Hub Silver to EDLH Counterparty. Registry shows the proposed Counterparty Risk Score product.

### Iteration 4 (Weeks 7–8): Gold, semantic model, agent

**Theme: the LOB hub becomes consumable**

- WS3: Capital Markets Hub Gold populated; Counterparty Risk Score computed and persisted; Fabric semantic model published with 5+ measures and 3+ dimensions on Hub Gold; Power BI report against the semantic model in production for Capital Markets analysts.
- WS3: Fabric Data Agent created in Capital Markets workspace; serving compute confirmed running on Enterprise capacity; agent answers basic questions correctly when called directly from Power BI Copilot.
- WS4: Gateway routes RBC Assist calls to the Capital Markets Fabric Data Agent; full request/response cycle working with proper identity propagation; PII scrubbing layer operational.
- WS5: Product certified; published to registry; contract finalized; first subscriber (Risk function) granted access via Ranger.

**Iteration 4 demo:** A Capital Markets analyst opens Power BI and uses Copilot to ask questions of the new semantic model. A test RBC Assist query via the gateway returns a real answer. The Counterparty Risk Score is visible in the registry as a certified product.

### Iteration 5 (Weeks 9–10): End-to-end integration and governance

**Theme: the slice works as one**

- WS4: Gateway prompt-injection defense operational; rate limiting and cost ceilings configured; observability dashboards live.
- WS3: Capital Markets Hub Data Quality SLAs measured and visible in registry; semantic model performance tuning to meet latency targets.
- WS2: EDLH lineage visible end-to-end in Purview from Raw Zone source through Silver dimension to LOB hub consumption.
- WS5: Subscription workflow tested with Risk function consuming Counterparty Risk Score; access grants flow to Ranger automatically.
- All workstreams: integration testing of the full path.

**Iteration 5 demo:** The full target query — *"What is RBC's exposure to counterparty X in Capital Markets, and what is the counterparty risk score?"* — works through RBC Assist via the gateway. Lineage and audit visible. SLAs reporting.

### Iteration 6 (Weeks 11–12): Hardening, performance, demo prep

**Theme: production-readiness for the demo, lessons captured**

- All workstreams: bug burndown, performance optimization to hit latency targets, security review completion, runbook authoring, on-call rotation defined.
- Documentation pass: every component has a README, every API has an OpenAPI spec, every pipeline has a runbook.
- Demo rehearsals: the full end-to-end demo run three times with different test questions; failure modes documented and rehearsed.
- Architecture review: lessons learned captured; ADR amendments drafted where needed.

**Iteration 6 demo:** Final PI demo. Live RBC Assist query through the full architecture. Architecture review presentation to Vinh, Rex, and broader Lumina governance forum.

### Stabilization Iteration (Week 13): Hand-off and PI close

- Production-ready handoff to operations.
- Cost analysis from the PI for forward planning.
- PI retrospective.
- Next-PI scope kickoff (likely: second LOB hub, FSDM CDC, gateway multi-agent orchestration).

## Success criteria for PI close

The PI passes if all of the following are demonstrably true at the PI demo:

| Criterion | Evidence |
| --- | --- |
| End-to-end query works | Live demo of RBC Assist answering the target question through gateway → agent → semantic model → data |
| Latency acceptable | P50 ≤ 5 seconds, P95 ≤ 12 seconds for the target query (looser than steady-state targets — this is MVP) |
| Governance enforced | Test with restricted user shows correct denial; Purview lineage visible end-to-end |
| Audit complete | Every gateway call logged; full audit trail visible in SIEM for the demo session |
| Product registered and consumable | Counterparty Risk Score visible in registry; Risk function has subscribed; access is enforced |
| Power BI consumption working | Capital Markets analytics team has used the new semantic model for at least 1 week of daily work |
| Architecture validated | All seven planes operational; ADR-014 pilot results positive or risks documented for next PI |

The PI fails if any of the following:

- The gateway does not work as a trust boundary (auth fails, audit incomplete, identity propagation broken).
- Conformed dimensions in EDLH cannot be reliably joined from the LOB hub.
- The semantic model returns inconsistent answers between Power BI and Fabric Data Agent.
- Latency is materially worse than 2× the target thresholds (architectural redesign needed).

## Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Fabric Data Agent + DirectQuery Snowflake performance unacceptable | Medium | High | Validate in iteration 2; have Fabric Mirroring as a fast-follow if needed |
| OCP / FastAPI auth integration with Entra ID slower than expected | Medium | Medium | Iteration 1 spike on auth specifically; involve RBC Assist team early |
| Capital Markets data engineering capacity insufficient | Medium | High | Confirm Capital Markets buy-in and resourcing before PI start; have platform team backfill capacity available |
| MCS extension to support data product registry takes longer than expected | Medium | Medium | Build registry as a separate service that *consumes* MCS rather than extending MCS; loose coupling |
| Snowflake Iceberg integration quirks (write/read patterns, catalog) | Low | Medium | Sanjeev's team has experience; have Snowflake account team on call |
| Purview lineage gaps at the Fabric–Trino boundary | Medium | Low | Document gaps; do not block PI on this; raise with Microsoft |
| Scope creep — pressure to add second hub mid-PI | High | High | This document is the contract; explicit "not in MVP" section above; George holds the line |
| Capital Markets analyst adoption insufficient to validate Power BI workflow | Low | Medium | Identify named pilot user(s) before iteration 4; weekly check-ins during iterations 4-5 |

## Dependencies

| Dependency | Owner | Needed by |
| --- | --- | --- |
| Snowflake account provisioned and accessible | Cloud platform team | Iteration 1 |
| OCP namespace and CI/CD for the gateway | OCP platform team | Iteration 1 |
| Fabric capacity F128 enterprise + access for the Capital Markets workspace | Microsoft licensing + procurement | Iteration 1 |
| Trading platform CDC feed approved by Capital Markets ops | Capital Markets | Iteration 2 |
| Customer master CDC approved by Enterprise Data Office | Enterprise Data | Iteration 2 |
| Risk function as the first product subscriber | Risk leadership | Iteration 4 |
| Capital Markets named pilot analyst(s) | Capital Markets analytics | Iteration 4 |
| RBC Assist team integration capacity | RBC Assist team | Iterations 4-5 |

## Open questions to resolve before PI start

1. **Capital Markets confirms participation as the MVP LOB.** If Capital Markets cannot commit data engineering capacity for a 13-week PI, the MVP shifts to a different LOB, likely P&CB. This decision needs to be made before PI planning.
2. **Counterparty Risk Score is the right MVP product.** Confirm with Capital Markets analytics that this is genuinely useful and not duplicative of an existing system. Alternative: trade reconciliation or position snapshot.
3. **OCP capacity for the gateway.** Confirm sufficient OCP capacity is provisioned for the gateway with HA from day one.
4. **Fabric Mirroring of Snowflake GA in Canada Central.** Microsoft confirmation needed; if not GA, MVP uses DirectQuery only and Mirroring is post-MVP.
5. **Risk function buy-in as first consumer.** Confirm Risk function is willing and resourced to be the first subscriber to the published product.

## Communication plan

- **Weekly:** Workstream leads sync with George; written status update from each lead.
- **Bi-weekly:** PI demo at end of each iteration. Vinh attends; Rex briefed.
- **Monthly:** Executive update to Lumina governance forum.
- **PI demo:** End of iteration 6. Vinh, Rex, EDW/EDL/Lakehouse domain leads, Capital Markets analytics, Risk function, RBC Assist team.
- **PI retrospective:** End of stabilization iteration. Workstream leads + George. Output: lessons learned + next-PI scope draft.

## Why this is the right MVP

The temptation in PI planning is to take an architecture this ambitious and either over-scope (a hub per LOB in 13 weeks — undeliverable) or under-scope (just stand up the lakehouse infrastructure — does not validate the architecture). This MVP threads the needle: it is genuinely thin in scope (one hub, one product, one consumer query, one PI) but architecturally complete (every plane exercised). At the end of 13 weeks, RBC has either validated the architecture or learned exactly where it does not work, with concrete evidence either way. That is the right outcome from an MVP.
