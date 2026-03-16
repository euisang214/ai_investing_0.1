# Roadmap: AI Investing

**Created:** 2026-03-08
**Granularity:** standard
**Execution:** parallel where dependencies allow

## Overview

Milestone v2.0 takes the shipped dev-only runtime to production readiness. The phases progress from foundational plumbing (providers, secrets, logging) through security and deployment hardening, into cost controls and CI/CD, and finish with comprehensive operator documentation.

## Phases

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 9 | Provider Activation And Observability | Wire real LLM providers with env-driven toggling, multi-provider extensibility, structured logging, and token tracking | PROV-02, PROV-03, PROV-05, OBS-01, OBS-02, OBS-03, COST-02 | 6 |
| 10 | 1/1 | Complete    | 2026-03-15 | 4 |
| 11 | 1/1 | Complete    | 2026-03-15 | 5 |
| 12 | Cost Controls And CI/CD | Per-run token budgets, cost exposure in API/CLI, and GitHub Actions pipeline | COST-01, COST-03, CI-01, CI-02 | 4 |
| 13 | 1/1 | Complete   | 2026-03-16 | 3 |

## Phase Details

### Phase 9: Provider Activation And Observability

**Goal:** Make the runtime capable of using real LLMs with proper error handling and visibility into what it's doing.
**Status:** Not started

**Requirements:** `PROV-02`, `PROV-03`, `PROV-05`, `OBS-01`, `OBS-02`, `OBS-03`, `COST-02`

**Success criteria:**
1. Setting `AI_INVESTING_PROVIDER=openai` with valid `OPENAI_API_KEY` and model env vars produces real LLM-backed analysis output.
2. Setting `AI_INVESTING_PROVIDER=fake` (or omitting the var) still works identically to v1.0 with no API keys needed.
3. Missing API keys or model names for a non-fake provider produce a clear startup validation error, not a runtime crash.
4. Google Gemini and Groq providers are available via optional dependency installs (`ai-investing[google]`, `ai-investing[groq]`), and any OpenAI-compatible endpoint works via `AI_INVESTING_PROVIDER=openai_compatible` with a custom base URL.
5. All log output uses structured JSON format with `run_id`, `company_id`, and `panel_id` fields where applicable.
6. Each LLM invocation logs input/output token counts and persists per-run totals in run metadata.
7. LLM calls retry with exponential backoff on 429 and transient 5xx errors.

### Phase 10: API Security

**Goal:** Protect the API from unauthorized access and enforce operator-only restrictions on sensitive operations.
**Status:** Not started

**Requirements:** `SEC-01`, `SEC-02`, `SEC-03`

**Success criteria:**
1. All API endpoints return 401 when called without a valid `X-API-Key` header (unless auth is explicitly disabled for local dev).
2. A `AI_INVESTING_API_KEYS` environment variable configures accepted API keys with associated roles.
3. CORS is configurable via environment variable and defaults to denying cross-origin requests.
4. Provisional continuation, worker run, and notification dispatch endpoints require operator-role keys and return 403 for read-only keys.

### Phase 11: Deployment Hardening

**Goal:** Make the Docker setup production-worthy with proper image hygiene, health checks, and environment separation.
**Status:** Not started

**Requirements:** `DEPLOY-01`, `DEPLOY-02`, `DEPLOY-03`, `DEPLOY-04`

**Success criteria:**
1. A `Dockerfile.prod` (or multi-stage target) produces an image without dev deps, test fixtures, or example data.
2. `GET /health` returns 200 when the service is alive; `GET /ready` returns 200 only when the database is reachable.
3. `docker compose --profile dev` starts the dev stack (fake provider, test data, dev deps); `docker compose --profile prod` starts the production stack (real provider, no test data, strong DB credentials).
4. Production profile reads DB credentials from environment variables and refuses to start with the default `postgres:postgres`.
5. Alembic migrations run cleanly in both profiles.

### Phase 12: Cost Controls And CI/CD

**Goal:** Give operators visibility into LLM costs and ensure code quality is automatically validated.
**Status:** Not started

**Requirements:** `COST-01`, `COST-03`, `CI-01`, `CI-02`

**Success criteria:**
1. Run result payload (API and CLI) includes `token_usage` with `input_tokens`, `output_tokens`, and `estimated_cost_usd`.
2. A configurable `AI_INVESTING_MAX_TOKENS_PER_RUN` budget cap aborts analysis mid-run when exceeded, records the reason, and reports it in the run result.
3. `.github/workflows/ci.yml` runs `ruff check`, `mypy --strict`, and `pytest` on every push and pull request.
4. The CI pipeline uses `AI_INVESTING_PROVIDER=fake` and requires no external API keys or services.

### Phase 13: Operator Documentation And Closeout

**Goal:** Create clear, actionable documentation so an operator can take the system from git clone to production without hidden knowledge.
**Status:** Not started

**Requirements:** `PROV-04`, `DOC-01`, `DOC-02`

**Success criteria:**
1. README includes a "Production Setup" section with numbered steps for creating API keys, configuring secrets, and deploying.
2. README includes a "Test vs Production" section showing the exact env var changes to toggle between fake and real providers.
3. All manual operator steps (account creation, key generation, secrets storage) are documented with links to vendor dashboards.

---
*Last updated: 2026-03-15 after v2.0 milestone start*
