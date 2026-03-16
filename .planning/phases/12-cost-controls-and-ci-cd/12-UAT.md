---
status: complete
phase: 12-cost-controls-and-ci-cd
source: [12-01-PLAN.md]
started: 2026-03-15T20:27:42-04:00
updated: 2026-03-15T20:29:05-04:00
---

## Current Test

[testing complete]

## Tests

### 1. TokenUsage Model Exists
expected: `TokenUsage` class exists in `domain/models.py` with fields `input_tokens`, `output_tokens`, `total_tokens`, and `estimated_cost_usd`, all defaulting to 0.
result: pass
verified: code inspection — `TokenUsage(DomainModel)` at line 43 with all four fields defaulting to 0.

### 2. RunResultResponseData Includes token_usage
expected: `RunResultResponseData` in `api/main.py` has a `token_usage: TokenUsage | None` field, so API responses include token cost data when available.
result: pass
verified: code inspection — line 150: `token_usage: TokenUsage | None = None`.

### 3. Settings Has max_tokens_per_run
expected: `Settings` in `settings.py` has `max_tokens_per_run: int | None = None`. Setting env var `AI_INVESTING_MAX_TOKENS_PER_RUN=5000` would cap token usage at 5000.
result: pass
verified: code inspection — line 22: `max_tokens_per_run: int | None = None` with `AI_INVESTING_` env prefix.

### 4. Rate Cards YAML Loaded at Startup
expected: `config/rate_cards.yaml` exists with model pricing entries and is loaded into the `RegistryBundle` via `RegistryLoader.load_all()`. Running the app with this config doesn't crash.
result: pass
verified: code inspection — `rate_cards.yaml` has 11 model entries. `RegistryLoader.load_all()` loads it at lines 78-80. `RegistryBundle` includes `rate_cards: RateCardsRegistry`.

### 5. FakeProvider generate_structured_with_usage Returns Tokens
expected: `FakeModelProvider.generate_structured_with_usage()` returns a `GenerationResult` with deterministic `input_tokens` and `output_tokens` based on prompt/output size, and `provider="fake"`.
result: pass
verified: code inspection — lines 85-100 return `GenerationResult` with deterministic token counts and `provider="fake"`, `model="fake/test-model"`.

### 6. RefreshRuntime Tracks Usage Across LLM Calls
expected: After each LLM call in `services.py`, `self.track_usage(res)` is called, incrementing `run.metadata["token_usage"]` with accumulated input/output/total tokens and estimated USD cost.
result: pass
verified: code inspection — `track_usage()` at line 351 accumulates tokens and applies rate cards. Called at 5 LLM call sites (lines 477, 691, 727, 774, 1229).

### 7. Budget Exceeded Aborts Gracefully
expected: When `AI_INVESTING_MAX_TOKENS_PER_RUN` is set and total tokens exceed the cap, `is_budget_exceeded()` returns True, sets `run.metadata["abort_reason"] = "budget_exceeded"`, and graph edges route to END instead of continuing to the next panel.
result: pass
verified: code inspection — `is_budget_exceeded()` at line 376 checks cap and sets abort_reason. `company_refresh.py` has 4 conditional edge checks (lines 55, 69, 83, 94) routing to END on budget exceeded.

### 8. CI Workflow File Structure
expected: `.github/workflows/ci.yml` exists with triggers on `push` to `main` and `pull_request` on all branches, uses `ubuntu-latest`, installs Python 3.11, runs `ruff check .`, `mypy --strict src tests`, and `pytest tests/ -v`, all with `AI_INVESTING_PROVIDER: fake`.
result: pass
verified: file inspection — all triggers, steps, and env vars present as specified.

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
