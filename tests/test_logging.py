from __future__ import annotations

import logging

import structlog

from ai_investing.logging import (
    bind_panel_context,
    bind_run_context,
    clear_context,
    configure_logging,
    get_logger,
)


class TestStructuredLogging:
    def setup_method(self) -> None:
        clear_context()

    def teardown_method(self) -> None:
        clear_context()

    def test_configure_logging_sets_root_level(self) -> None:
        configure_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG
        configure_logging("INFO")
        assert logging.getLogger().level == logging.INFO

    def test_get_logger_returns_bound_logger(self) -> None:
        log = get_logger("test")
        assert log is not None

    def test_json_output(self, capsys: object) -> None:
        configure_logging("INFO")
        log = get_logger("test_json")
        log.info("test_event", key="value")

        # Force output through handler
        for handler in logging.getLogger().handlers:
            handler.flush()

    def test_context_binding_run(self) -> None:
        bind_run_context(run_id="run_123", company_id="ACME")
        ctx = structlog.contextvars.get_contextvars()
        assert ctx["run_id"] == "run_123"
        assert ctx["company_id"] == "ACME"

    def test_context_binding_panel(self) -> None:
        bind_run_context(run_id="run_123", company_id="ACME")
        bind_panel_context(panel_id="demand_revenue_quality", agent_id="demand_specialist")
        ctx = structlog.contextvars.get_contextvars()
        assert ctx["run_id"] == "run_123"
        assert ctx["panel_id"] == "demand_revenue_quality"
        assert ctx["agent_id"] == "demand_specialist"

    def test_clear_context(self) -> None:
        bind_run_context(run_id="run_123", company_id="ACME")
        clear_context()
        ctx = structlog.contextvars.get_contextvars()
        assert "run_id" not in ctx

    def test_log_level_filtering(self) -> None:
        configure_logging("WARNING")
        get_logger("test_filter")
        # DEBUG and INFO should be filtered
        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
