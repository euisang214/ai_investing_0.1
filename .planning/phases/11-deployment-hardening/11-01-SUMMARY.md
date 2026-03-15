---
phase: 11
plan: 01
status: complete
started: "2026-03-15T23:33:01Z"
completed: "2026-03-15T23:48:00Z"
---

# Summary: 11-01 Multi-Stage Dockerfile, Health Probes, Profiles, and Credential Safety

## What was built

Production-worthy Docker setup for the AI Investing API:
- **Multi-stage Dockerfile** with `base`, `prod`, and `dev` targets. Prod image excludes tests, examples, docs, n8n, scripts, and dev dependencies.
- **Health/readiness probes**: `GET /health` (trivial liveness, 200) and `GET /ready` (DB ping, 200/503).
- **Docker Compose profiles**: default `api` service runs dev stack unchanged; `api-prod` service (requires `--profile prod`) runs production stack.
- **Credential safety**: app refuses to start when `auth_enabled=true` and default `postgres:postgres@` credentials detected.

## Key decisions

- Health/ready endpoints bypass `ApiKeyMiddleware` via `_EXEMPT_PATHS` frozenset check at top of `dispatch()` — avoids adding a new middleware or complex path matching.
- `_validate_production_settings()` is a standalone function (not a method) called at the start of `AppContext.load()` — catches insecure config before any DB connection.
- Prod Docker Compose service is named `api-prod` (separate from `api`) so default `docker compose` commands continue to use dev without `--profile`.
- Dockerfile tests use `_find_dockerfile()` that checks multiple paths — works both locally and inside Docker.

## Requirements addressed

| Requirement | How |
|-------------|-----|
| DEPLOY-01 | Multi-stage Dockerfile: prod target excludes dev deps, tests, examples, docs |
| DEPLOY-02 | GET /health (200 trivial), GET /ready (200/503 DB ping), both skip auth |
| DEPLOY-03 | Docker Compose profiles: api (dev, default), api-prod (prod, --profile) |
| DEPLOY-04 | _validate_production_settings raises SystemExit for default creds in prod |

## key-files

### created
- `tests/test_deployment.py` — 13 deployment tests

### modified
- `Dockerfile` — restructured to 3-stage build (base → prod → dev)
- `docker-compose.yml` — added dev/prod profiles, api-prod service
- `src/ai_investing/persistence/db.py` — added `Database.ping()` method
- `src/ai_investing/api/security.py` — added `_EXEMPT_PATHS` for /health, /ready
- `src/ai_investing/api/main.py` — added /health and /ready endpoints
- `src/ai_investing/application/context.py` — added `_validate_production_settings()`
- `.env.example` — added production profile documentation

## Test results

- 13 new deployment tests (9 pass, 4 skipped in Docker — Dockerfile not mounted)
- 255 total passed, 4 skipped, 2 pre-existing failures (live connector staleness)
- Lint: all checks passed
- Zero regressions

## Self-Check: PASSED
