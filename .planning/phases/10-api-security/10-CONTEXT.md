# Phase 10: API Security - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Protect the API from unauthorized access with API key authentication, enforce operator-only restrictions on sensitive mutation endpoints, and configure CORS to deny cross-origin requests by default. The existing test suite and local dev workflow must remain unaffected via a configurable auth bypass.

</domain>

<decisions>
## Implementation Decisions

### API Key Format and Roles
- Keys configured via `AI_INVESTING_API_KEYS` env var using simple `key:role` comma-separated format
- Example: `AI_INVESTING_API_KEYS=sk-prod-abc123:operator,sk-reader-xyz:readonly`
- Two roles only: `operator` (full access) and `readonly` (GET endpoints + notification claim/acknowledge)
- Workers use operator keys — they are trusted internal services, not separate security principals
- No metadata on keys (no names, no expiry) — keep it simple

### Auth Middleware
- **Deny-all middleware** — every request must include a valid `X-API-Key` header
- Invalid or missing key → 401 Unauthorized
- Middleware runs before route handlers; single enforcement point
- No per-route opt-in needed — everything is protected by default

### Local Dev Bypass
- `AI_INVESTING_AUTH_ENABLED` env var controls whether auth middleware is active
- Defaults to `true` (auth required)
- Set to `false` for local development — disables all auth checks
- This keeps existing tests working without modification (no API keys needed in test fixtures)

### Endpoint Authorization (Operator vs Readonly)
- Authorization enforced via a `require_role("operator")` FastAPI dependency on operator-only routes
- Middleware handles authentication (valid key → pass, invalid → 401)
- Dependency handles authorization (wrong role → 403 Forbidden)

**Operator-only endpoints (403 for readonly keys):**
- `POST /coverage` — creates coverage entries
- `POST /coverage/{id}/disable` — mutates coverage state
- `DELETE /coverage/{id}` — destructive
- `POST /coverage/{id}/next-run-at` — mutates schedule
- `POST /coverage/{id}/schedule` — mutates schedule
- `POST /coverage/run-due` — triggers LLM runs
- `POST /queue/enqueue-selected` — triggers job creation
- `POST /queue/enqueue-watchlist` — triggers job creation
- `POST /queue/enqueue-portfolio` — triggers job creation
- `POST /queue/enqueue-due` — triggers job creation
- `POST /queue/{id}/retry` — triggers re-execution
- `POST /queue/{id}/cancel` — mutates job state
- `POST /queue/{id}/force-run` — triggers execution
- `POST /workers/run` — runs worker batch
- `POST /runs/{id}/continue` — continues paused run
- `POST /notifications/{id}/dispatch` — side-effecting
- `POST /notifications/{id}/fail` — mutates notification state
- `POST /companies/{id}/ingest-public` — data ingestion
- `POST /companies/{id}/ingest-private` — data ingestion
- `POST /companies/{id}/analyze` — triggers LLM run
- `POST /companies/{id}/refresh` — triggers LLM run
- `POST /companies/{id}/panels/{id}/run` — triggers LLM run
- `POST /agents/{id}/enable` — mutates config
- `POST /agents/{id}/disable` — mutates config
- `POST /agents/{id}/reparent` — mutates config

**Readonly-accessible (any valid key):**
- `GET /coverage` — read-only listing
- `GET /cadence-policies` — read-only listing
- `GET /queue` — read-only summary
- `GET /queue/{id}` — read-only detail
- `GET /review-queue` — read-only listing
- `GET /notifications` — read-only listing
- `POST /notifications/claim` — read-side for consumers
- `POST /notifications/{id}/acknowledge` — low-risk ack
- `GET /runs/{id}` — read-only
- `GET /companies/{id}/memo` — read-only
- `GET /companies/{id}/delta` — read-only
- `GET /companies/{id}/monitoring-history` — read-only
- `GET /portfolio/monitoring-summary` — read-only
- `GET /agents` — read-only listing

### CORS Configuration
- Default: **block all cross-origin requests** (no CORS headers sent)
- `AI_INVESTING_DOMAIN` env var to allowlist origins (comma-separated if multiple needed)
- Example: `AI_INVESTING_DOMAIN=https://dashboard.example.com`
- When set: allow `GET, POST, PUT, DELETE, OPTIONS` methods and `X-API-Key, Content-Type` headers
- No credentials mode (API key auth doesn't need cookies)
- Current clients (CLI, n8n, curl) are unaffected since they're not browser-based

### Claude's Discretion
- Error response format for 401/403 (should follow existing `_error_response` pattern)
- Middleware implementation details (Starlette middleware vs FastAPI dependency injection)
- Test structure for auth tests

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_error_response()` helper in `api/main.py` — standardized error JSON format, reuse for 401/403
- `Settings` class in `settings.py` — `pydantic-settings` with `AI_INVESTING_` prefix, add new fields here
- `create_app()` factory pattern — middleware added here before routes

### Established Patterns
- Settings via `pydantic-settings` with `AI_INVESTING_` env prefix — new env vars follow this
- FastAPI exception handlers for KeyError, ValueError, FileNotFoundError — auth errors follow same pattern
- Single `create_app()` factory with all routes defined inline — middleware and dependencies added here

### Integration Points
- `create_app()` in `api/main.py` — add CORS and auth middleware here
- `Settings` in `settings.py` — add `auth_enabled`, `api_keys`, `domain` fields
- `.env.example` — document new environment variables
- Test fixtures in `conftest.py` — existing TestClient setup doesn't send API keys; bypass must handle this

</code_context>

<specifics>
## Specific Ideas

- Env var naming: `AI_INVESTING_DOMAIN` (not `CORS_ORIGINS`) to be more intuitive for operators
- Key format: `key:role` pairs keep configuration in a single env var, easy to manage in Docker/k8s
- Auth bypass: `AI_INVESTING_AUTH_ENABLED=false` is the simplest path to keep dev and test frictionless

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 10-api-security*
*Context gathered: 2026-03-15*
