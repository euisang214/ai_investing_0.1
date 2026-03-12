# Portfolio Fit Positioning Scaffold

## Panel Purpose
Assess portfolio interaction effects so position sizing, correlation, crowding, and exitability are explicit before capital is committed.

## Scaffold Status
This panel is scaffold-only. It documents the intended analysis surface for future implementation and is not approved for production execution.

## Output Contract
When implemented, the panel lead must produce a `PanelVerdict` backed by typed evidence, claim cards, and verdict memory records.

## Affected Memo Sections
- `portfolio_fit_positioning`
- `overall_recommendation`

## Factor Coverage
- `liquidity_exitability`
- `factor_exposures`
- `correlation_to_existing_book`
- `crowding`
- `downside_gap_risk`
- `event_risk_overlap`
- `sizing_considerations`
- `expected_value_vs_capital_at_risk`

## Evidence And Provenance Expectations
- Use sourceable evidence with dates, units, and provenance for liquidity, factor exposures, correlations, crowding, and sizing assumptions.
- Distinguish standalone attractiveness from portfolio fit so a good company is not automatically treated as a good position.
- Flag missing portfolio-context evidence explicitly when book overlap, exitability, or capital-at-risk estimates are not grounded.

## Future Implementation Handoff
- Keep the panel id, memo sections, and factor coverage aligned with config before adding runnable agents.
- Reuse the shared debate subgraph when specialists and judge roles are introduced, rather than adding bespoke orchestration.
- Preserve scaffold-only wording until portfolio-fit workflows can compare proposed positions against current book exposures and risk limits.
