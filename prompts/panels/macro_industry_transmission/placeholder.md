# Macro Industry Transmission Scaffold

## Panel Purpose
Assess how macro variables and industry transmission channels alter demand, costs, financing conditions, and risk posture.

## Scaffold Status
This panel is scaffold-only. It documents the intended analysis surface for future implementation and is not approved for production execution.

## Output Contract
When implemented, the panel lead must produce a `PanelVerdict` backed by typed evidence, claim cards, and verdict memory records.

## Affected Memo Sections
- `risk`

## Factor Coverage
- `macro_variable_exposure`
- `transmission_mechanisms`
- `cycle_sensitivity`
- `value_chain_relationships`
- `commodity_input_sensitivity`
- `fx_rates_credit_exposure`
- `budget_cycle_exposure`
- `regulation_subsidy_tax_transmission`

## Evidence And Provenance Expectations
- Use sourceable evidence with dates, units, and provenance for macro sensitivity, value-chain pass-through, and financing exposure.
- Distinguish direct company exposure from second-order industry transmission effects when judging materiality.
- Flag missing macro linkage evidence explicitly instead of assuming a recession, rate, or commodity view automatically applies.

## Future Implementation Handoff
- Keep the panel id, memo sections, and factor coverage aligned with config before adding runnable agents.
- Reuse the shared debate subgraph when specialists and judge roles are introduced, rather than adding bespoke orchestration.
- Preserve scaffold-only wording until macro and industry workflows can trace transmission paths with auditable evidence.
