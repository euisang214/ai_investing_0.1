# Phase 3: Remaining Panel Scaffolds - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 completes and hardens the scaffold surface for the remaining top-level panels without expanding the core runtime or turning those panels into runnable production flows. The scope is limited to config-backed panel/factor/agent scaffolding, placeholder prompt quality, policy/test/doc clarity, and extension-path documentation for future implementation work.

</domain>

<decisions>
## Implementation Decisions

### Scaffold depth
- Normalize every remaining top-level panel to have one disabled placeholder lead agent.
- Do not add specialist, skeptic, durability, or judge trees for the remaining panels in Phase 3.
- Keep the placeholder lead agents moderately specific: concrete role goals, prompt paths, likely tool-bundle defaults, and model-profile defaults are desirable, but they must remain clearly scaffold-only.
- Keep the scaffold shape structurally consistent across all remaining top-level panels.
- Do not add new runtime behavior just to support these scaffolds.

### Placeholder fidelity
- Replace generic `"Placeholder factor"` descriptions with real panel-specific factor descriptions for all remaining scaffolded factors.
- Replace one-line placeholder panel prompts with panel-specific scaffold prompts for every remaining panel.
- Use one shared prompt structure across the remaining panel placeholders, but customize each file with that panel's memo sections, factor coverage, and domain framing.
- Keep ontology meaning in config and runtime/task framing in prompt files; do not overload one layer with all specificity.

### Runtime exposure and policy posture
- Keep scaffolded panels visible in config and operator-facing inspection surfaces because config remains the source of truth for the intended panel topology.
- Keep future-facing policies such as `full_surface` loadable in config, even though they reference unimplemented panels.
- Continue to reject execution when a selected policy or explicit panel list includes unimplemented panels; do not make this a startup/load-time validation failure while future-facing policies remain first-class config entries.
- Add explicit tests that unimplemented panels are rejected from execution by default.
- Documentation should state clearly that future-facing scaffold policies may exist in config before they are safely runnable.

### Extension-path documentation
- Add both a short checklist in existing docs and a dedicated guide for taking a scaffolded panel to implementation readiness later.
- Write the extension material for a new engineer who does not already know the repo.
- Use a hybrid style: generic steps plus one short worked example based on one remaining panel.
- Emphasize the exact files to touch and the order of operations more than abstract architecture prose.

### Claude's Discretion
- Choose the exact naming pattern for the disabled placeholder lead agents as long as it is consistent and obviously scaffold-only.
- Choose the exact shared scaffold-prompt headings as long as the structure stays common across panels and the content is panel-specific.
- Choose which existing docs receive the short checklist versus where the dedicated guide lives, as long as both are easy to find.
- Choose the worked example panel for the extension guide, as long as it is one of the remaining scaffolded top-level panels.

</decisions>

<specifics>
## Specific Ideas

- Shared scaffold-prompt headings should include:
  - panel purpose
  - current scaffold-only status
  - output contract (`PanelVerdict`)
  - affected memo sections
  - factor coverage
  - evidence and provenance expectations
  - future implementation handoff note
- `full_surface` should remain visible as a future-facing config policy, but selecting it before the remaining panels are implemented should fail at execution time rather than block config loading.
- One disabled lead placeholder agent per remaining panel is enough for this phase; fuller debate trees belong to later implementation phases.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config/panels.yaml`: already defines all remaining top-level panels with `implemented: false`, prompt paths, and memo-section mappings.
- `config/factors.yaml`: already contains factor IDs for every remaining panel, but the remaining descriptions are still generic placeholders.
- `config/agents.yaml`: already shows the current placeholder-agent pattern for two remaining panels and can be normalized across the rest.
- `config/run_policies.yaml`: already contains both the runnable `weekly_default` policy and the future-facing `full_surface` policy that references scaffolded panels.
- `prompts/panels/*/placeholder.md`: existing prompt files establish the location and naming convention for scaffold prompts.
- `src/ai_investing/application/services.py`: `_resolve_panel_ids()` already blocks execution of unimplemented panels unless policy behavior explicitly changes.
- `src/ai_investing/application/context.py`: `active_agents_for_panel()` and the config-driven registry loading pattern support adding disabled placeholder lead agents without orchestration rewrites.
- `docs/factor_ontology.md`, `docs/architecture.md`, and `README.md`: existing docs already describe the scaffold posture and are the natural places for checklist and extension-path updates.

### Established Patterns
- Config and prompt files are the extension surface; runtime behavior should remain generic and registry-driven.
- Prompts belong in markdown files rather than embedded source code.
- Ontology breadth may exceed implementation breadth; scaffolded factors and panels are acceptable as long as runtime guardrails stay explicit.
- The working vertical slice remains limited to `gatekeepers` and `demand_revenue_quality`; Phase 3 should not blur that boundary.
- Unimplemented panels are currently visible in config but blocked at execution time, which is consistent with keeping the future surface inspectable without making it runnable.

### Integration Points
- Scaffold consistency work will center on `config/agents.yaml`, `config/factors.yaml`, `config/panels.yaml`, and the placeholder prompt files under `prompts/panels/`.
- Runtime-boundary tests will center on the execution-path tests that cover run selection and panel validation.
- Policy/documentation clarity will center on `config/run_policies.yaml`, `README.md`, `docs/architecture.md`, and `docs/factor_ontology.md`.
- Extension-path documentation will likely add one dedicated doc plus checklist updates in the existing architecture or ontology docs.

</code_context>

<deferred>
## Deferred Ideas

- Add explicit config metadata for non-runnable or future-only policies so startup validation can distinguish illustrative scaffold policies from operator-runnable policies.
- Add fuller multi-agent trees and real prompts for the remaining panels once each panel is selected for productionization in a later phase.

</deferred>

---

*Phase: 03-remaining-panel-scaffolds*
*Context gathered: 2026-03-12*
