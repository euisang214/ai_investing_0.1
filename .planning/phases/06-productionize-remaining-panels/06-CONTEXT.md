# Phase 6: Productionize Remaining Panels - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 turns the remaining scaffold-only top-level panels into executable, verified production flows without breaking the config-driven runtime. The scope is fixed to productionizing the existing panel surface under `V2-01`: no new panel families, no collapse of company quality into overlays, and no bespoke orchestration expansion unless the current abstractions truly cannot support a reusable need.

</domain>

<decisions>
## Implementation Decisions

### Rollout shape
- Deliver Phase 6 in waves by family rather than all at once or one panel per plan.
- Use a company-quality-first rollout order.
- Keep the default operator path hybrid during rollout: newly productionized panels can become runnable before they are added to the normal default policy.
- Use wave-specific run policies during rollout rather than reusing `full_surface` as the only intermediate path.
- Keep `full_surface` as the end-state policy, not the only rollout vehicle.

### Evidence sufficiency posture
- Hold a strict readiness bar for calling a panel productionized: the panel is not considered production-ready unless its factor coverage is substantively supported.
- If a live run reaches a productionized panel with thin company-specific evidence, still run the panel but emit explicit weak-confidence output rather than silently degrading confidence or blocking the whole run.
- Allow light panel-specific evidence expansion where needed, but do not require fully mature connector breadth before Phase 6 can ship.
- Use a high verification bar: fake-provider coverage is not enough on its own; productionized panels also need explicit truthfulness coverage and inspectable generated artifacts/examples.

### Public vs private coverage policy
- Treat both public and private company support as part of panel productionization from day one; do not declare a panel productionized for only one company type.
- Keep `scope: both` in panel config and enforce truthfulness through evidence and runtime gating rules rather than splitting the panel surface into separate config objects.
- When a panel is not supportable for a specific run or company context, skip that panel explicitly instead of rejecting the whole run.
- Do not bias Phase 6 toward public-first or private-first delivery; whichever company-quality panel family can be made truthful for both types should move first.

### Overlay activation policy
- Treat `security_or_deal_overlay` and `portfolio_fit_positioning` as the last wave only, after the company-quality waves are already productionized.
- Require a high context bar for `security_or_deal_overlay`; generic company evidence is not sufficient on its own.
- Require a high context bar for `portfolio_fit_positioning`; real portfolio and book context is required before it is considered supported.
- When overlays are absent or not supported for a run, keep the company-quality recommendation separate rather than pretending the final overall recommendation is fully complete.

### Claude's Discretion
- Choose the exact wave boundaries within the company-quality-first rollout, as long as overlays remain the final wave and the sequencing stays truthful to the analytical separation rules.
- Choose the exact names and composition of the intermediate wave-specific run policies.
- Choose the exact panel-skip surface and operator-facing wording, as long as skipped panels are explicit in run outputs and do not masquerade as completed analysis.
- Choose the exact evidence sufficiency heuristics and artifact set needed to satisfy the high verification bar, as long as panel readiness remains strict and thin-evidence execution remains visibly weak-confidence.

</decisions>

<specifics>
## Specific Ideas

- The rollout should proceed chronologically through company-quality analysis before touching overlay layers.
- Overlay panels should not ride with earlier waves just because nearby memo sections exist.
- The system should preserve an honest distinction between company-quality conclusions and later security or portfolio overlays.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ai_investing/graphs/company_refresh.py`: already composes panel execution from configured `panel_ids`, panel subgraphs, memo updates, monitoring, and IC synthesis, so Phase 6 should reuse this flow rather than introduce per-panel orchestration.
- `src/ai_investing/graphs/subgraphs.py`: the generic `debate` path already supports non-gatekeeper panels through the same specialist/judge/finalize sequence.
- `src/ai_investing/application/services.py`: `_resolve_panel_ids()`, `execute_panel()`, `_run_specialists()`, `_run_judge()`, `update_memo_for_panel()`, and `_build_memo()` already centralize panel execution, memo projection, and gating behavior.
- `config/panels.yaml`, `config/factors.yaml`, and `config/agents.yaml`: all remaining panels, factor ownership, and scaffold placeholders already exist and provide the main extension surface.
- `config/run_policies.yaml`: the repo already separates `weekly_default` from `full_surface`, which provides a natural seam for wave-specific rollout policies.
- `src/ai_investing/tools/builtins.py` and `config/tool_bundles.yaml`: evidence and claim retrieval are already bundle-enforced and can support light panel-specific evidence expansion without changing orchestration shape.
- `src/ai_investing/providers/fake.py`: the fake provider already supports generic claim and panel verdict generation across factor-driven panels, making it suitable for deterministic regression coverage and generated examples.

### Established Patterns
- The runtime already treats `gatekeepers` as the only hardcoded checkpointed special case; all remaining panels are expected to fit the shared `debate` path.
- Memo section ownership is derived from panel config and passed through claim `section_impacts` plus verdict `affected_section_ids`; panel rollout decisions therefore directly shape memo completeness and overwrite behavior.
- The repo intentionally keeps company quality, `security_or_deal_overlay`, and `portfolio_fit_positioning` separate in ontology, docs, and config.
- Current tests intentionally anchor the implemented/scaffold split around `gatekeepers` and `demand_revenue_quality`; Phase 6 planning must update those tests deliberately rather than incidentally.
- Current fake-provider success can mask thin evidence; Phase 6 verification must add truthfulness coverage beyond merely making tests green.

### Integration Points
- Wave rollout policy work will center on `config/run_policies.yaml`, policy-sensitive execution in `src/ai_investing/application/services.py`, and corresponding CLI/API/runtime tests.
- Panel productionization work will center on replacing scaffold placeholders in `config/agents.yaml`, upgrading prompt assets under `prompts/panels/`, and marking readiness in `config/panels.yaml`.
- Evidence sufficiency and explicit weak-confidence behavior will center on evidence tagging/fixture expansion in ingestion assets plus claim/verdict truthfulness tests around `src/ai_investing/providers/fake.py`, `src/ai_investing/application/services.py`, and monitoring/example generation.
- Explicit panel skipping for unsupported run contexts will need aligned service, CLI, API, and artifact behavior so skipped panels remain visible and truthful rather than silently disappearing.
- Overlay-final rollout will need memo and IC behavior to preserve a clear company-quality recommendation even before overlay sections are productionized.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-productionize-remaining-panels*
*Context gathered: 2026-03-13*
