# Prompting Strategy

## Prompt Storage

All substantive prompts live in `prompts/`. The runtime loads them by path from config rather than embedding large instructions in Python code.

## v1 Pattern

- role prompts for specialist, skeptic, durability, judge, and lead agents
- memo update prompt for section-level updates
- IC synthesis prompt for final reconciliation
- monitoring prompt for delta narratives

## Design Constraints

- Prompts should stay concise and schema-aware.
- Prompts should assume evidence-grounded outputs only.
- Delta-aware tasks should always compare against prior active memory when available.
- A prompt change should not require business-logic changes unless the schema contract changes too.

## Scaffold Prompt Contract

Scaffold placeholder prompts remain first-class prompt assets on disk. They are not throwaway text, and they must stay editable in Markdown rather than moving scaffold detail into Python code.

Every scaffold-only panel prompt should include these headings in the same order:

- `Panel Purpose`
- `Scaffold Status`
- `Output Contract`
- `Affected Memo Sections`
- `Factor Coverage`
- `Evidence And Provenance Expectations`
- `Future Implementation Handoff`

The scaffold contract is intentionally schema-aware:

- `Output Contract` should name `PanelVerdict`.
- `Affected Memo Sections` should mirror the owning panel's `memo_section_ids` in `config/panels.yaml`.
- `Factor Coverage` should mirror the owning panel's `factor_ids` in `config/panels.yaml` and the same factor ownership in `config/factors.yaml`.
- Evidence expectations should call for dated, sourceable provenance and should state that missing evidence must be surfaced rather than narrated away.

## Maintenance Rules

- Keep scaffold placeholder prompts on disk at the `prompt_path` referenced by panel config, even before the panel is runnable.
- Keep prompts panel-specific about memo sections, factor coverage, and evidence needs; do not collapse them back into generic "not implemented" boilerplate.
- Keep ontology meaning in YAML and prompt framing in Markdown so future panel expansion remains config-driven.
- When a scaffold panel gains or loses memo sections or factor coverage, update the prompt file in the same change and keep the contract tests green.
- Preserve scaffold-only language until runnable agents, tool bundles, and verification coverage exist for that panel.
