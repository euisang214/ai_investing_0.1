---
phase: 06-productionize-remaining-panels
plan: 02
subsystem: api
tags: [langgraph, panels, memo, pytest, yaml]
requires:
  - phase: 06-01
    provides: rollout waves, typed panel support surfaces, and partial-run memo wording for shared execution
provides:
  - production Wave 1 config and prompt suites for the internal company-quality panel family
  - truthful public and private evidence coverage for Wave 1 panels under one shared runtime contract
  - API and CLI support visibility for Wave 1 memo and panel outcomes
affects: [phase-06, memo-updates, operator-interfaces, fixture-regressions]
tech-stack:
  added: []
  patterns: [config-driven panel productionization, explicit panel support persistence, truthful weak-confidence operator surfacing]
key-files:
  created:
    - prompts/panels/supply_product_operations/panel_lead.md
    - prompts/panels/management_governance/panel_lead.md
    - prompts/panels/financial_quality/panel_lead.md
    - examples/beta_private/beta_kpi_packet.md
  modified:
    - config/panels.yaml
    - config/agents.yaml
    - config/tool_bundles.yaml
    - examples/acme_public/manifest.json
    - examples/beta_private/manifest.json
    - src/ai_investing/application/services.py
    - src/ai_investing/graphs/subgraphs.py
    - src/ai_investing/api/main.py
    - src/ai_investing/cli.py
    - tests/test_analysis_flow.py
    - tests/test_api.py
    - tests/test_cli.py
    - tests/test_generated_examples.py
key-decisions:
  - "Wave 1 productionizes only the internal company-quality family and keeps overlay, expectations, security, and portfolio-fit work out of these panels."
  - "Panel support posture is persisted and rehydrated through services, API, and CLI so thin-evidence runs stay explicit instead of reading like normal-confidence coverage."
  - "Parent requirement V2-01 remains open after this slice because later Phase 6 plans still need to productionize the remaining panel families."
patterns-established:
  - "Implemented panels become runnable by config, prompt assets, and fixture truthfulness rather than new panel-specific orchestration branches."
  - "Operator surfaces reconstruct support metadata from persisted run artifacts so memo and panel views stay aligned."
requirements-completed: [V2-01]
duration: 2h 29m
completed: 2026-03-13
---

# Phase 06 Plan 02: Productionize Remaining Panels Summary

**Wave 1 internal company-quality panels now run end-to-end with real agent trees, truthful support signals, and section-scoped memo updates across public and private fixtures**

## Performance

- **Duration:** 2h 29m
- **Started:** 2026-03-13T21:15:20Z
- **Completed:** 2026-03-13T23:44:15Z
- **Tasks:** 3
- **Files modified:** 38

## Accomplishments

- Replaced scaffold-only Wave 1 company-quality panels with implemented config, factor readiness, tool bundles, and full prompt suites for supply, management, and financial quality.
- Expanded checked public and private evidence fixtures so the same panel ids run truthfully under one policy, including explicit weak-confidence behavior when private support is still thin.
- Extended persisted operator surfaces so API and CLI outputs expose Wave 1 support posture and scoped memo updates without special-case runtime branches.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace Wave 1 placeholders with real config, factor readiness, and prompt suites** - `c01fada` (feat)
2. **Task 2: Expand public and private fixture coverage and lock weak-confidence truthfulness** - `3facc09` (feat)
3. **Task 3: Extend interface regressions for Wave 1 rollout policy and memo outcomes** - `cc82e2c` (fix)
4. **Verification cleanup:** `6ad5238` (fix)

## Files Created/Modified

- `config/panels.yaml` - Marks the three Wave 1 panels implemented and aligns evidence thresholds with truthful rollout coverage.
- `config/agents.yaml` - Replaces placeholder leads with advocate, skeptic, durability, judge, and panel lead trees for each Wave 1 panel.
- `config/tool_bundles.yaml` - Adds least-privilege research bundles for supply, management, and financial quality specialists.
- `examples/acme_public/manifest.json` - Expands public-company evidence tags for the new panel and factor coverage.
- `examples/beta_private/manifest.json` - Expands private-company evidence tags for the same panels and factors.
- `examples/beta_private/beta_kpi_packet.md` - Adds a third private-company source to support truthful Wave 1 coverage.
- `src/ai_investing/application/services.py` - Persists and returns panel support posture in graph and stored run results.
- `src/ai_investing/graphs/subgraphs.py` - Preserves support payloads and resets per-panel graph state correctly between skipped and executed panels.
- `src/ai_investing/api/main.py` - Rehydrates panel support metadata in API run views.
- `src/ai_investing/cli.py` - Rehydrates panel support metadata in CLI run views.
- `tests/test_analysis_flow.py` - Locks truthful Wave 1 execution, memo updates, and weak-confidence behavior.
- `tests/test_api.py` - Verifies Wave 1 policy visibility and support-aware API responses.
- `tests/test_cli.py` - Verifies Wave 1 policy visibility and support-aware CLI responses.
- `tests/test_generated_examples.py` - Ensures checked example manifests cover the new Wave 1 panel family.

## Decisions Made

- Kept Wave 1 strictly scoped to internal company-quality panels so later Phase 6 plans can add overlays and expectations without entangling memo ownership now.
- Preserved support assessments as first-class persisted data instead of recomputing or flattening them into prose-only outputs.
- Left parent requirement `V2-01` open even though this plan references that requirement id, because `06-02` delivers slice `V2-01B` rather than the entire remaining-panel production scope.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reset stale skip state between panels in the shared graph**
- **Found during:** Task 2 (Expand public and private fixture coverage and lock weak-confidence truthfulness)
- **Issue:** A skipped panel left stale graph state behind, which caused later runnable Wave 1 panels to be treated as skipped and triggered memo update failures.
- **Fix:** Explicitly rewrote specialist-node state updates so each panel stores fresh `verdict` and `skip` values before downstream memo updates run.
- **Files modified:** `src/ai_investing/graphs/subgraphs.py`
- **Verification:** `docker compose run --rm api pytest -q tests/test_analysis_flow.py tests/test_run_lifecycle.py tests/test_generated_examples.py -k "supply or management or financial"`
- **Committed in:** `3facc09`

**2. [Rule 3 - Blocking] Reconciled stale regressions after the Wave 1 panels became fully implemented**
- **Found during:** Final verification
- **Issue:** Existing tests and checked example artifacts still assumed scaffold or lower-coverage behavior, which broke the full suite once the panels were truly runnable.
- **Fix:** Updated stale assertions, adjusted the financial panel's minimum evidence threshold to truthful rollout depth, updated private-ingestion expectations for the added KPI packet, and regenerated checked ACME result artifacts.
- **Files modified:** `config/panels.yaml`, `tests/test_analysis_flow.py`, `tests/test_ingestion.py`, `examples/generated/ACME/initial/result.json`, `examples/generated/ACME/continued/result.json`, `examples/generated/ACME/rerun/result.json`
- **Verification:** `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests`
- **Committed in:** `6ad5238`

---

**Total deviations:** 2 auto-fixed (1 Rule 1, 1 Rule 3)
**Impact on plan:** Both deviations were required to keep the shared runtime truthful and the checked regression suite aligned with the newly productionized panel family.

## Issues Encountered

- Shared-graph state contamination surfaced only once Wave 1 panels moved from scaffold to runnable status; fixing it in the shared node update path preserved the config-driven architecture instead of adding panel-specific guards.
- Persisted run readers in API and CLI needed explicit support reconstruction from stored metadata so operator views matched direct in-process results.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 can continue productionizing later panel families on the same support-aware runtime and policy-based rollout pattern.
- Parent requirement `V2-01` should remain open until the remaining scaffolded panel families are implemented and verified.

---
*Phase: 06-productionize-remaining-panels*
*Completed: 2026-03-13*

## Self-Check: PASSED

- Verified `.planning/phases/06-productionize-remaining-panels/06-02-SUMMARY.md` exists.
- Verified commits `c01fada`, `3facc09`, `cc82e2c`, and `6ad5238` exist via `git rev-parse --verify <hash>^{commit}`.
- Used direct commit verification because the repository has an invalid `refs/heads/master` ref, which makes `git log --all` unreliable in this environment.
