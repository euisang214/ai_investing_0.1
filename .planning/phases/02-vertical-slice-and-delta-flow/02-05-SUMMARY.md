---
phase: 02-vertical-slice-and-delta-flow
plan: 05
subsystem: application
tags: [resume, baseline, memo, monitoring, examples]
requires:
  - phase: 02-02
    provides: checkpoint-aware memo projection and delta plumbing
  - phase: 02-04
    provides: deterministic example generation and phase 2 regression coverage
provides:
  - repaired first-completion baseline reconstruction for resumed runs
  - regression coverage for initial completion, legacy resumes, CLI/API continue flows, and generated artifacts
  - regenerated ACME examples and clean phase 2 verification status
affects: [phase-03, monitoring, operator-surfaces, examples]
tech-stack:
  added: []
  patterns: [explicit no-baseline metadata handling, legacy history recovery excluding current run, first-completion versus rerun memo posture]
key-files:
  created: []
  modified:
    - src/ai_investing/application/services.py
    - src/ai_investing/persistence/repositories.py
    - tests/test_analysis_flow.py
    - tests/test_monitoring_semantics.py
    - tests/test_generated_examples.py
    - tests/test_cli.py
    - tests/test_api.py
    - examples/generated/README.md
    - examples/generated/ACME/continued/result.json
    - examples/generated/ACME/continued/memo.md
    - examples/generated/ACME/continued/delta.json
    - examples/generated/ACME/rerun/result.json
    - examples/generated/ACME/rerun/memo.md
    - examples/generated/ACME/rerun/delta.json
    - .planning/ROADMAP.md
    - .planning/phases/02-vertical-slice-and-delta-flow/02-VERIFICATION.md
key-decisions:
  - "Treat explicit null and empty baseline metadata as an intentional no-baseline signal instead of falling back on truthiness."
  - "Recover legacy paused-run baselines from the latest non-current memo, claim, and verdict records instead of reading the paused run's own promoted state."
  - "Keep same-run placeholder memo sections not_advanced on first completion; only true reruns may carry them forward as stale."
patterns-established:
  - "Resume baselines: prefer persisted baseline metadata when present, even when empty, and fall back only to historical records that exclude the current run."
  - "Artifact parity: generated examples and regression tests lock the public first-completion versus rerun story together."
requirements-completed: [ORCH-03, MEMO-01, MEMO-03, TEST-01, TEST-02]
duration: 11min
completed: 2026-03-11
---

# Phase 02 Plan 05: Initial Completion Baseline Repair Summary

**Resumed initial coverage now keeps a null prior baseline, preserves same-run placeholder memo sections as not_advanced, and reserves stale carry-forward for true reruns**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-11T11:50:55Z
- **Completed:** 2026-03-11T12:02:10Z
- **Tasks:** 4
- **Files modified:** 16

## Accomplishments
- Repaired baseline selection so resumed first completions no longer reuse the paused run's own partial memo, claims, or verdicts as prior active state.
- Added regression coverage for initial completion, metadata-absent legacy resumes, CLI/API continue flows, and generated artifact parity.
- Regenerated ACME continued and rerun artifacts and reconciled the Phase 2 roadmap and verification record after full Docker verification passed.

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix baseline reconstruction for resumed first-completion runs** - `57a47e2` (fix)
2. **Task 2: Add regression coverage for first completion versus real rerun behavior** - `0de9b69` (test)
3. **Task 3: Regenerate and refresh the checked-in ACME examples** - `61cf150` (feat)
4. **Task 4: Reconcile planning-status artifacts after the repair passes** - `a2b05b8` (chore)

Additional verification cleanup:

1. **Generated example lint follow-up** - `bee2736` (test)

## Files Created/Modified
- `src/ai_investing/application/services.py` - repaired baseline selection and same-run placeholder memo projection
- `src/ai_investing/persistence/repositories.py` - added historical lookup helpers that exclude the paused run
- `tests/test_analysis_flow.py` - locked initial completion and legacy resume baseline behavior
- `tests/test_monitoring_semantics.py` - locked first-completion `not_advanced` posture and true-rerun stale carry-forward semantics
- `tests/test_generated_examples.py` - asserted generated artifact parity for null prior baseline and corrected memo wording
- `tests/test_cli.py` - asserted CLI continue output keeps initial coverage distinct from reruns
- `tests/test_api.py` - asserted API continue output keeps initial coverage distinct from reruns
- `examples/generated/README.md` - documented continued as initial coverage and rerun as the stale carry-forward path
- `examples/generated/ACME/continued/*` - regenerated initial-completion outputs with `prior_run_id: null`
- `examples/generated/ACME/rerun/*` - regenerated rerun outputs against the corrected prior baseline
- `.planning/ROADMAP.md` - marked Phase 2 plan progress `5 / 5` complete
- `.planning/phases/02-vertical-slice-and-delta-flow/02-VERIFICATION.md` - marked Phase 2 verification passed with no open gaps

## Decisions Made

- Used explicit metadata presence, not truthiness, to distinguish "no baseline exists" from "baseline key is absent on legacy runs."
- Recovered legacy baseline history from the latest non-current persisted artifacts because paused runs already promote partial state to active.
- Treated first-completion placeholders as same-run state that should stay `not_advanced`, while allowing later reruns to mark carried-forward sections stale.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Wrapped a generated-example assertion to satisfy Docker lint verification**
- **Found during:** Task 4 (Reconcile planning-status artifacts after the repair passes)
- **Issue:** A new regression assertion in `tests/test_generated_examples.py` exceeded the repo's line-length limit and blocked `docker compose run --rm api ruff check src tests`
- **Fix:** Reflowed the assertion across multiple lines without changing behavior
- **Files modified:** `tests/test_generated_examples.py`
- **Verification:** `docker compose run --rm api ruff check src tests`
- **Committed in:** `bee2736`

---

**Total deviations:** 1 auto-fixed (Rule 3)
**Impact on plan:** No scope creep. The follow-up was required to complete the plan's documented Docker lint verification.

## Issues Encountered

- Host `pytest` could not run because the local Python environment was missing `pydantic`, so verification stayed on the plan's Docker path.
- The repaired first-completion semantics changed a true rerun's low-material delta posture because previously untouched sections now correctly flip from `not_advanced` to `stale`; the regression expectations were updated to the new public behavior.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 2 is now clean: first completion and rerun semantics are distinct across service outputs, operator surfaces, and checked-in examples. Phase 3 can extend panel coverage without revisiting the baseline or memo-posture contracts.

## Self-Check: PASSED
