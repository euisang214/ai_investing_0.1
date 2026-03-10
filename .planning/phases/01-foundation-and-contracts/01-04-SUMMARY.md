---
phase: 01-foundation-and-contracts
plan: 04
subsystem: orchestration
tags: [langgraph, policies, monitoring, testing]
requires:
  - phase: 01-01
    provides: validated config, provider, and tool boundaries
  - phase: 01-02
    provides: migration-safe persistence and connector-driven ingestion
provides:
  - panel-subgraph builder lookup keyed by config-declared subgraph type
  - policy-aware memo and monitoring execution
  - failed-run persistence and orchestration regression coverage
affects: [phase-02, memo, monitoring, company-refresh]
tech-stack:
  added: []
  patterns:
    - config-driven graph composition through subgraph builders
    - failure-safe run lifecycle persistence
key-files:
  created: []
  modified:
    - src/ai_investing/graphs/company_refresh.py
    - src/ai_investing/graphs/subgraphs.py
    - src/ai_investing/graphs/state.py
    - src/ai_investing/application/services.py
    - tests/test_analysis_flow.py
key-decisions:
  - "Move panel graph selection behind a builder lookup keyed by panel.subgraph."
  - "Honor run-policy memo and monitoring flags in orchestration rather than ignoring them at runtime."
  - "Persist failed runs before re-raising so operator tooling can inspect what happened."
patterns-established:
  - "Top-level refresh composition is registry-driven instead of inline topology branching."
  - "Policy and failure handling are part of the analysis service contract, not incidental behavior."
requirements-completed: [ORCH-01]
duration: recovery-session
completed: 2026-03-10
---

# Phase 01 Plan 04 Summary

**Company refresh orchestration is now config-driven and failure-safe, with panel builder lookup, policy-aware monitoring/memo behavior, and stronger regression coverage.**

## Performance

- **Duration:** recovery session
- **Started:** 2026-03-10T00:00:00Z
- **Completed:** 2026-03-10T02:43:47Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Replaced top-level inline panel branching with a builder lookup based on `panel.subgraph`.
- Added run-policy-aware memo and monitoring behavior plus explicit failure persistence for broken runs.
- Expanded orchestration tests to cover unknown subgraphs, unsafe panel policies, monitoring skips, and failed-run recording.

## Task Commits

The executor handoff stalled before task-level commits were produced. Recovery execution continued directly in the workspace and verification was completed against the final working tree.

## Files Created/Modified

- `src/ai_investing/graphs/company_refresh.py` - Switched to builder-driven graph composition and policy-aware node selection.
- `src/ai_investing/graphs/subgraphs.py` - Added subgraph lookup and monitoring-skip behavior.
- `src/ai_investing/graphs/state.py` - Extended refresh state for graph composition.
- `src/ai_investing/application/services.py` - Added safe panel selection, policy gating, and failed-run persistence.
- `tests/test_analysis_flow.py` - Added orchestration guardrail coverage.

## Decisions Made

- Unsupported or unimplemented panels fail closed unless a policy explicitly allows them.
- Monitoring can be skipped by policy, but the run still records a delta artifact describing that choice.
- Failed runs are committed to persistence before exceptions propagate so operators do not lose the run record.

## Deviations from Plan

- None beyond the direct recovery execution path.

## Issues Encountered

- The original graph path already worked for the vertical slice, but it hid control flow inside nested `.invoke()` wrappers and did not persist failures. The recovery work pulled those contracts up into test-backed runtime behavior.

## User Setup Required

None.

## Next Phase Readiness

- Phase 02 can add panels and policy variations without rewriting the company refresh graph core.
- Memo, monitoring, and IC synthesis boundaries are explicit enough for later delta and panel expansion work.

---
*Phase: 01-foundation-and-contracts*
*Completed: 2026-03-10*
