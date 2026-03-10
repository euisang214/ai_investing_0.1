# Runbook

## Docker-First Workflow

1. Start Postgres with Docker Compose.
2. Initialize the database.
3. Ingest sample evidence.
4. Add a coverage entry.
5. Optionally set the next scheduled refresh.
6. Run an analysis or refresh.
7. Inspect the memo and delta outputs.

## Recommended Commands

```bash
docker compose up --build -d
docker compose exec api ai-investing init-db
docker compose exec api ai-investing ingest-public-data /app/examples/acme_public
docker compose exec api ai-investing add-coverage ACME "Acme Cloud" public watchlist
docker compose exec api ai-investing set-next-run-at ACME 2026-03-10T09:30:00+00:00
docker compose exec api ai-investing analyze-company ACME
docker compose exec api ai-investing list-coverage
docker compose exec api ai-investing generate-memo ACME
```

## Host Workflow

Only use the host workflow when Python 3.11+ is available locally.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
ai-investing init-db
```

## Python Version Note

The project target runtime is Python 3.11+ because current LangGraph releases require Python 3.10 or newer. Docker remains the recommended path when the host interpreter is older or missing the project dependencies.
