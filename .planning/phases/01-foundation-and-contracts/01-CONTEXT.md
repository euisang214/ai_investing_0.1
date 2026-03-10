# Phase 1: Foundation And Contracts - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 establishes the backend foundation for the project: config registries, typed contracts, persistence behavior, provider/tool abstractions, CLI/API interface posture, and the supported local development path. The scope is fixed by the roadmap and requirements. This phase should harden and align the existing implementation with the intended contracts rather than expand into new product capabilities.

</domain>

<decisions>
## Implementation Decisions

### Registry editing model
- Keep registry authoring explicit in YAML, but allow a small number of safe defaults to reduce repetition.
- YAML remains the canonical source of truth for registry changes.
- CLI/API mutations must stay minimal. The allowed mutation surface is `enable-agent`, `disable-agent`, and `reparent-agent`.
- Any additional registry-mutating CLI/API command requires explicit user confirmation before being added.
- Invalid registry references must fail fast at load/startup rather than warn and continue.
- Placeholder scaffolding should stop at panel-level entries. Do not add new placeholder agents or factors just for future expansion.

### Operator interface style
- CLI output should be mixed by command: concise or readable for operator workflows, structured where export or automation matters.
- API responses should move toward a consistent envelope shape such as `data/meta/errors`.
- Common operator-facing failures should use stable domain error codes and messages across CLI and API.
- Memo and delta retrieval should support both rendered and structured forms from the start.

### History visibility defaults
- Normal reads should default to current state: active claim cards, active panel verdicts, and the current active memo.
- History should be available only through explicit drill-down commands, flags, or endpoints.
- Rerun deltas should compare against the most recent active prior state by default.
- Default responses may include lightweight audit metadata such as `has_history`, `prior_run_id`, or `supersedes_*`, but should not embed rich history by default.

### Local boot path
- The primary supported local path is Docker-first.
- A host `uv` workflow is also supported when Python 3.11+ is available.
- If the host interpreter is older than Python 3.11, fail clearly and direct operators to Docker.
- The supported host path should cover CLI, API, and tests against Postgres.
- Documentation should present one primary Docker quick start with a separate supported host-`uv` section.

### Claude's Discretion
- Choose the exact safe-default fields for registries, as long as registry files remain explicit and reviewable.
- Choose which CLI commands stay fully structured versus which get concise human-readable summaries, as long as the split matches operator workflows and preserves automation paths.
- Choose the exact lightweight history metadata fields exposed by default.
- Choose the exact layout and commands for the host `uv` documentation, as long as Docker remains the primary quick start.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ai_investing/config/models.py`: strict typed registry models already exist and establish the current config contract surface.
- `src/ai_investing/config/loader.py`: centralized YAML loading and validation already provide the fail-fast backbone for registry handling.
- `src/ai_investing/domain/models.py`: structured domain records and status fields already capture the intended claim, verdict, memo, delta, and tool-log contracts.
- `src/ai_investing/persistence/repositories.py`: current repository methods already distinguish active/current reads from preserved history.
- `src/ai_investing/application/services.py`: shared application services already sit between persistence and both interfaces.
- `src/ai_investing/cli.py` and `src/ai_investing/api/main.py`: the CLI and API skeletons already cover the core operator workflow surface.
- `Dockerfile`, `docker-compose.yml`, and `docs/runbook.md`: the repo already has a working Docker-based local path that can anchor the supported runtime story.

### Established Patterns
- Registry and domain validation are intentionally strict, using Pydantic models with forbidden extra fields.
- Config is file-driven and loaded centrally rather than assembled ad hoc inside orchestration code.
- History is preserved by superseding prior active records instead of destructive overwrite.
- Runtime flows already prefer current state by default, such as active claims and the current memo.
- CLI and API both call shared services rather than duplicating business logic.
- The repo already contains substantial Phase 1 and Phase 2 implementation surface, so planning should reconcile and harden existing code rather than assume a greenfield build.

### Integration Points
- Registry behavior changes will center on `config/*.yaml`, `src/ai_investing/config/models.py`, and `src/ai_investing/config/loader.py`.
- Interface posture changes will center on `src/ai_investing/cli.py`, `src/ai_investing/api/main.py`, and shared rendering/service helpers in `src/ai_investing/application/services.py`.
- History visibility and audit metadata changes will center on `src/ai_investing/persistence/repositories.py`, domain models, and memo/delta render paths.
- Local boot-path changes will center on `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `README.md`, and `docs/runbook.md`.

</code_context>

<specifics>
## Specific Ideas

- Treat this repo as an operator-facing backend system, not a consumer-facing product surface.
- Keep config diffs reviewable and explicit; avoid introducing heavy templating or inheritance into registries.
- Keep registry mutation power deliberately narrow from the CLI/API surface.
- Expose history intentionally for auditability, but do not make routine reads noisy.
- Support a real local developer workflow outside Docker only when the machine is on Python 3.11+.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation-and-contracts*
*Context gathered: 2026-03-10*
