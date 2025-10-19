"""ProcessMonitor service - Orchestrator for process management services.

Coordinates ProcessLauncher, OutputCapture, and HealthChecker to provide
unified process monitoring and management capabilities.

This refactored version delegates to specialized services for better
maintainability and separation of concerns.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..models.system_configuration import SystemConfiguration
from ..exceptions import ProcessStartError, ProcessStopError, ProcessNotFoundError

# Import specialized services
from .process_launcher import ProcessLauncher, LaunchResult
from .output_capture import OutputCapture
from .health_checker import HealthChecker, ProcessInfo, HealthMetrics, ProcessState


class ProcessMonitor:
    """Orchestrator service for unified process monitoring.

    Delegates to specialized services:
    - ProcessLauncher: Process lifecycle (start/stop)
    - OutputCapture: Output stream management
    - HealthChecker: Health metrics and status monitoring
    """

    def __init__(self, config: SystemConfiguration):
        """Initialize the process monitor orchestrator.

        Args:
            config: System configuration
        """
        self.config = config

        # Initialize specialized services
        self.launcher = ProcessLauncher(config)
        self.output_capture = OutputCapture(config)
        self.health_checker = HealthChecker(config)

        # Track active sessions
        self.monitored_processes: Dict[str, ProcessInfo] = {}

    def start_monitoring(
        self,
        command: str,
        session_id: Optional[str] = None,
        work_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ProcessInfo:
        """Start monitoring a Claude Code process.

        Args:
            command: Command to execute
            session_id: Session identifier (auto-generated if None)
            work_dir: Working directory
            env_vars: Environment variables

        Returns:
            ProcessInfo object with process details

        Raises:
            ProcessStartError: If process fails to start
            ValueError: If command is invalid
        """
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")

        if session_id is None:
            session_id = f"proc_{int(time.time())}"

        # Check if session already exists
        if session_id in self.monitored_processes:
            raise ProcessStartError(
                f"Session {session_id} is already being monitored",
                details={"session_id": session_id},
            )

        try:
            # Launch process
            launch_result = self.launcher.launch_process(
                command=command,
                session_id=session_id,
                work_dir=work_dir,
                env_vars=env_vars,
            )

            # Register with health checker
            process_info = self.health_checker.register_process(
                session_id=session_id,
                pid=launch_result.pid,
                command=launch_result.command,
                start_time=launch_result.start_time,
            )

            # Start output capture (if we have a real process handle)
            if launch_result.process_handle:
                self.output_capture.start_capture(
                    session_id=session_id, process=launch_result.process_handle
                )

            # Track session
            self.monitored_processes[session_id] = process_info

            # Update initial status
            if self.launcher.is_running(session_id):
                process_info.status = ProcessState.RUNNING
            else:
                process_info.status = ProcessState.STOPPED

            return process_info

        except Exception as e:
            # Clean up on failure
            self._cleanup_session(session_id)
            raise

    def stop_monitoring(self, session_id: Optional[str] = None) -> bool:
        """Stop monitoring a process or all processes.

        Args:
            session_id: Specific session to stop, or None for all

        Returns:
            True if processes were stopped successfully
        """
        if session_id:
            return self._stop_single_process(session_id)
        else:
            return self._stop_all_processes()

    def _stop_single_process(self, session_id: str) -> bool:
        """Stop monitoring a single process.

        Args:
            session_id: Session to stop

        Returns:
            True if successful
        """
        if session_id not in self.monitored_processes:
            return False

        try:
            # Stop the process
            self.launcher.stop_process(session_id, force=False, timeout=5.0)

            # Clean up session
            self._cleanup_session(session_id)

            return True

        except ProcessNotFoundError:
            # Process already gone
            self._cleanup_session(session_id)
            return True
        except Exception:
            return False

    def _stop_all_processes(self) -> bool:
        """Stop monitoring all processes.

        Returns:
            True if all processes stopped successfully
        """
        success = True
        session_ids = list(self.monitored_processes.keys())

        for session_id in session_ids:
            if not self._stop_single_process(session_id):
                success = False

        return success

    def _cleanup_session(self, session_id: str) -> None:
        """Clean up all resources for a session.

        Args:
            session_id: Session to clean up
        """
        # Stop output capture
        self.output_capture.stop_capture(session_id)

        # Unregister from health checker
        self.health_checker.unregister_process(session_id)

        # Remove from tracked sessions
        if session_id in self.monitored_processes:
            del self.monitored_processes[session_id]

    def get_recent_output(self, session_id: str, lines: int = 50) -> List[str]:
        """Get recent output from a monitored process.

        Args:
            session_id: Session identifier
            lines: Maximum number of lines to return

        Returns:
            List of recent output lines
        """
        return self.output_capture.get_recent_output(session_id, lines)

    def get_all_output(self, session_id: str) -> List[str]:
        """Get all captured output for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of all output lines
        """
        return self.output_capture.get_all_output(session_id)

    def send_input(self, session_id: str, text: str) -> bool:
        """Send text input to the monitored process."""
        process_handle = self.launcher.get_process_handle(session_id)

        # Ensure trailing newline so the CLI receives the command
        payload = text if text.endswith("\n") else f"{text}\n"

        if process_handle and process_handle.stdin:
            try:
                process_handle.stdin.write(payload)
                process_handle.stdin.flush()
                return True
            except Exception:
                return False

        # If the process is simulated, treat the send as successful and inject output
        if self.launcher.is_running(session_id):
            try:
                self.output_capture.inject_output(
                    f"[Simulated input] {text}", session_id=session_id
                )
                return True
            except Exception:
                return False

        return False

    def get_health_metrics(self, session_id: str) -> Optional[HealthMetrics]:
        """Get health metrics for a monitored process.

        Args:
            session_id: Session identifier

        Returns:
            HealthMetrics object or None if process not found
        """
        return self.health_checker.get_health_metrics(session_id)

    def get_active_processes(self) -> List[ProcessInfo]:
        """Get list of all actively monitored processes.

        Returns:
            List of ProcessInfo objects
        """
        return list(self.monitored_processes.values())

    def is_process_monitored(self, pid: int) -> bool:
        """Check if a process is being monitored.

        Args:
            pid: Process ID to check

        Returns:
            True if process is monitored
        """
        return any(info.pid == pid for info in self.monitored_processes.values())

    def inject_output(self, text: str, session_id: Optional[str] = None) -> None:
        """Inject synthetic output lines for testing.

        Args:
            text: Text to inject
            session_id: Target session, or first available if None
        """
        self.output_capture.inject_output(text, session_id)

    def simulate_process_death(self, session_id: Optional[str] = None) -> None:
        """Simulate abrupt process termination for testing.

        Args:
            session_id: Session to terminate, or first available
        """
        target_session_id = session_id or next(
            iter(self.monitored_processes.keys()), None
        )
        if not target_session_id:
            return

        # Simulate death in launcher
        self.launcher.simulate_process_death(target_session_id)

        # Update status in health checker
        if target_session_id in self.monitored_processes:
            self.monitored_processes[target_session_id].status = ProcessState.CRASHED

    def get_monitoring_overhead(self) -> Dict[str, float]:
        """Get monitoring system overhead metrics.

        Returns:
            Dictionary with CPU, memory, and thread metrics
        """
        import psutil

        try:
            current_process = psutil.Process()
            return {
                "cpu_percent": current_process.cpu_percent(),
                "memory_mb": current_process.memory_info().rss / 1024 / 1024,
                "thread_count": current_process.num_threads(),
                "open_files": (
                    len(current_process.open_files())
                    if hasattr(current_process, "open_files")
                    else 0
                ),
            }
        except Exception:
            return {
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "thread_count": 0,
                "open_files": 0,
            }

    def shutdown(self) -> None:
        """Shutdown all monitoring services and clean up resources."""
        # Stop all processes
        self.stop_monitoring()

        # Shutdown services
        self.output_capture.shutdown()
        self.health_checker.shutdown()
        self.launcher.cleanup()

    def __del__(self):
        """Cleanup when monitor is destroyed."""
        try:
            self.shutdown()
        except Exception:
            pass

    def __str__(self) -> str:
        """String representation."""
        return (
            f"ProcessMonitor("
            f"sessions={len(self.monitored_processes)}, "
            f"launcher={self.launcher}, "
            f"output={self.output_capture}, "
            f"health={self.health_checker}"
            f")"
        )


# Export original classes for backward compatibility
__all__ = [
    "ProcessMonitor",
    "ProcessInfo",
    "HealthMetrics",
    "ProcessState",
    "ProcessLauncher",
    "OutputCapture",
    "HealthChecker",
]
