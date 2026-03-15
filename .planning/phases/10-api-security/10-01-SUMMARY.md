---
phase: 10
plan: 01
status: complete
started: "2026-03-15T20:02:53Z"
completed: "2026-03-15T20:15:00Z"
---

# Summary: 10-01 API Key Auth, CORS, and Role-Based Access

## What was built

API security layer for the AI Investing API:
- **Authentication middleware** (`ApiKeyMiddleware`) validates `X-API-Key` header on every request
- **Role-based authorization** via `require_role("operator")` dependency on 25 mutation endpoints
- **CORS configuration** conditionally added via `AI_INVESTING_DOMAIN` env var
- **Backward compatibility**: auth effectively disabled when no keys configured

## Key decisions

- Module-level `_operator = require_role("operator")` singleton avoids B008 lint (function call in default args)
- Auth disabled when `api_keys` is empty, regardless of `auth_enabled` setting — keeps all existing tests working without modification
- `RoleDeniedError` custom exception + FastAPI exception handler produces consistent `{"error": {"code": "forbidden", ...}}` JSON shape matching all other API errors
- CORS middleware skipped entirely when `AI_INVESTING_DOMAIN` is empty (default-deny)

## Requirements addressed

| Requirement | How |
|-------------|-----|
| SEC-01 | ApiKeyMiddleware returns 401 for missing/invalid keys; AI_INVESTING_AUTH_ENABLED bypass |
| SEC-02 | CORSMiddleware with AI_INVESTING_DOMAIN; defaults to no CORS headers |
| SEC-03 | require_role("operator") on all 25 mutation endpoints; 403 for readonly keys |

## key-files

### created
- `src/ai_investing/api/security.py` — auth middleware, key parser, role dependency
- `tests/test_api_security.py` — 22 security tests

### modified
- `src/ai_investing/api/main.py` — wired middleware, CORS, role deps on all endpoints
- `src/ai_investing/settings.py` — added auth_enabled, api_keys, domain fields
- `.env.example` — documented new env vars
- `pyproject.toml` — B008 lint ignore for FastAPI Depends pattern

## Test results

- 22 new security tests (parse, bypass, 401, 403, CORS)
- 246 total passed, 2 pre-existing failures (live connector staleness)
- Lint: all checks passed

## Self-Check: PASSED
