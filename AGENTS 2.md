# Project purpose

This repository implements a modular multi-agent investment research platform for public and private company analysis.

The system must produce:
- factor-level claim cards
- panel-level verdicts
- a living IC memo
- weekly refreshes for covered names
- delta summaries that show what changed since the prior run

Covered names include:
- watchlist companies
- portfolio companies

# Memo requirements

The memo is a living artifact, not a terminal report.

Required memo sections:
- investment_snapshot
- what_changed_since_last_run
- risk
- durability_resilience
- growth
- economic_spread
- valuation_terms
- expectations_variant_view
- realization_path_catalysts
- portfolio_fit_positioning
- overall_recommendation

The display label for durability_resilience may be configured as "sustainability".

# Non-negotiable architecture rules

1. Keep the cohort config-driven.
Do not hardcode agent topology in orchestration logic.
Agents, panels, factors, prompts, tool bundles, schemas, and memo sections must remain editable without major refactors.

2. Preserve separation of concerns.
Keep:
- graph orchestration
- provider/model wrappers
- schemas
- memory persistence
- prompts
- factor ontology
- memo update logic
- ingestion
- tool registry
- API/CLI
clearly separated.

3. Treat memory as structured data.
Do not store only prose.
Use typed records for:
- evidence
- claims
- verdicts
- memo sections
- memo updates
- monitoring deltas

4. Do not overwrite prior beliefs destructively.
Use status fields such as:
- active
- superseded
- rejected

5. Favor reusable subgraphs over bespoke orchestration.
Especially for:
- debate patterns
- gatekeepers
- panel leads
- memo updates
- monitoring diffs
- IC synthesis

6. Keep prompts in markdown files.
Do not bury large prompts in source code.

7. Keep company quality, security quality, and portfolio fit separate.

8. Update the memo continuously.
After relevant panel outputs are available, update affected memo sections.
At end of run, reconcile the memo.

9. Support weekly reruns for covered names.
Every rerun should produce a delta summary against the prior active memo.

10. Optimize for maintainability.
Readable code, strong typing, tests, simple abstractions, explicit docs.

# Implementation bias

- Prefer LangGraph for orchestration.
- Use LangChain only where it reduces integration friction.
- Use n8n as an external scheduling/webhook/notification layer, not the core reasoning runtime.
- Use fake model providers in tests.
- Build one vertical slice well before scaling across every panel.
- Keep provenance and evidence-quality metadata.
- Do not build compliance or entitlement systems in v1.

# Expected data contracts

Every specialist should write a ClaimCard-like object.
Every panel lead should write a PanelVerdict.
The memo layer should write MemoSection and MemoSectionUpdate records.
The IC layer should write a final reconciled ICMemo.
Monitoring logic should write MonitoringDelta records.

# Extension rule

When adding a new factor or agent:
- add config
- add prompt
- add schema mapping if needed
- add or update tool bundle if needed
- avoid changing core runtime unless the abstraction truly needs expansion

# Operating rule

When asked to implement a change:
1. inspect current config, schemas, prompt files, tool registry, and graph composition first
2. preserve backward compatibility where reasonable
3. update docs and tests with the code
4. keep memo updates and rerun delta logic intact