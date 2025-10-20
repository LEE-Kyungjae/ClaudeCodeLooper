"""Structured logging utilities for Claude Code Restart Monitor.

Provides context-aware logging with structured data for better observability.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredLogger:
    """Structured logger with context support."""

    def __init__(self, name: str, log_file: Optional[str] = None):
        """Initialize structured logger.

        Args:
            name: Logger name (usually __name__)
            log_file: Optional log file path
        """
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}

        # Configure formatter
        formatter = StructuredFormatter()

        # Console handler
        if not any(
            getattr(handler, "_structured_console", False)
            for handler in self.logger.handlers
        ):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler._structured_console = True  # type: ignore[attr-defined]
            self.logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            file_path = Path(log_file).expanduser()
            file_path.parent.mkdir(parents=True, exist_ok=True)

            existing_file_handler = next(
                (
                    handler
                    for handler in self.logger.handlers
                    if isinstance(handler, logging.FileHandler)
                    and getattr(handler, "_structured_log_path", None) == str(file_path)
                ),
                None,
            )
            if existing_file_handler is None:
                file_handler = logging.FileHandler(file_path)
                file_handler.setFormatter(formatter)
                file_handler._structured_log_path = str(file_path)  # type: ignore[attr-defined]
                self.logger.addHandler(file_handler)

    def set_level(self, level: str) -> None:
        """Set logging level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger.setLevel(getattr(logging, level.upper()))

    def add_context(self, **kwargs: Any) -> None:
        """Add persistent context to all log messages.

        Args:
            **kwargs: Context key-value pairs
        """
        self.context.update(kwargs)

    def remove_context(self, *keys: str) -> None:
        """Remove context keys.

        Args:
            *keys: Context keys to remove
        """
        for key in keys:
            self.context.pop(key, None)

    def clear_context(self) -> None:
        """Clear all context."""
        self.context.clear()

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Internal logging method with context.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional structured data
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": logging.getLevelName(level),
            "logger": self.logger.name,
            "message": message,
        }

        if self.context:
            log_data.update(self.context)
        if kwargs:
            log_data.update(kwargs)

        serialized = json.dumps(log_data, default=str)

        self._ensure_capture_handler_format()
        self.logger.log(level, serialized, extra={"structured_json": serialized})

    @staticmethod
    def _ensure_capture_handler_format() -> None:
        """Ensure pytest's LogCaptureHandler, if present, outputs raw messages."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if handler.__class__.__name__ == "LogCaptureHandler":
                if getattr(handler, "_structured_format_applied", False):
                    return
                handler.setFormatter(logging.Formatter("%(message)s"))
                handler._structured_format_applied = True  # type: ignore[attr-defined]

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with structured data."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with structured data."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with structured data."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with structured data."""
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with structured data."""
        self._log(logging.CRITICAL, message, **kwargs)


class StructuredFormatter(logging.Formatter):
    """Formatter for structured log messages."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data.

        Args:
            record: Log record to format

        Returns:
            Formatted log string
        """
        if hasattr(record, "structured_json"):
            return record.structured_json  # type: ignore[return-value]

        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class ContextLogger:
    """Context manager for temporary logging context."""

    def __init__(self, logger: StructuredLogger, **context: Any):
        """Initialize context logger.

        Args:
            logger: Structured logger
            **context: Temporary context
        """
        self.logger = logger
        self.context = context
        self.previous_context = {}

    def __enter__(self) -> StructuredLogger:
        """Enter context - save and set new context."""
        # Save previous values for keys we're about to change
        for key in self.context:
            if key in self.logger.context:
                self.previous_context[key] = self.logger.context[key]

        # Add new context
        self.logger.add_context(**self.context)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore previous context."""
        # Remove context we added
        self.logger.remove_context(*self.context.keys())

        # Restore previous values
        if self.previous_context:
            self.logger.add_context(**self.previous_context)


def get_logger(name: str, log_file: Optional[str] = None) -> StructuredLogger:
    """Get or create a structured logger.

    Args:
        name: Logger name
        log_file: Optional log file path

    Returns:
        StructuredLogger instance
    """
    logger = StructuredLogger(name, log_file)
    logger.set_level("INFO")  # Default level
    return logger


# Module-level logger for convenience
_default_logger: Optional[StructuredLogger] = None


def configure_default_logger(
    level: str = "INFO", log_file: Optional[str] = None
) -> StructuredLogger:
    """Configure the default module logger.

    Args:
        level: Log level
        log_file: Optional log file path

    Returns:
        Configured logger
    """
    global _default_logger
    _default_logger = get_logger("claude_restart_monitor", log_file)
    _default_logger.set_level(level)
    return _default_logger


def get_default_logger() -> StructuredLogger:
    """Get the default logger, creating if necessary.

    Returns:
        Default structured logger
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = configure_default_logger()
    return _default_logger
