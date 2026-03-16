# AI Investing

AI Investing is a config-driven multi-agent investment research platform for public and private company analysis. The shipped runtime persists structured evidence, factor-level claims, panel verdicts, memo section updates, and rerun deltas so weekly refreshes remain inspectable instead of collapsing into one terminal report.

## What The Runtime Produces

- factor-level claim cards
- panel-level verdicts
- a living IC memo
- rerun deltas against the prior active memo
- queue, review, and notification records for recurring operations

The memo remains a living artifact. Its required sections are:

- `investment_snapshot`
- `what_changed_since_last_run`
- `risk`
- `durability_resilience`
- `growth`
- `economic_spread`
- `valuation_terms`
- `expectations_variant_view`
- `realization_path_catalysts`
- `portfolio_fit_positioning`
- `overall_recommendation`

## Implemented Panel Surface

All top-level panels in the configured surface are now productionized and runnable through the shared runtime:

- `gatekeepers`
- `demand_revenue_quality`
- `supply_product_operations`
- `market_structure_growth`
- `macro_industry_transmission`
- `management_governance_capital_allocation`
- `financial_quality_liquidity_economic_model`
- `external_regulatory_geopolitical`
- `expectations_catalyst_realization`
- `security_or_deal_overlay`
- `portfolio_fit_positioning`

That does not mean every run executes every panel. Panel selection is still policy-driven and support-aware.

## Run Policies

The runtime keeps rollout and operator defaults config-driven in `config/run_policies.yaml`.

- `weekly_default`: narrow operator default for recurring coverage. Runs `gatekeepers` and `demand_revenue_quality`.
- `internal_company_quality`: adds `supply_product_operations`, `management_governance_capital_allocation`, and `financial_quality_liquidity_economic_model`.
- `external_company_quality`: adds `market_structure_growth`, `macro_industry_transmission`, and `external_regulatory_geopolitical`.
- `expectations_rollout`: adds `expectations_catalyst_realization`.
- `full_surface`: adds the overlay family, `security_or_deal_overlay` and `portfolio_fit_positioning`.

`weekly_default` intentionally stays narrower than `full_surface`. The repository ships the full productionized panel surface, but operators still choose how wide a given run should be.

## Support Contract

Every selected panel passes through the same support check before execution. The panel config declares:

- required evidence families by company type
- minimum factor coverage ratio
- minimum evidence count
- required context, when applicable
- whether weak confidence is allowed

The support outcome is explicit and persisted in run metadata:

- `supported`: the panel ran with its normal posture
- `weak_confidence`: the panel still ran, but the runtime calls out thin support directly in the panel support metadata and affected memo section text
- `unsupported`: the panel is skipped explicitly and the run continues

The runtime does not silently drop unsupported panels and it does not fail the whole run only because one later panel lacks support.

## Weak Confidence Versus Skip

Most company-quality panels can run with `weak_confidence` when evidence is present but thinner than the normal readiness bar. That preserves analytical continuity while keeping the confidence posture honest.

Some panels do not allow that fallback:

- `expectations_catalyst_realization` requires expectations-specific evidence such as consensus or milestone tracking
- `security_or_deal_overlay` requires overlay-specific context
- `portfolio_fit_positioning` requires portfolio context

When those requirements are missing, the runtime records an explicit skip instead of fabricating a conclusion.

## Analytical Separation

The runtime preserves the analytical boundary that the project requires:

- company quality lives in `demand_revenue_quality`, `supply_product_operations`, `market_structure_growth`, `macro_industry_transmission`, `management_governance_capital_allocation`, `financial_quality_liquidity_economic_model`, and `external_regulatory_geopolitical`
- expectations and catalysts live in `expectations_catalyst_realization`
- security quality or deal framing lives in `security_or_deal_overlay`
- portfolio fit lives in `portfolio_fit_positioning`

Those families remain separate in config, prompts, memo ownership, generated artifacts, CLI/API read surfaces, and docs. `security_or_deal_overlay` is not merged into company quality, and `portfolio_fit_positioning` is not treated as a generic extension of the company memo.

## Overall Recommendation Scope

`overall_recommendation` is truthful about what actually ran.

- If a run stops at company-quality and expectations policies, the memo calls out that the overlays are pending for that rollout.
- If `full_surface` is selected but overlay context is missing, the memo and interface surfaces call out that the relevant overlays were unsupported for this run.
- If both overlays run successfully, the recommendation scope is `overlay_complete`.

A partial recommendation therefore still has value, but it should be read as company-quality-only or company-quality-plus-expectations guidance until the overlays are either run or explicitly deemed unsupported.

## Quick Start

Docker is the primary local workflow. The host path is supported only when Python 3.11+ is available.

```bash
docker compose up --build -d
docker compose exec api ai-investing init-db
docker compose exec api ai-investing ingest-public-data /app/examples/acme_public
docker compose exec api ai-investing add-coverage ACME "Acme Cloud" public watchlist
docker compose exec api ai-investing set-coverage-schedule ACME --schedule-policy-id weekdays
docker compose exec api ai-investing analyze-company ACME
docker compose exec api ai-investing show-run <run_id>
docker compose exec api ai-investing generate-memo ACME
docker compose exec api ai-investing show-delta ACME
```

To run a broader surface, update the coverage policy or submit a refresh through the API or CLI with the relevant policy configured on the company.

## Production Setup

Follow these steps to go from test mode (fake provider, no API keys) to a production deployment with real LLM providers.

### 1. Choose a Provider

| Provider | Env Value | Models | Optional Install |
|----------|-----------|--------|------------------|
| OpenAI | `openai` | gpt-4o, gpt-4o-mini | — (included) |
| Anthropic | `anthropic` | claude-opus-4-20250514, claude-sonnet-4-20250514 | — (included) |
| Google Gemini | `google` | gemini-2.5-pro, gemini-2.5-flash | `pip install ai-investing[google]` |
| Groq | `groq` | llama-3.3-70b-versatile, mixtral-8x7b-32768 | `pip install ai-investing[groq]` |
| OpenAI-compatible | `openai_compatible` | Any model via custom endpoint | — (included) |

The runtime supports provider chains with automatic fallback. Set `AI_INVESTING_PROVIDER=auto` (or omit it) to use the chain defined in `config/model_profiles.yaml`. Set it to a specific provider name to restrict to that provider only.

### 2. Create API Keys

**OpenAI**

1. Create an account at [platform.openai.com/signup](https://platform.openai.com/signup)
2. Navigate to **API Keys** → **Create new secret key** at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. Copy the key and set `OPENAI_API_KEY=sk-...`

**Anthropic**

1. Create an account at [console.anthropic.com](https://console.anthropic.com)
2. Navigate to **API Keys** → **Create Key** at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
3. Copy the key and set `ANTHROPIC_API_KEY=sk-ant-...`

**Google Gemini**

1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the **Generative Language API** at [console.cloud.google.com/apis/library](https://console.cloud.google.com/apis/library)
3. Create an API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
4. Copy the key and set `GOOGLE_API_KEY=AI...`

**Groq**

1. Create an account at [console.groq.com](https://console.groq.com)
2. Navigate to **API Keys** → **Create API Key** at [console.groq.com/keys](https://console.groq.com/keys)
3. Copy the key and set `GROQ_API_KEY=gsk_...`

**OpenAI-Compatible Endpoint** (Together, Fireworks, Ollama, vLLM, etc.)

1. Set `OPENAI_COMPATIBLE_BASE_URL` to the endpoint URL (e.g., `https://api.together.xyz/v1`)
2. Set `OPENAI_COMPATIBLE_API_KEY` to the endpoint's API key
3. Update the model name in `config/model_profiles.yaml` to match the endpoint's model

### 3. Configure Environment

Create a `.env` file (see `.env.example` for reference):

```bash
# Provider selection
AI_INVESTING_PROVIDER=openai        # or anthropic, google, groq, openai_compatible, auto

# Provider API keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Logging
AI_INVESTING_LOG_LEVEL=INFO         # DEBUG, INFO, WARNING, ERROR
```

Model names and provider chain order are configured in `config/model_profiles.yaml`. Each profile tier (balanced, quality, budget) has its own provider chain with automatic fallback.

### 4. Set Up API Authentication

Configure API key authentication with role-based access:

```bash
AI_INVESTING_AUTH_ENABLED=true
AI_INVESTING_API_KEYS=sk-prod-abc:operator,sk-reader-xyz:readonly
```

Key format: `key:role` pairs, comma-separated. Supported roles:

- **operator** — full read/write access including provisional continuation, worker control, and notification dispatch
- **readonly** — read-only access to runs, memos, deltas, and coverage data

When `AI_INVESTING_AUTH_ENABLED=false` (or no keys configured), all endpoints are accessible without authentication.

### 5. Configure Database

For production, use a dedicated Postgres instance:

```bash
AI_INVESTING_DATABASE_URL=postgresql+psycopg://user:password@host:5432/ai_investing
```

The production profile refuses to start with the default `postgres:postgres` credentials when `AI_INVESTING_AUTH_ENABLED=true`.

### 6. Deploy

```bash
# Production deployment
docker compose --profile prod up --build -d

# Run database migrations
docker compose exec api-prod ai-investing init-db

# Verify the service is running
curl http://localhost:8000/health    # 200 = alive
curl http://localhost:8000/ready     # 200 = DB connected, 503 = DB unreachable
```

Required environment variables for the production profile:

- `AI_INVESTING_DATABASE_URL` — production Postgres connection string
- `AI_INVESTING_AUTH_ENABLED=true` — enables API key authentication
- `AI_INVESTING_API_KEYS` — at least one operator-role key
- At least one provider API key (e.g., `OPENAI_API_KEY`)

### 7. Configure Cost Controls

Set a per-run token budget to prevent runaway LLM costs:

```bash
AI_INVESTING_MAX_TOKENS_PER_RUN=100000   # abort analysis if token usage exceeds this
```

When the budget is exceeded mid-run, the system aborts gracefully, records the reason, and reports it in the run result. Token usage (input tokens, output tokens, estimated cost) is included in every run result payload via the API and CLI.

## Test vs Production

The runtime toggles between test and production modes entirely through environment variables:

```bash
# Test (default — no API keys needed)
AI_INVESTING_PROVIDER=fake
AI_INVESTING_AUTH_ENABLED=false
AI_INVESTING_LOG_LEVEL=INFO
# No provider API keys required
# Uses default in-memory or dev Postgres

# Production
AI_INVESTING_PROVIDER=openai            # or anthropic, google, groq, openai_compatible, auto
AI_INVESTING_AUTH_ENABLED=true
AI_INVESTING_API_KEYS=sk-prod-abc:operator,sk-reader-xyz:readonly
AI_INVESTING_DATABASE_URL=postgresql+psycopg://user:password@host:5432/ai_investing
AI_INVESTING_LOG_LEVEL=INFO
AI_INVESTING_MAX_TOKENS_PER_RUN=100000  # optional cost cap
# Plus provider API keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.
```

**Fake fallback behavior:** When `AI_INVESTING_ALLOW_FAKE_FALLBACK=true` (the default), the system falls back to the fake provider if no real provider is available. Set to `false` in production to ensure real LLM calls are always made — the system will error instead of silently falling back.

**Docker profiles:**

- `docker compose up` — starts the dev stack (fake provider, dev deps, test data accessible)
- `docker compose --profile prod up` — starts the production stack (no dev deps, no test data, enforces non-default credentials)

**CORS:** Set `AI_INVESTING_DOMAIN=https://dashboard.example.com` to allow cross-origin requests from a specific frontend. Defaults to denying all cross-origin requests when empty.

## Queue And Notification Operations

Recurring operations are queue-backed and remain outside the reasoning core.

- `enqueue-watchlist`, `enqueue-portfolio`, and `enqueue-due-coverage` submit work
- `run-worker` executes bounded queue work through the same service-owned runtime
- failed gatekeepers become review-queue items
- external automation claims and dispatches notification events instead of inferring them from memo text

The checkpoint policy is also explicit:

- every run enters `gatekeepers`
- `pass` and `review` auto-continue
- `fail` stops for review and only an operator can choose provisional continuation

## Generated Artifacts

Checked artifacts under `examples/generated/` document the shipped runtime contract.

- `ACME/initial`: initial lifecycle output for the configured policy
- `ACME/continued`: persisted reread of the same completed run
- `ACME/rerun`: rerun with delta output against the prior active memo
- `ACME/overlay_gap`: `full_surface` output where company-quality work still completes but overlay context is unsupported and skipped explicitly

These artifacts are generated by `scripts/generate_phase2_examples.py` and locked by `tests/test_generated_examples.py`.

## Repo Layout

See [docs/architecture.md](docs/architecture.md), [docs/factor_ontology.md](docs/factor_ontology.md), [docs/memory_model.md](docs/memory_model.md), and [docs/runbook.md](docs/runbook.md).

## Milestone Status

v2.0 productionization is complete. See [.planning/v2.0-CLOSEOUT.md](.planning/v2.0-CLOSEOUT.md) for a full summary of what was delivered across all phases.
