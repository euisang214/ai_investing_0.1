---
phase: 05-scheduling-and-notifications
plan: 02
subsystem: api
tags: [langgraph, queue, worker, notifications, scheduling, cli, fastapi, sqlite]
requires:
  - phase: 05-scheduling-and-notifications
    provides: Config-driven cadence policies, additive coverage schedule fields, and schedule advancement rules from Plan 01
provides:
  - Structured refresh job, review queue, and notification persistence
  - Bounded-concurrency worker execution with company-safe claim semantics
  - Shared gatekeeper lifecycle where pass/review auto-continue and fail stops into review
  - Additive API and CLI operator surfaces for queue, worker, review, and notification workflows
affects: [operations, monitoring, n8n, run-inspection, weekly-refresh]
tech-stack:
  added: [alembic migration]
  patterns: [typed operational records, queue-backed recurring execution, notification delivery boundary, review-required gatekeeper stops]
key-files:
  created: [src/ai_investing/application/queue.py, src/ai_investing/application/worker.py, src/ai_investing/application/notifications.py, tests/test_worker_runtime.py, alembic/versions/0003_phase5_background_operations.py]
  modified: [src/ai_investing/application/services.py, src/ai_investing/persistence/repositories.py, src/ai_investing/api/main.py, src/ai_investing/cli.py, tests/test_run_lifecycle.py, tests/test_analysis_flow.py, tests/test_api.py, tests/test_cli.py, tests/test_monitoring_semantics.py, scripts/generate_phase2_examples.py]
key-decisions:
  - "Persist refresh jobs, review stops, and notification events as first-class typed records instead of run metadata blobs or n8n-only state."
  - "Apply one shared gatekeeper policy across all entrypoints: pass and review auto-continue, fail stops into review, and provisional continuation stays explicit operator-only behavior."
  - "Expose notification delivery and queue controls through additive application, API, and CLI seams so external automation never needs direct database access."
  - "Enforce company-level deduplication and bounded concurrent worker claims at the repository and worker layers rather than relying on serialized scheduling."
patterns-established:
  - "Operational state lives beside memo/runtime state as typed repository models with dedicated read models."
  - "Worker-triggered runs carry job metadata into the existing AnalysisService runtime instead of introducing a separate execution path."
  - "Generated examples must be produced through the same public runtime behavior the app now exposes."
requirements-completed: [V2-03, V2-05]
duration: 34 min
completed: 2026-03-13
---

# Phase 05 Plan 02: Background Queue and Notification Surfaces Summary

**Structured refresh jobs, failed-gatekeeper review stops, bounded worker execution, and notification delivery seams wired through the existing LangGraph run runtime**

## Performance

- **Duration:** 34 min
- **Started:** 2026-03-13T15:32:53Z
- **Completed:** 2026-03-13T16:06:49Z
- **Tasks:** 3
- **Files modified:** 32

## Accomplishments

- Added durable refresh-job, review-queue, and notification-event persistence with typed repository read models and an Alembic migration.
- Built queue submission, worker execution, and notification services that reuse the existing `AnalysisService` runtime while preventing duplicate company work.
- Reconciled the gatekeeper lifecycle so `pass` and `review` auto-continue, while `fail` stops into a review queue and emits an immediate notification.
- Added additive API and CLI operator controls for queue inspection, enqueue, retry/cancel/force-run, worker execution, review inspection, and notification delivery workflows.
- Updated generated ACME examples and lifecycle regressions so the checked-in artifacts reflect the post-gatekeeper auto-continue policy.

## Task Commits

Each task was committed atomically:

1. **Task 1: Persist queue, review, and notification state as first-class records with read models** - `6b74b06` (feat)
2. **Task 2: Build worker execution services and reconcile the gatekeeper runtime with the new policy** - `2831f41` (feat)
3. **Task 3: Add operator enqueue and inspection surfaces while preserving compatibility entrypoints** - `e3dc324` (feat)

**Verification fix-up:** `bb20841` (fix: align generated examples and monitoring regressions with the auto-continue runtime)

## Files Created/Modified

- `alembic/versions/0003_phase5_background_operations.py` - migration for refresh jobs, review queue entries, and notification events
- `src/ai_investing/domain/models.py` - typed operational records for jobs, review entries, and notifications
- `src/ai_investing/domain/read_models.py` - queue summary, job detail, review queue, and notification list projections
- `src/ai_investing/persistence/repositories.py` - enqueue, claim, retry, cancel, force-run, review, and notification repository helpers
- `src/ai_investing/application/queue.py` - submission and queue read-side service
- `src/ai_investing/application/worker.py` - bounded concurrent worker claim-and-execute service
- `src/ai_investing/application/notifications.py` - notification classification and delivery boundary
- `src/ai_investing/application/services.py` - queue-aware refresh execution and shared gatekeeper lifecycle handling
- `src/ai_investing/api/main.py` - additive queue, review, worker, and notification endpoints
- `src/ai_investing/cli.py` - additive queue, worker, review, and notification commands
- `tests/test_worker_runtime.py` - worker concurrency, review-stop, and notification regressions
- `tests/test_generated_examples.py` - lifecycle example expectations for the auto-continue runtime

## Decisions Made

- Persisted background operations as dedicated typed records so weekly refresh state is queryable and automation-safe without scraping run metadata.
- Reused `AnalysisService` for queued work to preserve stable `run_id`, checkpoint fields, memo projection, and existing inspection entrypoints.
- Kept provisional downstream execution behind `continue_run(..., CONTINUE_PROVISIONAL)` only; neither workers nor notification automation can trigger it automatically.
- Treated checked-in generated examples as part of the runtime contract and regenerated them when the gatekeeper lifecycle changed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated generated examples and monitoring expectations for the new gatekeeper lifecycle**
- **Found during:** Overall verification after Task 3
- **Issue:** Full-suite regressions still assumed the old universal post-gatekeeper pause behavior, causing example generation and monitoring tests to call `continue_run` on already-complete runs.
- **Fix:** Updated the generator to reload completed runs from persistence, regenerated checked-in ACME artifacts, aligned monitoring semantics expectations, and cleaned the new CLI argument signature for lint.
- **Files modified:** `scripts/generate_phase2_examples.py`, `examples/generated/README.md`, `examples/generated/ACME/*`, `tests/test_generated_examples.py`, `tests/test_monitoring_semantics.py`, `src/ai_investing/cli.py`
- **Verification:** `docker compose run --rm api pytest -q`; `docker compose run --rm api ruff check src tests`
- **Committed in:** `bb20841`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The fix kept the plan aligned with the intended runtime policy and prevented stale example or regression contracts from contradicting shipped behavior.

## Issues Encountered

- Parallel `git add` attempts briefly collided on `.git/index.lock`; resolved by staging serially.
- Full-suite compatibility regressions surfaced only after Task 3 because the focused task tests already covered the new operator surfaces but not the older example-generation path.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Queue-backed recurring execution, review handling, and notification delivery seams are in place for Wave 3 scheduling and automation examples.
- Existing run-centric inspection surfaces remain stable, so downstream work can build on the additive queue and notification APIs without replacing current tooling.

## Self-Check: PASSED

- Verified `.planning/phases/05-scheduling-and-notifications/05-02-SUMMARY.md` exists.
- Verified task and fix-up commits `6b74b06`, `2831f41`, `e3dc324`, and `bb20841` resolve as commit objects.

---
*Phase: 05-scheduling-and-notifications*
*Completed: 2026-03-13*
