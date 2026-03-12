# Market Structure Growth Scaffold

## Panel Purpose
Assess market structure, addressable demand, and the mix of growth drivers that determine whether expansion is durable or overestimated.

## Scaffold Status
This panel is scaffold-only. It documents the intended analysis surface for future implementation and is not approved for production execution.

## Output Contract
When implemented, the panel lead must produce a `PanelVerdict` backed by typed evidence, claim cards, and verdict memory records.

## Affected Memo Sections
- `growth`
- `expectations_variant_view`

## Factor Coverage
- `industry_market_share_trends`
- `tam`
- `per_product_market_share_history`
- `industry_cagr_vs_revenue_cagr`
- `organic_vs_inorganic_growth`
- `growth_levers`
- `secular_vs_cyclical_growth`
- `adjacency_expansion_runway`

## Evidence And Provenance Expectations
- Use sourceable evidence with dates, units, and provenance for market size, share shifts, product cohorts, and acquisition history.
- Distinguish market growth, share gain, and accounting presentation so reported expansion is not overstated.
- Flag missing market structure evidence explicitly when TAM, adjacencies, or share data remain speculative.

## Future Implementation Handoff
- Keep the panel id, memo sections, and factor coverage aligned with config before adding runnable agents.
- Reuse the shared debate subgraph when specialists and judge roles are introduced, rather than adding bespoke orchestration.
- Preserve scaffold-only wording until market-growth workflows have source coverage for TAM, share, and adjacency validation.
