"""MonitoringSession model for Claude Code monitoring.

Represents an active monitoring period of Claude Code terminal output,
including start time, current status, and detection history.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .restart_command_config import RestartCommandConfiguration


class SessionStatus(str, Enum):
    """Possible states of a monitoring session."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    WAITING = "waiting"
    STOPPED = "stopped"


class MonitoringSession(BaseModel):
    """Model representing a Claude Code monitoring session."""

    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    start_time: datetime = Field(default_factory=datetime.now)
    status: SessionStatus = Field(default=SessionStatus.INACTIVE)
    claude_process_id: Optional[int] = Field(default=None)
    detection_count: int = Field(default=0, ge=0)
    last_activity: Optional[datetime] = Field(default=None)

    # Command configuration
    claude_command: str = Field(..., min_length=1)
    working_directory: Optional[str] = Field(default=None)
    restart_commands: List[str] = Field(default_factory=list)

    # Runtime information
    restart_config_id: Optional[str] = Field(default=None)
    waiting_period_id: Optional[str] = Field(default=None)
    error_count: int = Field(default=0, ge=0)
    last_error: Optional[str] = Field(default=None)
    restart_config: Optional[RestartCommandConfiguration] = Field(default=None)

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("claude_command")
    def validate_claude_command(cls, v):
        """Validate Claude Code command."""
        if not v or not v.strip():
            raise ValueError("Claude command cannot be empty")
        return v.strip()

    @field_validator("detection_count", "error_count")
    def validate_counts(cls, v):
        """Ensure counts are non-negative."""
        if v < 0:
            raise ValueError("Count values must be non-negative")
        return v

    def start_monitoring(self, process_id: int) -> None:
        """Start the monitoring session with a process ID."""
        if self.status != SessionStatus.INACTIVE:
            raise ValueError(f"Cannot start monitoring in {self.status} state")

        self.status = SessionStatus.ACTIVE
        self.claude_process_id = process_id
        self.last_activity = datetime.now()

    def stop_monitoring(self) -> None:
        """Stop the monitoring session."""
        self.status = SessionStatus.STOPPED
        self.last_activity = datetime.now()

    def mark_crashed(self) -> None:
        """Mark session as crashed and stop monitoring."""
        self.status = SessionStatus.STOPPED
        self.last_activity = datetime.now()

    def enter_waiting_period(self, waiting_period_id: str) -> None:
        """Enter waiting period after limit detection."""
        if self.status != SessionStatus.ACTIVE:
            raise ValueError(f"Cannot enter waiting from {self.status} state")

        self.status = SessionStatus.WAITING
        self.waiting_period_id = waiting_period_id
        self.detection_count += 1
        self.last_activity = datetime.now()

    def resume_from_waiting(self) -> None:
        """Resume monitoring after waiting period expires."""
        if self.status != SessionStatus.WAITING:
            raise ValueError(f"Cannot resume from {self.status} state")

        self.status = SessionStatus.ACTIVE
        self.waiting_period_id = None
        self.last_activity = datetime.now()

    def record_error(self, error_message: str) -> None:
        """Record an error during monitoring."""
        self.error_count += 1
        self.last_error = error_message
        self.last_activity = datetime.now()

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def get_uptime_seconds(self) -> float:
        """Get session uptime in seconds."""
        if self.status == SessionStatus.INACTIVE:
            return 0.0

        end_time = self.last_activity or datetime.now()
        return (end_time - self.start_time).total_seconds()

    def is_active(self) -> bool:
        """Check if session is actively monitoring."""
        return self.status == SessionStatus.ACTIVE

    def is_waiting(self) -> bool:
        """Check if session is in waiting period."""
        return self.status == SessionStatus.WAITING

    def is_stopped(self) -> bool:
        """Check if session is stopped."""
        return self.status == SessionStatus.STOPPED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "status": self.status.value,
            "claude_process_id": self.claude_process_id,
            "detection_count": self.detection_count,
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
            "claude_command": self.claude_command,
            "working_directory": self.working_directory,
            "restart_commands": self.restart_commands,
            "restart_config_id": self.restart_config_id,
            "waiting_period_id": self.waiting_period_id,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "restart_config": (
                self.restart_config.to_dict() if self.restart_config else None
            ),
            "uptime_seconds": self.get_uptime_seconds(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MonitoringSession":
        """Create instance from dictionary."""
        # Convert datetime strings back to datetime objects
        if isinstance(data.get("start_time"), str):
            data["start_time"] = datetime.fromisoformat(data["start_time"])

        if isinstance(data.get("last_activity"), str):
            data["last_activity"] = datetime.fromisoformat(data["last_activity"])

        # Remove computed fields
        data.pop("uptime_seconds", None)

        restart_config_data = data.pop("restart_config", None)
        instance = cls(**data)
        if restart_config_data:
            instance.restart_config = RestartCommandConfiguration.from_dict(
                restart_config_data
            )
        return instance

    def __str__(self) -> str:
        """String representation of the session."""
        return (
            f"MonitoringSession(id={self.session_id}, "
            f"status={self.status}, "
            f"pid={self.claude_process_id}, "
            f"detections={self.detection_count})"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"MonitoringSession("
            f"session_id='{self.session_id}', "
            f"start_time={self.start_time}, "
            f"status={self.status}, "
            f"claude_process_id={self.claude_process_id}, "
            f"detection_count={self.detection_count}, "
            f"claude_command='{self.claude_command}'"
            f")"
        )
