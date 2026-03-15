# Phase 4: Monitoring And Connectors - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 expands reusable monitoring services, deepens the sample connector surface, and adds additive operator-facing read models for monitoring history and portfolio-level visibility. The scope stays inside the existing typed evidence, memo, and delta contracts: richer connectors must still normalize into structured records, monitoring output must stay additive to `MonitoringDelta`, and portfolio visibility remains read-only rather than making `portfolio_fit_positioning` runnable.

</domain>

<decisions>
## Implementation Decisions

### Connector posture
- Add one lightweight live public connector path in Phase 4.
- The live path should prove a realistic recurring public evidence refresh, not a near-production vendor integration.
- Public connector emphasis should center on `market`, `events`, `ownership`, and `transcript/news` evidence families.
- Private connector emphasis should center on `dataroom` plus `KPI packet` evidence.

### Artifact handling and evidence granularity
- Keep raw landing zones flattened, but apply stable renames or prefixes when duplicate filenames would collide.
- Treat PDFs and spreadsheets as first-class evidence when extraction is feasible.
- Keep HTML and image artifacts attachment-only by default unless a later phase explicitly expands that policy.
- For packet-style sources, create one `EvidenceRecord` per meaningful item or document rather than one giant packet record or ultra-granular metric-by-metric records.
- The lightweight live connector should be usable by default, but its outputs must be explicitly time-bounded and staleness-tagged.

### Monitoring explanation depth
- Keep `MonitoringDelta` operator-facing output balanced: concise summary plus structured reasons for why the delta changed.
- When analog or base-rate support is relevant, show the top 1-2 references with a short explanation of why they are similar.
- Surface contradictions whenever the system finds meaningful conflicting evidence on a factor, not only when recommendation or risk changes.
- For concentration and thesis drift, show a broader current-state view rather than only worsening signals.

### Portfolio read surface
- Phase 4 should expose company monitoring history plus one portfolio-level monitoring summary.
- Organize the portfolio-level summary primarily by change type rather than by company or severity first.
- Include both portfolio and watchlist names in the summary by default, but keep them clearly separated so current holdings never blur with watchlist coverage.
- Portfolio-level analog output should default to actionable shared-risk or overlap clusters in the main summary.
- Broader exploratory analog discovery may exist, but it should appear as a secondary drill-down rather than sharing equal prominence with the main summary.

### Claude's Discretion
- Choose the specific lightweight live public connector source as long as it fits the repo's non-premium, test-double-friendly scope and supports recurring-refresh semantics.
- Choose the exact stable rename scheme for duplicate raw artifacts as long as collisions are deterministic and provenance remains clear.
- Choose the exact additive `MonitoringDelta` detail fields as long as they support structured reasons, 1-2 analog references, contradiction visibility, and a broader concentration/thesis-drift view without breaking old payloads.
- Choose the exact read-model and CLI/API payload shapes for company history and portfolio summaries as long as portfolio and watchlist remain visually and structurally distinct.

</decisions>

<specifics>
## Specific Ideas

- The live connector should feel like proof that the generalized connector seam can refresh real public evidence on a recurring basis, not a one-off demo and not a premium-vendor commitment.
- "First-class evidence" means a standalone normalized `EvidenceRecord` with its own provenance, factor tags, time period, quality, and staleness metadata.
- Public evidence breadth matters more for this phase than covering every hinted connector family; `market`, `events`, `ownership`, and `transcript/news` are the representative public mix to prioritize.
- Private evidence should feel like real diligence support, but Phase 4 does not need to sprawl beyond `dataroom` and `KPI packet` examples.
- Portfolio summaries may include watchlist names, but operators must be able to distinguish current portfolio names from watchlist names immediately.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config/source_connectors.yaml`: already provides a config-shaped connector inventory with ids, company types, kinds, manifest files, and raw landing zones.
- `src/ai_investing/ingestion/base.py`: already defines the stable connector contract as typed `CompanyProfile` plus `EvidenceRecord` output.
- `src/ai_investing/ingestion/file_connectors.py`: already implements strict manifest validation, raw provenance capture, evidence normalization, and quality/staleness tagging for file-backed bundles.
- `src/ai_investing/application/services.py`: already owns both ingestion entrypoints and the current monitoring-delta computation path, making it the natural seam for delegation rather than orchestration rewrites.
- `src/ai_investing/domain/models.py`: already provides the typed `MonitoringDelta` contract that Phase 4 should extend additively.
- `src/ai_investing/tools/builtins.py`: already contains `contradiction_finder` and `analog_lookup`, which should converge with the richer monitoring services rather than drift separately.
- `src/ai_investing/api/main.py` and `src/ai_investing/cli.py`: already expose stable run, memo, delta, and ingestion surfaces that Phase 4 should extend additively.
- `tests/test_ingestion.py`, `tests/test_monitoring_semantics.py`, `tests/test_run_lifecycle.py`, `tests/test_api.py`, and `tests/test_cli.py`: already lock the current ingestion, monitoring, lifecycle, and operator-surface contracts.

### Established Patterns
- Connectors normalize data into typed domain records during ingestion rather than passing connector-specific payloads deeper into the run graph.
- Raw provenance preservation through immutable landing zones is already part of the design and should remain mandatory.
- Monitoring semantics are based on structured claim, verdict, and memo-posture changes rather than raw memo text churn.
- Confidence-only drift below `0.05` is intentionally non-material by itself, and `what_changed_since_last_run` always refreshes on reruns.
- Paused gatekeeper runs must still project the full memo structure, and richer monitoring must not break `stale`, `not_advanced`, or provisional section behavior.
- Scaffold-only panels remain visible in config but non-runnable; `portfolio_fit_positioning` stays scaffold-only in Phase 4 even if new read models expose more portfolio monitoring.
- Portfolio fit, company quality, and security/deal overlay remain separate analytical surfaces and should not be collapsed in monitoring or read-side views.

### Integration Points
- Connector-runtime work will center on `config/source_connectors.yaml`, `src/ai_investing/ingestion/`, and the ingestion path inside `src/ai_investing/application/services.py`.
- Richer evidence-family handling must still feed repository-backed evidence retrieval and downstream factor/panel workflows through normalized `EvidenceRecord` metadata.
- Monitoring-service work will center on `src/ai_investing/application/services.py`, `src/ai_investing/tools/builtins.py`, `config/monitoring.yaml`, and additive fields in `src/ai_investing/domain/models.py`.
- Portfolio read-side work should extend repositories plus shared service code, then surface through additive CLI and API endpoints rather than bypassing the existing operator surface.
- Existing Phase 4 plans were created before this context existed, so downstream planning should reconcile them against these decisions before execution.

</code_context>

<deferred>
## Deferred Ideas

- Premium or near-production live vendor integrations are out of scope for this phase.
- Making `portfolio_fit_positioning` runnable remains a later implementation phase; Phase 4 only adds read-only visibility.
- Full per-factor portfolio rollups or equally prominent exploratory analog discovery are deferred beyond the Phase 4 first cut.
- Expanding HTML or image artifacts into first-class evidence by default is deferred unless a later phase selects that explicitly.

</deferred>

---

*Phase: 04-monitoring-and-connectors*
*Context gathered: 2026-03-12*
