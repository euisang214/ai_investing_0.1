# External Regulatory Geopolitical Scaffold

## Panel Purpose
Assess external regulatory, legal, tax, and geopolitical forces that can impair the investment case or alter economics abruptly.

## Scaffold Status
This panel is scaffold-only. It documents the intended analysis surface for future implementation and is not approved for production execution.

## Output Contract
When implemented, the panel lead must produce a `PanelVerdict` backed by typed evidence, claim cards, and verdict memory records.

## Affected Memo Sections
- `risk`

## Factor Coverage
- `government_exposure`
- `geopolitical_exposure`
- `subsidies_taxes`
- `litigation_contingent_liabilities`
- `regulatory_dependency`

## Evidence And Provenance Expectations
- Use sourceable evidence with dates, units, and provenance for regulatory filings, legal matters, tax regimes, sanctions, and government counterparties.
- Distinguish background policy noise from concrete mechanisms that can change demand, costs, licenses, or solvency.
- Flag missing legal or geopolitical evidence explicitly when downside depends on assumptions rather than documented exposure.

## Future Implementation Handoff
- Keep the panel id, memo sections, and factor coverage aligned with config before adding runnable agents.
- Reuse the shared debate subgraph when specialists and judge roles are introduced, rather than adding bespoke orchestration.
- Preserve scaffold-only wording until regulatory and geopolitical workflows can connect source events to business-model transmission paths.
