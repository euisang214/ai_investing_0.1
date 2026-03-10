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
| 2 | Vertical Slice And Delta Flow | Run one company through ingestion, gatekeepers + demand panels, memo updates, IC synthesis, and rerun delta generation | COV-03, ING-03, MEM-03, ORCH-02, ORCH-03, MEMO-01, MEMO-03, TOOLS-02, TEST-01, TEST-02 | 5 |
| 3 | Remaining Panel Scaffolds | Add configurable placeholder prompts, schemas, and registry entries for the remaining top-level panels | V2-01 | 3 |
| 4 | Monitoring And Connectors | Expand monitoring logic, add reusable services, and include richer sample public/private adapters | V2-02, V2-04 | 3 |
| 5 | Scheduling And Notifications | Harden n8n workflows, configurable cadence policies, and run notifications | V2-03, V2-05 | 3 |

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
**Status:** Next active phase.

**Requirements:** `COV-03`, `ING-03`, `MEM-03`, `ORCH-02`, `ORCH-03`, `MEMO-01`, `MEMO-03`, `TOOLS-02`, `TEST-01`, `TEST-02`

**Success criteria:**
1. The `CompanyRefreshGraph` executes `gatekeepers` and `demand_revenue_quality` using reusable subgraphs, not one-off orchestration code.
2. Panel verdicts trigger section-level memo updates before final IC reconciliation.
3. A rerun against prior active memory produces `what_changed_since_last_run` and a `MonitoringDelta`.
4. Sample data generates deterministic memo and delta artifacts through the fake provider.
5. Automated tests cover the vertical slice, registry behavior, memo semantics, reruns, and tool bundle enforcement.

### Phase 3: Remaining Panel Scaffolds

**Goal:** Prepare the rest of the panel surface area for future implementation without destabilizing the core runtime.

**Requirements:** `V2-01`

**Success criteria:**
1. All top-level panels exist in config with placeholder prompts and factor mappings.
2. Panels can be enabled later by config changes rather than runtime rewrites.
3. Documentation explains the extension path for new factors and agents.

### Phase 4: Monitoring And Connectors

**Goal:** Expand reusable services and connector depth once the core slice is stable.

**Requirements:** `V2-02`, `V2-04`

**Success criteria:**
1. Dependency concentration, base-rate analog, contradiction, and thesis-drift services are broadened.
2. Sample public and private adapters cover more evidence types.
3. Monitoring outputs become richer without changing memo contracts.

### Phase 5: Scheduling And Notifications

**Goal:** Move from local repeatability to reliable recurring operations.

**Requirements:** `V2-03`, `V2-05`

**Success criteria:**
1. Cadence policies expand beyond weekly.
2. n8n workflow examples cover weekly refreshes, ingestion webhooks, and notifications.
3. Background execution and notification boundaries are documented cleanly.

---
*Last updated: 2026-03-10 after Phase 01 completion*
