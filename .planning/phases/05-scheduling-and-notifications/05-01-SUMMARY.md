---
phase: 05-scheduling-and-notifications
plan: 01
subsystem: scheduling
tags: [cadence-policies, timezone, cli, fastapi, pytest]
requires:
  - phase: 04-monitoring-and-connectors
    provides: coverage persistence, monitoring deltas, additive operator surfaces
provides:
  - config-driven cadence policy registry with workspace timezone validation
  - policy-driven coverage schedule computation and additive schedule fields
  - additive CLI and API schedule inspection plus update controls
affects: [phase-05-workers, notifications, n8n, coverage-operations]
tech-stack:
  added: [zoneinfo]
  patterns: [config-driven cadence registry, shared schedule computation, additive compatibility fields]
key-files:
  created:
    - config/cadence_policies.yaml
    - src/ai_investing/application/scheduling.py
  modified:
    - src/ai_investing/config/models.py
    - src/ai_investing/config/loader.py
    - src/ai_investing/domain/models.py
    - src/ai_investing/application/services.py
    - src/ai_investing/api/main.py
    - src/ai_investing/cli.py
    - tests/test_config_and_registry.py
    - tests/test_analysis_flow.py
    - tests/test_run_lifecycle.py
    - tests/test_api.py
    - tests/test_cli.py
key-decisions:
  - "Keep legacy `cadence` as a scheduled-vs-manual compatibility field while `schedule_policy_id` owns real cadence semantics."
  - "Drive first-run and next-run math through one workspace timezone plus per-coverage preferred run time, with legacy weekly entries staying immediately due unless operators choose a richer policy."
  - "Advance `next_run_at` only for completed or provisional terminal runs, and clear it for schedule-disabled/manual one-offs so due coverage does not repeat forever."
patterns-established:
  - "Cadence policies live in YAML registries and are validated before runtime, including run-policy references."
  - "Coverage schedule updates stay additive through API and CLI surfaces instead of replacing legacy commands."
requirements-completed: [V2-03]
duration: 12min
completed: 2026-03-13
---

# Phase 5 Plan 01: Cadence Policy Scheduling Summary

**Config-driven cadence policies with workspace-timezone scheduling, additive coverage schedule fields, and backward-compatible API or CLI controls**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-13T15:00:21Z
- **Completed:** 2026-03-13T15:12:35Z
- **Tasks:** 3
- **Files modified:** 16

## Accomplishments

- Added a dedicated cadence-policy registry with workspace timezone metadata and pre-runtime validation for policy shape plus run-policy references.
- Replaced hardcoded weekly schedule advancement with shared policy-driven computation that preserves legacy weekly callers, supports explicit schedule disablement, and collapses missed windows to one catch-up run.
- Exposed additive cadence policy inspection and schedule update controls in FastAPI and Typer while keeping legacy coverage create, due-run, and next-run commands valid.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a dedicated cadence-policy registry and validate it at config-load time** - `fbaa4d1` (`feat`)
2. **Task 2: Refactor coverage schedule semantics around shared policy-driven computation** - `7310e8a` (`feat`)
3. **Task 3: Expose additive schedule controls and preserve the existing coverage interface** - `4262738` (`feat`)

**Follow-up fix:** `0023b70` (`fix`) refreshed generated example fixtures and lint-safe cleanup after the full verification gate surfaced snapshot drift.

## Files Created/Modified

- `config/cadence_policies.yaml` - Workspace-timezone cadence registry with built-in weekly, biweekly, weekdays, monthly, and constrained custom-weekdays policies.
- `src/ai_investing/application/scheduling.py` - Shared first-run and next-run computation for cadence policies.
- `src/ai_investing/config/models.py` - Typed cadence policy models and additive coverage schedule fields.
- `src/ai_investing/config/loader.py` - Registry loading and validation for cadence policy definitions and run-policy references.
- `src/ai_investing/domain/models.py` - Backward-compatible coverage normalization for `schedule_policy_id`, `schedule_enabled`, and `preferred_run_time`.
- `src/ai_investing/application/services.py` - Coverage schedule integration for create, update, due-run, and post-run advancement.
- `src/ai_investing/api/main.py` - Additive cadence policy inspection plus coverage schedule update routes.
- `src/ai_investing/cli.py` - Additive cadence policy inspection plus schedule update commands.
- `tests/test_config_and_registry.py` - Registry coverage for cadence policy loading and invalid references.
- `tests/test_analysis_flow.py` - Coverage scheduling regressions for future-slot creation and schedule-disabled manual runs.
- `tests/test_run_lifecycle.py` - Catch-up roll-forward and no-advance regressions for interrupted runs.
- `tests/test_api.py` - API regression coverage for cadence policy listing and schedule updates.
- `tests/test_cli.py` - CLI regression coverage for cadence policy listing and schedule updates.
- `examples/generated/ACME/initial/result.json` - Regenerated example output with additive schedule metadata.
- `examples/generated/ACME/continued/result.json` - Regenerated example output with additive schedule metadata.
- `examples/generated/ACME/rerun/result.json` - Regenerated example output with additive schedule metadata.

## Decisions Made

- Kept `Cadence` narrow instead of widening the enum; richer cadence behavior now comes from named registry policies.
- Used one workspace timezone from config and per-coverage preferred run time so later worker and notification code has deterministic schedule semantics.
- Treated schedule disablement as separate from coverage disablement while preserving legacy clients that only send `cadence`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Refreshed checked-in generated examples after coverage payload changes**
- **Found during:** Final verification
- **Issue:** `tests/test_generated_examples.py` failed because generated ACME result fixtures no longer matched the updated coverage shape.
- **Fix:** Regenerated the checked-in Phase 2 ACME result artifacts so they now include additive schedule metadata.
- **Files modified:** `examples/generated/ACME/initial/result.json`, `examples/generated/ACME/continued/result.json`, `examples/generated/ACME/rerun/result.json`
- **Verification:** `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests`
- **Committed in:** `0023b70`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation was required to keep the repo's checked-in generated artifacts truthful after the new schedule fields became part of the coverage contract.

## Issues Encountered

- The full-suite fixture check surfaced snapshot drift that task-scoped tests could not see because generated examples serialize coverage entries directly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 worker and notification work can now rely on `schedule_policy_id`, `schedule_enabled`, `preferred_run_time`, and shared next-run computation instead of reimplementing cadence logic.
- Queue and notification plans still need to complete `V2-05`; this plan establishes schedule semantics but does not add background worker infrastructure.

## Self-Check: PASSED

- Found `.planning/phases/05-scheduling-and-notifications/05-01-SUMMARY.md`
- Verified commits `fbaa4d1`, `7310e8a`, `4262738`, and `0023b70`

---
*Phase: 05-scheduling-and-notifications*
*Completed: 2026-03-13*
