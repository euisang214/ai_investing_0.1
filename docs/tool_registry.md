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

## Connector Alignment

The builtins and declared connector surface intentionally tell a narrower story than a production data platform:

- `public_doc_fetch` and `evidence_search` operate against normalized evidence records after ingestion, whether the source was a deterministic packet or the one lightweight live market path.
- `private_doc_fetch` covers the same normalized read pattern for private dataroom and KPI packet evidence after ingestion.
- The required Phase 4 connector families are `regulatory`, `market`, `consensus`, `ownership`, and private `dataroom`.
- `events` plus `transcript/news` remain supplemental public examples. They expand evidence breadth but do not stand in for the required families.
- Exactly one lightweight live public connector exists today: `public_market_live_connector`. It proves the transport seam and recurring-refresh posture, but it does not imply live regulatory, consensus, ownership, or private-vendor integrations.

## Runtime Contract

Connector-specific tools are not allowed to leak bespoke payloads into panel logic. Everything still lands as typed `EvidenceRecord` data with provenance, quality, and staleness metadata first, then the tool registry operates on that normalized layer.

## Stubbed Interfaces

The remaining tools are intentionally declared but stubbed. This preserves extension points for future connectors without forcing premature integration work in v1.
