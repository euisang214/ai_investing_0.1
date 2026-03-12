# Financial Quality Liquidity Economic Model Scaffold

## Panel Purpose
Assess reporting quality, liquidity posture, and the economic model that converts revenue into cash flow and reinvestment returns.

## Scaffold Status
This panel is scaffold-only. It documents the intended analysis surface for future implementation and is not approved for production execution.

## Output Contract
When implemented, the panel lead must produce a `PanelVerdict` backed by typed evidence, claim cards, and verdict memory records.

## Affected Memo Sections
- `economic_spread`
- `valuation_terms`
- `risk`

## Factor Coverage
- `financial_audit`
- `earnings_quality`
- `business_model_cash_timing`
- `unit_economics`
- `margin_profile_operating_leverage`
- `seasonality`
- `variable_vs_fixed_costs`
- `capital_efficiency`
- `ltv_cac`
- `off_balance_sheet_liabilities_equity`
- `capitalization`
- `fiscal_health`
- `roic_decomposition`
- `incremental_roic_reinvestment_runway`

## Evidence And Provenance Expectations
- Use sourceable evidence with dates, units, and provenance for filings, audit opinions, cohorts, leverage, working capital, and return metrics.
- Distinguish accounting presentation from underlying cash economics when assessing earnings quality and valuation relevance.
- Flag missing financial evidence explicitly when liquidity, liabilities, or reinvestment returns cannot be tied to hard numbers.

## Future Implementation Handoff
- Keep the panel id, memo sections, and factor coverage aligned with config before adding runnable agents.
- Reuse the shared debate subgraph when specialists and judge roles are introduced, rather than adding bespoke orchestration.
- Preserve scaffold-only wording until financial-quality workflows have deterministic extraction paths for filings, KPIs, and capital structure evidence.
