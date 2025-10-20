"""Signal handling utilities for graceful shutdown."""

from __future__ import annotations

import signal
from datetime import datetime
from types import FrameType
from typing import Callable, Dict, Optional

from ..services.restart_controller import RestartController


class SignalHandler:
    """Gracefully handle termination signals and coordinate shutdown."""

    def __init__(self, controller: RestartController):
        self.controller = controller
        self._original_handlers: Dict[int, Callable] = {}
        self._registered = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def register(self) -> None:
        """Register SIGINT and SIGTERM handlers."""
        if self._registered:
            return

        for sig, handler in (
            (signal.SIGINT, self.handle_sigint),
            (signal.SIGTERM, self.handle_sigterm),
        ):
            self._original_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, handler)  # type: ignore[arg-type]

        self._registered = True

    def restore(self) -> None:
        """Restore previously registered handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers.clear()
        self._registered = False

    def handle_sigint(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle SIGINT (Ctrl+C)."""
        self._log_signal("SIGINT", signum)
        self._shutdown_controller()

    def handle_sigterm(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle SIGTERM."""
        self._log_signal("SIGTERM", signum)
        self._shutdown_controller()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _log_signal(self, name: str, signum: int) -> None:
        try:
            self.controller._log(f"{name} (signal {signum}) received - initiating shutdown")
        except Exception:
            pass

    def _shutdown_controller(self) -> None:
        try:
            self.controller.stop_monitoring()
        finally:
            # Persist current state even if stop_monitoring fails
            try:
                cached_state = self.controller.state_manager.get_cached_state()
                state_payload = cached_state or {
                    "heartbeat": datetime.utcnow().isoformat()  # type: ignore[attr-defined]
                }
                self.controller.state_manager.save_state(state_payload)
            except Exception:
                pass
