# Ingestion

## Common Spine

1. Source connector
2. Raw immutable landing zone
3. Parser / extractor
4. Entity and period normalization
5. Evidence object creation
6. Evidence quality and provenance tagging
7. Downstream claim-generation trigger
8. Memo update trigger
9. Monitoring / delta trigger

## v1 Connectors

- `public_file_connector`
- `private_file_connector`
- `mcp_stub`

The file connectors read `manifest.json` plus referenced local documents. They copy source files into a raw landing zone and persist normalized `EvidenceRecord` objects with factor signals and provenance metadata.

