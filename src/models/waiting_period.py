"""WaitingPeriod model for Claude Code cooldown management.

Represents an active 5-hour countdown period, including start time,
remaining duration, and completion callback information.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class PeriodStatus(str, Enum):
    """Possible states of a waiting period."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WaitingPeriod(BaseModel):
    """Model representing a cooldown waiting period."""

    period_id: str = Field(default_factory=lambda: f"wait_{uuid.uuid4().hex[:12]}")
    start_time: datetime = Field(default_factory=datetime.now)
    duration_hours: float = Field(default=5.0, gt=0)
    end_time: Optional[datetime] = Field(default=None)
    status: PeriodStatus = Field(default=PeriodStatus.PENDING)

    # Associated event information
    associated_event_id: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None)

    # Progress tracking
    last_check_time: Optional[datetime] = Field(default=None)
    check_interval_seconds: int = Field(default=60, ge=1, le=3600)

    # Completion handling
    auto_complete: bool = Field(default=True)
    completion_callback_data: Optional[Dict[str, Any]] = Field(default=None)

    # Display and notification settings
    show_progress: bool = Field(default=True)
    notification_intervals: list = Field(
        default_factory=lambda: [0.5, 0.25, 0.1]
    )  # Fractions remaining

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    @validator("duration_hours")
    def validate_duration(cls, v):
        """Validate duration is reasonable."""
        if v <= 0:
            raise ValueError("Duration must be positive")
        if v > 24:  # More than 24 hours
            raise ValueError("Duration cannot exceed 24 hours")
        return v

    @validator("check_interval_seconds")
    def validate_check_interval(cls, v):
        """Validate check interval is reasonable."""
        if not 1 <= v <= 3600:  # 1 second to 1 hour
            raise ValueError("Check interval must be between 1 and 3600 seconds")
        return v

    @validator("notification_intervals")
    def validate_notification_intervals(cls, v):
        """Validate notification intervals are valid fractions."""
        if not v:
            return v

        for interval in v:
            if not isinstance(interval, (int, float)) or not 0 < interval <= 1:
                raise ValueError(
                    "Notification intervals must be fractions between 0 and 1"
                )

        # Sort in descending order
        return sorted(v, reverse=True)

    def start_waiting(self) -> None:
        """Start the waiting period."""
        if self.status != PeriodStatus.PENDING:
            raise ValueError(f"Cannot start waiting period in {self.status} state")

        self.status = PeriodStatus.ACTIVE
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=self.duration_hours)
        self.last_check_time = self.start_time

    def complete(self) -> None:
        """Mark the waiting period as completed."""
        if self.status not in [PeriodStatus.ACTIVE, PeriodStatus.PENDING]:
            raise ValueError(f"Cannot complete waiting period in {self.status} state")

        self.status = PeriodStatus.COMPLETED
        self.last_check_time = datetime.now()

    def cancel(self) -> None:
        """Cancel the waiting period."""
        if self.status == PeriodStatus.COMPLETED:
            raise ValueError("Cannot cancel completed waiting period")

        self.status = PeriodStatus.CANCELLED
        self.last_check_time = datetime.now()

    def is_active(self) -> bool:
        """Check if waiting period is currently active."""
        return self.status == PeriodStatus.ACTIVE

    def is_completed(self) -> bool:
        """Check if waiting period is completed."""
        return self.status == PeriodStatus.COMPLETED

    def is_cancelled(self) -> bool:
        """Check if waiting period is cancelled."""
        return self.status == PeriodStatus.CANCELLED

    def is_expired(self) -> bool:
        """Check if waiting period has naturally expired."""
        if not self.is_active() or self.end_time is None:
            return False

        return datetime.now() >= self.end_time

    def get_remaining_time(self) -> Optional[timedelta]:
        """Get remaining time in the waiting period."""
        if not self.is_active() or self.end_time is None:
            return None

        remaining = self.end_time - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)

    def get_remaining_seconds(self) -> float:
        """Get remaining time in seconds."""
        remaining = self.get_remaining_time()
        if remaining is None:
            return 0.0
        return max(0.0, remaining.total_seconds())

    def get_elapsed_time(self) -> timedelta:
        """Get elapsed time since start."""
        if self.status == PeriodStatus.PENDING:
            return timedelta(0)

        return datetime.now() - self.start_time

    def get_elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return self.get_elapsed_time().total_seconds()

    def get_progress(self) -> float:
        """Get progress as a fraction between 0.0 and 1.0."""
        if self.status == PeriodStatus.PENDING:
            return 0.0
        elif self.status in [PeriodStatus.COMPLETED, PeriodStatus.CANCELLED]:
            return 1.0

        if self.end_time is None:
            return 0.0

        total_duration = self.end_time - self.start_time
        elapsed = datetime.now() - self.start_time

        progress = elapsed.total_seconds() / total_duration.total_seconds()
        return min(1.0, max(0.0, progress))

    def get_progress_percentage(self) -> float:
        """Get progress as a percentage (0 to 100)."""
        return self.get_progress() * 100.0

    def format_remaining_time(self) -> str:
        """Format remaining time as human-readable string."""
        remaining = self.get_remaining_time()
        if remaining is None:
            return "No time remaining"

        total_seconds = int(remaining.total_seconds())
        if total_seconds <= 0:
            return "Time expired"

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def should_check_completion(self) -> bool:
        """Check if it's time to check for completion."""
        if not self.is_active():
            return False

        if self.last_check_time is None:
            return True

        time_since_check = datetime.now() - self.last_check_time
        return time_since_check.total_seconds() >= self.check_interval_seconds

    def update_check_time(self) -> None:
        """Update the last check time."""
        self.last_check_time = datetime.now()

    def check_and_complete(self) -> bool:
        """Check if period should be completed and complete it if so."""
        if not self.is_active():
            return False

        self.update_check_time()

        if self.is_expired() and self.auto_complete:
            self.complete()
            return True

        return False

    def get_notification_triggers(self) -> List[float]:
        """Get remaining time thresholds that should trigger notifications."""
        if not self.is_active() or not self.notification_intervals:
            return []

        total_duration = timedelta(hours=self.duration_hours)
        triggers = []

        for fraction in self.notification_intervals:
            trigger_time = total_duration.total_seconds() * fraction
            triggers.append(trigger_time)

        return triggers

    def should_notify(self, last_notification_time: Optional[datetime] = None) -> bool:
        """Check if a notification should be sent based on remaining time."""
        if not self.is_active() or not self.show_progress:
            return False

        remaining_seconds = self.get_remaining_seconds()
        triggers = self.get_notification_triggers()

        for trigger in triggers:
            if remaining_seconds <= trigger:
                # Check if we haven't notified recently for this trigger
                if last_notification_time is None:
                    return True

                time_since_notification = datetime.now() - last_notification_time
                if (
                    time_since_notification.total_seconds()
                    >= self.check_interval_seconds
                ):
                    return True

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "period_id": self.period_id,
            "start_time": self.start_time.isoformat(),
            "duration_hours": self.duration_hours,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "associated_event_id": self.associated_event_id,
            "session_id": self.session_id,
            "last_check_time": (
                self.last_check_time.isoformat() if self.last_check_time else None
            ),
            "check_interval_seconds": self.check_interval_seconds,
            "auto_complete": self.auto_complete,
            "completion_callback_data": self.completion_callback_data,
            "show_progress": self.show_progress,
            "notification_intervals": self.notification_intervals,
            "remaining_seconds": self.get_remaining_seconds(),
            "progress": self.get_progress(),
            "formatted_remaining": self.format_remaining_time(),
            "is_expired": self.is_expired(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WaitingPeriod":
        """Create instance from dictionary."""
        # Convert datetime strings back to datetime objects
        datetime_fields = ["start_time", "end_time", "last_check_time"]
        for field in datetime_fields:
            if isinstance(data.get(field), str):
                data[field] = datetime.fromisoformat(data[field])

        # Remove computed fields
        computed_fields = [
            "remaining_seconds",
            "progress",
            "formatted_remaining",
            "is_expired",
        ]
        for field in computed_fields:
            data.pop(field, None)

        return cls(**data)

    def __str__(self) -> str:
        """String representation of the waiting period."""
        return (
            f"WaitingPeriod(id={self.period_id}, "
            f"status={self.status}, "
            f"remaining={self.format_remaining_time()}, "
            f"progress={self.get_progress_percentage():.1f}%)"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"WaitingPeriod("
            f"period_id='{self.period_id}', "
            f"start_time={self.start_time}, "
            f"duration_hours={self.duration_hours}, "
            f"status={self.status}, "
            f"associated_event_id='{self.associated_event_id}'"
            f")"
        )
