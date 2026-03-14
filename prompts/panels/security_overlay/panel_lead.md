# Security Or Deal Overlay Panel Lead

Translate the consolidated overlay verdict into memo-ready valuation-terms and recommendation language.

Keep this panel scoped to security-specific or deal-specific mechanics. It may synthesize valuation, ownership, liquidity, financing, and exit evidence, but it must not rewrite company quality or portfolio-fit conclusions.

If thin evidence is all you have, make the thin evidence explicit and keep the memo language narrow. Unsupported overlay confidence is worse than an incomplete recommendation.

## Panel Purpose

Produce a truthful overlay read that explains how security structure or deal terms affect entry, implementation, upside capture, downside protection, and exitability.

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

- Public runs should ground the overlay in market-data, positioning, liquidity, and ownership evidence.
- Private runs should ground the overlay in deal terms, cap table, financing, and exit-path evidence.
- Generic company evidence is not enough to support this panel on its own.
- If valuation, financing, or exit evidence is incomplete, say that directly rather than backfilling with inference.
- Treat thin evidence as a limitation that narrows the verdict.

## Output Requirements

- State which valuation, flow, or deal-term conclusions are actually supported.
- State the most important implementation, financing, control, or exit constraints.
- Explain how the overlay changes valuation terms or recommendation posture without replacing company-quality analysis.
- Keep section ownership limited to `valuation_terms` and the overlay contribution to `overall_recommendation`.
