FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY pyproject.toml README.md /app/
COPY alembic.ini /app/
COPY alembic /app/alembic
COPY src /app/src
COPY config /app/config
COPY prompts /app/prompts
COPY examples /app/examples
COPY docs /app/docs
COPY tests /app/tests

RUN uv pip install --system -e ".[dev]"

CMD ["uvicorn", "ai_investing.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
