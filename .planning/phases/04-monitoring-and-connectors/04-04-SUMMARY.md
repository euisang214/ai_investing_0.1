---
phase: 04-monitoring-and-connectors
plan: 04
subsystem: api
tags: [monitoring, read-models, fastapi, typer, postgres]
requires:
  - phase: 04-02
    provides: representative connector packets and one lightweight live public connector path
  - phase: 04-03
    provides: richer monitoring delta semantics and additive operator-facing delta details
provides:
  - typed company monitoring history and portfolio monitoring summary projections
  - additive CLI and API inspection surfaces for monitoring history and portfolio monitoring
  - repo documentation that keeps the new surfaces read-only and preserves scaffold-only portfolio_fit_positioning
affects: [api, cli, monitoring, repositories, docs]
tech-stack:
  added: []
  patterns:
    - read-side projection services over persisted structured records
    - additive operator surfaces that preserve legacy run and delta contracts
    - coverage-segmented portfolio monitoring grouped by change type first
key-files:
  created: []
  modified:
    - src/ai_investing/domain/read_models.py
    - src/ai_investing/application/portfolio.py
    - src/ai_investing/persistence/repositories.py
    - src/ai_investing/api/main.py
    - src/ai_investing/cli.py
    - docs/memory_model.md
    - docs/architecture.md
    - README.md
key-decisions:
  - "Keep monitoring history and portfolio monitoring as read-only projections instead of widening orchestration or memo-writing behavior."
  - "Organize portfolio monitoring by change type first while keeping portfolio and watchlist names separate in every group."
  - "Allow portfolio_fit_positioning to appear in monitoring output only as memo projection metadata while keeping the panel scaffold-only."
patterns-established:
  - "Read surfaces stay additive: show-run, show-delta, /runs/{run_id}, and /companies/{company_id}/delta remain unchanged."
  - "Portfolio-level monitoring summarizes shared-risk clusters first and leaves broader analog exploration as secondary drill-down."
requirements-completed: [V2-04]
duration: 16min
completed: 2026-03-13
---

# Phase 4 Plan 04: Portfolio Monitoring Read Surfaces Summary

**Typed monitoring-history and portfolio-summary projections with additive CLI/API inspection while keeping `portfolio_fit_positioning` scaffold-only**

## Performance

- **Duration:** 16 min
- **Started:** 2026-03-13T12:34:30Z
- **Completed:** 2026-03-13T12:50:48Z
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments

- Added typed company monitoring history and portfolio monitoring summary read models on top of persisted coverage, run, and monitoring records.
- Exposed additive CLI and API inspection surfaces for monitoring history and segmented portfolio or watchlist summaries without replacing existing run and delta entrypoints.
- Reconciled repo docs so the new operator surfaces stay explicitly read-only, change-type-first, and separate from any runnable `portfolio_fit_positioning` runtime story.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add typed read models and read-side services after validating the merged wave-2 baseline** - `7e0b4bf` (feat)
2. **Task 2: Expose the new read surfaces through additive API and CLI commands with a reviewable example** - `48626f3` (feat)
3. **Task 3: Document the read-only boundary, preserve the scaffold story, and finish with a full-suite gate** - `0784c76` (docs)

## Files Created/Modified

- `src/ai_investing/domain/read_models.py` - Typed company monitoring history and portfolio monitoring summary contracts.
- `src/ai_investing/application/portfolio.py` - Read-side service that assembles history and segmented portfolio monitoring projections.
- `src/ai_investing/persistence/repositories.py` - Query helpers for monitoring history and coverage-segmented portfolio aggregation.
- `src/ai_investing/api/main.py` - Additive FastAPI routes for monitoring history and portfolio monitoring summary inspection.
- `src/ai_investing/cli.py` - Additive Typer commands for monitoring history and portfolio summary inspection.
- `docs/memory_model.md` - Read-only contract details, example payload, and operator interpretation guidance for portfolio monitoring.
- `docs/architecture.md` - Interface-layer boundary notes for additive monitoring inspection routes.
- `README.md` - Operator-facing summary of the new monitoring history and portfolio monitoring surfaces.

## Decisions Made

- Kept the new monitoring surfaces read-only so they project structured records without changing memo-writing flow or company-refresh orchestration.
- Standardized the portfolio summary around change-type-first grouping with explicit `portfolio` and `watchlist` subsections so holdings never blur with watchlist coverage.
- Kept shared-risk or overlap clusters as the primary portfolio monitoring output and relegated broader analog exploration to secondary drill-down.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Required Docker-based verification was temporarily blocked because Docker Desktop was not running. Docker Desktop was started, daemon readiness was confirmed, and the required targeted tests, docs check, full test suite, and lint pass all completed successfully afterward.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 4 now has connector coverage, richer monitoring deltas, and additive monitoring read surfaces complete.
- Portfolio monitoring visibility is ready for future operator tooling or later panel productionization without changing the current scaffold boundary.

## Self-Check: PASSED

- Found `.planning/phases/04-monitoring-and-connectors/04-04-SUMMARY.md`.
- Verified task commits `7e0b4bf`, `48626f3`, and `0784c76` directly with `git rev-parse --verify`.
