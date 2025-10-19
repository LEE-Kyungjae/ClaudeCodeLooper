"""TimingManager service for precise 5-hour countdown management.

Handles waiting periods, countdown timers, clock drift detection,
and precise timing for Claude Code restart cycles.
"""

import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from ..models.system_configuration import SystemConfiguration
from ..models.waiting_period import WaitingPeriod, PeriodStatus


@dataclass
class ClockDriftEvent:
    """Information about detected clock drift."""

    detection_time: datetime
    drift_seconds: float
    previous_time: datetime
    current_time: datetime
    action_taken: str


class TimingManager:
    """Service for managing precise timing and countdown periods."""

    def __init__(self, config: SystemConfiguration):
        """Initialize the timing manager."""
        self.config = config
        self.active_periods: Dict[str, WaitingPeriod] = {}
        self.completed_periods: List[WaitingPeriod] = []
        self.clock_drift_events: List[ClockDriftEvent] = []

        # Timing configuration
        self.check_frequency = config.timing.get("check_frequency_seconds", 60)
        self.clock_drift_tolerance = config.timing.get(
            "clock_drift_tolerance_seconds", 30
        )
        self.default_cooldown_hours = config.timing.get("default_cooldown_hours", 5.0)

        # Monitoring thread
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._lock = threading.RLock()

        # Clock drift detection
        self.last_clock_check = datetime.now()
        self.system_boot_time = self._get_system_boot_time()

        # Callbacks
        self.completion_callbacks: Dict[str, Callable] = {}

    def add_waiting_period(
        self,
        period_id: Optional[str] = None,
        duration_hours: Optional[float] = None,
        session_id: Optional[str] = None,
        event_id: Optional[str] = None,
        auto_start: bool = True,
    ) -> WaitingPeriod:
        """
        Add a new waiting period.

        Args:
            period_id: Unique identifier (generated if None)
            duration_hours: Duration in hours (uses default if None)
            session_id: Associated session ID
            event_id: Associated detection event ID
            auto_start: Whether to start immediately

        Returns:
            WaitingPeriod instance
        """
        if duration_hours is None:
            duration_hours = self.default_cooldown_hours

        waiting_period = WaitingPeriod(
            period_id=period_id,
            duration_hours=duration_hours,
            session_id=session_id,
            associated_event_id=event_id,
            check_interval_seconds=self.check_frequency,
        )

        with self._lock:
            self.active_periods[waiting_period.period_id] = waiting_period

            if auto_start:
                waiting_period.start_waiting()

            # Start monitoring if not already running
            if not self.monitoring_active:
                self._start_monitoring()

        return waiting_period

    def remove_waiting_period(
        self, period_id: str, mark_completed: bool = True
    ) -> bool:
        """
        Remove a waiting period.

        Args:
            period_id: Period identifier
            mark_completed: Whether to mark as completed

        Returns:
            True if period was removed
        """
        with self._lock:
            if period_id not in self.active_periods:
                return False

            period = self.active_periods[period_id]

            if mark_completed and period.status == PeriodStatus.ACTIVE:
                period.complete()

            # Move to completed list
            self.completed_periods.append(period)
            del self.active_periods[period_id]

            # Remove callback if exists
            self.completion_callbacks.pop(period_id, None)

            return True

    def cancel_waiting_period(self, period_id: str) -> bool:
        """
        Cancel a waiting period.

        Args:
            period_id: Period identifier

        Returns:
            True if period was cancelled
        """
        with self._lock:
            if period_id not in self.active_periods:
                return False

            period = self.active_periods[period_id]
            period.cancel()

            return self.remove_waiting_period(period_id, mark_completed=False)

    def get_waiting_period(self, period_id: str) -> Optional[WaitingPeriod]:
        """Get a waiting period by ID."""
        with self._lock:
            return self.active_periods.get(period_id)

    def get_active_periods(self) -> List[WaitingPeriod]:
        """Get all active waiting periods."""
        with self._lock:
            return list(self.active_periods.values())

    def get_completed_periods(self, limit: Optional[int] = None) -> List[WaitingPeriod]:
        """Get completed waiting periods."""
        with self._lock:
            if limit is None:
                return self.completed_periods.copy()
            return self.completed_periods[-limit:] if limit > 0 else []

    def check_waiting_periods(self) -> List[str]:
        """
        Check all waiting periods for completion.

        Returns:
            List of period IDs that completed
        """
        completed_ids = []

        with self._lock:
            for period_id, period in list(self.active_periods.items()):
                if period.check_and_complete():
                    completed_ids.append(period_id)

                    # Execute completion callback if exists
                    callback = self.completion_callbacks.get(period_id)
                    if callback:
                        try:
                            callback(period)
                        except Exception as e:
                            print(
                                f"Error executing completion callback for {period_id}: {e}"
                            )

                    # Move to completed list
                    self.completed_periods.append(period)
                    del self.active_periods[period_id]
                    self.completion_callbacks.pop(period_id, None)

        return completed_ids

    def set_completion_callback(
        self, period_id: str, callback: Callable[[WaitingPeriod], None]
    ) -> bool:
        """
        Set a callback to execute when a waiting period completes.

        Args:
            period_id: Period identifier
            callback: Function to call on completion

        Returns:
            True if callback was set
        """
        with self._lock:
            if period_id in self.active_periods:
                self.completion_callbacks[period_id] = callback
                return True
            return False

    def get_remaining_time(self, period_id: str) -> Optional[timedelta]:
        """Get remaining time for a waiting period."""
        period = self.get_waiting_period(period_id)
        return period.get_remaining_time() if period else None

    def get_remaining_seconds(self, period_id: str) -> float:
        """Get remaining time in seconds for a waiting period."""
        remaining = self.get_remaining_time(period_id)
        return remaining.total_seconds() if remaining else 0.0

    def fast_forward_period(self, period_id: str, seconds: float) -> bool:
        """
        Fast-forward a waiting period (for testing).

        Args:
            period_id: Period identifier
            seconds: Seconds to fast-forward

        Returns:
            True if period was fast-forwarded
        """
        with self._lock:
            period = self.active_periods.get(period_id)
            if not period or not period.is_active():
                return False

            # Adjust the start time to simulate time passage
            if period.start_time:
                period.start_time -= timedelta(seconds=seconds)
                if period.end_time:
                    period.end_time -= timedelta(seconds=seconds)

            return True

    def check_clock_drift(self) -> Optional[ClockDriftEvent]:
        """
        Check for system clock drift.

        Returns:
            ClockDriftEvent if significant drift detected
        """
        current_time = datetime.now()
        expected_time = self.last_clock_check + timedelta(seconds=self.check_frequency)

        # Calculate drift
        actual_elapsed = (current_time - self.last_clock_check).total_seconds()
        expected_elapsed = self.check_frequency
        drift = abs(actual_elapsed - expected_elapsed)

        if drift > self.clock_drift_tolerance:
            # Significant drift detected
            drift_event = ClockDriftEvent(
                detection_time=current_time,
                drift_seconds=drift,
                previous_time=self.last_clock_check,
                current_time=current_time,
                action_taken="adjusting_periods",
            )

            self.clock_drift_events.append(drift_event)
            self._adjust_periods_for_drift(drift_event)

            self.last_clock_check = current_time
            return drift_event

        self.last_clock_check = current_time
        return None

    def _adjust_periods_for_drift(self, drift_event: ClockDriftEvent) -> None:
        """Adjust waiting periods for detected clock drift."""
        with self._lock:
            adjustment = timedelta(seconds=drift_event.drift_seconds)

            for period in self.active_periods.values():
                if period.is_active() and period.end_time:
                    # Adjust end time to compensate for drift
                    if drift_event.drift_seconds > 0:
                        # Clock jumped forward, reduce remaining time
                        period.end_time -= adjustment
                    else:
                        # Clock jumped backward, increase remaining time
                        period.end_time += adjustment

    def get_system_uptime(self) -> timedelta:
        """Get system uptime since boot."""
        if self.system_boot_time:
            return datetime.now() - self.system_boot_time
        return timedelta(0)

    def _get_system_boot_time(self) -> Optional[datetime]:
        """Get system boot time."""
        try:
            import psutil

            boot_timestamp = psutil.boot_time()
            return datetime.fromtimestamp(boot_timestamp)
        except Exception:
            return None

    def get_timing_statistics(self) -> Dict[str, Any]:
        """Get timing system statistics."""
        with self._lock:
            active_count = len(self.active_periods)
            completed_count = len(self.completed_periods)

            avg_duration = 0.0
            if completed_count > 0:
                total_duration = sum(
                    p.get_elapsed_seconds()
                    for p in self.completed_periods
                    if p.is_completed()
                )
                avg_duration = total_duration / completed_count

            return {
                "active_periods": active_count,
                "completed_periods": completed_count,
                "drift_events": len(self.clock_drift_events),
                "monitoring_active": self.monitoring_active,
                "check_frequency_seconds": self.check_frequency,
                "average_period_duration_seconds": avg_duration,
                "system_uptime_hours": self.get_system_uptime().total_seconds() / 3600,
                "last_clock_check": self.last_clock_check.isoformat(),
                "default_cooldown_hours": self.default_cooldown_hours,
            }

    def create_notification_schedule(self, period_id: str) -> List[datetime]:
        """
        Create notification schedule for a waiting period.

        Args:
            period_id: Period identifier

        Returns:
            List of datetime objects when notifications should be sent
        """
        period = self.get_waiting_period(period_id)
        if not period or not period.is_active():
            return []

        notifications = []
        triggers = period.get_notification_triggers()

        for trigger_seconds in triggers:
            notification_time = period.end_time - timedelta(seconds=trigger_seconds)
            if notification_time > datetime.now():
                notifications.append(notification_time)

        return sorted(notifications)

    def _start_monitoring(self) -> None:
        """Start the monitoring thread."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self._shutdown_event.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitoring_thread.start()

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active and not self._shutdown_event.is_set():
            try:
                # Check for clock drift
                self.check_clock_drift()

                # Check waiting periods
                self.check_waiting_periods()

                # Stop monitoring if no active periods
                with self._lock:
                    if not self.active_periods:
                        self.monitoring_active = False
                        break

                # Wait until next check
                self._shutdown_event.wait(self.check_frequency)

            except Exception as e:
                # Log error but continue monitoring
                print(f"Error in timing monitoring loop: {e}")
                time.sleep(1)

    def stop_monitoring(self) -> None:
        """Stop the monitoring thread."""
        self.monitoring_active = False
        self._shutdown_event.set()

        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

    def force_check_all_periods(self) -> Dict[str, str]:
        """
        Force check all periods immediately.

        Returns:
            Dictionary mapping period IDs to their new status
        """
        results = {}

        with self._lock:
            for period_id, period in self.active_periods.items():
                old_status = period.status
                period.check_and_complete()
                results[period_id] = f"{old_status} -> {period.status}"

        return results

    def __del__(self):
        """Cleanup when timing manager is destroyed."""
        try:
            self.stop_monitoring()
        except Exception:
            pass

    def __str__(self) -> str:
        """String representation of the timing manager."""
        return (
            f"TimingManager("
            f"active={len(self.active_periods)}, "
            f"completed={len(self.completed_periods)}, "
            f"monitoring={self.monitoring_active}"
            f")"
        )
