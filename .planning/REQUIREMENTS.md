# Requirements: AI Investing

**Defined:** 2026-03-08
**Core Value:** Produce a continuously updatable, auditable investment view where factor-level claims, panel verdicts, and memo deltas remain structured and reusable across reruns.

## v1 Requirements

### Configuration And Registry

- [ ] **CONF-01**: Engineers can define panels, factors, memo sections, model profiles, tool bundles, and source connectors through YAML configuration files.
- [ ] **CONF-02**: Engineers can enable, disable, or reparent an agent without changing orchestration code.
- [ ] **CONF-03**: Every agent declares prompt path, schema, tool bundle, memory namespaces, model profile, and scope.

### Coverage And Scheduling

- [ ] **COV-01**: A user can register a company coverage entry with company type, coverage status, cadence, next run time, and panel policy.
- [ ] **COV-02**: A user can disable or remove a coverage entry without deleting historical memory.
- [x] **COV-03**: The system can run all due coverage entries and skip disabled entries.

### Ingestion

- [ ] **ING-01**: The platform can ingest sample public-company evidence from a file-based connector and persist immutable raw artifacts plus normalized evidence records.
- [ ] **ING-02**: The platform can ingest sample private-company evidence from a file-based connector and persist normalized evidence records with provenance and quality metadata.
- [x] **ING-03**: Evidence creation records factor tags, source references, time periods, and staleness metadata for downstream agent use.

### Memory And Persistence

- [ ] **MEM-01**: The platform stores evidence, claims, verdicts, memo sections, memo section updates, memo snapshots, monitoring deltas, tool logs, and company profiles as structured records.
- [ ] **MEM-02**: Claim and verdict records preserve history using statuses such as `active`, `superseded`, and `rejected`.
- [x] **MEM-03**: Each company has a readable current memo snapshot plus memo history and memo section update logs.

### Orchestration

- [ ] **ORCH-01**: The system composes a company refresh from reusable LangGraph subgraphs for gatekeeping, debate, panel leadership, memo updates, monitoring diffs, and IC synthesis.
- [x] **ORCH-02**: The initial production slice runs `gatekeepers` and `demand_revenue_quality` end-to-end using config-driven agents.
- [x] **ORCH-03**: The orchestration runtime can generate a per-company delta against the prior active memo on reruns.

### Memo And Monitoring

- [x] **MEMO-01**: The memo initializes on first coverage and updates section-by-section as panel verdicts arrive.
- [ ] **MEMO-02**: The memo exposes stable section IDs and configurable display labels, including optional `sustainability` labeling for `durability_resilience`.
- [x] **MEMO-03**: Each rerun writes `what_changed_since_last_run` and a `MonitoringDelta` record with thesis drift metadata.

### Tooling And Providers

- [ ] **TOOLS-01**: Tools are declared in a registry and assigned to agents through least-privilege bundles.
- [x] **TOOLS-02**: Every tool invocation is logged with run, agent, tool, input summary, and output references.
- [ ] **PROV-01**: The service supports OpenAI and Anthropic provider adapters plus a fake provider for tests.

### Interfaces And Operations

- [ ] **API-01**: The project exposes a CLI for database init, ingestion, coverage management, analysis, refresh, memo generation, delta viewing, and agent configuration updates.
- [ ] **API-02**: The project exposes a FastAPI service with coverage, company run, memo, delta, and agent management endpoints.
- [ ] **OPS-01**: Local development works through Docker Compose with Postgres and documented startup steps.

### Validation

- [x] **TEST-01**: The repo includes tests for config loading, registries, graph composition, memo update semantics, rerun deltas, tool bundle enforcement, ingestion parsing, and an end-to-end fake-provider run.
- [x] **TEST-02**: The repo ships sample data plus sample generated memo and delta artifacts for another engineer to inspect.

## v2 Requirements

### Broader Panel Coverage

- **V2-01**: Productionize all remaining top-level panels beyond the initial vertical slice.
- **V2-02**: Add richer live connectors for regulatory, market, consensus, ownership, and dataroom systems.
- **V2-03**: Add configurable cadence schedules beyond weekly defaults.

### Platform Expansion

- **V2-04**: Add richer contradiction resolution, analog graph search, and portfolio-level analytics views.
- **V2-05**: Add background worker infrastructure for large-scale concurrent coverage refreshes.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Frontend UI | Explicitly excluded from v1 in favor of API and CLI delivery |
| Compliance or entitlement workflow engine | User explicitly excluded this from v1 |
| Premium live data integrations | File-based examples and connector interfaces are sufficient for the initial architecture |
| Full panel-specific reasoning for every domain panel | The initial objective is a strong vertical slice and extensible scaffolding |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 1 | Complete |
| CONF-02 | Phase 1 | Complete |
| CONF-03 | Phase 1 | Complete |
| COV-01 | Phase 1 | Complete |
| COV-02 | Phase 1 | Complete |
| COV-03 | Phase 2 | Complete |
| ING-01 | Phase 1 | Complete |
| ING-02 | Phase 1 | Complete |
| ING-03 | Phase 2 | Complete |
| MEM-01 | Phase 1 | Complete |
| MEM-02 | Phase 1 | Complete |
| MEM-03 | Phase 2 | Complete |
| ORCH-01 | Phase 1 | Complete |
| ORCH-02 | Phase 2 | Complete |
| ORCH-03 | Phase 2 | Complete |
| MEMO-01 | Phase 2 | Complete |
| MEMO-02 | Phase 1 | Complete |
| MEMO-03 | Phase 2 | Complete |
| TOOLS-01 | Phase 1 | Complete |
| TOOLS-02 | Phase 2 | Complete |
| PROV-01 | Phase 1 | Complete |
| API-01 | Phase 1 | Complete |
| API-02 | Phase 1 | Complete |
| OPS-01 | Phase 1 | Complete |
| TEST-01 | Phase 2 | Complete |
| TEST-02 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-03-08*
*Last updated: 2026-03-11 after Phase 02 Plan 05 completion*
