"""ProcessMonitor service for Claude Code process management.

Handles starting, monitoring, and managing Claude Code processes including
real-time output capture, health monitoring, and Windows-specific features.
"""
import os
import sys
import time
import psutil
import subprocess
import threading
import queue
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, TextIO
from dataclasses import dataclass
from enum import Enum

from ..models.system_configuration import SystemConfiguration


class ProcessState(Enum):
    """Process monitoring states."""
    UNKNOWN = "unknown"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    CRASHED = "crashed"
    ZOMBIE = "zombie"


@dataclass
class ProcessInfo:
    """Information about a monitored process."""
    pid: int
    session_id: str
    command: str
    start_time: datetime
    status: ProcessState
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    open_files: int = 0


@dataclass
class HealthMetrics:
    """Process health metrics."""
    cpu_percent: float
    memory_usage: float
    memory_mb: float
    status: str
    open_files: int
    thread_count: int
    uptime_seconds: float


class ProcessMonitor:
    """Service for monitoring Claude Code processes."""

    def __init__(self, config: SystemConfiguration):
        """Initialize the process monitor."""
        self.config = config
        self.monitored_processes: Dict[str, ProcessInfo] = {}
        self.output_queues: Dict[str, queue.Queue] = {}
        self.output_threads: Dict[str, threading.Thread] = {}
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()

        # Output capture settings
        self.output_buffer_size = config.monitoring.get("output_buffer_size", 1000)
        self.check_interval = config.monitoring.get("check_interval", 1.0)

        # Performance settings
        self.max_memory_mb = config.performance.get("max_memory_mb", 500)
        self.cpu_limit_percent = config.performance.get("cpu_limit_percent", 20)

    def start_monitoring(
        self,
        command: str,
        session_id: Optional[str] = None,
        work_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> ProcessInfo:
        """
        Start monitoring a Claude Code process.

        Args:
            command: Command to execute
            session_id: Session identifier
            work_dir: Working directory
            env_vars: Environment variables

        Returns:
            ProcessInfo object with process details

        Raises:
            RuntimeError: If process fails to start
            ValueError: If command is invalid
        """
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")

        if session_id is None:
            session_id = f"proc_{int(time.time())}"

        with self._lock:
            if session_id in self.monitored_processes:
                raise ValueError(f"Session {session_id} is already being monitored")

            # Prepare environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            # Validate working directory
            if work_dir:
                work_dir = os.path.expandvars(os.path.expanduser(work_dir))
                if not os.path.exists(work_dir):
                    raise ValueError(f"Working directory does not exist: {work_dir}")

            try:
                # Start the process
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    cwd=work_dir,
                    env=env,
                    shell=self.config.security.get("allow_shell_commands", False)
                )

                # Create process info
                process_info = ProcessInfo(
                    pid=process.pid,
                    session_id=session_id,
                    command=command,
                    start_time=datetime.now(),
                    status=ProcessState.STARTING
                )

                # Set up output capture
                output_queue = queue.Queue(maxsize=self.output_buffer_size)
                self.output_queues[session_id] = output_queue

                # Start output capture thread
                output_thread = threading.Thread(
                    target=self._capture_output,
                    args=(process, output_queue, session_id),
                    daemon=True
                )
                output_thread.start()
                self.output_threads[session_id] = output_thread

                # Store process info
                self.monitored_processes[session_id] = process_info

                # Start monitoring if not already running
                if not self.monitoring_active:
                    self._start_monitoring_thread()

                # Wait a moment to check if process started successfully
                time.sleep(0.1)
                if process.poll() is not None:
                    # Process exited immediately
                    self._cleanup_process(session_id)
                    raise RuntimeError(f"Process exited immediately with code {process.returncode}")

                process_info.status = ProcessState.RUNNING
                return process_info

            except subprocess.SubprocessError as e:
                raise RuntimeError(f"Failed to start process: {e}")
            except Exception as e:
                # Cleanup on failure
                if session_id in self.monitored_processes:
                    self._cleanup_process(session_id)
                raise RuntimeError(f"Unexpected error starting process: {e}")

    def stop_monitoring(self, session_id: Optional[str] = None) -> bool:
        """
        Stop monitoring a process or all processes.

        Args:
            session_id: Specific session to stop, or None for all

        Returns:
            True if processes were stopped successfully
        """
        with self._lock:
            if session_id:
                return self._stop_single_process(session_id)
            else:
                return self._stop_all_processes()

    def _stop_single_process(self, session_id: str) -> bool:
        """Stop monitoring a single process."""
        if session_id not in self.monitored_processes:
            return False

        process_info = self.monitored_processes[session_id]
        process_info.status = ProcessState.STOPPING

        try:
            # Try to terminate the process gracefully
            if psutil.pid_exists(process_info.pid):
                process = psutil.Process(process_info.pid)
                process.terminate()

                # Wait for graceful termination
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    # Force kill if necessary
                    process.kill()

            self._cleanup_process(session_id)
            return True

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self._cleanup_process(session_id)
            return True
        except Exception:
            return False

    def _stop_all_processes(self) -> bool:
        """Stop monitoring all processes."""
        success = True
        session_ids = list(self.monitored_processes.keys())

        for session_id in session_ids:
            if not self._stop_single_process(session_id):
                success = False

        # Stop monitoring thread
        self.monitoring_active = False
        self._shutdown_event.set()

        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

        return success

    def _cleanup_process(self, session_id: str) -> None:
        """Clean up resources for a process."""
        # Update process status
        if session_id in self.monitored_processes:
            self.monitored_processes[session_id].status = ProcessState.STOPPED
            del self.monitored_processes[session_id]

        # Clean up output queue
        if session_id in self.output_queues:
            del self.output_queues[session_id]

        # Clean up output thread
        if session_id in self.output_threads:
            thread = self.output_threads[session_id]
            if thread.is_alive():
                thread.join(timeout=1)
            del self.output_threads[session_id]

    def get_recent_output(self, session_id: str, lines: int = 50) -> List[str]:
        """
        Get recent output from a monitored process.

        Args:
            session_id: Session identifier
            lines: Maximum number of lines to return

        Returns:
            List of recent output lines
        """
        if session_id not in self.output_queues:
            return []

        output_queue = self.output_queues[session_id]
        recent_lines = []

        # Drain the queue up to the specified number of lines
        while len(recent_lines) < lines and not output_queue.empty():
            try:
                line = output_queue.get_nowait()
                recent_lines.append(line)
            except queue.Empty:
                break

        return recent_lines

    def get_all_output(self, session_id: str) -> List[str]:
        """Get all captured output for a session."""
        return self.get_recent_output(session_id, lines=self.output_buffer_size)

    def get_health_metrics(self, session_id: str) -> Optional[HealthMetrics]:
        """
        Get health metrics for a monitored process.

        Args:
            session_id: Session identifier

        Returns:
            HealthMetrics object or None if process not found
        """
        if session_id not in self.monitored_processes:
            return None

        process_info = self.monitored_processes[session_id]

        try:
            if not psutil.pid_exists(process_info.pid):
                return None

            process = psutil.Process(process_info.pid)

            # Get CPU and memory usage
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # Get additional metrics
            try:
                open_files = len(process.open_files())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                open_files = 0

            try:
                thread_count = process.num_threads()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                thread_count = 0

            uptime = (datetime.now() - process_info.start_time).total_seconds()

            return HealthMetrics(
                cpu_percent=cpu_percent,
                memory_usage=memory_info.percent if hasattr(memory_info, 'percent') else 0.0,
                memory_mb=memory_mb,
                status=process.status(),
                open_files=open_files,
                thread_count=thread_count,
                uptime_seconds=uptime
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def get_active_processes(self) -> List[ProcessInfo]:
        """Get list of all actively monitored processes."""
        with self._lock:
            return list(self.monitored_processes.values())

    def is_process_monitored(self, pid: int) -> bool:
        """Check if a process is being monitored."""
        with self._lock:
            return any(info.pid == pid for info in self.monitored_processes.values())

    def get_monitoring_overhead(self) -> Dict[str, float]:
        """Get monitoring system overhead metrics."""
        try:
            current_process = psutil.Process()
            return {
                "cpu_percent": current_process.cpu_percent(),
                "memory_mb": current_process.memory_info().rss / 1024 / 1024,
                "thread_count": current_process.num_threads(),
                "open_files": len(current_process.open_files()) if hasattr(current_process, 'open_files') else 0
            }
        except Exception:
            return {"cpu_percent": 0.0, "memory_mb": 0.0, "thread_count": 0, "open_files": 0}

    def _capture_output(self, process: subprocess.Popen, output_queue: queue.Queue, session_id: str) -> None:
        """Capture output from a process in a separate thread."""
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    time.sleep(0.01)
                    continue

                line = line.strip()
                if line:
                    try:
                        output_queue.put(line, timeout=0.1)
                    except queue.Full:
                        # Remove oldest item to make room
                        try:
                            output_queue.get_nowait()
                            output_queue.put(line, timeout=0.1)
                        except queue.Empty:
                            pass

        except Exception:
            pass  # Thread will exit

    def _start_monitoring_thread(self) -> None:
        """Start the main monitoring thread."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self._shutdown_event.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

    def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs in a separate thread."""
        while self.monitoring_active and not self._shutdown_event.is_set():
            try:
                with self._lock:
                    # Update process status for all monitored processes
                    for session_id, process_info in list(self.monitored_processes.items()):
                        self._update_process_status(process_info)

                # Sleep until next check
                self._shutdown_event.wait(self.check_interval)

            except Exception:
                pass  # Continue monitoring

    def _update_process_status(self, process_info: ProcessInfo) -> None:
        """Update the status of a monitored process."""
        try:
            if not psutil.pid_exists(process_info.pid):
                process_info.status = ProcessState.STOPPED
                return

            process = psutil.Process(process_info.pid)
            status = process.status()

            if status == psutil.STATUS_RUNNING:
                process_info.status = ProcessState.RUNNING
            elif status == psutil.STATUS_SLEEPING:
                process_info.status = ProcessState.RUNNING  # Still active
            elif status == psutil.STATUS_ZOMBIE:
                process_info.status = ProcessState.ZOMBIE
            elif status == psutil.STATUS_STOPPED:
                process_info.status = ProcessState.STOPPED
            else:
                process_info.status = ProcessState.UNKNOWN

            # Update metrics
            process_info.cpu_percent = process.cpu_percent()
            process_info.memory_mb = process.memory_info().rss / 1024 / 1024

            try:
                process_info.open_files = len(process.open_files())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                process_info.open_files = 0

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_info.status = ProcessState.CRASHED

    def __del__(self):
        """Cleanup when monitor is destroyed."""
        try:
            self.stop_monitoring()
        except Exception:
            pass