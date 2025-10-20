"""ProcessMonitor service - Orchestrator for process management services."""

import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import psutil

from ..exceptions import ProcessNotFoundError, ProcessStartError, ProcessStopError
from ..models.system_configuration import SystemConfiguration
from .health_checker import HealthChecker, HealthMetrics, ProcessInfo, ProcessState
from .output_capture import OutputCapture

# Import specialized services
from .process_launcher import LaunchResult, ProcessLauncher


@dataclass
class CrashEvent:
    """Recorded crash information for a monitored process."""

    session_id: str
    pid: int
    exit_code: int
    timestamp: datetime
    reason: str = ""


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
        self.crash_callbacks: List[Callable[[str], None]] = []

        self.platform_monitor = None
        if os.name == "nt":
            try:
                from ..lib.windows_process import WindowsProcessMonitor

                self.platform_monitor = WindowsProcessMonitor()
            except Exception:
                self.platform_monitor = None

        # Track active sessions
        self.monitored_processes: Dict[str, ProcessInfo] = {}
        self._crash_events: List[CrashEvent] = []
        self._recorded_crash_sessions: set[tuple[str, int]] = set()
        self._archived_output: Dict[str, List[str]] = {}
        self._recovered_processes: List[str] = []

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

        self._refresh_process_states()

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
        archived_output = self.output_capture.get_all_output(session_id)
        if archived_output:
            self._archived_output[session_id] = archived_output
        self.output_capture.stop_capture(session_id)

        # Unregister from health checker
        self.health_checker.unregister_process(session_id)

        # Remove from tracked sessions
        if session_id in self.monitored_processes:
            del self.monitored_processes[session_id]

    def _pick_session_id(self, session_id: Optional[str]) -> Optional[str]:
        """Return a valid session id, prefer provided else first active."""
        if session_id:
            return session_id if session_id in self.monitored_processes else None
        if self.monitored_processes:
            return next(iter(self.monitored_processes.keys()))
        return None

    def get_recent_output(
        self, session_id: Optional[str] = None, lines: int = 50
    ) -> List[str]:
        """Get recent output from a monitored process.

        Args:
            session_id: Session identifier
            lines: Maximum number of lines to return

        Returns:
            List of recent output lines
        """
        self._refresh_process_states()
        target_session = self._pick_session_id(session_id)
        if not target_session:
            archived_key = session_id
            if archived_key is None and self._archived_output:
                archived_key = next(reversed(self._archived_output))
            if archived_key and archived_key in self._archived_output:
                data = self._archived_output[archived_key]
                if lines is None or lines >= len(data):
                    return list(data)
                return data[-lines:]
            return []

        return self.output_capture.get_recent_output(target_session, lines)

    def get_all_output(self, session_id: Optional[str] = None) -> List[str]:
        """Get all captured output for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of all output lines
        """
        self._refresh_process_states()
        target_session = self._pick_session_id(session_id)
        if not target_session:
            archived_key = session_id
            if archived_key is None and self._archived_output:
                archived_key = next(reversed(self._archived_output))
            if archived_key and archived_key in self._archived_output:
                return list(self._archived_output[archived_key])
            return []
        return self.output_capture.get_all_output(target_session)

    def clear_output(self, session_id: Optional[str] = None) -> int:
        """Clear stored output for a session."""
        target_session = self._pick_session_id(session_id)
        if not target_session:
            return 0
        cleared = self.output_capture.clear_output(target_session)
        if target_session in self._archived_output:
            self._archived_output[target_session] = []
        return cleared

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

    def get_health_metrics(
        self, session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get health metrics for a monitored process."""
        self._refresh_process_states()
        target_session = self._pick_session_id(session_id)
        if not target_session:
            return None
        metrics = self.health_checker.get_health_metrics(target_session)
        if not metrics:
            return None
        return {
            "cpu_percent": metrics.cpu_percent,
            "memory_usage": metrics.memory_usage,
            "memory_mb": metrics.memory_mb,
            "status": metrics.status,
            "open_files": metrics.open_files,
            "thread_count": metrics.thread_count,
            "uptime_seconds": metrics.uptime_seconds,
        }

    def get_active_processes(self) -> List[ProcessInfo]:
        """Get list of all actively monitored processes.

        Returns:
            List of ProcessInfo objects
        """
        self._refresh_process_states()
        return list(self.monitored_processes.values())

    def is_process_monitored(self, pid: int) -> bool:
        """Check if a process is being monitored.

        Args:
            pid: Process ID to check

        Returns:
            True if process is monitored
        """
        return any(info.pid == pid for info in self.monitored_processes.values())

    def get_memory_usage(self, session_id: Optional[str] = None) -> float:
        """Return memory usage in MB for a session or total across sessions."""
        self._refresh_process_states()
        if session_id:
            metrics = self.get_health_metrics(session_id)
            return metrics.get("memory_mb", 0.0) if metrics else 0.0

        total = 0.0
        for sid in list(self.monitored_processes.keys()):
            metrics = self.get_health_metrics(sid)
            if metrics:
                total += metrics.get("memory_mb", 0.0)
        return total

    def get_open_file_handles(self) -> int:
        """Return aggregate open file handles for monitored processes."""
        self._refresh_process_states()
        total = 0
        for sid in list(self.monitored_processes.keys()):
            metrics = self.get_health_metrics(sid)
            if metrics:
                total += metrics.get("open_files", 0)
        return total

    def get_resource_usage(self, pid: int) -> Optional[Dict[str, Any]]:
        """Return resource usage metrics for a given PID."""
        self._refresh_process_states()
        try:
            process = psutil.Process(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

        try:
            cpu_percent = process.cpu_percent(interval=0.0)
            memory_mb = process.memory_info().rss / 1024 / 1024
            open_files = len(process.open_files())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

        return {
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "open_files": open_files,
        }

    def get_crash_events(self) -> List[CrashEvent]:
        """Return recorded crash events."""
        self._refresh_process_states()
        return list(self._crash_events)

    def restart_monitoring(self) -> None:
        """Simulate a monitor restart by stopping existing sessions."""
        self._refresh_process_states()
        self._recovered_processes = list(self.monitored_processes.keys())
        if self._recovered_processes:
            self.stop_monitoring()

    def get_recovered_processes(self) -> List[str]:
        """Return sessions collected during restart."""
        return list(self._recovered_processes)

    def inject_output(self, text: str, session_id: Optional[str] = None) -> None:
        """Inject synthetic output lines for testing.

        Args:
            text: Text to inject
            session_id: Target session, or first available if None
        """
        target_session = self._pick_session_id(session_id)
        if not target_session:
            return
        self.output_capture.inject_output(text, target_session)

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
            info = self.monitored_processes[target_session_id]
            self.monitored_processes[target_session_id].status = ProcessState.CRASHED
            self._record_crash_event(
                session_id=target_session_id,
                pid=info.pid,
                exit_code=-1,
                reason="simulated_crash",
            )

        for callback in self.crash_callbacks:
            try:
                callback(target_session_id)
            except Exception:
                continue

    def simulate_process_crash(self, session_id: Optional[str] = None) -> None:
        """Alias for simulate_process_death used in tests."""
        self.simulate_process_death(session_id)

    def add_crash_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked when a crash is detected."""
        self.crash_callbacks.append(callback)

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

    def stop_all_monitoring(self) -> bool:
        """Compatibility helper to stop all monitored processes."""
        return self._stop_all_processes()

    def request_graceful_shutdown(self, pid: int, timeout: float = 5.0) -> bool:
        """Attempt to terminate the process gracefully."""
        session_id = None
        for sid, info in self.monitored_processes.items():
            if info.pid == pid:
                session_id = sid
                break

        if not session_id:
            return False

        try:
            if session_id in self.launcher._process_handles:
                process = self.launcher._process_handles[session_id]
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        process.kill()
            else:
                psutil.Process(pid).terminate()
        except Exception:
            return False

        self._cleanup_session(session_id)
        return True

    # Windows compatibility helpers (no-ops on non-Windows)
    def get_process_tree(self, pid: int) -> Dict[str, Any]:
        try:
            process = psutil.Process(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}

        children = [child.pid for child in process.children(recursive=True)]
        return {"pid": pid, "children": children}

    def get_performance_counters(self, pid: int) -> Dict[str, Any]:
        try:
            process = psutil.Process(pid)
            return {
                "cpu_percent": process.cpu_percent(interval=0.0),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "thread_count": process.num_threads(),
                "open_files": len(process.open_files()),
                "handle_count": getattr(process, "num_handles", lambda: 0)(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "thread_count": 0,
                "open_files": 0,
                "handle_count": 0,
            }

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _record_crash_event(
        self, session_id: str, pid: int, exit_code: int, reason: str = ""
    ) -> None:
        """Record a crash event, avoiding duplicates for the same session."""
        event_key = (session_id, exit_code)
        if event_key in self._recorded_crash_sessions:
            return

        self._crash_events.append(
            CrashEvent(
                session_id=session_id,
                pid=pid,
                exit_code=exit_code,
                timestamp=datetime.now(),
                reason=reason,
            )
        )
        self._recorded_crash_sessions.add(event_key)

    def _refresh_process_states(self) -> None:
        """Refresh process information and capture crashes."""
        for session_id in list(self.monitored_processes.keys()):
            handle = self.launcher.get_process_handle(session_id)
            info = self.monitored_processes.get(session_id)

            if handle:
                exit_code = handle.poll()
                if exit_code is None:
                    continue

                if info and exit_code != 0:
                    self._record_crash_event(
                        session_id=session_id,
                        pid=info.pid,
                        exit_code=exit_code,
                        reason="process_exit",
                    )

                try:
                    self.launcher.stop_process(session_id, force=False, timeout=0.1)
                except ProcessNotFoundError:
                    pass
                except ProcessStopError:
                    pass
                finally:
                    self._cleanup_session(session_id)
            else:
                # For simulated sessions or already cleaned up handles
                if not self.launcher.is_running(session_id):
                    self._cleanup_session(session_id)


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
