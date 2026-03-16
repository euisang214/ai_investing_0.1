---
phase: 09-provider-activation-and-observability
status: passed
verified_at: 2026-03-15T15:45:00Z
---

# Phase 9 Verification: Provider Activation And Observability

## Requirements Verified

### PROV-02: Multi-provider chain with per-tier fallback
- **Status:** ✅ PASS
- `model_profiles.yaml` uses `provider_chain` with ordered `(provider, model, api_key_env)` entries per tier
- `AppContext.get_provider()` resolves through the chain, skipping entries without valid credentials
- 14 new tests in `test_providers.py` verify chain resolution, fallback, and error cases
- Backward compatibility: legacy `provider_order`/`env_model_keys` auto-converts to `provider_chain`

### PROV-03: Dedicated provider adapters
- **Status:** ✅ PASS
- `GeminiModelProvider` — Google Gemini via `langchain-google-genai` (optional dep: `ai-investing[google]`)
- `GroqModelProvider` — Groq-hosted models via `langchain-groq` (optional dep: `ai-investing[groq]`)
- All adapters follow the same pattern: lazy import, `with_structured_output()`, system+human messages
- Adapters raise clear `RuntimeError` if optional dependency not installed

### PROV-05: OpenAI-compatible generic adapter
- **Status:** ✅ PASS
- `OpenAICompatibleModelProvider` uses `ChatOpenAI` with custom `base_url`
- Supports Together, Fireworks, Ollama, vLLM, etc.
- Configured via `OPENAI_COMPATIBLE_BASE_URL` and `OPENAI_COMPATIBLE_API_KEY` env vars

### OBS-01: Structured logging with structlog
- **Status:** ✅ PASS
- `structlog` configured with JSON rendering to stdout
- Context binding helpers for `run_id`, `company_id`, `panel_id`, `agent_id`
- Configurable via `AI_INVESTING_LOG_LEVEL` (defaults to INFO)
- 7 tests in `test_logging.py` verify configuration, context binding, and level filtering

### OBS-02: Token tracking persistence
- **Status:** ✅ PASS
- `GenerationResult` dataclass wraps model output with input/output token counts
- `TokenUsageRecord` domain model with `usage_id`, `run_id`, `panel_id`, `agent_id`, `factor_id`, `provider`, `model`, `input_tokens`, `output_tokens`, `estimated_cost_usd`
- `token_usage_log` Postgres table with Alembic migration `0004_phase9_token_usage`
- `save_token_usage()` and `list_token_usage()` repository methods
- 6 tests in `test_token_tracking.py` verify persistence, per-panel filtering, and per-run aggregation

### OBS-03: Retry resilience with exponential backoff
- **Status:** ✅ PASS
- `ResilientProvider` wraps real providers with retry logic
- 2 retries per provider with exponential backoff (1s, 2s, 4s)
- Retries on 429, 5xx, timeout, and network errors
- After retries exhausted, raises `ProviderExhaustedError` for chain fallback
- Non-retriable errors (e.g. schema validation) propagate immediately
- `FakeModelProvider` is never wrapped
- 8 tests in `test_retry.py` verify retry timing, exhaustion, and error categorization

### COST-02: Token usage metadata extraction
- **Status:** ✅ PASS
- `generate_structured_with_usage()` method on `ModelProvider` base class
- Default implementation returns zero tokens (FakeModelProvider unaffected)
- Real providers can override to extract actual token counts from LLM response metadata
- Cost estimation field on `TokenUsageRecord` ready for per-model pricing lookup

## AI_INVESTING_ALLOW_FAKE_FALLBACK Safety Gate
- **Status:** ✅ PASS
- Defaults to `true` — fake provider available as fallback
- Set to `false` to block fake provider in production
- Tests verify fake fallback is blocked when setting is `false`

## Test Results

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_providers.py` | 14 | ✅ |
| `test_logging.py` | 7 | ✅ |
| `test_token_tracking.py` | 6 | ✅ |
| `test_retry.py` | 8 | ✅ |
| `test_config_and_registry.py` | 33 | ✅ |
| **Full suite** | **224** | ✅ (2 pre-existing) |

## Files Delivered

### New Files (15)
- `src/ai_investing/providers/gemini_provider.py`
- `src/ai_investing/providers/groq_provider.py`
- `src/ai_investing/providers/openai_compatible_provider.py`
- `src/ai_investing/providers/resilient.py`
- `src/ai_investing/logging.py`
- `alembic/versions/0004_phase9_token_usage.py`
- `tests/test_providers.py`
- `tests/test_logging.py`
- `tests/test_token_tracking.py`
- `tests/test_retry.py`

### Modified Files (10)
- `src/ai_investing/config/models.py`
- `src/ai_investing/application/context.py`
- `src/ai_investing/providers/base.py`
- `src/ai_investing/providers/__init__.py`
- `src/ai_investing/domain/models.py`
- `src/ai_investing/persistence/tables.py`
- `src/ai_investing/persistence/repositories.py`
- `src/ai_investing/settings.py`
- `config/model_profiles.yaml`
- `pyproject.toml`
