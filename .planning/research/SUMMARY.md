# Research Summary

## Stack

Use Python 3.11+, `uv`, FastAPI, Typer, LangGraph, SQLAlchemy, Postgres, Pydantic v2, pytest, Ruff, and mypy. Keep LangChain limited to provider and tool-wrapper friction points, not domain logic.

## Table Stakes

The platform needs config-driven orchestration, structured memory, continuous memo updates, weekly coverage reruns, deterministic tests, and both CLI/API interfaces from the start.

## Watch Out For

Avoid hardcoding topology, rewriting the full memo on every update, coupling logic to a specific provider, or spending phase-1 time on premium connectors. The core risk is architectural drift before the first vertical slice proves the contracts.
