"""Structured logging configuration using structlog.

All log output goes to stdout as JSON — standard for Docker/container
deployments. Context fields (run_id, company_id, panel_id) are bound
per-request using structlog's context variables.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for JSON rendering to stdout.

    Call once at application startup (e.g. in AppContext.load or FastAPI lifespan).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer()
        if sys.stderr.isatty()
        else structlog.processors.JSONRenderer(),
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to the given name."""
    return structlog.get_logger(name)


def bind_run_context(*, run_id: str, company_id: str) -> None:
    """Bind run-level context variables for structured logging."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        run_id=run_id,
        company_id=company_id,
    )


def bind_panel_context(*, panel_id: str, agent_id: str | None = None) -> None:
    """Bind panel-level context variables (additive to run context)."""
    ctx: dict[str, str] = {"panel_id": panel_id}
    if agent_id:
        ctx["agent_id"] = agent_id
    structlog.contextvars.bind_contextvars(**ctx)


def clear_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()
