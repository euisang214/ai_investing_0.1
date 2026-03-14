# AI Investing

AI Investing is a config-driven multi-agent investment research platform for public and private company analysis. The shipped runtime persists structured evidence, factor-level claims, panel verdicts, memo section updates, and rerun deltas so weekly refreshes remain inspectable instead of collapsing into one terminal report.

## What The Runtime Produces

- factor-level claim cards
- panel-level verdicts
- a living IC memo
- rerun deltas against the prior active memo
- queue, review, and notification records for recurring operations

The memo remains a living artifact. Its required sections are:

- `investment_snapshot`
- `what_changed_since_last_run`
- `risk`
- `durability_resilience`
- `growth`
- `economic_spread`
- `valuation_terms`
- `expectations_variant_view`
- `realization_path_catalysts`
- `portfolio_fit_positioning`
- `overall_recommendation`

## Implemented Panel Surface

All top-level panels in the configured surface are now productionized and runnable through the shared runtime:

- `gatekeepers`
- `demand_revenue_quality`
- `supply_product_operations`
- `market_structure_growth`
- `macro_industry_transmission`
- `management_governance_capital_allocation`
- `financial_quality_liquidity_economic_model`
- `external_regulatory_geopolitical`
- `expectations_catalyst_realization`
- `security_or_deal_overlay`
- `portfolio_fit_positioning`

That does not mean every run executes every panel. Panel selection is still policy-driven and support-aware.

## Run Policies

The runtime keeps rollout and operator defaults config-driven in `config/run_policies.yaml`.

- `weekly_default`: narrow operator default for recurring coverage. Runs `gatekeepers` and `demand_revenue_quality`.
- `internal_company_quality`: adds `supply_product_operations`, `management_governance_capital_allocation`, and `financial_quality_liquidity_economic_model`.
- `external_company_quality`: adds `market_structure_growth`, `macro_industry_transmission`, and `external_regulatory_geopolitical`.
- `expectations_rollout`: adds `expectations_catalyst_realization`.
- `full_surface`: adds the overlay family, `security_or_deal_overlay` and `portfolio_fit_positioning`.

`weekly_default` intentionally stays narrower than `full_surface`. The repository ships the full productionized panel surface, but operators still choose how wide a given run should be.

## Support Contract

Every selected panel passes through the same support check before execution. The panel config declares:

- required evidence families by company type
- minimum factor coverage ratio
- minimum evidence count
- required context, when applicable
- whether weak confidence is allowed

The support outcome is explicit and persisted in run metadata:

- `supported`: the panel ran with its normal posture
- `weak_confidence`: the panel still ran, but the runtime calls out thin support directly in the panel support metadata and affected memo section text
- `unsupported`: the panel is skipped explicitly and the run continues

The runtime does not silently drop unsupported panels and it does not fail the whole run only because one later panel lacks support.

## Weak Confidence Versus Skip

Most company-quality panels can run with `weak_confidence` when evidence is present but thinner than the normal readiness bar. That preserves analytical continuity while keeping the confidence posture honest.

Some panels do not allow that fallback:

- `expectations_catalyst_realization` requires expectations-specific evidence such as consensus or milestone tracking
- `security_or_deal_overlay` requires overlay-specific context
- `portfolio_fit_positioning` requires portfolio context

When those requirements are missing, the runtime records an explicit skip instead of fabricating a conclusion.

## Analytical Separation

The runtime preserves the analytical boundary that the project requires:

- company quality lives in `demand_revenue_quality`, `supply_product_operations`, `market_structure_growth`, `macro_industry_transmission`, `management_governance_capital_allocation`, `financial_quality_liquidity_economic_model`, and `external_regulatory_geopolitical`
- expectations and catalysts live in `expectations_catalyst_realization`
- security quality or deal framing lives in `security_or_deal_overlay`
- portfolio fit lives in `portfolio_fit_positioning`

Those families remain separate in config, prompts, memo ownership, generated artifacts, CLI/API read surfaces, and docs. `security_or_deal_overlay` is not merged into company quality, and `portfolio_fit_positioning` is not treated as a generic extension of the company memo.

## Overall Recommendation Scope

`overall_recommendation` is truthful about what actually ran.

- If a run stops at company-quality and expectations policies, the memo calls out that the overlays are pending for that rollout.
- If `full_surface` is selected but overlay context is missing, the memo and interface surfaces call out that the relevant overlays were unsupported for this run.
- If both overlays run successfully, the recommendation scope is `overlay_complete`.

A partial recommendation therefore still has value, but it should be read as company-quality-only or company-quality-plus-expectations guidance until the overlays are either run or explicitly deemed unsupported.

## Quick Start

Docker is the primary local workflow. The host path is supported only when Python 3.11+ is available.

```bash
docker compose up --build -d
docker compose exec api ai-investing init-db
docker compose exec api ai-investing ingest-public-data /app/examples/acme_public
docker compose exec api ai-investing add-coverage ACME "Acme Cloud" public watchlist
docker compose exec api ai-investing set-coverage-schedule ACME --schedule-policy-id weekdays
docker compose exec api ai-investing analyze-company ACME
docker compose exec api ai-investing show-run <run_id>
docker compose exec api ai-investing generate-memo ACME
docker compose exec api ai-investing show-delta ACME
```

To run a broader surface, update the coverage policy or submit a refresh through the API or CLI with the relevant policy configured on the company.

## Queue And Notification Operations

Recurring operations are queue-backed and remain outside the reasoning core.

- `enqueue-watchlist`, `enqueue-portfolio`, and `enqueue-due-coverage` submit work
- `run-worker` executes bounded queue work through the same service-owned runtime
- failed gatekeepers become review-queue items
- external automation claims and dispatches notification events instead of inferring them from memo text

The checkpoint policy is also explicit:

- every run enters `gatekeepers`
- `pass` and `review` auto-continue
- `fail` stops for review and only an operator can choose provisional continuation

## Generated Artifacts

Checked artifacts under `examples/generated/` document the shipped runtime contract.

- `ACME/initial`: initial lifecycle output for the configured policy
- `ACME/continued`: persisted reread of the same completed run
- `ACME/rerun`: rerun with delta output against the prior active memo
- `ACME/overlay_gap`: `full_surface` output where company-quality work still completes but overlay context is unsupported and skipped explicitly

These artifacts are generated by `scripts/generate_phase2_examples.py` and locked by `tests/test_generated_examples.py`.

## Repo Layout

See [docs/architecture.md](docs/architecture.md), [docs/factor_ontology.md](docs/factor_ontology.md), [docs/memory_model.md](docs/memory_model.md), and [docs/runbook.md](docs/runbook.md).

## Next Work

- close the remaining Phase 4 and Phase 5 verification chains
- deepen connector realism without breaking the config-driven runtime
- extend operator tooling around review and notification flows
