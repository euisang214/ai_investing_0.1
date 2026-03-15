# Requirements: AI Investing

**Defined:** 2026-03-08
**Core Value:** Produce a continuously updatable, auditable investment view where factor-level claims, panel verdicts, and memo deltas remain structured and reusable across reruns.

## v1 Requirements (Complete)

### Configuration And Registry

- [x] **CONF-01**: Engineers can define panels, factors, memo sections, model profiles, tool bundles, and source connectors through YAML configuration files.
- [x] **CONF-02**: Engineers can enable, disable, or reparent an agent without changing orchestration code.
- [x] **CONF-03**: Every agent declares prompt path, schema, tool bundle, memory namespaces, model profile, and scope.

### Coverage And Scheduling

- [x] **COV-01**: A user can register a company coverage entry with company type, coverage status, cadence, next run time, and panel policy.
- [x] **COV-02**: A user can disable or remove a coverage entry without deleting historical memory.
- [x] **COV-03**: The system can run all due coverage entries and skip disabled entries.

### Ingestion

- [x] **ING-01**: The platform can ingest sample public-company evidence from a file-based connector and persist immutable raw artifacts plus normalized evidence records.
- [x] **ING-02**: The platform can ingest sample private-company evidence from a file-based connector and persist normalized evidence records with provenance and quality metadata.
- [x] **ING-03**: Evidence creation records factor tags, source references, time periods, and staleness metadata for downstream agent use.

### Memory And Persistence

- [x] **MEM-01**: The platform stores evidence, claims, verdicts, memo sections, memo section updates, memo snapshots, monitoring deltas, tool logs, and company profiles as structured records.
- [x] **MEM-02**: Claim and verdict records preserve history using statuses such as `active`, `superseded`, and `rejected`.
- [x] **MEM-03**: Each company has a readable current memo snapshot plus memo history and memo section update logs.

### Orchestration

- [x] **ORCH-01**: The system composes a company refresh from reusable LangGraph subgraphs for gatekeeping, debate, panel leadership, memo updates, monitoring diffs, and IC synthesis.
- [x] **ORCH-02**: The initial production slice runs `gatekeepers` and `demand_revenue_quality` end-to-end using config-driven agents.
- [x] **ORCH-03**: The orchestration runtime can generate a per-company delta against the prior active memo on reruns.

### Memo And Monitoring

- [x] **MEMO-01**: The memo initializes on first coverage and updates section-by-section as panel verdicts arrive.
- [x] **MEMO-02**: The memo exposes stable section IDs and configurable display labels, including optional `sustainability` labeling for `durability_resilience`.
- [x] **MEMO-03**: Each rerun writes `what_changed_since_last_run` and a `MonitoringDelta` record with thesis drift metadata.

### Tooling And Providers

- [x] **TOOLS-01**: Tools are declared in a registry and assigned to agents through least-privilege bundles.
- [x] **TOOLS-02**: Every tool invocation is logged with run, agent, tool, input summary, and output references.
- [x] **PROV-01**: The service supports OpenAI and Anthropic provider adapters plus a fake provider for tests.

### Interfaces And Operations

- [x] **API-01**: The project exposes a CLI for database init, ingestion, coverage management, analysis, refresh, memo generation, delta viewing, and agent configuration updates.
- [x] **API-02**: The project exposes a FastAPI service with coverage, company run, memo, delta, and agent management endpoints.
- [x] **OPS-01**: Local development works through Docker Compose with Postgres and documented startup steps.

### Validation

- [x] **TEST-01**: The repo includes tests for config loading, registries, graph composition, memo update semantics, rerun deltas, tool bundle enforcement, ingestion parsing, and an end-to-end fake-provider run.
- [x] **TEST-02**: The repo ships sample data plus sample generated memo and delta artifacts for another engineer to inspect.

### Broader Panel Coverage (v2 from v1.0 milestone)

- [x] **V2-01**: Productionize all remaining top-level panels beyond the initial vertical slice.
- [x] **V2-02**: Add richer live connectors for regulatory, market, consensus, ownership, and dataroom systems.
- [x] **V2-03**: Add configurable cadence schedules beyond weekly defaults.
- [x] **V2-04**: Add richer contradiction resolution, analog graph search, and portfolio-level analytics views.
- [x] **V2-05**: Add background worker infrastructure for large-scale concurrent coverage refreshes.

## v2.0 Requirements (Productionization)

### Provider And Secrets Management

- [ ] **PROV-02**: Operator can toggle between `fake`, `openai`, and `anthropic` providers via a single environment variable, with model names configurable per profile tier (balanced, quality, budget).
- [ ] **PROV-03**: API keys and model names are loaded from environment variables with clear validation errors when missing in non-fake mode.
- [ ] **PROV-04**: README documents the exact steps to create OpenAI and Anthropic API keys and configure them for test versus production use.

### API Security

- [ ] **SEC-01**: All API endpoints require authentication via API key header with a configurable bypass for local development.
- [ ] **SEC-02**: CORS policy is configurable and defaults to restrictive settings.
- [ ] **SEC-03**: Provisional continuation and worker control endpoints are restricted to operator-role API keys.

### Deployment Hardening

- [ ] **DEPLOY-01**: Production Dockerfile uses multi-stage build, excludes dev dependencies and test fixtures.
- [ ] **DEPLOY-02**: API service exposes `/health` and `/ready` endpoints for container orchestration probes.
- [ ] **DEPLOY-03**: Docker Compose supports separate dev and production profiles with environment-specific settings.
- [ ] **DEPLOY-04**: Database credentials are configurable through environment variables with no hardcoded defaults in production profile.

### Observability

- [ ] **OBS-01**: All application log output uses structured JSON logging with run IDs, company IDs, and panel names.
- [ ] **OBS-02**: LLM calls log token usage (input and output tokens) per invocation and persist per-run totals.
- [ ] **OBS-03**: Application errors are captured with context sufficient for debugging via an error tracking integration point.

### Cost And Rate Limiting

- [ ] **COST-01**: Token usage is tracked per run and exposed through the run result API and CLI.
- [ ] **COST-02**: LLM provider calls implement retry with exponential backoff on rate limit (429) and transient errors.
- [ ] **COST-03**: A configurable per-run token budget cap can abort analysis and report the reason.

### CI/CD And Testing

- [ ] **CI-01**: Project includes a GitHub Actions workflow that runs lint, type check, and tests on every push.
- [ ] **CI-02**: Test suite can run entirely with the fake provider without requiring any API keys or external services.

### Operator Documentation

- [ ] **DOC-01**: README includes a production deployment section with step-by-step instructions for API key setup, secrets configuration, and environment toggling.
- [ ] **DOC-02**: README documents how to switch between test (fake provider) and production (real LLM) modes.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Frontend UI | v2 remains API/CLI only |
| Premium live data integrations (Bloomberg, FactSet) | Stub connectors stay; free-tier connectors explored separately |
| Compliance or entitlement workflow engine | Excluded from v2 scope |
| Kubernetes or managed orchestration | v2 targets single-host Docker with CI/CD readiness |
| OAuth-based LLM authentication | OpenAI and Anthropic use API keys only; OAuth is not supported for programmatic LLM calls |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 1 (v1.0) | Complete |
| CONF-02 | Phase 1 (v1.0) | Complete |
| CONF-03 | Phase 1 (v1.0) | Complete |
| COV-01 | Phase 1 (v1.0) | Complete |
| COV-02 | Phase 1 (v1.0) | Complete |
| COV-03 | Phase 2 (v1.0) | Complete |
| ING-01 | Phase 1 (v1.0) | Complete |
| ING-02 | Phase 1 (v1.0) | Complete |
| ING-03 | Phase 2 (v1.0) | Complete |
| MEM-01 | Phase 1 (v1.0) | Complete |
| MEM-02 | Phase 1 (v1.0) | Complete |
| MEM-03 | Phase 2 (v1.0) | Complete |
| ORCH-01 | Phase 1 (v1.0) | Complete |
| ORCH-02 | Phase 2 (v1.0) | Complete |
| ORCH-03 | Phase 2 (v1.0) | Complete |
| MEMO-01 | Phase 2 (v1.0) | Complete |
| MEMO-02 | Phase 1 (v1.0) | Complete |
| MEMO-03 | Phase 2 (v1.0) | Complete |
| TOOLS-01 | Phase 1 (v1.0) | Complete |
| TOOLS-02 | Phase 2 (v1.0) | Complete |
| PROV-01 | Phase 1 (v1.0) | Complete |
| API-01 | Phase 1 (v1.0) | Complete |
| API-02 | Phase 1 (v1.0) | Complete |
| OPS-01 | Phase 1 (v1.0) | Complete |
| TEST-01 | Phase 2 (v1.0) | Complete |
| TEST-02 | Phase 2 (v1.0) | Complete |
| V2-01 | Phase 6 (v1.0) | Complete |
| V2-02 | Phase 4 (v1.0) | Complete |
| V2-03 | Phase 5 (v1.0) | Complete |
| V2-04 | Phase 4 (v1.0) | Complete |
| V2-05 | Phase 5+8 (v1.0) | Complete |
| PROV-02 | — | Pending |
| PROV-03 | — | Pending |
| PROV-04 | — | Pending |
| SEC-01 | — | Pending |
| SEC-02 | — | Pending |
| SEC-03 | — | Pending |
| DEPLOY-01 | — | Pending |
| DEPLOY-02 | — | Pending |
| DEPLOY-03 | — | Pending |
| DEPLOY-04 | — | Pending |
| OBS-01 | — | Pending |
| OBS-02 | — | Pending |
| OBS-03 | — | Pending |
| COST-01 | — | Pending |
| COST-02 | — | Pending |
| COST-03 | — | Pending |
| CI-01 | — | Pending |
| CI-02 | — | Pending |
| DOC-01 | — | Pending |
| DOC-02 | — | Pending |

**Coverage:**
- v1.0 requirements: 26 total, all complete
- v2.0 requirements: 20 total
- Unmapped: 20 (roadmap pending)

---
*Requirements defined: 2026-03-08*
*Last updated: 2026-03-15 after v2.0 milestone start*
