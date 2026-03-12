# Security Or Deal Overlay Scaffold

## Panel Purpose
Assess security-specific or deal-specific terms, flows, and market structure that can change entry price, upside capture, or downside realization.

## Scaffold Status
This panel is scaffold-only. It documents the intended analysis surface for future implementation and is not approved for production execution.

## Output Contract
When implemented, the panel lead must produce a `PanelVerdict` backed by typed evidence, claim cards, and verdict memory records.

## Affected Memo Sections
- `valuation_terms`
- `overall_recommendation`

## Factor Coverage
- `valuation_multiples_vs_peers`
- `insider_institutional_flow`
- `technical_stock_movement`
- `positioning_liquidity`
- `borrow_short_interest_if_relevant`
- `cap_table`
- `financing_dependency`
- `round_terms_preferences`
- `control_rights`
- `exit_path`

## Evidence And Provenance Expectations
- Use sourceable evidence with dates, units, and provenance for valuation, ownership, trading, financing terms, and exit mechanics.
- Distinguish business quality from security structure so deal terms and market flows do not get mixed into core-company analysis.
- Flag missing overlay evidence explicitly when borrow, cap table, or exit economics are inferred rather than documented.

## Future Implementation Handoff
- Keep the panel id, memo sections, and factor coverage aligned with config before adding runnable agents.
- Reuse the shared debate subgraph when specialists and judge roles are introduced, rather than adding bespoke orchestration.
- Preserve scaffold-only wording until security-overlay workflows can ground valuation, flow, and term analysis in repeatable source collection.
