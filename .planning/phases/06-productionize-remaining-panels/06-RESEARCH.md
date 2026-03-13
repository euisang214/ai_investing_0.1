# Phase 6 Research: Productionize Remaining Panels

## Current Baseline

- `gatekeepers` and `demand_revenue_quality` are the only runnable panels today.
- The remaining scaffold-only panels are:
  - `supply_product_operations`
  - `market_structure_growth`
  - `macro_industry_transmission`
  - `management_governance_capital_allocation`
  - `financial_quality_liquidity_economic_model`
  - `external_regulatory_geopolitical`
  - `expectations_catalyst_realization`
  - `security_or_deal_overlay`
  - `portfolio_fit_positioning`
- The runtime shape is already reusable:
  - panel inventory and memo ownership live in `config/panels.yaml`
  - factor ownership lives in `config/factors.yaml`
  - agent topology lives in `config/agents.yaml`
  - execution composes configured panels through `build_company_refresh_graph()` and the shared `debate` subgraph
- The current block is intentional:
  - `_resolve_panel_ids()` rejects `implemented: false` panels before run creation
  - scaffold panels only have disabled placeholder leads
  - placeholder prompts are locked by tests and docs
- Critical truthfulness gap: no current manifest under `examples/` tags evidence to any of the nine remaining panels. Today the repo has connector breadth, but not panel-specific evidence coverage for Phase 6.

## Standard Stack

- Keep LangGraph orchestration and the shared `gatekeeper` / `debate` subgraph model.
- Keep YAML registries as the control plane:
  - `config/panels.yaml`
  - `config/factors.yaml`
  - `config/agents.yaml`
  - `config/run_policies.yaml`
  - `config/tool_bundles.yaml`
- Keep prompts in Markdown under `prompts/`.
- Keep structured persistence centered on `ClaimCard`, `PanelVerdict`, `MemoSectionUpdate`, `ICMemo`, and `MonitoringDelta`.
- Keep fake-provider support for deterministic regression tests, but require fixture-backed truthfulness tests before marking a panel productionized.

## Architecture Patterns

- Reuse the existing per-panel pattern:
  - specialists produce `ClaimCard`
  - judge produces `PanelVerdict`
  - memo updater rewrites only affected sections
  - IC synthesis reconciles the full memo and rerun delta
- Add rollout by run policy, not by orchestration branch.
  - Keep `weekly_default` narrow during rollout.
  - Add wave-specific policies instead of using `full_surface` as the only intermediate surface.
- Add panel support evaluation as a reusable runtime step before panel execution.
  - `implemented: true` should mean the panel is globally productionized.
  - per-run support should still be able to skip a panel explicitly when context is insufficient.
- Keep company quality, security/deal overlay, and portfolio fit separate all the way through prompts, policies, memo wording, and verification.

## Rollout Waves

### Wave 0: Foundation

Ship the runtime and config changes that let implemented panels run honestly without requiring every run to support every panel.

- Add wave-specific run policies.
- Add config-driven panel support rules.
- Add explicit skipped-panel surfacing in run results, CLI, API, and generated artifacts.
- Update memo / IC wording so missing overlay support does not masquerade as a complete `overall_recommendation`.

### Wave 1: Internal Company-Quality Panels

Productionize the panels with the strongest path to truthful public and private evidence using existing filing, dataroom, KPI, transcript, and core company documents.

- `supply_product_operations`
- `management_governance_capital_allocation`
- `financial_quality_liquidity_economic_model`

Why first:

- They are company-quality panels.
- They can lean most on company-provided or filing-like evidence.
- They avoid the portfolio/security overlay seam.

### Wave 2: External Company-Quality Panels

Productionize the panels that depend on external context and transmission logic.

- `market_structure_growth`
- `macro_industry_transmission`
- `external_regulatory_geopolitical`

Why second:

- They need richer public market / regulatory evidence and private diligence analogs.
- They are still company-quality, but truthfulness depends more heavily on connector/fixture depth.

### Wave 3: Expectations And Realization

- `expectations_catalyst_realization`

Why third:

- It depends on Wave 1 and Wave 2 outputs to form a credible variant view.
- It also depends on consensus / milestone / rerun-aware context, so it benefits from the earlier support-channel work.

### Wave 4: Final Overlays

- `security_or_deal_overlay`
- `portfolio_fit_positioning`

Why last:

- Phase context explicitly requires overlays to be the final wave.
- `security_or_deal_overlay` needs security-specific or deal-specific context, not generic company evidence.
- `portfolio_fit_positioning` needs real portfolio/book context; the current runtime has no agent-accessible portfolio-context tool.

## Config, Prompt, And Schema Work

### Config

- Replace each placeholder lead with a real agent tree in `config/agents.yaml`:
  - advocate
  - skeptic
  - durability
  - judge
  - lead
- Flip `implemented` to `true` only wave-by-wave after prompts, evidence fixtures, and tests exist.
- Add wave policies to `config/run_policies.yaml`, for example:
  - Wave 1 company-quality
  - Wave 2 company-quality
  - Wave 3 expectations
  - final `full_surface`
- Add a config-driven support/readiness block per panel, either as an additive `PanelConfig` field or a separate panel-support registry. The runtime needs panel-specific rules such as:
  - minimum evidence count
  - minimum factor coverage ratio
  - required evidence families by company type
  - whether thin evidence yields weak confidence vs explicit skip
  - whether special context is mandatory (`portfolio_fit_positioning`, `security_or_deal_overlay`)

### Prompts

- Replace each `placeholder.md` with role-specific prompts under the existing panel directories.
- Update `prompts/ic/synthesizer.md` so `overall_recommendation` can say:
  - company-quality only
  - overlay pending
  - overlay unsupported for this run
- Update `prompts/memo_updates/section_update.md` so skipped or weak-confidence panels are rendered honestly instead of reading like normal refreshed sections.
- Keep panel-specific evidence expectations in prompt text; do not move those rules into source code comments.

### Schema

- The current core schemas are sufficient for completed panels.
- Add an additive structured skip surface for unsupported panels. Minimum need:
  - `panel_id`
  - `reason`
  - `company_type`
  - support/evidence summary
- Prefer a typed model over opaque prose in run metadata if the skip state must be persisted or exposed broadly.
- Keep `ClaimCard` / `PanelVerdict` unchanged for successful execution where possible.

## Runtime And Service Changes

### Required

- Keep `_resolve_panel_ids()` as the global implementation gate, but stop using it as the only truthfulness control once a panel is productionized.
- Add a generic per-panel support check in runtime before `execute_panel()`.
  - If the panel is supported, run it.
  - If the panel is not supported for this run, skip it explicitly and keep the run going.
- Surface skipped panels in:
  - service result payloads
  - CLI / API responses
  - generated examples
  - operator-facing memo / IC wording

### Strongly Recommended

- Make agent `input_channels` real.
  - Today `input_channels` are declarative, but panel execution is hardcoded.
  - `_run_specialists()` only passes evidence, prior-claim text, and section ids.
  - `_run_judge()` ignores configured evidence channels and passes claims only.
  - `finalize_panel_verdict()` does not actually execute a lead prompt; it only prefixes the judge verdict.
- Phase 6 will be easier and more truthful if runtime builds agent input from config rather than continuing the current hardcoded payload shape.
- The minimum generic channel set worth honoring now:
  - `evidence`
  - `prior_claims`
  - `prior_memo`
  - `claims`
  - `panel_verdict`
  - `panel_verdicts`
  - `memo_sections`
  - `prior_run`

### Overlay-Specific Runtime Gap

- `portfolio_fit_positioning` currently lacks an agent-accessible source of portfolio/book context.
- The repo has `PortfolioReadService`, but agents cannot access it through current execution flow.
- Phase 6 likely needs one additive least-privilege tool or runtime-provided input for:
  - current book overlap
  - shared-risk clusters
  - coverage status segmentation
  - portfolio summary context
- Do not widen this into a new orchestration family; make it one reusable context/tool seam.

## Evidence And Truthfulness Requirements

- Do not mark a panel productionized until both public and private fixture paths exist and are truthful.
- Thin evidence is acceptable only when the output says so explicitly.
  - weak confidence is acceptable
  - fabricated confidence is not
- Unsupported context should skip the panel, not reject the whole run.
- The main missing repo work is evidence tagging and fixture expansion:
  - no current example manifests tag the nine remaining panels
  - public fixtures need factor/panel coverage beyond the current gatekeeper/demand tags
  - private fixtures need more than dataroom + KPI support for overlays, financial quality, and external/market views
- Recommended posture by panel family:
  - internal company-quality panels: allow thin evidence with weak confidence
  - external company-quality panels: allow thin evidence only when provenance is explicit and missing context is called out
  - `expectations_catalyst_realization`: require consensus / expectation / milestone grounding or skip
  - `security_or_deal_overlay`: require security/deal-specific context or skip
  - `portfolio_fit_positioning`: require real portfolio context or skip

## Tool Bundle Implications

- Keep tool bundles config-driven.
- Do not assume new tool bundles alone make panels runnable.
  - current panel execution only calls `evidence_search` and `claim_search`
  - most other configured tools are currently inert during panel runs
- Phase 6 should avoid building a generic autonomous tool-calling loop.
- Prefer this order:
  1. ingest or fixture the evidence needed for the panel
  2. search that evidence through the existing memory tools
  3. add only narrow new runtime/tool seams where evidence cannot naturally be ingested (`portfolio_fit_positioning`)

## Don’t Hand-Roll

- Do not add new panel families or bespoke orchestration branches.
- Do not introduce one-off per-panel graph builders.
- Do not collapse security/deal overlay or portfolio fit into company-quality prompts.
- Do not rely on `full_surface` as the only rollout lever.
- Do not treat config visibility as execution readiness.
- Do not implement broad LLM tool-calling infrastructure as a prerequisite for V2-01.

## Common Pitfalls

- Marking panels `implemented: true` before evidence fixtures and tests exist.
- Replacing placeholder prompts without making the lead/judge/runtime path actually consume the new prompt inputs.
- Letting fake-provider runs pass without thin-evidence or skip-path assertions.
- Returning a polished `overall_recommendation` when overlay panels were skipped or unsupported.
- Building public-only truthfulness and calling the panel done.
- Hiding skipped panels by omission instead of surfacing a structured reason.

## Recommended Plan Decomposition

1. Foundation and rollout contract
   - add wave run policies
   - add per-panel support/readiness config
   - add explicit skip/result surfaces
   - make memo/IC wording overlay-aware
   - decide whether lead execution and generic `input_channels` become real in this slice
2. Wave 1 internal company-quality panels
   - agent trees
   - prompts
   - evidence fixture/tagging expansion for both company types
   - service/API/CLI tests
3. Wave 2 external company-quality panels
   - same work pattern
   - heavier connector/fixture and truthfulness coverage
4. Wave 3 expectations/catalyst
   - consensus / milestone / rerun-aware support
   - delta-focused verification
5. Wave 4 overlays
   - security/deal-specific support rules
   - portfolio-context seam
   - explicit partial-recommendation wording
6. Docs, checked artifacts, and final verification
   - regenerate examples
   - update README/docs/runbook/architecture/factor ontology/memory docs
   - update planning state after rollout

## Code Examples

- Reuse `src/ai_investing/graphs/company_refresh.py` for sequential panel composition.
- Reuse `src/ai_investing/graphs/subgraphs.py` and keep the `debate` path as the default for all non-gatekeeper panels.
- Extend `RefreshRuntime` in `src/ai_investing/application/services.py` rather than creating panel-specific runtimes.
- Keep prompt assets under:
  - `prompts/panels/<panel_id>/...`
  - `prompts/ic/synthesizer.md`
  - `prompts/memo_updates/section_update.md`

## Validation Architecture

- Registry validation
  - each productionized panel has enabled advocate/skeptic/durability/judge/lead agents
  - panel prompt inventory exists and aligns to config
  - factor ownership remains panel-local
  - wave run policies contain only intended panels
- Truthfulness validation
  - public and private fixture runs for every productionized panel
  - thin-evidence runs downgrade confidence visibly
  - unsupported-context runs skip explicitly and do not fabricate verdicts
- Runtime validation
  - memo updates remain section-scoped
  - rerun delta logic still writes `what_changed_since_last_run`
  - skipped overlay panels do not block company-quality completion
  - `overall_recommendation` stays explicit about missing overlays
- Interface validation
  - service / CLI / API all surface the same skip semantics
  - wave policies are runnable before `full_surface` is made the default end-state
- Artifact validation
  - regenerate checked examples for at least:
    - public company wave run
    - private company wave run
    - rerun delta after a prior active memo
    - overlay skip due to missing portfolio/security context
- Suggested verification commands
  - targeted pytest per changed area while building
  - final full `pytest`
  - `ruff check src tests`
  - regenerate and diff checked examples

