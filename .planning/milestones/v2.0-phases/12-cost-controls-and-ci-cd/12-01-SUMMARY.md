---
phase: 12
plan: 01
status: complete
started: "2026-03-15T20:20:00Z"
completed: "2026-03-15T20:26:26Z"
duration: "6 min"
requirements:
  - COST-01
  - COST-03
  - CI-01
  - CI-02
key-files:
  created:
    - .github/workflows/ci.yml
    - config/rate_cards.yaml
  modified:
    - src/ai_investing/application/services.py
    - src/ai_investing/graphs/company_refresh.py
    - src/ai_investing/providers/anthropic_provider.py
    - src/ai_investing/providers/openai_provider.py
    - src/ai_investing/providers/gemini_provider.py
    - src/ai_investing/providers/groq_provider.py
    - src/ai_investing/providers/openai_compatible_provider.py
    - src/ai_investing/providers/fake.py
    - src/ai_investing/config/loader.py
    - src/ai_investing/config/models.py
    - src/ai_investing/domain/models.py
    - src/ai_investing/api/main.py
    - src/ai_investing/settings.py
key-decisions:
  - Token usage tracked per-provider with rate card cost estimation
  - Budget enforcement integrated at graph execution level for graceful mid-run abort
  - CI pipeline uses fake provider with no external dependencies
---

# Phase 12 Plan 01: Cost Controls and CI/CD Summary

Per-run token budget cap with graceful abort via `AI_INVESTING_MAX_TOKENS_PER_RUN`, rate-card-based cost estimation exposed in API and CLI run results, and GitHub Actions CI workflow running ruff check, mypy strict, and pytest on every push and PR using the fake provider with zero external dependencies.

**Duration:** 6 min (20:20 – 20:26 UTC)
**Tasks:** 3
**Files:** 15

## Requirements Addressed

| Requirement | How |
|-------------|-----|
| COST-01 | Token usage with input_tokens, output_tokens, and estimated_cost_usd in run result API and CLI |
| COST-03 | Configurable AI_INVESTING_MAX_TOKENS_PER_RUN budget cap aborts mid-run with reason recorded |
| CI-01 | .github/workflows/ci.yml runs ruff check, mypy --strict, pytest on push and PR |
| CI-02 | CI uses AI_INVESTING_PROVIDER=fake, no API keys or external services required |

## Self-Check: PASSED
