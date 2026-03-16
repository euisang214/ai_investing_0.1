---
phase: 09-provider-activation-and-observability
plan: 01
status: complete
started: 2026-03-15T14:35:00Z
completed: 2026-03-15T15:10:00Z
---

## Summary

Refactored the provider layer from flat `provider_order` config to a per-tier `provider_chain` with `(provider, model, api_key_env)` pairs. Implemented 5 provider adapters (OpenAI, Anthropic, Gemini, Groq, OpenAI-compatible) and refactored `AppContext.get_provider()` for chain resolution with fallback and fake-fallback safety gate.

## Key Changes

### Config Schema
- Added `ProviderChainEntry` model with `provider`, `model`, `api_key_env` fields
- Updated `ModelProfileConfig` with `provider_chain` list — backward-compatible with legacy `provider_order`/`env_model_keys` fields
- Added `allow_fake_fallback` and `log_level` to `Settings`

### Provider Adapters
- **GeminiModelProvider** — Google Gemini via `langchain-google-genai`
- **GroqModelProvider** — Groq-hosted models via `langchain-groq`
- **OpenAICompatibleModelProvider** — any OpenAI-compatible endpoint via custom `base_url`
- Optional dependency groups: `ai-investing[google]`, `ai-investing[groq]`

### Provider Resolution
- `get_provider()` iterates `provider_chain` entries, checks API key availability, skips unavailable providers
- `AI_INVESTING_ALLOW_FAKE_FALLBACK` gates fake provider fallback in production
- `AI_INVESTING_PROVIDER` setting filters to a specific provider when not set to `auto`
- Clear error messages listing which providers were tried and why they failed

## Self-Check: PASSED

- [x] Config schema supports provider_chain with backward compatibility
- [x] 5 provider adapters implemented and importable
- [x] Provider chain resolution with fallback works
- [x] Fake-fallback gating works
- [x] All 33 existing config tests pass
- [x] 14 new provider tests pass
- [x] model_profiles.yaml migrated to provider_chain format

## key-files

### created
- `src/ai_investing/providers/gemini_provider.py`
- `src/ai_investing/providers/groq_provider.py`
- `src/ai_investing/providers/openai_compatible_provider.py`
- `tests/test_providers.py`

### modified
- `src/ai_investing/config/models.py`
- `src/ai_investing/application/context.py`
- `src/ai_investing/settings.py`
- `config/model_profiles.yaml`
- `.env.example`
- `pyproject.toml`
- `src/ai_investing/providers/__init__.py`
- `tests/test_config_and_registry.py`
