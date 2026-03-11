from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from ai_investing.settings import Settings

_MEMORY_SAVERS: dict[tuple[str, str, str], Any] = {}
_POSTGRES_SETUP_COMPLETE: set[str] = set()


def checkpoint_config(run_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": run_id}}


def interrupt_payloads(result: dict[str, Any]) -> list[Any]:
    payloads = result.get("__interrupt__")
    if payloads is None:
        return []
    if isinstance(payloads, list):
        return [getattr(payload, "value", payload) for payload in payloads]
    return [getattr(payloads, "value", payloads)]


@contextmanager
def graph_checkpointer(settings: Settings) -> Iterator[Any]:
    checkpoint_url = settings.langgraph_checkpoint_url or settings.database_url
    if _should_use_postgres(checkpoint_url):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
        except ImportError as exc:  # pragma: no cover - dependency contract
            raise RuntimeError(
                "Install langgraph-checkpoint-postgres to enable durable checkpoint storage."
            ) from exc

        with PostgresSaver.from_conn_string(checkpoint_url) as saver:
            if checkpoint_url not in _POSTGRES_SETUP_COMPLETE:
                saver.setup()
                _POSTGRES_SETUP_COMPLETE.add(checkpoint_url)
            yield saver
        return

    saver = _MEMORY_SAVERS.setdefault(_memory_saver_key(settings), _build_memory_saver())
    yield saver


def _memory_saver_key(settings: Settings) -> tuple[str, str, str]:
    return (settings.database_url, str(settings.config_dir), settings.provider)


def _should_use_postgres(checkpoint_url: str) -> bool:
    normalized = checkpoint_url.lower()
    return normalized.startswith(("postgres://", "postgresql://", "postgresql+"))


def _build_memory_saver() -> Any:
    try:
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()
    except ImportError:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
