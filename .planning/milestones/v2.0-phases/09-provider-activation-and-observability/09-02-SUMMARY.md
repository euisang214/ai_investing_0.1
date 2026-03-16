---
phase: 09-provider-activation-and-observability
plan: 02
status: complete
started: 2026-03-15T15:10:00Z
completed: 2026-03-15T15:45:00Z
---

## Summary

Added structured logging via structlog, per-agent token usage tracking with Postgres persistence, and retry resilience with exponential backoff. The `ResilientProvider` wrapper retries on transient errors (429, 5xx, timeout, network) with 2 retries per provider before falling to the next entry in the chain.

## Key Changes

### Structured Logging
- `structlog` added as a core dependency
- `src/ai_investing/logging.py` — `configure_logging()`, `get_logger()`, context binding helpers
- JSON rendering to stdout (console renderer when TTY detected)
- Context variables: `run_id`, `company_id`, `panel_id`, `agent_id`

### Token Tracking
- `GenerationResult` dataclass in `providers/base.py` — wraps model output with input/output token counts
- `generate_structured_with_usage()` method on `ModelProvider` — default returns zero tokens (FakeModelProvider unaffected)
- `TokenUsageRecord` domain model and `TokenUsageRow` table
- Alembic migration `0004_phase9_token_usage`
- `save_token_usage()` and `list_token_usage()` repository methods

### Retry Resilience
- `ResilientProvider` wrapper in `providers/resilient.py`
- Retry on 429, 5xx, timeout, network errors with exponential backoff (1s, 2s, 4s)
- 2 retries per provider, then `ProviderExhaustedError` for chain fallback
- Real providers wrapped automatically; `FakeModelProvider` is never wrapped

## Self-Check: PASSED

- [x] structlog configured with JSON rendering and context binding
- [x] TokenUsageRecord persisted per-agent in token_usage_log table
- [x] Alembic migration created and revision ID fits 32-char limit
- [x] ResilientProvider retries on transient errors with correct backoff
- [x] ProviderExhaustedError enables chain fallback
- [x] FakeModelProvider unaffected (no retry, zero tokens)
- [x] 7 logging tests pass
- [x] 6 token tracking tests pass
- [x] 8 retry tests pass
- [x] Full suite: 224 passed

## key-files

### created
- `src/ai_investing/logging.py`
- `src/ai_investing/providers/resilient.py`
- `alembic/versions/0004_phase9_token_usage.py`
- `tests/test_logging.py`
- `tests/test_token_tracking.py`
- `tests/test_retry.py`

### modified
- `src/ai_investing/providers/base.py`
- `src/ai_investing/domain/models.py`
- `src/ai_investing/persistence/tables.py`
- `src/ai_investing/persistence/repositories.py`
- `src/ai_investing/application/context.py`
- `pyproject.toml`
