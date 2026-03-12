# Expectations Catalyst Realization Scaffold

## Panel Purpose
Assess what the market already expects, where a credible variant view exists, and how that view could be realized or disproven.

## Scaffold Status
This panel is scaffold-only. It documents the intended analysis surface for future implementation and is not approved for production execution.

## Output Contract
When implemented, the panel lead must produce a `PanelVerdict` backed by typed evidence, claim cards, and verdict memory records.

## Affected Memo Sections
- `expectations_variant_view`
- `realization_path_catalysts`

## Factor Coverage
- `implied_expectations`
- `consensus_narrative_map`
- `variant_view`
- `falsification_kill_criteria`
- `catalyst_path`
- `timing_path_dependency`
- `milestone_checklist`

## Evidence And Provenance Expectations
- Use sourceable evidence with dates, units, and provenance for valuation context, consensus framing, milestones, and catalyst sequencing.
- Distinguish thesis statements from actual falsification criteria so the variant view can be disproved, not just narrated.
- Flag missing expectations evidence explicitly when price, consensus, or milestone references remain hand-wavy.

## Future Implementation Handoff
- Keep the panel id, memo sections, and factor coverage aligned with config before adding runnable agents.
- Reuse the shared debate subgraph when specialists and judge roles are introduced, rather than adding bespoke orchestration.
- Preserve scaffold-only wording until expectations and catalyst workflows can compare consensus, variant view, and milestone updates across reruns.
