---
status: complete
phase: 01-foundation-and-contracts
source:
  - .planning/phases/01-foundation-and-contracts/01-01-SUMMARY.md
  - .planning/phases/01-foundation-and-contracts/01-02-SUMMARY.md
  - .planning/phases/01-foundation-and-contracts/01-03-SUMMARY.md
  - .planning/phases/01-foundation-and-contracts/01-04-SUMMARY.md
started: 2026-03-10T11:46:39Z
updated: 2026-03-10T12:09:21Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: From a fully stopped stack, bringing the app up with the documented Docker workflow should finish without startup crashes or duplicate-table/init errors. The `api` container should stay running, `ai-investing init-db` should succeed, and a primary check such as `GET /coverage` should return live JSON instead of a boot failure.
result: pass

### 2. Public Sample Ingestion
expected: Running the documented public ingest flow for `examples/acme_public` should succeed without manifest lookup problems. The system should accept the sample bundle, and the ingested company id should remain consistent with the manifest rather than silently drifting.
result: pass

### 3. Coverage Lifecycle via CLI
expected: Using a throwaway coverage id such as `UAT_COVERAGE_20260310`, the CLI coverage flow should work end to end: add coverage, list it, set `next_run_at`, disable it, and remove it. Each command should return structured JSON with the expected `company_id`, `enabled`, or normalized `next_run_at` values without disturbing the existing `ACME` sample coverage.
result: pass

### 4. Operator API Responses
expected: The HTTP operator endpoints should behave consistently: successful coverage and agent-management actions return a `{data: ...}` envelope, and requesting a missing company resource returns a `{error: {code, message}}` response instead of a raw traceback or ad-hoc shape.
result: pass

### 5. Agent Reparenting
expected: Listing agents and reparenting `demand_skeptic` under `gatekeeper_advocate` should succeed through the supported surface you choose. The change should be acknowledged explicitly with the new `parent_id`, not ignored silently.
result: pass

### 6. Analyze, Memo, and Delta Flow
expected: After sample data is ingested and coverage exists for `ACME`, running the analysis or refresh flow should complete without orchestration crashes. Generating the memo and delta afterward should produce live output for the covered company rather than failing because of memo or monitoring execution.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

none yet
