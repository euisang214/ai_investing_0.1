---
phase: 02-vertical-slice-and-delta-flow
plan: 03
subsystem: api
tags: [cli, fastapi, checkpointing, operator-workflow]
requires:
  - phase: 02-01
    provides: checkpoint-aware run lifecycle and persisted gatekeeper pause state
provides:
  - explicit CLI run inspection and continue controls for paused gatekeeper runs
  - typed FastAPI run payloads and persisted GET /runs/{run_id} inspection
  - operator docs for stop, continue, and provisional resume behavior
affects: [phase-02-04, operator-workflows, checkpoint-observability]
tech-stack:
  added: []
  patterns:
    [
      persisted run lookup for operator inspection,
      typed API envelopes over shared run payloads,
      explicit CLI continue flags for stop and provisional resume,
    ]
key-files:
  created: []
  modified:
    [
      src/ai_investing/cli.py,
      src/ai_investing/api/main.py,
      tests/test_cli.py,
      tests/test_api.py,
      README.md,
      docs/runbook.md,
      docs/architecture.md,
    ]
key-decisions:
  - "Expose paused-run inspection through persisted run lookups instead of relying on service-internal state."
  - "Keep CLI continue behavior backward compatible with --action while adding explicit --stop and --provisional flags."
  - "Use typed FastAPI envelopes for run payloads while preserving the existing {data: ...} response wrapper."
patterns-established:
  - "Checkpoint-aware operator interfaces read the same persisted run artifacts the runtime writes."
  - "Paused, stopped, provisional, and completed states stay machine-readable through stable run fields."
requirements-completed: [COV-03, MEM-03, ORCH-02]
duration: 6 min
completed: 2026-03-11
---

# Phase 2 Plan 3: Checkpoint Operator Interfaces Summary

**Checkpoint-aware CLI and FastAPI run controls with persisted run inspection and explicit provisional resume flows**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-11T02:55:52Z
- **Completed:** 2026-03-11T03:01:37Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Added `show-run` plus explicit `--stop` and `--provisional` CLI controls for paused gatekeeper runs.
- Added typed FastAPI run envelopes, `GET /runs/{run_id}`, and run-due payload coverage for paused and resumed flows.
- Updated quick-start and operator docs to describe the mandatory gatekeeper pause, explicit continue actions, and provisional override behavior.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add explicit CLI controls for checkpointed runs** - `3fbcba5` (feat)
2. **Task 2: Add typed API routes and payloads for run checkpoint control** - `5466167` (feat), `54f1f7b` (fix)
3. **Task 3: Refresh operator documentation for the checkpointed workflow** - `cf5a579` (docs)

## Files Created/Modified

- `src/ai_investing/cli.py` - Added persisted run inspection and explicit continue flag handling.
- `tests/test_cli.py` - Covered paused run inspection and provisional continue CLI behavior.
- `src/ai_investing/api/main.py` - Added typed run response envelopes and `GET /runs/{run_id}`.
- `tests/test_api.py` - Covered persisted run lookup, due-coverage paused responses, and provisional continue requests.
- `README.md` - Updated quick start and CLI examples for checkpoint-aware workflows.
- `docs/runbook.md` - Documented inspect, continue, stop, and provisional operator paths.
- `docs/architecture.md` - Documented the mandatory gatekeeper checkpoint contract across CLI and API.
- `.planning/phases/02-vertical-slice-and-delta-flow/02-03-SUMMARY.md` - Recorded plan outcomes and verification status.

## Decisions Made

- Added interface-level run inspection by rebuilding persisted run payloads from repository state rather than modifying service ownership outside this plan.
- Kept the CLI continue contract explicit and operator-friendly by supporting `--stop` and `--provisional` in addition to the existing `--action` option.
- Typed all run-control API responses around the existing run payload shape so automation clients can rely on stable fields without changing the top-level envelope.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- A transient `.git/index.lock` race occurred while a parallel git status command was reading the index during the Task 2 commit. Resolved by committing `src/ai_investing/api/main.py` in a follow-up commit (`54f1f7b`) instead of rewriting history.
- `docker compose exec api ruff check src tests` still fails on pre-existing `E501` line-length violations in `src/ai_investing/application/services.py:711`, `src/ai_investing/application/services.py:874`, and `src/ai_investing/application/services.py:934`. Those lines are outside this plan's ownership and were left unchanged.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CLI and API operators can now inspect paused runs by `run_id`, continue them explicitly, or mark downstream work provisional after a failed gatekeeper.
- The checkpoint workflow was exercised end to end against the fake provider through the API.
- `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` were left unchanged for orchestrator reconciliation because Plan `02-02` is executing in parallel and the shared GSD progress/state updates are not isolated to this plan.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/02-vertical-slice-and-delta-flow/02-03-SUMMARY.md`.
- Verified task commits: `3fbcba5`, `5466167`, `54f1f7b`, and `cf5a579`.
