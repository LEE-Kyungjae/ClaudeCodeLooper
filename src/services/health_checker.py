"""HealthChecker service for process health monitoring.

Provides real-time health metrics and status monitoring for running processes
including CPU usage, memory consumption, and process state tracking.
"""
import time
import psutil
import threading
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from ..models.system_configuration import SystemConfiguration
from ..exceptions import ProcessHealthError


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


class HealthChecker:
    """Service for monitoring process health and performance metrics."""

    def __init__(self, config: SystemConfiguration):
        """Initialize the health checker service.

        Args:
            config: System configuration containing performance thresholds
        """
        self.config = config
        self.monitored_processes: Dict[str, ProcessInfo] = {}

        # Performance thresholds
        self.max_memory_mb = config.performance.get("max_memory_mb", 500)
        self.cpu_limit_percent = config.performance.get("cpu_limit_percent", 20)
        self.check_interval = config.monitoring.get("check_interval", 1.0)

        # Monitoring thread
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()

    def register_process(
        self,
        session_id: str,
        pid: int,
        command: str,
        start_time: Optional[datetime] = None
    ) -> ProcessInfo:
        """Register a process for health monitoring.

        Args:
            session_id: Unique session identifier
            pid: Process ID
            command: Command that started the process
            start_time: When the process started

        Returns:
            ProcessInfo object

        Raises:
            ValueError: If session is already registered
        """
        with self._lock:
            if session_id in self.monitored_processes:
                raise ValueError(f"Process {session_id} is already registered")

            process_info = ProcessInfo(
                pid=pid,
                session_id=session_id,
                command=command,
                start_time=start_time or datetime.now(),
                status=ProcessState.STARTING
            )

            self.monitored_processes[session_id] = process_info

            # Start monitoring thread if not active
            if not self.monitoring_active:
                self._start_monitoring_thread()

            return process_info

    def unregister_process(self, session_id: str) -> bool:
        """Unregister a process from health monitoring.

        Args:
            session_id: Session to unregister

        Returns:
            True if process was unregistered
        """
        with self._lock:
            if session_id in self.monitored_processes:
                del self.monitored_processes[session_id]
                return True
            return False

    def get_health_metrics(self, session_id: str) -> Optional[HealthMetrics]:
        """Get health metrics for a monitored process.

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

    def get_process_status(self, session_id: str) -> Optional[ProcessState]:
        """Get current status of a monitored process.

        Args:
            session_id: Session identifier

        Returns:
            ProcessState or None if not found
        """
        if session_id not in self.monitored_processes:
            return None
        return self.monitored_processes[session_id].status

    def is_healthy(self, session_id: str) -> bool:
        """Check if a process is healthy based on thresholds.

        Args:
            session_id: Session identifier

        Returns:
            True if process is healthy
        """
        metrics = self.get_health_metrics(session_id)
        if metrics is None:
            return False

        # Check against thresholds
        if metrics.memory_mb > self.max_memory_mb:
            return False

        if metrics.cpu_percent > self.cpu_limit_percent:
            return False

        # Check if process is in a healthy state
        healthy_states = ["running", "sleeping"]
        if metrics.status not in healthy_states:
            return False

        return True

    def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """Get all monitored processes.

        Returns:
            Dictionary of session_id to ProcessInfo
        """
        with self._lock:
            return self.monitored_processes.copy()

    def _start_monitoring_thread(self) -> None:
        """Start the health monitoring thread."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self._shutdown_event.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="HealthChecker"
        )
        self.monitoring_thread.start()

    def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs in a separate thread."""
        while self.monitoring_active and not self._shutdown_event.is_set():
            try:
                with self._lock:
                    # Update status for all monitored processes
                    for process_info in list(self.monitored_processes.values()):
                        self._update_process_status(process_info)

                # Sleep until next check
                self._shutdown_event.wait(self.check_interval)

            except Exception:
                # Continue monitoring on error
                pass

    def _update_process_status(self, process_info: ProcessInfo) -> None:
        """Update the status of a monitored process.

        Args:
            process_info: Process to update
        """
        try:
            if not psutil.pid_exists(process_info.pid):
                process_info.status = ProcessState.STOPPED
                return

            process = psutil.Process(process_info.pid)
            status = process.status()

            # Map psutil status to our ProcessState
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

    def shutdown(self) -> None:
        """Shutdown the health monitoring service."""
        self.monitoring_active = False
        self._shutdown_event.set()

        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

    def __del__(self):
        """Cleanup when service is destroyed."""
        try:
            self.shutdown()
        except Exception:
            pass

    def __str__(self) -> str:
        """String representation."""
        return (
            f"HealthChecker("
            f"processes={len(self.monitored_processes)}, "
            f"active={self.monitoring_active}"
            f")"
        )
