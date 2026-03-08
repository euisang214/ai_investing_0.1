# Architecture Research

## Component Boundaries

1. Registry/config loader
2. Prompt loader
3. Provider/model adapters
4. Tool registry and bundle enforcement
5. Ingestion pipeline
6. Persistence repositories
7. LangGraph orchestration layer
8. Coverage and run services
9. API and CLI interfaces
10. n8n integration boundary

## Data Flow

1. Coverage entry or ingest request enters via CLI/API/n8n.
2. Ingestion writes raw artifacts, normalized evidence, and provenance metadata.
3. Company refresh graph reads active config, evidence memory, and prior memo/claim state.
4. Specialist agents emit `ClaimCard` records.
5. Panel lead subgraphs consolidate claims into `PanelVerdict` records.
6. Memo update subgraph updates affected sections immediately.
7. IC synthesis reconciles the final memo snapshot.
8. Monitoring diff compares the new run to the prior active run and writes deltas.

## Build Order Implications

1. Registries and schemas first
2. Persistence and repositories second
3. Tool/provider abstractions third
4. Orchestration subgraphs fourth
5. Interfaces and sample workflows fifth
