---
phase: 02-vertical-slice-and-delta-flow
plan: 01
subsystem: orchestration
tags: [langgraph, postgres, checkpointing, fastapi, typer, memo-history]
requires:
  - phase: 01-foundation-and-contracts
    provides: config registries, typed persistence contracts, and CLI/API scaffolding for company refresh workflows
provides:
  - checkpoint-aware run lifecycle records with queryable pause, stop, provisional, and completion states
  - durable gatekeeper pause/resume routing through LangGraph checkpointers and stable run IDs
  - cadence-safe start and continue flows across service, CLI, and API entrypoints
affects: [03-remaining-panel-scaffolds, 04-monitoring-and-connectors, 05-scheduling-and-notifications]
tech-stack:
  added: [langgraph-checkpoint-postgres]
  patterns: [graph-native interrupts, session-scoped persistence boundaries, same-run resume flows]
key-files:
  created:
    - alembic/versions/0002_phase2_checkpoint_runtime.py
    - src/ai_investing/graphs/checkpointing.py
    - .planning/phases/02-vertical-slice-and-delta-flow/02-01-SUMMARY.md
  modified:
    - src/ai_investing/application/services.py
    - src/ai_investing/domain/models.py
    - src/ai_investing/persistence/repositories.py
    - src/ai_investing/graphs/company_refresh.py
    - src/ai_investing/graphs/subgraphs.py
    - src/ai_investing/api/main.py
    - src/ai_investing/cli.py
    - tests/test_run_lifecycle.py
key-decisions:
  - "Persist awaiting_continue, provisional, gate_decision, and checkpoint_panel_id as typed run fields instead of inferring lifecycle from metadata blobs."
  - "Let LangGraph own the gatekeeper pause/resume path through interrupt() and Command(resume=...) using run_id as the durable thread identity."
  - "Keep analyze_company, refresh_company, and run_panel as public entrypoints, but force downstream panel work to resume existing checkpointed runs instead of bypassing gatekeepers."
patterns-established:
  - "Checkpoint-native orchestration: graph interrupts represent gatekeeper review state rather than ad hoc service branching."
  - "Session-scoped writes: start and resume flows reopen repositories around durable boundaries so paused runs stay queryable."
  - "Memo baseline reconstruction: resume flows rebuild prior and current memo state from persisted snapshots plus active records."
requirements-completed: [COV-03, MEM-03, ORCH-02, ORCH-03]
duration: 21 min
completed: 2026-03-11
---

# Phase 02 Plan 01: Checkpoint Runtime Summary

**Checkpoint-aware company refresh runtime with persisted gatekeeper pauses, same-run resume flows, and cadence-safe scheduling semantics**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-10T22:16:06-04:00
- **Completed:** 2026-03-11T02:37:11Z
- **Tasks:** 3
- **Files modified:** 18

## Accomplishments
- Added typed run lifecycle contracts, migration support, and repository queries for paused, provisional, stopped, gated-out, failed, and completed runs.
- Compiled the company refresh graph with a durable Postgres-backed LangGraph checkpointer and a graph-owned gatekeeper interrupt/resume boundary.
- Refactored service, CLI, and API flows so runs start once, resume through the same `run_id`, stay visible to due-coverage logic, and fail closed on direct downstream panel shortcuts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add first-class checkpoint and run-lifecycle contracts** - `2cb77e8` (feat)
2. **Task 2: Compile the company refresh graph with durable checkpoint support** - `24fb12e` (feat)
3. **Task 3: Refactor service execution into start, resume, and due-coverage flows** - `2ef74fc` (feat)

## Files Created/Modified
- `alembic/versions/0002_phase2_checkpoint_runtime.py` - Projects the new checkpoint and run-lifecycle columns needed for queryable resume state.
- `src/ai_investing/domain/models.py` - Defines typed run checkpoint payloads and explicit lifecycle fields.
- `src/ai_investing/graphs/checkpointing.py` - Chooses durable Postgres or in-memory checkpoint savers behind one graph boundary.
- `src/ai_investing/graphs/company_refresh.py` - Compiles the top-level refresh graph with gatekeeper checkpoint routing.
- `src/ai_investing/application/services.py` - Splits execution into durable start and continue flows with cadence-safe completion handling.
- `src/ai_investing/api/main.py` - Exposes run continuation through `POST /runs/{run_id}/continue`.
- `src/ai_investing/cli.py` - Adds the `continue-run` command for operator-driven resume actions.
- `tests/test_run_lifecycle.py` - Covers pause/resume, provisional continue, due-coverage behavior, and downstream shortcut rejection.

## Decisions Made
- Persisted lifecycle status in first-class run fields so coverage scheduling and operator tooling can query run state without decoding metadata.
- Stored the baseline memo and active-claim snapshot in run metadata so resume flows can reconcile current output without overwriting prior beliefs.
- Kept gatekeeper review as a graph-native checkpoint so future panel expansion can reuse the same boundary instead of adding bespoke orchestration branches.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed a stray tracked FastAPI module copy that broke required lint verification**
- **Found during:** Task 3 (Refactor service execution into start, resume, and due-coverage flows)
- **Issue:** The tracked file `src/ai_investing/api/main 2.py` sat outside the planned runtime changes but caused `ruff check src tests` to fail with an invalid module name and stale formatting issues.
- **Fix:** Deleted the duplicate module and kept `src/ai_investing/api/main.py` as the single canonical API entrypoint.
- **Files modified:** `src/ai_investing/api/main 2.py`
- **Verification:** `docker compose run --rm api ruff check src tests`
- **Committed in:** `2ef74fc` (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The cleanup was required to satisfy the plan's lint gate and did not expand scope beyond the intended checkpoint runtime work.

## Issues Encountered
- The host Python 3.9 environment did not have the full project dependency set for LangGraph verification, so the validation suite ran in Docker Compose, which matches the repository's documented development path.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The runtime can now pause after `gatekeepers` and resume through stable run IDs, so remaining Phase 2 work can focus on richer memo, delta, and tool-log outputs instead of orchestration mechanics.
- Due coverage, CLI, and API entrypoints already understand checkpointed runs, which keeps future panel additions config-driven and reusable.

## Self-Check: PASSED
- Verified `.planning/phases/02-vertical-slice-and-delta-flow/02-01-SUMMARY.md` exists.
- Verified task commits `2cb77e8`, `24fb12e`, and `2ef74fc` resolve as commits.

---
*Phase: 02-vertical-slice-and-delta-flow*
*Completed: 2026-03-11*
