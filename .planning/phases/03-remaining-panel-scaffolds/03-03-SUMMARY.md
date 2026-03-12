---
phase: 03-remaining-panel-scaffolds
plan: 03
subsystem: testing
tags: [pytest, cli, api, services, scaffolds, run-policies]
requires:
  - phase: 02-vertical-slice-and-delta-flow
    provides: gatekeeper-first runtime entrypoints and persisted run lifecycle contracts
  - phase: 03-remaining-panel-scaffolds
    provides: config-visible scaffold panels and future-facing run policies from the expanded registry surface
provides:
  - service-level regression coverage for rejecting scaffold-only panels before run creation
  - CLI and API contract coverage for the same scaffold rejection semantics
  - proof that full_surface stays loadable in config while execution still fails fast
affects: [phase-03, runtime-boundary, api, cli, test-suite]
tech-stack:
  added: []
  patterns:
    - execution-boundary regression tests for scaffold-only panels
    - no-partial-run rejection assertions across service, CLI, and API entrypoints
key-files:
  created:
    - .planning/phases/03-remaining-panel-scaffolds/03-03-SUMMARY.md
  modified:
    - tests/test_analysis_flow.py
    - tests/test_run_lifecycle.py
    - tests/test_cli.py
    - tests/test_api.py
    - .planning/STATE.md
    - .planning/ROADMAP.md
key-decisions:
  - "Keep the runtime boundary in services.py unchanged unless new regressions prove a real defect; this plan only needed coverage."
  - "Treat full_surface as config-visible but execution-blocked, and assert that rejection contract uniformly across service, CLI, and API entrypoints."
patterns-established:
  - "Future-facing policies may remain first-class config entries as long as execution rejects unimplemented panels before persisting a run."
  - "Operator-facing interfaces should surface the same not-implemented error text the service layer raises for scaffold-only panels."
requirements-completed: []
duration: 13min
completed: 2026-03-12
---

# Phase 03 Plan 03: Scaffold Execution Boundary Summary

**Service, CLI, and API regression coverage now proves that scaffold-only panels and the `full_surface` policy remain visible in config while execution still fails fast before any partial run starts**

## Performance

- **Duration:** 13 min
- **Started:** 2026-03-12T11:03:30Z
- **Completed:** 2026-03-12T11:16:23Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added service-level regressions for `full_surface`, explicit scaffold panel selection, and adjacent run entrypoints so unimplemented panels are rejected before run creation.
- Extended the CLI and API suites to assert the same user-facing `not implemented` contract for scaffold-only panels and future-facing policies.
- Confirmed the existing `AnalysisService` rejection path was already correct, so runtime behavior stayed unchanged and the guardrail remains generic.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add service-level regressions and stabilize the rejection path only if they expose a real gap** - `9b0c64c` (test)
2. **Task 2: Extend CLI and API tests to expose the same scaffold boundary** - `1917aa2` (test)

**Verification cleanup:** `124be64` (style)

**Plan metadata:** captured in the final docs/state commit for this plan

## Files Created/Modified

- `tests/test_analysis_flow.py` - adds `full_surface` and explicit scaffold-selection regressions that assert no run is created when execution is rejected
- `tests/test_run_lifecycle.py` - covers `refresh_company` and `run_panel` rejection for scaffold-only panels at the service boundary
- `tests/test_cli.py` - verifies CLI operators see scaffold-only panel and `full_surface` failures without partial runs being persisted
- `tests/test_api.py` - verifies the API returns stable `invalid_request` envelopes for the same scaffold-only rejection paths
- `.planning/phases/03-remaining-panel-scaffolds/03-03-SUMMARY.md` - records the plan outcome, decisions, and verification results
- `.planning/STATE.md` - advances execution tracking after Plan 03-03 completion while keeping V2-01 open
- `.planning/ROADMAP.md` - refreshes Phase 3 plan-progress after this execution-boundary slice landed

## Decisions Made

- Left `src/ai_investing/application/services.py` untouched because the new regressions confirmed the existing `_resolve_panel_ids()` guardrail already rejected scaffold-only panels correctly.
- Locked the operator contract to the existing service-layer error text instead of introducing interface-specific filtering or translation.
- Left parent requirement `V2-01` open because this plan delivers prerequisite slice `V2-01C`, not full remaining-panel productionization.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Wrapped a new API error assertion to satisfy the repo lint gate**
- **Found during:** Overall verification
- **Issue:** A new `full_surface` API assertion exceeded the repository line-length limit and blocked `ruff check src tests`
- **Fix:** Wrapped the expected error string without changing the asserted response payload
- **Files modified:** `tests/test_api.py`
- **Verification:** `docker compose run --rm api pytest -q tests/test_analysis_flow.py tests/test_run_lifecycle.py tests/test_cli.py tests/test_api.py`; `docker compose run --rm api ruff check src tests`
- **Committed in:** `124be64` (style)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Verification-only cleanup. No runtime scope change and no relaxation of the scaffold boundary.

## Issues Encountered

- Final lint verification failed once on a long assertion line in `tests/test_api.py`; wrapping the string resolved it immediately.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 3 now has explicit regression coverage that the future-facing scaffold surface stays non-runnable across all public entrypoints. The remaining Phase 3 plans can keep expanding prompt, factor, and documentation coverage without weakening the runtime safety boundary.

## Self-Check: PASSED
