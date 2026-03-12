---
status: testing
phase: 03-remaining-panel-scaffolds
source:
  - .planning/phases/03-remaining-panel-scaffolds/03-01-SUMMARY.md
  - .planning/phases/03-remaining-panel-scaffolds/03-02-SUMMARY.md
  - .planning/phases/03-remaining-panel-scaffolds/03-03-SUMMARY.md
  - .planning/phases/03-remaining-panel-scaffolds/03-04-SUMMARY.md
started: 2026-03-12T11:52:24Z
updated: 2026-03-12T12:18:35Z
---

## Current Test

number: 6
name: Extension Path Documentation
expected: |
  The repo docs should consistently explain that only `gatekeepers` and `demand_revenue_quality` are implemented today, that the remaining panels are config-visible but non-runnable, and that a clear file-by-file extension path exists for future productionization.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: From a fully stopped stack with fresh ephemeral state, start the application using the documented Docker workflow. The stack should boot without startup errors or stale-mount surprises, and a primary operator check such as loading the API service or running a quick config-facing verification command should succeed with live repository state.
result: pass

### 2. Scaffold Registry Surface
expected: Inspecting the config-backed panel registry should show all remaining top-level panels present but still non-runnable. Each scaffold-only panel should expose explicit factor ownership, and each should have exactly one disabled placeholder lead instead of a deeper hardcoded agent tree.
result: pass

### 3. Scaffold Prompt Specificity
expected: Opening the scaffold prompt and factor assets should show panel-specific memo sections, factor coverage, evidence expectations, and non-generic factor descriptions. The placeholder assets should read like intentional scaffolds, not generic filler text.
result: pass

### 4. CLI Scaffold Rejection
expected: Running a CLI workflow that targets `full_surface` or an explicit scaffold-only panel should fail fast with a clear not-implemented message. The command should reject the request before creating or partially advancing a run.
result: pass

### 5. API Scaffold Rejection
expected: Hitting the matching API path with `full_surface` or an explicit scaffold-only panel should return the same stable invalid-request style error story rather than a traceback or partial success. No run should be persisted when execution is rejected.
result: pass

### 6. Extension Path Documentation
expected: The repo docs should consistently explain that only `gatekeepers` and `demand_revenue_quality` are implemented today, that the remaining panels are config-visible but non-runnable, and that a clear file-by-file extension path exists for future productionization.
result: [pending]

## Summary

total: 6
passed: 5
issues: 0
pending: 1
skipped: 0

## Gaps

none yet
