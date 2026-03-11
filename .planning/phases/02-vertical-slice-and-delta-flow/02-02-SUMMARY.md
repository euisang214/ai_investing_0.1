---
phase: 02-vertical-slice-and-delta-flow
plan: 02
subsystem: application
tags: [memo, monitoring, fake-provider, tool-logs, prompts]
requires:
  - phase: 02-01
    provides: checkpoint-aware gatekeeper pause/resume flow and partial run persistence
provides:
  - full memo projection semantics across refreshed, stale, and not_advanced sections
  - structured rerun delta materiality driven by claims, verdicts, and memo posture
  - stale-evidence-aware fake provider outputs and record-level tool log references
affects: [monitoring, memo, providers, tools, prompts]
tech-stack:
  added: []
  patterns:
    [
      partial memo projection,
      config-driven delta materiality,
      deterministic stale-evidence downgrades,
      record-level tool-log refs,
    ]
key-files:
  created: [tests/test_monitoring_semantics.py]
  modified:
    [
      src/ai_investing/application/services.py,
      src/ai_investing/providers/fake.py,
      src/ai_investing/tools/builtins.py,
      src/ai_investing/tools/registry.py,
      config/monitoring.yaml,
    ]
key-decisions:
  - "Keep checkpointed and completed memo projection in one service pipeline, and express posture through section status plus operator-facing content."
  - "Classify rerun deltas from structured claim, verdict, and memo posture changes while always refreshing the what_changed_since_last_run run log."
  - "Expose tool log provenance as returned evidence, claim, and memo section ids, and mirror stale-evidence semantics in the fake provider for deterministic tests."
patterns-established:
  - "Projection-first memo building: every run emits the full memo contract even when execution pauses."
  - "Monitoring materiality stays config-driven and ignores sub-threshold confidence churn by itself."
  - "Fake-provider semantics should mirror prompt contracts closely enough to lock behavior in regression tests."
requirements-completed: [ING-03, MEMO-01, MEMO-03, TOOLS-02]
duration: 14min
completed: 2026-03-11
---

# Phase 2 Plan 2: Living Memo And Delta Semantics Summary

**Full memo posture projection, structured rerun materiality, and stale-evidence-aware fake outputs for the vertical slice**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-11T02:55:10Z
- **Completed:** 2026-03-11T03:09:35Z
- **Tasks:** 3
- **Files modified:** 21

## Accomplishments

- Made memo projection explicit about `refreshed`, `stale`, and `not_advanced` posture without creating a second checkpoint-specific memo flow.
- Replaced text-churn delta detection with config-driven claim, verdict, and memo-posture materiality rules while always refreshing the run-log section.
- Propagated stale-evidence semantics through prompts, fake-provider claims and memo updates, and tool logs that now point to returned evidence and claim ids.

## Task Commits

Each task was committed atomically:

1. **Task 1: Project the full memo contract across partial, stale, and never-advanced sections** - `d88e58d` (feat)
2. **Task 2: Replace noisy delta logic with a structured materiality comparator** - `0af961e` (feat)
3. **Task 3: Surface evidence staleness and real output references through tools and prompts** - `b9e4db7` (feat)
4. **Verification cleanup** - `b1ef655` (refactor)

**Plan metadata:** Recorded in the final docs commit for this plan.

## Files Created/Modified

- `tests/test_monitoring_semantics.py` - Regression coverage for memo posture, rerun materiality, stale evidence, and tool-log refs.
- `src/ai_investing/application/services.py` - Memo projection helpers, verdict baselines, and structured monitoring delta classification.
- `src/ai_investing/providers/fake.py` - Deterministic stale-evidence downgrades for claims, verdicts, and memo section updates.
- `src/ai_investing/tools/builtins.py` - Builtin tool results now expose record-level output refs.
- `src/ai_investing/tools/registry.py` - Tool logs persist returned output refs instead of generic tool ids.
- `config/monitoring.yaml` - Materiality thresholds and alert semantics moved into config.
- `prompts/memo_updates/section_update.md` - Memo update contract now preserves stale and provisional posture.
- `prompts/monitoring/delta.md` - Monitoring prompt now emphasizes structured materiality over wording churn.
- `prompts/ic/synthesizer.md` - IC synthesis prompt now preserves full memo posture across checkpointed runs.
- `docs/memory_model.md` - Memo projection rules documented alongside structured memory rules.
- `docs/monitoring.md` - Monitoring materiality and alerting rules documented.

## Decisions Made

- Used memo section status plus projected content to communicate paused, stale, and provisional posture instead of inventing a second memo pipeline.
- Stored baseline active verdicts on run metadata so resumed reruns can compare gatekeeper changes against the pre-run baseline.
- Treated `what_changed_since_last_run` as an always-refreshed run log while excluding it from material section escalation.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Host verification was blocked by the local shell only exposing Python 3.9 without `uv`; verification was completed in the repo's Dockerized Python 3.11 environment instead.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The vertical slice now projects honest partial memos, balanced rerun deltas, and inspectable tool provenance, which unblocks richer operator flows and downstream panel expansion.
- No blockers remain in the owned files for the next plan.

## Self-Check: PASSED

- Verified `.planning/phases/02-vertical-slice-and-delta-flow/02-02-SUMMARY.md` exists on disk.
- Verified task commits `d88e58d`, `0af961e`, `b9e4db7`, and `b1ef655` are present in local history.
- Verified plan checks in Dockerized Python 3.11: `pytest -q tests/test_monitoring_semantics.py`, `pytest -q tests/test_repository_semantics.py`, and `ruff check src tests`.

---
*Phase: 02-vertical-slice-and-delta-flow*
*Completed: 2026-03-11*
