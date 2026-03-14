# Roadmap: AI Investing

**Created:** 2026-03-08
**Granularity:** standard
**Execution:** parallel where dependencies allow

## Overview

This roadmap emphasizes one strong vertical slice over broad but shallow coverage. Phase 1 establishes configuration, schemas, persistence, interfaces, and extensible scaffolding. Phase 2 proves the architecture with a working company refresh for `gatekeepers` and `demand_revenue_quality`, including living memo updates and rerun deltas.

## Phases

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Foundation And Contracts | Establish the repo, registries, schemas, persistence contracts, provider/tool abstractions, and interface skeletons | CONF-01, CONF-02, CONF-03, COV-01, COV-02, ING-01, ING-02, MEM-01, MEM-02, MEMO-02, ORCH-01, TOOLS-01, PROV-01, API-01, API-02, OPS-01 | 5 |
| 2 | Vertical Slice And Delta Flow | Completed on 2026-03-11 with repaired first-completion baseline semantics, deterministic artifacts, and full regression coverage | COV-03, ING-03, MEM-03, ORCH-02, ORCH-03, MEMO-01, MEMO-03, TOOLS-02, TEST-01, TEST-02 | 5 |
| 3 | Remaining Panel Scaffolds | Add configurable placeholder prompts, schemas, and registry entries for the remaining top-level panels | V2-01 | 3 |
| 4 | Monitoring And Connectors | Completed on 2026-03-13 with connector-runtime, representative adapters, richer monitoring deltas, and read-only portfolio monitoring surfaces | V2-02, V2-04 | 3 |
| 5 | Scheduling And Notifications | Harden n8n workflows, configurable cadence policies, and run notifications | V2-03, V2-05 | 3 |
| 6 | Productionize Remaining Panels | Completed on 2026-03-14 with all top-level panels productionized, truthful rollout docs, deterministic `overlay_gap` artifacts, and a final parent-requirement verification chain for `V2-01` | V2-01 | 3 |
| 7 | Close Phase 04 Verification Gap | Reconcile Phase 04 verification coverage and parent requirement evidence so monitoring and connector work is archive-ready | V2-02, V2-04 | 3 |
| 8 | Close Phase 05 Operational Gaps | Finish the worker-state and notification-failure boundaries needed for truthful large-scale refresh operations | V2-05 | 3 |

## Phase Details

### Phase 1: Foundation And Contracts

**Goal:** Make the project structurally sound before model logic scales.
**Status:** Completed on 2026-03-10.

**Requirements:** `CONF-01`, `CONF-02`, `CONF-03`, `COV-01`, `COV-02`, `ING-01`, `ING-02`, `MEM-01`, `MEM-02`, `MEMO-02`, `ORCH-01`, `TOOLS-01`, `PROV-01`, `API-01`, `API-02`, `OPS-01`

**Success criteria:**
1. Config registries for panels, factors, agents, memo sections, tools, bundles, policies, and connectors load and validate successfully.
2. Typed domain schemas and persistence tables exist for evidence, claims, verdicts, memos, deltas, coverage, and tool logs.
3. CLI and FastAPI skeletons expose the required commands and endpoints.
4. Fake, OpenAI, and Anthropic provider abstractions exist behind a shared model interface.
5. Docker Compose and runbook documentation allow another engineer to boot the stack locally.

### Phase 2: Vertical Slice And Delta Flow

**Goal:** Prove the architecture by analyzing one company end-to-end and producing memo history plus rerun deltas.
**Status:** Completed on 2026-03-11 with repaired first-completion baseline semantics.

**Requirements:** `COV-03`, `ING-03`, `MEM-03`, `ORCH-02`, `ORCH-03`, `MEMO-01`, `MEMO-03`, `TOOLS-02`, `TEST-01`, `TEST-02`

**Plan progress:** `5 / 5` completed (`02-01`, `02-02`, `02-03`, `02-04`, and `02-05` done)

**Success criteria:**
1. The `CompanyRefreshGraph` executes `gatekeepers` and `demand_revenue_quality` using reusable subgraphs, not one-off orchestration code.
2. Panel verdicts trigger section-level memo updates before final IC reconciliation.
3. A rerun against prior active memory produces `what_changed_since_last_run` and a `MonitoringDelta`.
4. Sample data generates deterministic memo and delta artifacts through the fake provider.
5. Automated tests cover the vertical slice, registry behavior, memo semantics, reruns, and tool bundle enforcement.

### Phase 3: Remaining Panel Scaffolds

**Goal:** Prepare the rest of the panel surface area for future implementation without destabilizing the core runtime.
**Status:** Completed on 2026-03-12 with scaffold registry coverage, prompt and ontology contracts, execution-boundary regressions, and extension-path documentation. Parent requirement `V2-01` remains open until the remaining panels are actually productionized.

**Requirements:** `V2-01`

**Plan progress:** `4 / 4` completed (`03-01`, `03-02`, `03-03`, and `03-04` done)

**Success criteria:**
1. All top-level panels exist in config with placeholder prompts and factor mappings.
2. Panels can be enabled later by config changes rather than runtime rewrites.
3. Documentation explains the extension path for new factors and agents.

### Phase 4: Monitoring And Connectors

**Goal:** Expand reusable services and connector depth once the core slice is stable.
**Status:** Completed on 2026-03-13 at the implementation slice level. Plans `04-01`, `04-02`, `04-03`, and `04-04` delivered the registry-backed connector runtime seam, representative adapter slice, richer monitoring services, and read-only portfolio monitoring history plus summary surfaces. The 2026-03-13 milestone audit found the parent verification chain incomplete, so final requirement closure for `V2-02` and `V2-04` now moves to Phase 7.

**Requirements:** `V2-02`, `V2-04`

**Plan progress:** `4 / 4` completed (`04-01`, `04-02`, `04-03`, and `04-04` done)

**Success criteria:**
1. Dependency concentration, base-rate analog, contradiction, and thesis-drift services are broadened.
2. Sample public and private adapters cover more evidence types.
3. Monitoring outputs become richer and operators can inspect monitoring history plus portfolio summaries without changing memo contracts.

### Phase 5: Scheduling And Notifications

**Goal:** Move from local repeatability to reliable recurring operations.
**Status:** Completed on 2026-03-13 at the primary slice level. Plans `05-01`, `05-02`, and `05-03` delivered config-driven cadence policies, queue-backed worker execution, review handling, notification delivery surfaces, and truthful external-automation docs plus checked examples. The 2026-03-13 milestone audit found two supported-boundary gaps under `V2-05`, so final closure of that requirement moves to Phase 8 while `V2-03` remains complete.

**Requirements:** `V2-03`, `V2-05`

**Plan progress:** `3 / 3` completed (`05-01`, `05-02`, and `05-03` done)

**Success criteria:**
1. Cadence policies expand beyond weekly.
2. n8n workflow examples cover weekly refreshes, ingestion webhooks, and notifications.
3. Background execution and notification boundaries are documented cleanly.

### Phase 6: Productionize Remaining Panels

**Goal:** Turn the remaining scaffold-only top-level panels into executable, verified production flows without breaking the config-driven runtime.
**Status:** Completed on 2026-03-14. Plans `06-01` through `06-06` shipped rollout support and skip surfaces, truthful partial-run memo wording, runnable Wave 1 internal company-quality panels, runnable Wave 2 external-context company-quality panels, a runnable Wave 3 expectations rollout, a runnable final overlay wave, bounded portfolio-context support, overlay-aware operator surfaces, truthful closeout docs, deterministic checked examples including `overlay_gap`, and the final parent-requirement verification artifact for `V2-01`.

**Requirements:** `V2-01`

**Gap Closure:** Closes the audit's partial `V2-01` requirement gap carried forward from Phase 03.

**Plan progress:** `6 / 6` completed (`06-01`, `06-02`, `06-03`, `06-04`, `06-05`, and `06-06` done)

**Success criteria:**
1. The remaining top-level panels execute through supported graph paths instead of stopping at placeholder scaffolds.
2. Each newly productionized panel keeps prompts, schemas, factor mappings, and tool bundles config-driven and editable.
3. Phase verification marks parent requirement `V2-01` complete with regression coverage for the added production panels.

### Phase 7: Close Phase 04 Verification Gap

**Goal:** Finish the missing verification and requirement-evidence chain for the monitoring and connector work already shipped in Phase 04.
**Status:** Planned on 2026-03-13 from the milestone audit.

**Requirements:** `V2-02`, `V2-04`

**Gap Closure:** Closes the audit's `V2-02` unsatisfied gap, `V2-04` partial gap, and the broken "Phase 4 verification chain" flow.

**Success criteria:**
1. Phase 04 has a complete verification artifact that covers the parent milestone requirements, not only individual plan slices.
2. Requirement traceability and summary evidence consistently show the completed parent outcomes for `V2-02` and `V2-04`.
3. The milestone audit can verify the Phase 04 chain without relying on implied completion from summaries alone.

### Phase 8: Close Phase 05 Operational Gaps

**Goal:** Complete the supported execution and notification boundaries needed for truthful queue state and failure handling in recurring refresh operations.
**Status:** Planned on 2026-03-13 from the milestone audit.

**Requirements:** `V2-05`

**Gap Closure:** Closes the audit's two `V2-05` integration gaps in worker running-state truthfulness and external notification failure reporting.

**Success criteria:**
1. Worker execution persists a truthful `running` transition through the supported repository boundary so queue read surfaces reflect active work.
2. External API and CLI flows can report notification delivery failure using the supported boundary, not only internal helpers.
3. Verification covers the full `due coverage -> queue enqueue -> worker execution -> review queue/notifications` flow with the repaired operational boundaries.

---
*Last updated: 2026-03-14 after Phase 06 Plan 06 execution*
