"""Logging configuration helpers with safe rotation."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class SafeRotatingFileHandler(RotatingFileHandler):
    """Rotating handler that tolerates rotation failures gracefully."""

    def doRollover(self) -> None:  # pragma: no cover - defensive path
        try:
            super().doRollover()
        except Exception as exc:  # pylint: disable=broad-except
            logging.getLogger(__name__).warning(
                "Log rotation failed: %s", exc
            )
            # Keep using current file without rotation


class LoggingConfig:
    """Configure application logging with optional rotation support."""

    def __init__(
        self,
        log_file: str,
        *,
        max_size_mb: int = 5,
        backup_count: int = 5,
        logger_name: str = "claude_code_looper",
    ):
        self.log_file = Path(log_file)
        self.max_bytes = max_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self.logger_name = logger_name
        self._logger: Optional[logging.Logger] = None

    def get_logger(self) -> logging.Logger:
        """Return a configured logger instance."""
        if self._logger:
            return self._logger

        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger(self.logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not any(isinstance(h, SafeRotatingFileHandler) for h in logger.handlers):
            try:
                handler = SafeRotatingFileHandler(
                    filename=str(self.log_file),
                    maxBytes=self.max_bytes,
                    backupCount=self.backup_count,
                    encoding="utf-8",
                )
                formatter = logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
                )
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            except (PermissionError, OSError) as exc:  # pragma: no cover - env specific
                logging.getLogger(__name__).warning(
                    "File logging disabled due to error: %s", exc
                )
                self._ensure_directory_executable()

        # Also ensure console output for visibility
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            console = logging.StreamHandler()
            console.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            logger.addHandler(console)

        self._logger = logger
        return logger

    def _ensure_directory_executable(self) -> None:
        """Ensure the log directory retains execute permission for visibility."""
        try:
            current_mode = self.log_file.parent.stat().st_mode & 0o777
            if current_mode & 0o111:
                return
            new_mode = current_mode | 0o111
            os.chmod(self.log_file.parent, new_mode)
        except Exception:  # pragma: no cover - defensive
            pass
