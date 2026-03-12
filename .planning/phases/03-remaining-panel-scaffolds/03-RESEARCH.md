# Phase 3 Research: Remaining Panel Scaffolds

## Recommendation

Phase 3 should not change the orchestration model, persistence model, or provider abstraction.
Use the existing workflow-first LangGraph architecture, keep unimplemented panels non-runnable at execution time, and expand only the scaffold surface:

- add one disabled placeholder lead agent per remaining top-level panel
- replace generic factor descriptions with panel-specific descriptions
- replace 3-line placeholder prompts with panel-specific scaffold prompts that read like implementation specs
- add explicit tests for execution-time rejection of scaffolded panels
- add docs that show the exact extension path from scaffold to production panel

This is the established pattern for a deterministic, checkpointed, config-driven LangGraph system: keep topology declarative, keep workflow generic, and let future panel productionization happen by config, prompts, and reusable subgraphs rather than bespoke runtime branches.

## Standard Stack

- High confidence: Keep `langgraph` as the orchestration core, using `StateGraph`, reusable subgraphs, interrupts, and durable checkpoints. LangGraph's official docs still distinguish deterministic workflows from autonomous agents, and this repository is clearly workflow-first, not agent-loop-first. Do not migrate Phase 3 to a higher-level agent factory. Sources: [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview), [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents), [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence). Repo fit: `src/ai_investing/graphs/company_refresh.py`, `src/ai_investing/graphs/subgraphs.py`, `pyproject.toml`.
- High confidence: Keep `langgraph-checkpoint-postgres` for durable run state. Do not build custom pause/resume persistence around ad-hoc tables or JSON blobs. LangGraph documents checkpointers as the persistence primitive for short-term thread state and interruptions. Sources: [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [Add memory](https://docs.langchain.com/oss/python/langgraph/add-memory). Repo fit: `pyproject.toml`, `src/ai_investing/graphs/checkpointing.py`.
- High confidence: Keep `langchain-core` plus the official provider integrations behind the existing `ModelProvider` wrappers. As of LangChain v1, `create_agent` is the standard high-level entrypoint and `langgraph.prebuilt.create_react_agent` is deprecated, but that is a future runtime-shape decision, not a Phase 3 scaffold task. Sources: [LangChain v1 release notes](https://docs.langchain.com/oss/python/releases/langchain-v1), [LangChain v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1), [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api). Repo fit: `src/ai_investing/providers/`, `pyproject.toml`.
- High confidence: Keep Pydantic v2 for config and domain contracts, and use `pydantic-settings` for environment-bound settings. Tighten validation at external boundaries instead of relying on coercion. Sources: [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), [Pydantic settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). Repo fit: `src/ai_investing/config/models.py`, `src/ai_investing/settings.py`, `src/ai_investing/domain/models.py`.
- High confidence: Keep YAML registries loaded with `yaml.safe_load`, then validate once in a centralized loader. Do not replace this with ad-hoc dynamic imports or Python-embedded topology. Source: [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation). Repo fit: `src/ai_investing/config/loader.py`, `config/*.yaml`.
- High confidence: Keep SQLAlchemy 2.x typed persistence with Postgres/`psycopg`. Do not introduce the SQLAlchemy mypy plugin; SQLAlchemy marks it deprecated and removed from current mypy compatibility support. Source: [SQLAlchemy Mypy / Pep-484 Support for ORM Mappings](https://docs.sqlalchemy.org/en/20/orm/extensions/mypy.html). Repo fit: `src/ai_investing/persistence/`, `pyproject.toml`.
- High confidence: Keep `pytest` plus the fake provider as the default verification stack for scaffold work. Phase 3 is topology work, so deterministic contract tests matter more than live-model tests. Repo fit: `src/ai_investing/providers/fake.py`, `tests/test_config_and_registry.py`, `tests/test_analysis_flow.py`, `tests/test_monitoring_semantics.py`.
- Medium confidence: If live debugging becomes expensive later, add LangSmith tracing as an operator tool, not as a prerequisite for Phase 3. Sources: [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview), [LangChain overview](https://docs.langchain.com/oss/python/overview).

## Architecture Patterns

- High confidence: Keep topology registry-driven. Panels, factors, agents, prompts, run policies, and tool bundles should remain YAML-defined and centrally validated. The runtime should continue iterating config and dispatching on `panel.subgraph`, not on per-panel `if` branches. Sources: [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview), [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api). Repo fit: `src/ai_investing/config/loader.py`, `src/ai_investing/application/context.py`, `src/ai_investing/graphs/company_refresh.py`.
- High confidence: Treat remaining panels as scaffold-only workflow nodes, not half-implemented runnable panels. For each remaining top-level panel, keep `implemented: false`, add exactly one disabled placeholder lead agent, keep a real prompt file, and keep panel-specific factor descriptions. This aligns with the repo's current runtime guardrails: execution rejects unimplemented panels, disabled agents are filtered out, missing judges are dangerous, and disabled leads are effectively harmless. Repo fit: `src/ai_investing/application/services.py`, `src/ai_investing/application/context.py`, `config/panels.yaml`, `config/agents.yaml`, `config/factors.yaml`.
- High confidence: Reuse the existing subgraph shapes. Phase 3 should not add a new panel subgraph type just to host scaffolds. The established LangGraph pattern is to compose reusable subgraphs and keep the company graph generic. Sources: [Use subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs), [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api). Repo fit: `src/ai_investing/graphs/subgraphs.py`, `src/ai_investing/graphs/company_refresh.py`.
- High confidence: Keep the gatekeeper-first checkpoint boundary intact. LangGraph interruptions are designed for human-in-the-loop workflow pauses, and this repo already treats gatekeepers as the mandatory checkpoint before downstream panels. Phase 3 should not weaken that to make scaffolded panels "inspectable." Sources: [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence). Repo fit: `src/ai_investing/graphs/company_refresh.py`, `src/ai_investing/application/services.py`.
- High confidence: Keep thread state and durable analytical memory separate. LangGraph's checkpointer is for per-thread state, while long-lived cross-run memory belongs in the app's typed repositories, or in LangGraph Store only if cross-thread memory becomes necessary later. Do not overload checkpoint state to hold evidence, claims, memo history, or deltas. Sources: [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [Add memory](https://docs.langchain.com/oss/python/langgraph/add-memory). Repo fit: `src/ai_investing/persistence/`, `docs/memory_model.md`.
- High confidence: Keep prompts as versioned Markdown specs on disk, with a shared scaffold structure and panel-specific content. Anthropic's prompt docs still recommend clear direct instructions and XML tags for separating sections. For Phase 3, that means each placeholder prompt should explicitly call out panel purpose, scaffold-only status, output contract, memo impact, factor coverage, evidence/provenance expectations, and implementation handoff notes. Sources: [Be clear and direct](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct), [Use XML tags](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags). Repo fit: `prompts/panels/*/placeholder.md`, `docs/prompting_strategy.md`.
- High confidence: Test policy posture directly. Keep future-facing policies such as `full_surface` loadable in config, but assert that execution rejects unimplemented panels by default. That preserves inspectability without pretending the surface is runnable. Repo fit: `config/run_policies.yaml`, `src/ai_investing/config/models.py`, `src/ai_investing/application/services.py`, `tests/test_run_lifecycle.py`.

## SOTA Delta

- High confidence: The current SOTA is not "replace LangGraph with something newer." LangGraph v1 kept the graph-first model and formalized a stable Graph API. The repo's `StateGraph` plus reusable subgraph architecture is still the right base. Sources: [LangGraph v1 release notes](https://docs.langchain.com/oss/python/releases/langgraph-v1), [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api).
- High confidence: The training-era default of "build agents with `create_react_agent`" is stale. LangChain v1 moved the default high-level agent API to `create_agent`, and the migration docs explicitly call out the deprecation of `langgraph.prebuilt.create_react_agent`. Phase 3 should not chase that migration because this repo needs deterministic workflow orchestration, not a generic tool loop. Sources: [LangChain v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1), [LangChain v1 release notes](https://docs.langchain.com/oss/python/releases/langchain-v1), [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents).
- High confidence: Prompt-only "return JSON" patterns are no longer the best baseline. Provider-native structured output is now the preferred path when available, with LangChain exposing provider and tool strategies. Future panel production phases should target typed structured output paths, not prose parsing. Sources: [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output), [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs), [LangChain v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1).

## Don't Hand-Roll

- High confidence: Do not hand-roll checkpointing, pause/resume state, or interruption plumbing. Use LangGraph interrupts plus a supported checkpointer. Sources: [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts), [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence).
- High confidence: Do not hand-roll cross-thread memory inside checkpoint payloads. Keep evidence, claims, verdicts, memo sections, memo updates, and deltas in typed repositories; if shared memory is ever needed across threads, use LangGraph Store instead of inventing a parallel memory substrate. Sources: [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence), [Add memory](https://docs.langchain.com/oss/python/langgraph/add-memory).
- High confidence: Do not hand-roll JSON extraction from prose model responses. Use Pydantic schemas and, in future production panel phases, provider-native structured output or LangChain's structured-output strategies. Sources: [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output), [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs), [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/).
- High confidence: Do not hand-roll config/env parsing. Keep `yaml.safe_load` plus a single centralized `RegistryLoader`, and keep `pydantic-settings` for runtime settings. Sources: [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation), [Pydantic settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). Repo fit: `src/ai_investing/config/loader.py`, `src/ai_investing/settings.py`.
- High confidence: Do not hand-roll panel-specific orchestration branches for scaffolded panels. Add config, prompt files, tests, and docs; only add runtime code if a genuinely new subgraph abstraction is required later. Sources: [Use subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs), [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api). Repo fit: `src/ai_investing/graphs/subgraphs.py`, `src/ai_investing/graphs/company_refresh.py`.
- High confidence: Do not hand-roll SQLAlchemy typing support through the deprecated mypy plugin. Use SQLAlchemy 2 typed mappings and regular strict mypy checks. Source: [SQLAlchemy Mypy / Pep-484 Support for ORM Mappings](https://docs.sqlalchemy.org/en/20/orm/extensions/mypy.html).
- High confidence: Do not bury large prompt bodies in Python source. Keep them in Markdown files under `prompts/`, because the whole scaffold extension path depends on prompts being editable without code refactors. Sources: [Be clear and direct](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct), [Use XML tags](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags). Repo fit: `docs/prompting_strategy.md`, `src/ai_investing/prompts/loader.py`.

## Common Pitfalls

- High confidence: Do not flip `implemented: true` on scaffolded panels just to satisfy a future-facing policy. In this repo, that would make `full_surface` executable before specialists, judges, and real prompts exist.
- High confidence: Do not add enabled placeholder judges or specialists. The current runtime can tolerate a missing/disabled lead placeholder, but a missing/disabled judge path is much more likely to hard-fail execution.
- High confidence: Do not assume improving `panel.prompt_path` changes runtime behavior today. Current runtime prompt loading is driven by `agent.prompt_path`; panel prompt files are presently validated scaffold artifacts, not active execution prompts.
- High confidence: Do not hide future multi-step reasoning behind tools when you need checkpoint visibility or subgraph inspection. LangGraph docs note that subgraphs only appear in graph introspection if they are added as nodes or called from nodes, not if buried inside tool calls. Source: [Use subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs).
- High confidence: Do not leave generic `"Placeholder factor"` text in `config/factors.yaml`. Poor factor descriptions create ontology debt and make future prompts/test cases ambiguous.
- High confidence: Do not let docs claim broader scaffold coverage than config actually provides. This repo already has slight drift: docs imply disabled placeholder agents exist broadly, while config currently only includes two such agents.
- Medium confidence: Do not spend Phase 3 on a LangChain/LangGraph major-version migration. The architecture is already correct; version migration is separate risk that would dilute the phase and destabilize tests.

## Code Examples

### 1. Disabled placeholder lead agent per remaining panel

Use one lead-only agent entry for each remaining panel, keep it disabled, and point it at the panel's scaffold prompt.

```yaml
- id: external_regulatory_placeholder
  name: External Regulatory Placeholder
  panel_id: external_regulatory_geopolitical
  parent_id: null
  role_type: lead
  goal: Scaffold-only lead agent until this panel is productionized.
  enabled: false
  prompt_path: prompts/panels/external_regulatory/placeholder.md
  input_channels:
    - evidence
  output_schema: PanelVerdict
  memory_read_namespaces:
    - company/{company_id}/evidence
  memory_write_namespaces:
    - company/{company_id}/verdicts/{panel_id}
  allowed_tool_bundle: demand_research
  model_profile: budget
  scope: both
  tags:
    - placeholder
    - scaffold_only
```

Why this shape:

- it keeps topology visible in config
- it avoids making the panel runnable
- it stays consistent with the existing placeholder pattern in `config/agents.yaml`

### 2. Shared scaffold prompt structure with panel-specific content

Use a common heading structure, but customize every file to the panel's ontology and memo footprint.

```md
# External Regulatory Geopolitical Scaffold

<panel_purpose>
Assess exogenous regulatory, legal, tax, and geopolitical forces that can alter the investment case.
</panel_purpose>

<scaffold_status>
This panel is scaffold-only. It is not yet approved for production execution.
</scaffold_status>

<output_contract>
When this panel is implemented, the lead workflow must produce a `PanelVerdict`.
</output_contract>

<affected_memo_sections>
- risk
</affected_memo_sections>

<factor_coverage>
- government_exposure
- geopolitical_exposure
- subsidies_taxes
- litigation_contingent_liabilities
- regulatory_dependency
</factor_coverage>

<evidence_expectations>
Use only sourced evidence with provenance, dates, and explicit discussion of transmission path and materiality.
</evidence_expectations>

<future_handoff>
To productionize this panel later, add specialists/judge config, map the tool bundle, keep the same panel id, and reuse the existing `debate` subgraph unless a new reusable subgraph abstraction is truly necessary.
</future_handoff>
```

This follows Anthropic's current prompt-structuring guidance while preserving the repo rule that prompts live on disk.

### 3. Test the policy boundary explicitly

Add a test that future-facing policies remain loadable but fail at execution time when they include unimplemented panels.

```python
def test_full_surface_policy_rejects_unimplemented_panels(seeded_acme) -> None:
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")
        assert coverage is not None
        coverage.panel_policy = "full_surface"
        repository.upsert_coverage(coverage)

    with pytest.raises(ValueError, match="not implemented"):
        AnalysisService(seeded_acme).analyze_company("ACME")
```

That test is more valuable than a startup-load failure because it preserves the intended config posture:

- future surface remains inspectable
- runtime safety remains explicit
- docs can truthfully say "present in config, blocked from execution"

## Source Notes

Critical claims above were checked against official documentation first, with repo files used to resolve repo-specific behavior:

- LangGraph official docs for workflows, subgraphs, interrupts, persistence, and memory/store separation
- LangChain official docs for v1 agent API changes and structured output
- OpenAI official docs for current structured output expectations
- Anthropic official docs for prompt-structure guidance
- Pydantic official docs for strict validation and settings
- SQLAlchemy official docs for typing guidance
- local repo code for runtime guardrails, prompt loading, config validation, and test seams
