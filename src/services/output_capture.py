"""OutputCapture service for process output management."""

import time
import threading
import subprocess
from typing import Dict, List, Optional
from collections import deque

from ..models.system_configuration import SystemConfiguration


class OutputCapture:
    """Service for capturing and managing process output streams."""

    def __init__(self, config: SystemConfiguration):
        """Initialize the output capture service.

        Args:
            config: System configuration containing buffer settings
        """
        self.config = config
        self.output_buffer_size = config.monitoring.get("output_buffer_size", 1000)

        # Storage for captured output
        self.output_buffers: Dict[str, deque] = {}
        self.output_threads: Dict[str, threading.Thread] = {}

        # Thread safety
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()

    def start_capture(self, session_id: str, process: subprocess.Popen) -> None:
        """Start capturing output from a process.

        Args:
            session_id: Unique session identifier
            process: Subprocess to capture output from

        Raises:
            ValueError: If session is already being captured
        """
        with self._lock:
            if session_id in self.output_buffers:
                raise ValueError(
                    f"Output capture already active for session {session_id}"
                )

            # Create buffered deque
            self.output_buffers[session_id] = deque(maxlen=self.output_buffer_size)

            # Start capture thread
            output_thread = threading.Thread(
                target=self._capture_output,
                args=(process, session_id),
                daemon=True,
                name=f"OutputCapture-{session_id}",
            )
            output_thread.start()
            self.output_threads[session_id] = output_thread

    def stop_capture(self, session_id: str) -> None:
        """Stop capturing output for a session.

        Args:
            session_id: Session to stop capturing
        """
        with self._lock:
            # Clean up output thread
            if session_id in self.output_threads:
                thread = self.output_threads[session_id]
                if thread.is_alive():
                    thread.join(timeout=1)
                del self.output_threads[session_id]

            # Clean up output queue
            if session_id in self.output_buffers:
                del self.output_buffers[session_id]

    def get_recent_output(self, session_id: str, lines: int = 50) -> List[str]:
        """Get recent output lines from a session.

        Args:
            session_id: Session identifier
            lines: Maximum number of lines to return

        Returns:
            List of recent output lines (newest last)
        """
        with self._lock:
            buffer = self.output_buffers.get(session_id)
            if buffer is None:
                return []
            if lines is None or lines >= len(buffer):
                return list(buffer)
            return list(buffer)[-lines:]

    def get_all_output(self, session_id: str) -> List[str]:
        """Get all captured output for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of all output lines
        """
        with self._lock:
            buffer = self.output_buffers.get(session_id)
            if buffer is None:
                return []
            return list(buffer)

    def inject_output(self, text: str, session_id: Optional[str] = None) -> None:
        """Inject synthetic output lines for testing.

        Args:
            text: Text to inject (will be split by newlines)
            session_id: Target session, or first available if None

        Raises:
            ValueError: If no sessions are available
        """
        with self._lock:
            target_session_id = session_id or next(
                iter(self.output_buffers.keys()), None
            )
            if not target_session_id:
                raise ValueError("No monitored sessions available for output injection")

            if target_session_id not in self.output_buffers:
                self.output_buffers[target_session_id] = deque(
                    maxlen=self.output_buffer_size
                )

            buf = self.output_buffers[target_session_id]

            for line in text.splitlines():
                cleaned = line.strip()
                if not cleaned:
                    continue
                buf.append(cleaned)

    def has_output(self, session_id: str) -> bool:
        """Check if there is any output available for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if output is available
        """
        with self._lock:
            buffer = self.output_buffers.get(session_id)
            return bool(buffer)

    def get_queue_size(self, session_id: str) -> int:
        """Get the current size of the output queue.

        Args:
            session_id: Session identifier

        Returns:
            Number of items in queue, or 0 if session not found
        """
        with self._lock:
            buffer = self.output_buffers.get(session_id)
            return len(buffer) if buffer is not None else 0

    def clear_output(self, session_id: str) -> int:
        """Clear all output for a session.

        Args:
            session_id: Session identifier

        Returns:
            Number of items cleared
        """
        with self._lock:
            buffer = self.output_buffers.get(session_id)
            if buffer is None:
                return 0
            count = len(buffer)
            buffer.clear()
            return count

    def _capture_output(
        self, process: subprocess.Popen, session_id: str
    ) -> None:
        """Capture output from a process in a separate thread.

        Args:
            process: Subprocess to capture from
            output_queue: Queue to store output lines
            session_id: Session identifier for logging
        """
        try:
            while True:
                # Check if we should shutdown
                if self._shutdown_event.is_set():
                    break

                # Read line from process
                line = process.stdout.readline()
                if not line:
                    # Check if process has terminated
                    if process.poll() is not None:
                        break
                    time.sleep(0.01)
                    continue

                # Add line to queue
                line = line.strip()
                if line:
                    with self._lock:
                        buffer = self.output_buffers.get(session_id)
                        if buffer is not None:
                            buffer.append(line)

        except Exception:
            # Thread will exit on any error
            pass

    def shutdown(self) -> None:
        """Shutdown all capture threads and clean up resources."""
        self._shutdown_event.set()

        with self._lock:
            session_ids = list(self.output_buffers.keys())
            for session_id in session_ids:
                self.stop_capture(session_id)

    def __del__(self):
        """Cleanup when service is destroyed."""
        try:
            self.shutdown()
        except Exception:
            pass

    def __str__(self) -> str:
        """String representation."""
        return (
            f"OutputCapture("
            f"sessions={len(self.output_queues)}, "
            f"buffer_size={self.output_buffer_size}"
            f")"
        )
