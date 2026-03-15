# Phase 11: Deployment Hardening - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the Docker setup production-worthy with proper image hygiene, health checks, and environment separation. The existing dev workflow (`docker compose run --rm api pytest`) must remain unchanged.

</domain>

<decisions>
## Implementation Decisions

### Production Dockerfile Strategy
- Multi-stage Dockerfile with three targets: `base`, `prod`, `dev`
- `base` stage: Python 3.11-slim, system deps (curl, build-essential), uv
- `prod` stage: extends base, copies only `src/`, `config/`, `prompts/`, `alembic/`, `alembic.ini`, `pyproject.toml`, `README.md`. Installs runtime deps only (`uv pip install --system .`)
- `dev` stage: extends base, copies everything (tests, examples, docs, n8n, scripts). Installs runtime + dev deps (`uv pip install --system -e ".[dev]"`)
- Prod excludes: `tests/`, `examples/`, `docs/`, `n8n/`, `scripts/`, dev dependencies
- `docker compose build` defaults to `dev` target for unchanged local workflow

### Health and Readiness Probes
- `GET /health` — trivial liveness check, returns `{"status": "ok"}` with 200, no dependencies
- `GET /ready` — DB ping only, returns `{"status": "ready", "checks": {"database": "ok"}}` with 200, or `{"status": "not_ready", "checks": {"database": "unreachable"}}` with 503
- Both endpoints skip API key authentication (infrastructure probes called by orchestrators, not humans)
- No config or provider checks in readiness — config errors crash on startup, provider checks are too slow/flaky

### Dev/Prod Profile Separation
- Single `docker-compose.yml` with Docker Compose profiles (`dev` / `prod`)
- Default (no profile flag) = `dev` behavior — unchanged existing workflow
- Dev profile: `target: dev`, volume mounts (hot reload), fake provider, `postgres:postgres`, auth disabled, `AI_INVESTING_ALLOW_FAKE_FALLBACK=true`, `log_level=DEBUG`
- Prod profile: `target: prod`, no volume mounts (baked image), real providers (`auto`), env var credentials, auth enabled, `AI_INVESTING_ALLOW_FAKE_FALLBACK=false`, `log_level=INFO`
- Data (IC memos, runs, evidence) lives in PostgreSQL volume (`postgres_data`) — survives all rebuilds

### Credential Safety in Production
- Belt and suspenders approach: Docker Compose AND app-level validation
- Prod profile in docker-compose.yml: no hardcoded `AI_INVESTING_DATABASE_URL` — must come from `.env` or host environment
- App startup check: if `auth_enabled=true` (prod mode signal) and database URL contains `postgres:postgres@`, refuse to start with clear error message
- Dev profile: keeps `postgres:postgres` hardcoded — zero friction for local dev
- `auth_enabled` used as prod mode proxy — no separate `AI_INVESTING_ENV` variable needed

### Claude's Discretion
- Exact health/ready endpoint implementation (sync vs async DB ping)
- Order of stages in Dockerfile
- Specific Docker Compose profile YAML structure
- Alembic migration execution in both profiles
- Test structure for health/ready endpoints

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Settings` class in `settings.py` — already has `auth_enabled`, `database_url`; startup check goes here or in `AppContext.load()`
- `Database` class — has session management, can add a `ping()` method for readiness
- `ApiKeyMiddleware` in `api/security.py` — health/ready endpoints need to bypass this
- `create_app()` in `api/main.py` — add health/ready routes here, exempt from auth

### Established Patterns
- Settings via `pydantic-settings` with `AI_INVESTING_` env prefix
- Error responses use `_error_response()` helper with `{"error": {"code": ..., "message": ...}}`
- Middleware added in `create_app()` before routes

### Integration Points
- `Dockerfile` — restructure into multi-stage build
- `docker-compose.yml` — add profiles, conditional build targets
- `src/ai_investing/api/main.py` — add `/health` and `/ready` endpoints
- `ApiKeyMiddleware` — exempt health/ready paths from auth
- `AppContext.load()` or app startup — add credential validation

</code_context>

<specifics>
## Specific Ideas

- Health/ready endpoints exempt from auth by path check in middleware (e.g. skip auth for paths starting with `/health` or `/ready`)
- Prod credential check: `if settings.auth_enabled and "postgres:postgres@" in settings.database_url: raise SystemExit(...)`
- Dev profile should be the default to avoid breaking anyone's muscle memory

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-deployment-hardening*
*Context gathered: 2026-03-15*
