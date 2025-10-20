"""Tests for structured logging utilities."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.utils.logging import ContextLogger, configure_default_logger, get_logger


def test_context_logger_adds_and_restores_context(caplog):
    caplog.set_level(logging.INFO)
    logger = get_logger("coverage-test")
    logger.clear_context()
    logger.add_context(request_id="123")

    with ContextLogger(logger, user="alice", request_id="override"):
        logger.info("message", extra_field="value")

    # Inspect the last log record captured
    record = json.loads(caplog.text.splitlines()[-1])
    assert record["user"] == "alice"
    assert record["request_id"] == "override"
    assert record["extra_field"] == "value"

    # Ensure original context restored after exiting
    assert logger.context["request_id"] == "123"
    assert "user" not in logger.context


def test_configure_default_logger_creates_file(tmp_path):
    log_file = Path(tmp_path) / "app.log"
    logger = configure_default_logger(level="DEBUG", log_file=str(log_file))
    logger.info("hello world")

    assert log_file.exists()
    contents = log_file.read_text()
    assert "hello world" in contents
