"""RestartController service for orchestrating restart cycles.

Main orchestration service that coordinates all components for the
automated Claude Code restart system.
"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from ..models.system_configuration import SystemConfiguration
from ..models.monitoring_session import MonitoringSession, SessionStatus
from ..models.limit_detection_event import LimitDetectionEvent
from ..models.waiting_period import WaitingPeriod, PeriodStatus
from ..models.restart_command_config import RestartCommandConfiguration
from ..models.task_completion_monitor import TaskCompletionMonitor, TaskStatus

from .process_monitor import ProcessMonitor
from .pattern_detector import PatternDetector
from .timing_manager import TimingManager
from .state_manager import StateManager
from .config_manager import ConfigManager


class ControllerState(Enum):
    """Controller states."""
    INACTIVE = "inactive"
    STARTING = "starting"
    MONITORING = "monitoring"
    LIMIT_DETECTED = "limit_detected"
    WAITING = "waiting"
    RESTARTING = "restarting"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class SystemStatus:
    """Overall system status."""
    state: ControllerState
    active_sessions: int
    waiting_periods: int
    total_detections: int
    uptime_seconds: float
    last_activity: Optional[datetime]
    error_message: Optional[str] = None


class RestartController:
    """Main orchestration service for Claude Code restart system."""

    def __init__(self, config: SystemConfiguration):
        """Initialize the restart controller."""
        self.config = config
        self.state = ControllerState.INACTIVE

        # Initialize services
        self.process_monitor = ProcessMonitor(config)
        self.pattern_detector = PatternDetector(config)
        self.timing_manager = TimingManager(config)
        self.state_manager = StateManager(config)
        self.config_manager = ConfigManager()

        # Data storage
        self.active_sessions: Dict[str, MonitoringSession] = {}
        self.waiting_periods: Dict[str, WaitingPeriod] = {}
        self.detection_events: List[LimitDetectionEvent] = []
        self.task_monitors: Dict[str, TaskCompletionMonitor] = {}

        # Thread safety
        self._lock = threading.RLock()

        # Main control loop
        self.controller_thread: Optional[threading.Thread] = None
        self.running = False
        self._shutdown_event = threading.Event()

        # Statistics
        self.start_time = datetime.now()
        self.last_activity = datetime.now()
        self.error_count = 0
        self.restart_count = 0

        # Callbacks
        self.event_callbacks: Dict[str, List[Callable]] = {
            "limit_detected": [],
            "waiting_started": [],
            "restart_initiated": [],
            "restart_completed": [],
            "error_occurred": []
        }

    def start_monitoring(
        self,
        claude_cmd: str,
        work_dir: Optional[str] = None,
        restart_commands: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> MonitoringSession:
        """
        Start monitoring a Claude Code process.

        Args:
            claude_cmd: Command to start Claude Code
            work_dir: Working directory
            restart_commands: Commands to execute on restart
            session_id: Session identifier

        Returns:
            MonitoringSession instance

        Raises:
            RuntimeError: If monitoring fails to start
        """
        with self._lock:
            try:
                # Create monitoring session
                session_kwargs = {
                    "claude_command": claude_cmd,
                    "working_directory": work_dir,
                    "restart_commands": restart_commands or []
                }
                if session_id:
                    session_kwargs["session_id"] = session_id

                session = MonitoringSession(**session_kwargs)

                # Create restart configuration snapshot for the session
                restart_config = RestartCommandConfiguration.create_default(claude_cmd)
                if restart_commands:
                    restart_config.arguments.extend(list(restart_commands))
                session.restart_config = restart_config
                session.restart_config_id = restart_config.config_id
                session.restart_commands = restart_config.arguments.copy()

                # Start process monitoring
                process_info = self.process_monitor.start_monitoring(
                    command=claude_cmd,
                    session_id=session.session_id,
                    work_dir=work_dir
                )

                # Update session with process info
                session.start_monitoring(process_info.pid)

                # Create task completion monitor
                task_monitor = TaskCompletionMonitor(session_id=session.session_id)
                task_monitor.start_monitoring(session.session_id)
                self.task_monitors[session.session_id] = task_monitor

                # Store session
                self.active_sessions[session.session_id] = session

                # Start main controller if not running
                if not self.running:
                    self._start_controller()

                self.state = ControllerState.MONITORING
                self.last_activity = datetime.now()

                # Save state
                self._save_current_state()

                return session

            except Exception as e:
                self.state = ControllerState.ERROR
                self._trigger_event("error_occurred", {"error": str(e), "context": "start_monitoring"})
                raise RuntimeError(f"Failed to start monitoring: {e}")

    def stop_monitoring(self, session_id: Optional[str] = None) -> bool:
        """
        Stop monitoring a specific session or all sessions.

        Args:
            session_id: Session to stop (all if None)

        Returns:
            True if stopped successfully
        """
        with self._lock:
            try:
                if session_id:
                    return self._stop_single_session(session_id)
                else:
                    return self._stop_all_sessions()

            except Exception as e:
                self._trigger_event("error_occurred", {"error": str(e), "context": "stop_monitoring"})
                return False

    def _stop_single_session(self, session_id: str) -> bool:
        """Stop a single monitoring session."""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]

        # Stop process monitoring
        self.process_monitor.stop_monitoring(session_id)

        # Stop task monitoring
        if session_id in self.task_monitors:
            self.task_monitors[session_id].stop_monitoring()
            del self.task_monitors[session_id]

        # Cancel any waiting periods
        waiting_periods_to_cancel = [
            period_id for period_id, period in self.waiting_periods.items()
            if period.session_id == session_id
        ]

        for period_id in waiting_periods_to_cancel:
            self.timing_manager.cancel_waiting_period(period_id)
            del self.waiting_periods[period_id]

        # Update session status
        session.stop_monitoring()
        del self.active_sessions[session_id]

        # Update controller state
        if not self.active_sessions:
            self.state = ControllerState.INACTIVE

        self._save_current_state()
        return True

    def _stop_all_sessions(self) -> bool:
        """Stop all monitoring sessions."""
        success = True
        session_ids = list(self.active_sessions.keys())

        for session_id in session_ids:
            if not self._stop_single_session(session_id):
                success = False

        # Stop controller
        self._stop_controller()

        return success

    def _start_controller(self) -> None:
        """Start the main controller thread."""
        if self.running:
            return

        self.running = True
        self._shutdown_event.clear()
        self.controller_thread = threading.Thread(target=self._controller_loop, daemon=True)
        self.controller_thread.start()

    def _stop_controller(self) -> None:
        """Stop the main controller thread."""
        self.running = False
        self._shutdown_event.set()

        if self.controller_thread and self.controller_thread.is_alive():
            self.controller_thread.join(timeout=5)

        self.state = ControllerState.INACTIVE

    def _controller_loop(self) -> None:
        """Main controller loop."""
        while self.running and not self._shutdown_event.is_set():
            try:
                # Check for limit detections
                self._check_for_limit_detections()

                # Check waiting periods
                self._check_waiting_periods()

                # Check task completions
                self._check_task_completions()

                # Auto-save state if needed
                if self.state_manager.should_auto_save():
                    self._save_current_state()

                # Sleep until next check
                check_interval = self.config.monitoring.get("check_interval", 1.0)
                self._shutdown_event.wait(check_interval)

            except Exception as e:
                self.error_count += 1
                self._trigger_event("error_occurred", {"error": str(e), "context": "controller_loop"})
                time.sleep(1)  # Prevent tight error loops

    def _check_for_limit_detections(self) -> None:
        """Check all active sessions for limit detections."""
        for session_id, session in list(self.active_sessions.items()):
            if not session.is_active():
                continue

            # Get recent output from process monitor
            recent_output = self.process_monitor.get_recent_output(session_id, lines=10)

            for line in recent_output:
                # Check for limit detection
                detection_event = self.pattern_detector.detect_limit_message(line)

                if detection_event:
                    detection_event.session_id = session_id
                    self._handle_limit_detection(session, detection_event)
                    break  # Only process one detection per check

    def _handle_limit_detection(self, session: MonitoringSession, event: LimitDetectionEvent) -> None:
        """Handle a detected usage limit."""
        with self._lock:
            # Check if task is in progress
            task_monitor = self.task_monitors.get(session.session_id)
            if task_monitor and task_monitor.should_wait_for_completion():
                # Wait for task completion before entering waiting period
                return

            # Start cooldown period
            event.start_cooldown()

            # Create waiting period
            waiting_period = self.timing_manager.add_waiting_period(
                duration_hours=event.cooldown_duration_hours,
                session_id=session.session_id,
                event_id=event.event_id
            )

            # Set completion callback
            self.timing_manager.set_completion_callback(
                waiting_period.period_id,
                lambda period: self._handle_waiting_completion(period)
            )

            # Update session state
            session.enter_waiting_period(waiting_period.period_id)

            # Store data
            self.detection_events.append(event)
            self.waiting_periods[waiting_period.period_id] = waiting_period

            # Update controller state
            self.state = ControllerState.WAITING
            self.last_activity = datetime.now()

            # Save state
            self._save_current_state()

            # Trigger event
            self._trigger_event("limit_detected", {
                "session_id": session.session_id,
                "event": event,
                "waiting_period": waiting_period
            })

    def _check_waiting_periods(self) -> None:
        """Check all waiting periods for completion."""
        completed_periods = self.timing_manager.check_waiting_periods()

        for period_id in completed_periods:
            if period_id in self.waiting_periods:
                period = self.waiting_periods[period_id]
                self._handle_waiting_completion(period)

    def _handle_waiting_completion(self, waiting_period: WaitingPeriod) -> None:
        """Handle completion of a waiting period."""
        with self._lock:
            session_id = waiting_period.session_id
            if not session_id or session_id not in self.active_sessions:
                return

            session = self.active_sessions[session_id]

            # Initiate restart
            self._initiate_restart(session)

            # Clean up waiting period
            if waiting_period.period_id in self.waiting_periods:
                del self.waiting_periods[waiting_period.period_id]

    def _initiate_restart(self, session: MonitoringSession) -> None:
        """Initiate Claude Code restart."""
        with self._lock:
            try:
                self.state = ControllerState.RESTARTING
                self._trigger_event("restart_initiated", {"session_id": session.session_id})

                # Stop current process
                self.process_monitor.stop_monitoring(session.session_id)

                # Build restart command
                restart_config = session.restart_config.clone() if session.restart_config else RestartCommandConfiguration.create_default(session.claude_command)

                # Start new process
                process_info = self.process_monitor.start_monitoring(
                    command=" ".join(restart_config.build_full_command()),
                    session_id=session.session_id,
                    work_dir=session.working_directory
                )

                # Update session
                session.resume_from_waiting()
                session.claude_process_id = process_info.pid
                session.restart_config = restart_config
                session.restart_config_id = restart_config.config_id
                session.restart_commands = restart_config.arguments.copy()

                # Reset task monitor
                task_monitor = self.task_monitors.get(session.session_id)
                if task_monitor:
                    task_monitor.reset_for_new_task()

                self.state = ControllerState.MONITORING
                self.restart_count += 1
                self.last_activity = datetime.now()

                # Save state
                self._save_current_state()

                # Trigger event
                self._trigger_event("restart_completed", {"session_id": session.session_id})

            except Exception as e:
                self.state = ControllerState.ERROR
                session.record_error(f"Restart failed: {e}")
                self._trigger_event("error_occurred", {
                    "error": str(e),
                    "context": "restart",
                    "session_id": session.session_id
                })

    def _check_task_completions(self) -> None:
        """Check task completion monitors."""
        for session_id, task_monitor in self.task_monitors.items():
            if session_id not in self.active_sessions:
                continue

            # Get recent output
            recent_output = self.process_monitor.get_recent_output(session_id, lines=5)

            # Process output through task monitor
            for line in recent_output:
                task_monitor.process_output_line(line)

    def get_session(self, session_id: str) -> Optional[MonitoringSession]:
        """Get a monitoring session by ID."""
        with self._lock:
            return self.active_sessions.get(session_id)

    def get_system_status(self) -> SystemStatus:
        """Get overall system status."""
        with self._lock:
            uptime = (datetime.now() - self.start_time).total_seconds()

            return SystemStatus(
                state=self.state,
                active_sessions=len(self.active_sessions),
                waiting_periods=len(self.waiting_periods),
                total_detections=len(self.detection_events),
                uptime_seconds=uptime,
                last_activity=self.last_activity,
                error_message=None
            )

    @property
    def waiting_period(self) -> Optional[WaitingPeriod]:
        """Compatibility accessor returning the first active waiting period."""
        with self._lock:
            for period in self.waiting_periods.values():
                return period
            return None

    @property
    def task_monitor(self) -> Optional[TaskCompletionMonitor]:
        """Compatibility accessor returning the primary task monitor."""
        with self._lock:
            for monitor in self.task_monitors.values():
                return monitor
            return None

    def get_recent_logs(self, lines: int = 50) -> List[str]:
        """Get recent system logs."""
        # This would integrate with the logging system
        # For now, return basic status information
        return [
            f"System state: {self.state.value}",
            f"Active sessions: {len(self.active_sessions)}",
            f"Waiting periods: {len(self.waiting_periods)}",
            f"Total detections: {len(self.detection_events)}",
            f"Restart count: {self.restart_count}",
            f"Error count: {self.error_count}"
        ]

    def reload_config(self, config_file: Optional[str] = None) -> bool:
        """Reload configuration from file."""
        try:
            new_config = self.config_manager.load_config(config_file)
            self.config = new_config

            # Update services with new configuration
            self.pattern_detector.update_patterns(new_config.detection_patterns)

            return True
        except Exception as e:
            self._trigger_event("error_occurred", {"error": str(e), "context": "reload_config"})
            return False

    def add_event_callback(self, event_type: str, callback: Callable) -> None:
        """Add event callback."""
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)

    def remove_event_callback(self, event_type: str, callback: Callable) -> bool:
        """Remove event callback."""
        if event_type in self.event_callbacks:
            try:
                self.event_callbacks[event_type].remove(callback)
                return True
            except ValueError:
                pass
        return False

    def _trigger_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger event callbacks."""
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in event callback for {event_type}: {e}")

    def _save_current_state(self) -> None:
        """Save current system state."""
        try:
            state_data = {
                "sessions": {sid: session.to_dict() for sid, session in self.active_sessions.items()},
                "waiting_periods": {pid: period.to_dict() for pid, period in self.waiting_periods.items()},
                "detection_events": [event.to_dict() for event in self.detection_events[-100:]],  # Keep last 100
                "statistics": {
                    "start_time": self.start_time.isoformat(),
                    "restart_count": self.restart_count,
                    "error_count": self.error_count,
                    "state": self.state.value
                }
            }

            self.state_manager.save_state(state_data)
        except Exception as e:
            print(f"Error saving state: {e}")

    def restore_state(self) -> bool:
        """Restore system state from persistence."""
        try:
            state_data = self.state_manager.load_state()
            if not state_data:
                return False

            # Restore sessions (but don't restart processes)
            for session_id, session_data in state_data.get("sessions", {}).items():
                session = MonitoringSession.from_dict(session_data)
                # Mark as stopped since processes won't be running
                session.stop_monitoring()
                self.active_sessions[session_id] = session

            # Restore waiting periods
            for period_id, period_data in state_data.get("waiting_periods", {}).items():
                period = WaitingPeriod.from_dict(period_data)
                # Only restore active periods
                if period.is_active() and not period.is_expired():
                    self.waiting_periods[period_id] = period
                    self.timing_manager.active_periods[period_id] = period

            # Restore detection events
            for event_data in state_data.get("detection_events", []):
                event = LimitDetectionEvent.from_dict(event_data)
                self.detection_events.append(event)

            # Restore statistics
            stats = state_data.get("statistics", {})
            if "restart_count" in stats:
                self.restart_count = stats["restart_count"]
            if "error_count" in stats:
                self.error_count = stats["error_count"]

            return True

        except Exception as e:
            print(f"Error restoring state: {e}")
            return False

    def __del__(self):
        """Cleanup when controller is destroyed."""
        try:
            self._stop_all_sessions()
        except Exception:
            pass

    def __str__(self) -> str:
        """String representation of the controller."""
        return (
            f"RestartController("
            f"state={self.state.value}, "
            f"sessions={len(self.active_sessions)}, "
            f"waiting={len(self.waiting_periods)}"
            f")"
        )
