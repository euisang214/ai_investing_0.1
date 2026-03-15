# Phase 4 Research: Monitoring And Connectors

## Scope Snapshot

- Phase 4 targets `V2-02` and `V2-04`.
- Goal: expand reusable monitoring services and connector depth after the Phase 2 vertical slice and Phase 3 scaffold work stabilized the core runtime.
- Success criteria already narrow the phase: broaden dependency concentration, base-rate analog, contradiction, and thesis-drift services; add richer public/private adapters; enrich monitoring outputs without changing memo contracts.

## Current Repo State Relevant To Phase 4

- Monitoring is already part of the production runtime, not a stub. `RefreshRuntime` computes and persists a `MonitoringDelta` and refreshes `what_changed_since_last_run` on reruns.
- Monitoring materiality is mostly config-driven through `config/monitoring.yaml`. Current config covers confidence materiality, always-refresh sections, alert escalation sections, and four drift flags.
- Memo projection behavior is already locked down by tests: paused gatekeeper runs still project the full memo, untouched downstream sections remain `not_advanced`, reruns can mark carried-forward sections `stale`, and provisional runs prefix refreshed sections.
- Connector configuration exists in `config/source_connectors.yaml`, but runtime ingestion is still hardcoded to `public_file_connector` and `private_file_connector`. `mcp_stub` is only an extension marker today.
- The existing file connector is the main contract to preserve. It copies raw artifacts and normalizes them into `EvidenceRecord` objects with provenance, factor tags, time period, quality, and staleness metadata.
- Tooling already exposes the intended Phase 4 extension surface. `config/tool_registry.yaml` includes stubbed tools for filings, transcripts, public news, market/estimate/ownership/event queries, plus builtins such as `contradiction_finder` and `analog_lookup`.
- Portfolio-level analytics views do not exist yet in the current runtime surface.

## Implementation Seams And Constraints

- Keep connector expansion behind reusable abstractions. The current `IngestionService` hardcodes connector ids and `file_bundle` behavior; Phase 4 should introduce a connector factory/registry rather than add more `if connector_id == ...` branches.
- Preserve the existing normalized evidence contract. New adapters can add evidence types, but they should still land as typed `EvidenceRecord` objects with raw artifact provenance and quality/staleness metadata.
- Keep monitoring enrichment behind the existing monitoring service seam, centered on `compute_monitoring_delta()` and the monitoring subgraph. Do not leak new logic into memo-writing or graph composition unnecessarily.
- Memo contracts are intentionally stable. Richer monitoring must stay additive to delta output and operator surfaces, not a rewrite of memo section ids, section semantics, or `what_changed_since_last_run`.
- Portfolio analytics should be a separate aggregation/read-model concern. The current tool context is company-scoped, so cross-company views should not silently widen single-company tool semantics.
- Monitoring config is flexible but weakly typed today. Adding richer rules without stronger validation risks silent no-op config drift.
- The repo still expects Docker or Python `3.11+` for trustworthy verification. The host machine noted in `STATE.md` is Python `3.9.6`, so plans should assume Docker-based validation.

## Recommended Plan Breakdown

1. Connector Runtime Generalization
   - Add a connector factory/registry keyed from `config/source_connectors.yaml`.
   - Move file-bundle-specific logic out of `IngestionService`.
   - Define connector capabilities explicitly enough that new adapters can be added by config plus adapter code, not orchestration rewrites.

2. Representative Public And Private Adapter Expansion
   - Add a small set of representative public adapters aligned to the existing stub surface, such as filings, transcripts/news, or market/ownership/event evidence.
   - Add richer private adapters that cover more than plain text bundles, such as dataroom exports, diligence artifacts, KPI files, or board/deal materials.
   - Keep these fixture-backed and deterministic unless the phase explicitly chooses a lightweight live sample path.

3. Monitoring Service Deepening
   - Broaden contradiction handling, analog/base-rate retrieval, dependency concentration, and thesis-drift classification as reusable services.
   - Keep output additive on `MonitoringDelta`, for example reason codes, supporting factor ids, analog references, contradiction references, or concentration signals.

4. Portfolio Analytics Read Surface
   - Add a separate service or query layer for cross-company analytics required by `V2-04`.
   - Keep this out of memo contracts and separate from single-company refresh flow.

5. Docs And Regression Coverage
   - Update monitoring and tool-registry docs to describe the new extension points and limits.
   - Add deterministic fixtures and regression tests before widening phase scope further.

## Risks/Pitfalls

- Hardcoding new connector kinds into `IngestionService` would violate the repo's config-driven extension rule and make future adapters expensive again.
- The current file connector assumes local UTF-8-readable artifacts and copies files by basename. PDF/HTML/spreadsheet assets, binary artifacts, and duplicate filenames will need an explicit normalization/raw-storage policy.
- Monitoring change detection is currently narrower than the Phase 4 goal. It appears optimized for current active-claim matching and basic drift flags; removals, multi-claim factors, or richer verdict drift can be underdetected unless the comparison model is widened deliberately.
- Richer monitoring can accidentally change alert levels or memo statuses on stable reruns. Existing materiality semantics are already tested and should be treated as compatibility constraints.
- Portfolio analytics can sprawl into a new product surface. Keep the phase focused on reusable services and read models, not a broad interface redesign.
- If monitoring config stays as a generic dict, new keys may silently do nothing. Stronger schema validation is likely worth planning early.

## Requirement Traceability

| Requirement | What Phase 4 should implement | Notes |
| --- | --- | --- |
| `V2-02` | Connector factory/registry, richer public/private adapters, added connector/tool config, ingestion normalization for more evidence types | This is the main connector-depth requirement. The current repo already advertises the target surface through stub tools and connector config, but runtime support is still file-bundle-only. |
| `V2-04` | Broader contradiction resolution, analog/base-rate services, dependency concentration and thesis-drift enrichment, plus a portfolio analytics read surface | Current builtins and drift flags are the seed surface. Phase 4 should deepen them without changing memo section contracts or single-company refresh entrypoints. |

## Validation Architecture

- Preserve monitoring semantic regressions:
  - confidence-only drift below `0.05` should remain non-material by itself
  - `what_changed_since_last_run` should still refresh every rerun
  - recommendation/gatekeeper/core-risk movement should still escalate alerts correctly
- Preserve memo contract regressions:
  - paused gatekeeper runs still project full memo state
  - reruns still preserve `stale`, `not_advanced`, and provisional semantics
  - richer monitoring output must not require memo section contract changes
- Add connector contract tests:
  - config selects the correct adapter without service hardcoding
  - raw artifacts still persist deterministically
  - normalized evidence still includes provenance, factor tags, quality, and staleness
  - new evidence media types and duplicate-filename cases have explicit coverage
- Add richer monitoring service tests:
  - contradiction, analog, concentration, and thesis-drift outputs are deterministic with fixture data
  - additive delta fields do not break existing `MonitoringDelta` persistence and retrieval
  - claim removals or expanded matching rules are either tested or explicitly deferred
- Add portfolio analytics tests:
  - multi-company aggregates are computed from persisted structured records
  - cross-company views do not mutate or bypass single-company memo and run contracts
- Run verification in Docker so the phase is validated on the repo's supported Python version.

## Planner Guidance

- Treat this phase as service and adapter expansion, not as a reason to rewrite graph composition or memo contracts.
- Pick a representative connector set up front. Trying to cover every hinted connector family in one phase will create shallow abstractions and weak tests.
- Decide early whether richer monitoring stays within the existing `MonitoringDelta` model additively or needs a new typed sub-structure. That choice affects persistence, CLI/API exposure, and regression scope.
