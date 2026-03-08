# Runbook

## Local Workflow

1. Start Postgres with Docker Compose.
2. Initialize the database.
3. Ingest sample evidence.
4. Add a coverage entry.
5. Run an analysis or refresh.
6. Inspect the memo and delta outputs.

## Recommended Commands

```bash
docker compose up --build -d
docker compose exec api ai-investing init-db
docker compose exec api ai-investing ingest-public-data /app/examples/acme_public
docker compose exec api ai-investing add-coverage ACME "Acme Cloud" public watchlist
docker compose exec api ai-investing analyze-company ACME
docker compose exec api ai-investing generate-memo ACME
```

## Python Version Note

The project target runtime is Python 3.11+ because current LangGraph releases require Python 3.10 or newer. Docker is the safest local path if the host interpreter is older.

