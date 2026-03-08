# Tool Registry

## Goals

- least-privilege access by bundle
- centralized invocation logging
- clean split between deterministic local tools and MCP-backed tools

## v1 Builtins

- `evidence_search`
- `claim_search`
- `contradiction_finder`
- `analog_lookup`
- `memo_section_writer`
- `public_doc_fetch`
- `private_doc_fetch`

## Stubbed Interfaces

The remaining tools are intentionally declared but stubbed. This preserves extension points for future connectors without forcing premature integration work in v1.

