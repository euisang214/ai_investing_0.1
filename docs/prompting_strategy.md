# Prompting Strategy

## Prompt Storage

All substantive prompts live in `prompts/`. The runtime loads them by path from config rather than embedding large instructions in Python code.

## v1 Pattern

- role prompts for specialist, skeptic, durability, judge, and lead agents
- memo update prompt for section-level updates
- IC synthesis prompt for final reconciliation
- monitoring prompt for delta narratives

## Design Constraints

- Prompts should stay concise and schema-aware.
- Prompts should assume evidence-grounded outputs only.
- Delta-aware tasks should always compare against prior active memory when available.
- A prompt change should not require business-logic changes unless the schema contract changes too.

