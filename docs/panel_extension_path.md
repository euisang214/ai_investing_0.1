# Panel Extension Path

## Purpose

This guide shows how to take one scaffold-only panel from Phase 3 posture to implementation readiness without breaking the config-driven runtime. It is written for an engineer who did not build the original vertical slice.

Current boundary:

- `gatekeepers` and `demand_revenue_quality` are the only implemented panels today.
- Every other top-level panel is scaffold-only and may appear in config before it is runnable.
- Runtime changes are allowed only when the abstraction truly needs expansion.

## File-By-File Checklist

Use this checklist before marking any scaffold-only panel as implemented.

| File or Area | What to verify or change | Why it matters |
| --- | --- | --- |
| `config/panels.yaml` | Keep the existing panel id, update `implemented`, confirm `memo_section_ids`, `factor_ids`, `subgraph`, and prompt path | This is the panel contract consumed by the runtime |
| `config/agents.yaml` | Replace disabled placeholder entries with the real advocate, skeptic, durability, judge, and lead tree the panel needs | Agent topology must stay config-driven |
| `config/factors.yaml` | Keep factor ids stable and update descriptions only when ontology meaning changes | Factor ids anchor claims, memory, and tests |
| `prompts/` | Replace placeholder panel prompts and add role-specific prompts for each new agent | Prompt bodies live in Markdown, not source code |
| `config/tool_bundles.yaml` and `config/tool_registry.yaml` | Extend only if the panel needs a new reusable tool contract | Tool access must stay explicit and reusable |
| `tests/` | Add config, runtime, CLI, and API coverage for the new panel | The panel is not implementation-ready until behavior is verified |
| `src/ai_investing/` | Touch runtime code only if a genuinely reusable abstraction is missing | Avoid bespoke orchestration for one panel |

## Order Of Operations

The safest order of operations is:

1. Start in `config/panels.yaml` and confirm the existing scaffolded panel contract is correct.
2. Review the factor inventory in `config/factors.yaml` so the panel scope is explicit before prompts or agents change.
3. Replace the disabled placeholder topology in `config/agents.yaml` with the real agent tree required for that panel.
4. Upgrade the scaffold prompt assets in `prompts/` to implementation-ready role prompts while preserving the same output contracts.
5. Update any tool bundle or tool registry entries only if the panel truly needs different reusable tools.
6. Add tests in `tests/` for registry loading, runtime execution, and user-facing interfaces.
7. Only after the above is green should you flip the panel to implemented and allow it into normal execution paths.

Do not reverse that sequence. If prompts or agents move first without a stable panel and factor contract, the panel drifts away from the config-driven architecture and becomes harder to verify.

## Contracts To Preserve

These contracts should remain stable while the panel moves from scaffold to production:

- Preserve the panel id in `config/panels.yaml`.
- Preserve factor ids in `config/factors.yaml` unless you are deliberately changing ontology, memory namespaces, and downstream tests together.
- Keep prompts in `prompts/` rather than embedding large instructions in Python.
- Keep memo section ownership derived from panel config rather than hand-coded interface logic.
- Keep tool access attached through bundle config, not inline conditionals in runtime code.
- Preserve the existing execution guardrail: config visibility does not imply runnable status.

## Testing Expectations

Implementation readiness requires more than a prompt file and an enabled agent.

Add tests in `tests/` that cover:

- config loading for the panel, factors, prompts, and agents
- service-layer execution behavior
- CLI and API behavior if the panel is user-addressable there
- prompt asset presence and any contract headings the repo expects
- any new reusable tool bundle or provider interaction seam

If a panel needs new runtime changes, add the failing regression first and make the minimal generic fix second. The runtime changes section of this guide is strict on purpose: runtime changes are allowed only when the abstraction truly needs expansion.

## When Runtime Changes Are Actually Allowed

Most panel work should stop at config, prompts, and tests. Runtime changes are justified only when one of these is true:

- the existing subgraph types cannot express the panel's reusable workflow
- a new shared persistence contract is required for correctness
- a new tool execution or provider boundary is needed for multiple panels, not just one

Runtime changes are not justified when:

- a single panel wants special-case branching
- the panel can fit the existing debate or lead patterns with config changes
- the only missing work is prompt quality or agent coverage

If you need runtime changes, prove the gap with tests and design the smallest reusable extension.

## Worked Example: `external_regulatory_geopolitical`

Use `external_regulatory_geopolitical` as the model panel for a future implementation slice.

### 1. Confirm The Existing Scaffold

Start with the current scaffolded assets:

- `config/panels.yaml` already defines `external_regulatory_geopolitical`
- `config/factors.yaml` already defines `government_exposure`, `geopolitical_exposure`, `subsidies_taxes`, `litigation_contingent_liabilities`, and `regulatory_dependency`
- `config/agents.yaml` should evolve from placeholder topology to the real agent tree
- `prompts/panels/external_regulatory/placeholder.md` is the scaffold prompt that should be replaced by implementation-ready prompts

At this stage, do not rename the panel or factor ids. Those ids are the stable contract.

### 2. Expand The Agent Tree

Replace the placeholder in `config/agents.yaml` with the real roles the panel needs, likely:

- advocate
- skeptic
- durability or risk-specific challenger if the existing pattern still fits
- judge
- panel lead

Keep the same `panel_id`, keep bundle assignment explicit, and keep output schemas aligned with `ClaimCard` or `PanelVerdict` as appropriate.

### 3. Upgrade Prompt Assets

Under `prompts/`, create or replace the role prompts for the new agents. The prompts should:

- call out regulatory and geopolitical transmission paths
- require dated and sourceable evidence
- preserve the `PanelVerdict` handoff for the lead flow
- state what memo sections the panel can affect

Do not bury this logic in runtime code. Prompt content belongs in Markdown files on disk.

### 4. Verify Tooling And Runtime Fit

If `external_regulatory_geopolitical` can run inside the existing subgraph and tool-bundle model, do not change the runtime. If it needs a new reusable evidence workflow, add that abstraction once and make it reusable for future panels. This is the point where you decide whether runtime changes are needed, and the default answer should be no.

### 5. Add Tests Before Enabling Execution

Before enabling the panel, add tests in `tests/` that prove:

- config references are valid
- prompt files exist
- the panel can execute through the intended service path
- CLI and API entrypoints either accept or reject the panel exactly as expected
- memo-section and factor mappings stay aligned with config

### 6. Mark The Panel Ready

Only after config, prompts, tests, and any justified reusable runtime changes are in place should you treat `external_regulatory_geopolitical` as implemented. Until then, it stays scaffold-only even if future-facing policies reference it.

## Practical Rule

If you are unsure whether work belongs in config or runtime, start in config. The core extension path for this repository is:

1. config
2. prompts
3. tests
4. runtime changes only when the abstraction truly needs expansion
