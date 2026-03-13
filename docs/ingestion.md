# Ingestion

## Common Spine

Every connector in this repo still follows the same ingestion spine:

1. Source connector selection from config
2. Raw immutable landing zone copy
3. Parser or extractor selection
4. Entity and period normalization
5. `EvidenceRecord` creation
6. Evidence quality, provenance, and staleness tagging
7. Downstream claim-generation trigger
8. Memo update trigger
9. Monitoring and delta trigger

That separation matters because Phase 4 is expanding connector depth without changing the downstream evidence contract. New public and private inputs still need to land as typed, provenance-rich structured data rather than bespoke payloads.

## Phase 4 Connector Inventory

Phase 4 keeps the default file-backed connectors for backward-compatible public and private ingestion, then adds a representative fixture inventory that makes `V2-02` coverage explicit:

| Connector id | Company type | Family | Role in Phase 4 |
| --- | --- | --- | --- |
| `public_file_connector` | public | baseline file bundle | Backward-compatible default public entrypoint |
| `private_file_connector` | private | baseline file bundle | Backward-compatible default private entrypoint |
| `acme_regulatory_packet` | public | regulatory | Thin but real required public slice |
| `acme_market_packet` | public | market | Deeper required public slice |
| `acme_consensus_packet` | public | consensus | Thin but real required public slice |
| `acme_ownership_packet` | public | ownership | Deeper required public slice |
| `acme_events_packet` | public | events | Supplemental public example only |
| `acme_transcript_news_packet` | public | transcript/news | Supplemental public example only |
| `beta_dataroom` | private | dataroom | Required private diligence family |
| `beta_kpi_packet` | private | KPI packet | Supporting private diligence fixture |
| `public_market_live_connector` | public | market | The single lightweight live public connector path for recurring refresh proof |

The required public families for this phase are `regulatory`, `market`, `consensus`, and `ownership`. The required private family is `dataroom`. `events` and `transcript/news` stay supplemental public examples and are not substitutes for the required families.

## Scope Boundary For Live Coverage

Phase 4 intentionally ships exactly one lightweight live public connector. Its job is to prove that the generalized runtime can refresh a real public source through a typed seam, not to imply broad live coverage across every connector family.

This means:

- The live path is public only.
- The live path is time-bounded and explicitly staleness-tagged.
- Regulatory, consensus, ownership, and dataroom remain deterministic fixture-backed examples in this phase.
- Premium vendors and broader multi-system live coverage remain deferred.

The live path currently uses a tiny request package (`request.json`) plus one public market transport. The runtime persists the raw quote response into the connector landing zone, emits a staleness-tagged `EvidenceRecord`, and leaves every other richer family fixture-backed on purpose.

## Evidence Media Policy

Phase 4 broadens the sample evidence media mix, but the policy stays honest and narrow:

- Plain text remains first-class evidence.
- PDF documents become first-class evidence when extraction is feasible.
- Spreadsheet artifacts become first-class evidence when extraction is feasible.
- HTML artifacts stay attachment-only by default.
- Image artifacts stay attachment-only by default.
- Attachment-only files still copy into the raw landing zone so provenance is preserved even when the body is not extracted into full text.

This repo uses "first-class evidence" to mean a standalone normalized `EvidenceRecord` with its own provenance, factor tags, time period, quality metadata, and staleness metadata. Packet-style sources should emit one record per meaningful document or item, not one giant packet summary and not one record per tiny metric cell.

In the current fixtures, that means:

- regulatory, market, consensus, ownership, transcript, and news markdown or delimited files are extracted into first-class evidence
- dataroom PDF packets are extracted when text is available
- KPI packet spreadsheets are extracted into first-class evidence when their contents are readable
- event HTML and event images still land as attachment-only evidence with preserved raw provenance

## Raw Artifact Handling

Raw storage is still immutable and flattened under connector-specific landing zones. When two source artifacts share the same basename, the runtime should apply a deterministic rename or prefix so both files persist without losing provenance clarity. The rename policy must be stable across reruns.

The current runtime keeps the landing zone flat per connector and company, then uses stable path-derived prefixes such as `finance__summary.md` when duplicate basenames would otherwise collide.

## Fixture Expectations

The staged connector manifests under `examples/connectors/` are meant to show the evidence families this phase covers:

- `acme_regulatory_packet` and `acme_consensus_packet` stay intentionally thin.
- `acme_market_packet` and `acme_ownership_packet` are the deeper public representative bundles.
- `acme_events_packet` and `acme_transcript_news_packet` show supplemental public breadth.
- `beta_dataroom` and `beta_kpi_packet` keep private diligence support grounded in dataroom and KPI materials rather than a sprawling private integration stack.
- `public_market_live_connector` proves one lightweight real-public refresh path without changing the broader deterministic fixture posture.

Those fixtures are deterministic by design. They exist to prove normalization behavior, media handling, provenance persistence, and downstream compatibility without binding the repo to a vendor-specific public or private data product.
