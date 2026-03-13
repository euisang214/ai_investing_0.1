# Memory Model

## Structured Stores

The platform persists the following typed records:

- `CompanyProfile`
- `CoverageEntry`
- `EvidenceRecord`
- `ClaimCard`
- `PanelVerdict` / `GatekeeperVerdict`
- `MemoSectionUpdate`
- `ICMemo`
- `MonitoringDelta`
- `ToolInvocationLog`
- `RunRecord`

## Namespace Conventions

- `company/{company_id}/profile`
- `company/{company_id}/evidence`
- `company/{company_id}/claims/{factor_id}`
- `company/{company_id}/debates/{panel_id}`
- `company/{company_id}/verdicts/{panel_id}`
- `company/{company_id}/memos/current`
- `company/{company_id}/memos/history`
- `company/{company_id}/monitoring`
- `company/{company_id}/tool_logs`
- `portfolio/framework_notes`
- `portfolio/analogs`

## History Rules

- Evidence is append-only.
- New claim cards supersede prior active claim cards for the same `company_id + factor_id + agent_id`.
- New panel verdicts supersede prior active verdicts for the same `company_id + panel_id`.
- Memo snapshots are versioned; only one memo is active at a time.
- Memo section updates are logged independently from memo snapshots.
- Monitoring deltas are append-only per run and can be projected into company history or portfolio-level read models without mutating the underlying memo state.

## Memo Projection Rules

- Every run projects the full required memo section set, even when execution pauses after `gatekeepers`.
- Memo sections use explicit posture states: `refreshed`, `stale`, or `not_advanced`.
- `stale` means prior active memo content is carried forward because the current run did not refresh that section.
- `not_advanced` means the section has never been advanced for the company, or this run stopped before any supporting work existed.
- A gatekeeper-only run must say that deeper work has not run yet instead of inserting generic filler.
- A failed gatekeeper override must keep downstream memo language visibly provisional.

## Monitoring Read Models

Phase 4 adds two read-only projections over persisted `CoverageEntry`, `RunRecord`, and
`MonitoringDelta` rows:

- `CompanyMonitoringHistory` for per-company delta history with run metadata.
- `PortfolioMonitoringSummary` for the latest covered-name monitoring view across portfolio and
  watchlist segments.

These are operator-facing inspection models, not new reasoning runtimes.

- They do not write memo sections or alter run orchestration.
- Portfolio and watchlist names stay structurally separate in every group.
- Shared-risk or overlap clusters lead the summary when multiple covered names point at the same
  factor pressure.
- The primary portfolio monitoring view is grouped by change type first so operators can scan the
  current change pattern before drilling into individual names.
- `portfolio_fit_positioning` may still appear as a changed memo section in history or summary
  output, but that remains a read-only memo projection signal. The `portfolio_fit_positioning`
  panel is still scaffold-only and not runnable in this phase.

## Portfolio Summary Example

Representative payload from `GET /portfolio/monitoring-summary` or
`ai-investing show-portfolio-summary`:

```json
{
  "generated_at": "2026-03-13T02:00:00Z",
  "included_segments": [
    "portfolio",
    "watchlist"
  ],
  "portfolio_company_count": 1,
  "watchlist_company_count": 1,
  "shared_risk_clusters": [
    {
      "factor_id": "customer_concentration",
      "label": "Customer concentration",
      "summary": "Customer concentration appears across 2 covered names: 1 portfolio and 1 watchlist.",
      "categories": [
        "contradiction",
        "thesis_drift",
        "concentration"
      ],
      "portfolio": {
        "coverage_status": "portfolio",
        "company_count": 1,
        "companies": [
          {
            "company_id": "BETA",
            "company_name": "Beta Logistics Software",
            "coverage_status": "portfolio",
            "current_run_id": "run_000000000022",
            "alert_level": "medium",
            "recorded_at": "2026-03-13T01:58:00Z",
            "change_summary": "Portfolio name shows overlapping concentration and drift pressure.",
            "changed_sections": [
              {
                "section_id": "economic_spread",
                "label": "Economic Spread"
              },
              {
                "section_id": "growth",
                "label": "Growth"
              }
            ],
            "trigger_categories": [
              "thesis_drift",
              "concentration"
            ],
            "factor_ids": [
              "customer_concentration"
            ]
          }
        ]
      },
      "watchlist": {
        "coverage_status": "watchlist",
        "company_count": 1,
        "companies": [
          {
            "company_id": "ACME",
            "company_name": "Acme Cloud",
            "coverage_status": "watchlist",
            "current_run_id": "run_000000000021",
            "alert_level": "high",
            "recorded_at": "2026-03-13T01:57:00Z",
            "change_summary": "Watchlist name now shows contradictory concentration evidence.",
            "changed_sections": [
              {
                "section_id": "risk",
                "label": "Risk"
              },
              {
                "section_id": "overall_recommendation",
                "label": "Overall Recommendation"
              }
            ],
            "trigger_categories": [
              "contradiction",
              "concentration"
            ],
            "factor_ids": [
              "customer_concentration"
            ]
          }
        ]
      }
    }
  ],
  "change_groups": [
    {
      "change_type": "contradiction",
      "label": "Contradictions",
      "summary": "contradictions currently affect 0 portfolio names and 1 watchlist names.",
      "portfolio": {
        "coverage_status": "portfolio",
        "company_count": 0,
        "companies": []
      },
      "watchlist": {
        "coverage_status": "watchlist",
        "company_count": 1,
        "companies": [
          {
            "company_id": "ACME",
            "company_name": "Acme Cloud",
            "coverage_status": "watchlist",
            "current_run_id": "run_000000000021",
            "alert_level": "high",
            "recorded_at": "2026-03-13T01:57:00Z",
            "change_summary": "Watchlist name now shows contradictory concentration evidence.",
            "changed_sections": [
              {
                "section_id": "risk",
                "label": "Risk"
              },
              {
                "section_id": "overall_recommendation",
                "label": "Overall Recommendation"
              }
            ],
            "trigger_categories": [
              "contradiction",
              "concentration"
            ],
            "factor_ids": [
              "customer_concentration"
            ]
          }
        ]
      }
    },
    {
      "change_type": "concentration",
      "label": "Concentration Signals",
      "summary": "concentration signals currently affect 1 portfolio names and 1 watchlist names.",
      "portfolio": {
        "coverage_status": "portfolio",
        "company_count": 1,
        "companies": [
          {
            "company_id": "BETA",
            "company_name": "Beta Logistics Software",
            "coverage_status": "portfolio",
            "current_run_id": "run_000000000022",
            "alert_level": "medium",
            "recorded_at": "2026-03-13T01:58:00Z",
            "change_summary": "Portfolio name shows overlapping concentration and drift pressure.",
            "changed_sections": [
              {
                "section_id": "economic_spread",
                "label": "Economic Spread"
              },
              {
                "section_id": "growth",
                "label": "Growth"
              }
            ],
            "trigger_categories": [
              "thesis_drift",
              "concentration"
            ],
            "factor_ids": [
              "customer_concentration"
            ]
          }
        ]
      },
      "watchlist": {
        "coverage_status": "watchlist",
        "company_count": 1,
        "companies": [
          {
            "company_id": "ACME",
            "company_name": "Acme Cloud",
            "coverage_status": "watchlist",
            "current_run_id": "run_000000000021",
            "alert_level": "high",
            "recorded_at": "2026-03-13T01:57:00Z",
            "change_summary": "Watchlist name now shows contradictory concentration evidence.",
            "changed_sections": [
              {
                "section_id": "risk",
                "label": "Risk"
              },
              {
                "section_id": "overall_recommendation",
                "label": "Overall Recommendation"
              }
            ],
            "trigger_categories": [
              "contradiction",
              "concentration"
            ],
            "factor_ids": [
              "customer_concentration"
            ]
          }
        ]
      }
    }
  ],
  "exploratory_analog_drilldown": []
}
```

The example is intentionally read-only. It shows how operators can inspect monitoring history and
coverage-segmented change patterns without implying that a new portfolio panel, frontend, or
portfolio-fit reasoning runtime exists.

## How To Read The Portfolio Monitoring Summary

- Treat `shared_risk_clusters` as the main portfolio monitoring signal when it is populated. Those
  clusters highlight factor overlap that spans multiple covered names.
- Treat `change_groups` as the default scan order for the rest of the summary. The response is
  organized by change type first, not as one blended company leaderboard.
- Compare the `portfolio` and `watchlist` subsections inside each group instead of merging them in
  your head. The separation is intentional so current holdings never blur with watchlist coverage.
- Treat `exploratory_analog_drilldown` as secondary context. It can support follow-up research, but
  it is not meant to outrank the main read-only summary.
