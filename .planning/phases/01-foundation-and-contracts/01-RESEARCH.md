# Phase 1 Research: Foundation And Contracts

## Repo-Specific Assessment

Phase 1 is no longer a greenfield design exercise. The repo already contains most of the foundational surface the roadmap calls for:

- YAML registries for panels, agents, factors, memo sections, model profiles, tools, tool bundles, connectors, monitoring, and run policies
- strict Pydantic contracts for coverage, evidence, claims, verdicts, memo sections and updates, memo snapshots, monitoring deltas, tool logs, and run records
- SQLAlchemy tables plus repositories with active-versus-superseded semantics for claims, verdicts, and memos
- LangGraph composition for company refresh, panel debate or gatekeeper flow, memo updates, monitoring diffs, and IC synthesis
- file-bundle ingestion for both public and private example companies
- prompt markdown files for the current vertical slice and placeholder prompts for future panels
- a Typer CLI, a FastAPI service, Docker assets, and a passing fake-provider pytest suite

The Phase 1 question is therefore not "what stack should we use?" The real work is to harden the current implementation so future panel expansion stays config-driven, safe, and maintainable.

The main structural risk is config-runtime drift. Several fields are declared in config or settings but are still decorative rather than executable, which means extension work would still force changes in orchestration or service code unless that drift is closed now.

## Current Repo Shape

### Config and prompts

- `RegistryLoader` loads all registries through strict Pydantic models.
- Prompt content stays in markdown under `prompts/`, which matches the repo rule to keep prompts out of source code.
- The only fully active panel trees today are `gatekeepers` and `demand_revenue_quality`.
- `panels.yaml` scaffolds a broader future surface, but only two placeholder agents exist in `agents.yaml`, so the broader panel surface is not yet safely runnable.

### Schemas and persistence

- Domain models already cover the structured memory contracts Phase 1 expects.
- Repository writes supersede prior active claims and verdicts rather than overwriting them.
- Memos are stored as structured `ICMemo` snapshots with `MemoSectionUpdate` history and separate `MonitoringDelta` records.

### Orchestration and runtime

- `build_company_refresh_graph()` composes reusable LangGraph subgraphs and the fake-provider end-to-end path works.
- Memo updates already happen panel by panel before final IC synthesis.
- Reruns already write `what_changed_since_last_run` and a monitoring delta.
- The remaining issue is not absence of orchestration. It is that parts of orchestration are still hardcoded instead of being fully resolved from config.

### Interfaces and ops

- The CLI and API cover the main happy path for boot, ingest, analyze, refresh, memo, delta, and agent toggles.
- Docker Compose is the only verified local validation path in this environment because the host interpreter is Python `3.9.12` while the repo targets Python `3.11+`.

## Phase 1 Requirement Reconciliation

| Requirement | Status | What exists now | Remaining Phase 1 gap |
| --- | --- | --- | --- |
| `CONF-01` | Mostly met | YAML registries exist for panels, agents, factors, memo sections, model profiles, tools, bundles, connectors, monitoring, and run policies. | There is no cross-registry integrity pass for broken references, missing prompt files, or invalid schema names. |
| `CONF-02` | Partial | Agents can be enabled, disabled, and reparented by rewriting `config/agents.yaml` and reloading registries. | `parent_id` is not used by runtime orchestration, so reparenting changes config state but not execution behavior. |
| `CONF-03` | Partial | Agent config declares prompt path, schema, tool bundle, memory namespaces, model profile, and scope. | `agent.output_schema`, `input_channels`, `memory_*_namespaces`, and `scope` are not runtime-enforced or consumed. |
| `COV-01` | Partial | `CoverageEntry` stores company type, coverage status, cadence, next run, last run, and panel policy. | CLI and API coverage creation do not let operators set `next_run_at` directly. |
| `COV-02` | Partial | Service methods exist to disable or remove coverage while leaving the rest of historical memory intact. | Disable and remove are not exposed through the CLI or FastAPI. |
| `ING-01` | Met | Public file-bundle ingestion copies raw artifacts into a landing zone and persists normalized evidence. | `manifest_file` is configured but not actually consumed by the connector runtime. |
| `ING-02` | Met | Private file-bundle ingestion uses the same path with provenance, quality, and staleness metadata. | No additional Phase 1 blocker beyond connector-config parity. |
| `MEM-01` | Met | Structured models and tables exist for evidence, claims, verdicts, memos, memo section updates, deltas, tool logs, profiles, and runs. | None required before Phase 2 starts. |
| `MEM-02` | Met | Claim and verdict writes supersede prior active rows; status enums include `active`, `superseded`, and `rejected`. | None. |
| `MEMO-02` | Met | Memo section IDs are stable and config-driven, including the `sustainability` alternate label for `durability_resilience`. | None. |
| `ORCH-01` | Partial | Reusable subgraphs exist for panel debate, gatekeeper flow, panel lead, memo updates, monitoring diffs, and IC synthesis. | `company_refresh.py` still hardcodes subgraph selection, invokes compiled subgraphs through wrapper nodes, and ignores `panel.enabled`, `panel.implemented`, `run_policy.memo_reconciliation`, and `run_policy.monitoring_enabled`. |
| `TOOLS-01` | Met | Tool registry plus least-privilege bundles are loaded from config and enforced at execution time. | Bundle and handler integrity are not validated up front. |
| `PROV-01` | Mostly met | Fake, OpenAI, and Anthropic providers all implement the shared model interface and are selectable through model profiles. | `primary_provider` is unused and real-provider misconfiguration silently falls back to fake. |
| `API-01` | Partial | CLI supports DB init, ingestion, add coverage, analyze, run panel, refresh, run due, memo, delta, and agent toggles or reparent. | Coverage list, disable, and remove are missing; there is no explicit config-validation command. |
| `API-02` | Partial | FastAPI exposes coverage, ingest, run, memo, delta, and basic agent-management endpoints. | Coverage disable or remove and agent reparent are missing; ingest routes ignore the URL `company_id`; response and error envelopes are inconsistent. |
| `OPS-01` | Mostly met | Dockerfile, Compose, and runbook provide a working local boot path. | The supported host `uv` / Python `3.11+` path described in phase context is not yet documented or verified. |

## Highest-Value Hardening Work

1. Add a startup-time registry integrity audit.
   - Validate cross-file references for panel IDs, factor IDs, memo section IDs, tool bundles, tool IDs, model profiles, schema names, and prompt paths.
   - Reject active run policies that reference disabled or unimplemented panels.

2. Make config fields executable instead of decorative.
   - Either consume or remove fields that are currently ignored: `panel.prompt_path`, `panel.output_schema`, `panel.enabled`, `panel.implemented`, `agent.output_schema`, `parent_id`, `input_channels`, `memory_read_namespaces`, `memory_write_namespaces`, `scope`, `primary_provider`, `manifest_file`, `memo_reconciliation`, and `monitoring_enabled`.

3. Harden orchestration selection and panel safety.
   - Resolve subgraph builders from a registry keyed by `panel.subgraph`.
   - Block `run_panel`, `refresh_company`, and `full_surface` execution for panels that are disabled, unimplemented, or missing required agents.

4. Close the operator-surface gaps.
   - Expose coverage list, disable, and remove in the CLI.
   - Expose coverage disable or remove and agent reparent in the API.
   - Allow operator-controlled `next_run_at` on create or update.

5. Make run lifecycle failure-safe.
   - When graph execution fails, persist `RunStatus.FAILED` with failure metadata instead of leaving runs stranded in `running`.

6. Tighten provider behavior for non-test runs.
   - Keep fake as the explicit test and local-default mode, but fail clearly when a requested real provider is not installed or not configured.

7. Keep the Docker-first path, but document the host path honestly.
   - This repo is currently validated in Docker.
   - If a host workflow remains supported, document it only for Python `3.11+` and include exact install and test commands.

## Architecture Patterns To Keep

- Keep YAML as the canonical topology surface, but pair it with a second-stage integrity validator.
- Keep Pydantic domain models as the contract boundary and SQLAlchemy rows as query projections plus canonical JSON payloads.
- Keep prompts in markdown files and block placeholder panels from active run policies until their agent trees exist.
- Keep reusable LangGraph subgraphs, but move panel and subgraph selection out of inline conditionals and into a small builder registry.
- Keep provider wrappers thin and structured. Orchestration, retries, memo semantics, and run lifecycle belong in services, not provider classes.
- Keep memo history structured. Rendered markdown and delta prose should remain derived read models, not the source of truth.

## Don't Hand-Roll

- Registry inheritance or templating DSLs. The current YAML files are explicit and reviewable; keep them that way.
- Prompt validation scattered across runtime code. Use one central registry audit for prompt and schema references.
- Tool permission checks inside agents. Keep enforcement in `ToolRegistryService`.
- Prose-only memo persistence. The existing memo, update, and delta contracts are the right base.
- Shadow provider-selection logic in services. Keep selection centralized in `AppContext`, then make it strict enough for non-test runs.

## Common Pitfalls In The Current Repo

- Treating config as authoritative when runtime still ignores several config fields.
- Assuming `full_surface` is safe because it exists in `run_policies.yaml`; it is not safe today.
- Treating reparent as a topology control when `parent_id` is not read during execution.
- Assuming panel `enabled` or `implemented` flags prevent execution; they do not today.
- Assuming a real-provider request will fail loudly; it may silently downgrade to fake.
- Assuming passing pytest means the whole validation story is green; the automated suite passes, but static gates fail and the automated tests run on SQLite rather than Postgres.

## Validation Architecture

### Current framework and test configuration

- Test framework: `pytest`
- Pytest config: `testpaths = ["tests"]`, `pythonpath = ["src"]`
- Test harness behavior:
  - copies `config/` into a temp directory
  - rewrites connector landing zones into temp paths
  - uses in-memory SQLite with `StaticPool`
  - forces the fake provider
  - seeds example companies through the real ingestion and service layers
- Verified runtime path: Docker and Docker Compose
- Host status in this environment: Python `3.9.12`, `uv` not installed, so host-native validation is not a supported path here
- Container runtime target: Python `3.11`

### Verified automated commands

Quick structural smoke:

```bash
docker compose run --rm api pytest -q tests/test_config_and_registry.py tests/test_repository_semantics.py tests/test_ingestion.py
```

- Verified result: `6 passed`
- Likely runtime: about `0.7s` pytest time plus a few seconds of container startup overhead
- Coverage:
  - registry loading
  - agent config mutation and reload
  - claim schema validation
  - supersede and history semantics
  - public and private ingestion parsing and persistence

Full automated suite:

```bash
docker compose run --rm api pytest -q
```

- Verified result: `14 passed`
- Likely runtime: about `3.7s` pytest time plus a few seconds of container startup overhead
- Coverage:
  - tool bundle enforcement
  - graph composition
  - fake-provider end-to-end analysis
  - memo section update semantics
  - IC memo synthesis
  - rerun delta generation
  - thesis drift flags
  - due-coverage execution

Configured static gates:

```bash
docker compose run --rm api ruff check .
docker compose run --rm api mypy src tests
```

- Current status: both fail in Docker
- Current wave-0 findings:
  - `ruff` reports `57` issues, including import ordering, long lines, unused imports or locals, and at least one noisy security false positive on enum value names
  - `mypy` reports `55` errors across `14` files, including missing stubs or optional dependencies, missing annotations, possible `None` access, and test typing issues
- Typical runtime:
  - `ruff check .`: about `7s`
  - `mypy src tests`: about `14s`
- Phase implication: static validation exists on paper but is not yet part of the green Phase 1 baseline

### Manual-only checks

These checks still need human or shell-level confirmation because they are not covered by the current pytest suite:

1. Docker boot path

```bash
docker compose up --build -d
docker compose exec api ai-investing init-db
```

2. Public and private ingestion happy path

```bash
docker compose exec api ai-investing ingest-public-data /app/examples/acme_public
docker compose exec api ai-investing ingest-private-data /app/examples/beta_private
```

3. Coverage plus analysis workflow

```bash
docker compose exec api ai-investing add-coverage ACME "Acme Cloud" public watchlist
docker compose exec api ai-investing analyze-company ACME
docker compose exec api ai-investing refresh-company ACME
docker compose exec api ai-investing run-due-coverage
docker compose exec api ai-investing generate-memo ACME
docker compose exec api ai-investing show-delta ACME
```

4. API smoke

```bash
curl http://localhost:8000/coverage
curl http://localhost:8000/companies/ACME/memo
curl http://localhost:8000/companies/ACME/delta
```

### Wave-0 validation gaps

- No automated API endpoint tests
- No automated CLI command tests
- No automated cross-registry integrity tests
- No automated prompt-existence or schema-mapping tests
- No automated Postgres-backed integration suite; automated tests currently run on SQLite
- No automated Docker or runbook smoke
- No automated guardrail proving `full_surface` is rejected or safely skipped while non-implemented panels remain scaffold-only
- Static quality gates are not green

### Recommended sampling cadence

- Per config, schema, prompt, tool-registry, or persistence change:
  - run the quick pytest slice
  - run `ruff check` on touched files or the whole repo if the change is broad

- Per orchestration, provider, CLI, or API change:
  - run the full pytest suite
  - rerun `ruff check .` and `mypy src tests`

- Before Phase 1 sign-off or any phase-handoff commit:
  - run the full Docker pytest suite
  - execute the Docker manual happy path once end to end
  - confirm the API smoke endpoints return current data

- Weekly while Phase 1 remains open:
  - run one Docker refresh against sample rerun data
  - confirm memo continuity, `what_changed_since_last_run`, and delta output remain stable

## Bottom Line

Phase 1 already has a strong foundation: structured contracts, history-preserving memory, reusable subgraphs, provider adapters, prompt files, operator interfaces, Docker assets, and a passing fake-provider test suite are in place.

The remaining work is mostly hardening, not invention. The highest-leverage Phase 1 tasks are to eliminate config-runtime drift, close the missing coverage-management and API surfaces, enforce safe panel selection, make failure states explicit, and turn the existing validation setup into a truly green baseline instead of a partial one.
