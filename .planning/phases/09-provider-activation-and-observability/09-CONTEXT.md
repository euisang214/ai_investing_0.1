# Phase 9: Provider Activation And Observability - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire real LLM providers into the runtime with env-driven toggling, multi-provider extensibility, structured logging, token tracking, and retry resilience. The runtime must support OpenAI, Anthropic, Google Gemini, Groq, and any OpenAI-compatible endpoint through a pluggable adapter pattern. Existing test behavior (fake provider) must remain unchanged.

</domain>

<decisions>
## Implementation Decisions

### Provider Architecture
- Each model profile tier (quality, balanced, budget) has its own ordered **provider chain** — a list of `(provider, model)` pairs
- If the primary provider+model fails after retries, the system falls to the next provider+model in the chain
- The `fake` provider is never used as a fallback in production — controlled by `AI_INVESTING_ALLOW_FAKE_FALLBACK` (default `false` in prod, `true` in test)
- If all real providers in the chain are exhausted, the run aborts and reports the error

### Provider Chain Configuration
- Config lives in `model_profiles.yaml` with a new `provider_chain` structure per tier
- Example shape:
  ```yaml
  quality:
    provider_chain:
      - provider: anthropic
        model: claude-opus-4-20250514
      - provider: openai
        model: gpt-4o
      - provider: fake
    temperature: 0.1
    max_tokens: 2400
  ```
- Each entry specifies both the provider AND the specific model, so operators can choose Claude Opus vs Claude Sonnet, GPT-4o vs GPT-4o-mini, etc.

### Provider Adapters
- **Dedicated adapters** for: OpenAI, Anthropic, Google Gemini, Groq — each with their own LangChain binding and proper structured output / token counting
- **Generic `openai_compatible` adapter** for any OpenAI-compatible endpoint (Together, Fireworks, Ollama, vLLM, etc.)
- One `OPENAI_COMPATIBLE_BASE_URL` env var shared across tiers; per-tier model selection via the `model` field in `provider_chain`
- Optional dependency installs: `ai-investing[openai]`, `ai-investing[anthropic]`, `ai-investing[google]`, `ai-investing[groq]`

### Logging
- Use **structlog** for structured JSON logging
- Output to **stdout only** (standard for Docker/container deployments)
- Log levels:
  - ERROR: LLM call failures, DB connection errors, unhandled exceptions
  - WARNING: Rate limit retries, stale evidence detected, fallback provider used
  - INFO: Run started/completed, panel completed, memo updated, provider selected
  - DEBUG: Full prompt text, raw LLM response, evidence selection details
- Default production level: INFO
- Configurable via `AI_INVESTING_LOG_LEVEL` environment variable

### Token Tracking
- Track at **per-agent granularity** — every individual LLM call gets a row
- Automatic roll-ups to per-panel and per-run totals (computed on read by summing)
- Stored in a new `token_usage_log` Postgres table (Alembic migration)
- Each row contains: `run_id`, `panel_id`, `agent_id`, `factor_id`, `provider`, `model`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `timestamp`
- Panel totals = SUM WHERE panel_id, run totals = SUM WHERE run_id

### Retry and Resilience
- Retry on: 429 (rate limit), 5xx (server error), timeout, network errors
- Exponential backoff: 1s → 2s → 4s between retries
- **2 retries** per provider (3 total attempts per provider in the chain)
- After retries exhausted, fall to next provider+model in the chain
- Never fall to `fake` in production (gated by `AI_INVESTING_ALLOW_FAKE_FALLBACK`)
- If all real providers in the chain fail, the run aborts with a clear error message

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ModelProvider` ABC in `src/ai_investing/providers/base.py` — single `generate_structured()` method, already the right interface
- `FakeModelProvider` in `providers/fake.py` — 400-line deterministic provider, stays unchanged
- `OpenAIModelProvider` and `AnthropicModelProvider` — thin wrappers already exist but need retry logic and token extraction
- `AppContext.get_provider()` — current provider resolution logic; needs refactoring to support per-tier chains
- Optional dependency pattern in `pyproject.toml` — already has `[openai]` and `[anthropic]` extras

### Established Patterns
- Settings via `pydantic-settings` with `AI_INVESTING_` prefix — new env vars follow this pattern
- Config-driven everything: `model_profiles.yaml`, `panels.yaml`, `factors.yaml` — provider chain config fits naturally
- `StructuredGenerationRequest` dataclass carries prompt + input data to providers — all providers use this contract

### Integration Points
- `AppContext.get_provider(profile_name)` is the single point where provider instances are created — refactor here
- `RefreshRuntime._run_specialists()` and `._run_judge()` call `provider.generate_structured()` — token tracking hooks go here or in the provider itself
- `model_profiles.yaml` config is loaded in `AppContext.__init__()` — schema change needed for provider_chain
- Alembic migrations in `alembic/versions/` — new migration for `token_usage_log` table

</code_context>

<specifics>
## Specific Ideas

- The `provider_chain` config explicitly pairs provider+model so operators can mix Claude Opus for quality work and Claude Sonnet for budget work within the same provider
- `AI_INVESTING_ALLOW_FAKE_FALLBACK=false` is the production safety net — prevents accidental deterministic output in real analysis
- Token cost estimation should use a provider-specific cost table (GPT-4o input/output rates differ from Claude rates)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-provider-activation-and-observability*
*Context gathered: 2026-03-15*
