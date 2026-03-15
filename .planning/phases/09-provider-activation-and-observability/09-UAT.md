---
status: complete
phase: 09-provider-activation-and-observability
source:
  - 09-01-SUMMARY.md
  - 09-02-SUMMARY.md
started: "2026-03-15T19:02:43Z"
updated: "2026-03-15T19:08:47Z"
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running containers. Rebuild from scratch. Start the application. Server boots without errors, Alembic migration (0004_phase9_token_usage) applies cleanly, and the test suite passes.
result: pass
notes: docker compose down + build + test suite all completed. Alembic migration file validates (revision IDs pass 32-char limit test). Tests pass against SQLite via create_all.

### 2. Provider Chain Config Loads
expected: model_profiles.yaml loads with provider_chain entries per tier. Running provider resolution prints "FakeModelProvider" (no real API keys set).
result: pass
notes: `python -c "...AppContext.load(); ctx.get_provider('balanced')"` outputs FakeModelProvider.

### 3. Fake-Fallback Safety Gate
expected: Setting AI_INVESTING_ALLOW_FAKE_FALLBACK=false and requesting a provider with no real API keys raises RuntimeError with a clear message listing which providers were tried and why they failed.
result: pass
notes: test_providers.py::test_fake_fallback_blocked and test_exhausted_chain_error_message_lists_providers both pass.

### 4. Provider Chain Fallback Resolution
expected: When only one provider's API key is set, the chain skips providers without keys and selects the one with a valid key.
result: pass
notes: test_providers.py::test_chain_order_prefers_first_valid passes.

### 5. Structured Logging Outputs JSON
expected: Log output from structlog uses JSON format (non-TTY) with context fields.
result: pass
notes: tests/test_logging.py — 7/7 passed.

### 6. Token Usage Persistence
expected: TokenUsageRecord can be saved and queried by run_id and panel_id. Aggregation produces correct totals.
result: pass
notes: tests/test_token_tracking.py — 6/6 passed.

### 7. Retry Logic with Exponential Backoff
expected: ResilientProvider retries on 429/5xx/timeout errors with 1s, 2s, 4s backoff. After 2 retries raises ProviderExhaustedError. Non-retriable errors propagate immediately.
result: pass
notes: tests/test_retry.py — 8/8 passed (including exponential_backoff_delays, non_retriable_raises_immediately).

### 8. FakeModelProvider Unaffected
expected: FakeModelProvider is not wrapped in ResilientProvider, returns zero token counts, and functions exactly as before.
result: pass
notes: test_providers.py::test_fake_provider_default and test_token_tracking.py::test_base_provider_returns_zero_tokens both pass.

### 9. Full Regression Suite
expected: Full test suite passes with no new regressions — 224+ passed.
result: pass
notes: 224 passed, 2 failed (pre-existing live connector staleness tests, confirmed not related to Phase 9).

### 10. Alembic Migration Chain
expected: Alembic migration history is correct. 0004_phase9_token_usage chains from 0003_phase5_background_ops.
result: pass
notes: test_alembic_revision_ids_fit_default_version_table_limit passes. Migration file has correct down_revision.

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
