"""TaskCompletionMonitor model for Claude Code task monitoring.

Represents the mechanism for ensuring Claude Code tasks finish before
restart cycles begin, preventing token waste and incomplete operations.
"""

import uuid
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Pattern
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum


class TaskStatus(str, Enum):
    """Possible states of task monitoring."""

    IDLE = "idle"
    MONITORING = "monitoring"
    TASK_DETECTED = "task_detected"
    WAITING_COMPLETION = "waiting_completion"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"


class TaskCompletionMonitor(BaseModel):
    """Model for monitoring Claude Code task completion."""

    monitor_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    session_id: Optional[str] = Field(default=None)
    status: TaskStatus = Field(default=TaskStatus.IDLE)

    # Pattern configuration
    task_start_patterns: List[str] = Field(
        default_factory=lambda: [
            r"generating.*response",
            r"processing.*request",
            r"analyzing.*code",
            r"working.*on",
            r"thinking.*about",
            r"creating.*file",
            r"implementing.*",
            r"writing.*code",
        ]
    )

    task_completion_patterns: List[str] = Field(
        default_factory=lambda: [
            r"completed.*successfully",
            r"finished.*task",
            r"done.*processing",
            r"ready.*for.*next",
            r"task.*complete",
            r"✓.*complete",
            r"generation.*finished",
            r"operation.*successful",
        ]
    )

    # Timing configuration
    timeout_seconds: int = Field(default=300, ge=60, le=3600)  # 5 minutes default
    check_interval: float = Field(default=1.0, ge=0.1, le=60.0)
    grace_period_seconds: int = Field(default=10, ge=0, le=300)

    # State tracking
    task_start_time: Optional[datetime] = Field(default=None)
    last_activity_time: Optional[datetime] = Field(default=None)
    last_check_time: Optional[datetime] = Field(default=None)
    completion_detected_time: Optional[datetime] = Field(default=None)

    # Output monitoring
    monitored_output_lines: int = Field(default=0, ge=0)
    task_related_output: List[str] = Field(default_factory=list, max_items=100)

    # Advanced detection
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    require_explicit_completion: bool = Field(default=False)
    ignore_system_messages: bool = Field(default=True)

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("task_start_patterns", "task_completion_patterns")
    def validate_patterns(cls, v):
        """Validate regex patterns are compilable."""
        if not v:
            return v

        compiled_patterns = []
        for pattern in v:
            try:
                re.compile(pattern, re.IGNORECASE)
                compiled_patterns.append(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

        return compiled_patterns

    @field_validator("timeout_seconds")
    def validate_timeout(cls, v):
        """Validate timeout is reasonable."""
        if not 60 <= v <= 3600:  # 1 minute to 1 hour
            raise ValueError("Timeout must be between 60 and 3600 seconds")
        return v

    @field_validator("check_interval")
    def validate_check_interval(cls, v):
        """Validate check interval is reasonable."""
        if not 0.1 <= v <= 60.0:
            raise ValueError("Check interval must be between 0.1 and 60 seconds")
        return v

    def get_compiled_patterns(self, pattern_list: List[str]) -> List[Pattern]:
        """Get compiled regex patterns."""
        return [re.compile(pattern, re.IGNORECASE) for pattern in pattern_list]

    def start_monitoring(self, session_id: str) -> None:
        """Start monitoring for task activity."""
        if self.status not in [TaskStatus.IDLE, TaskStatus.COMPLETED]:
            raise ValueError(f"Cannot start monitoring in {self.status} state")

        self.status = TaskStatus.MONITORING
        self.session_id = session_id
        self.last_check_time = datetime.now()
        self.monitored_output_lines = 0
        self.task_related_output.clear()

    def stop_monitoring(self) -> None:
        """Stop monitoring and reset state."""
        self.status = TaskStatus.IDLE
        self.task_start_time = None
        self.last_activity_time = None
        self.completion_detected_time = None

    def process_output_line(self, line: str) -> bool:
        """
        Process a line of output and update task state.
        Returns True if task completion is detected.
        """
        if self.status == TaskStatus.IDLE:
            return False

        self.monitored_output_lines += 1
        self.last_check_time = datetime.now()

        # Skip system messages if configured
        if self.ignore_system_messages and self._is_system_message(line):
            return False

        # Check for task start patterns
        if self.status == TaskStatus.MONITORING:
            if self._matches_start_patterns(line):
                self.status = TaskStatus.TASK_DETECTED
                self.task_start_time = datetime.now()
                self.last_activity_time = datetime.now()
                self.task_related_output.append(line)
                return False

        # Check for task completion patterns
        elif self.status in [TaskStatus.TASK_DETECTED, TaskStatus.WAITING_COMPLETION]:
            self.last_activity_time = datetime.now()

            if self._matches_completion_patterns(line):
                self.status = TaskStatus.COMPLETED
                self.completion_detected_time = datetime.now()
                self.task_related_output.append(line)
                return True

            # Add to task-related output if it seems relevant
            if self._is_task_related(line):
                self.task_related_output.append(line)

        return False

    def _is_system_message(self, line: str) -> bool:
        """Check if line is a system message to ignore."""
        system_indicators = [
            "[DEBUG]",
            "[INFO]",
            "[WARN]",
            "[ERROR]",
            "claude-code:",
            "system:",
            "debug:",
            "timestamp:",
            "process id:",
        ]

        line_lower = line.lower().strip()
        return any(indicator.lower() in line_lower for indicator in system_indicators)

    def _matches_start_patterns(self, line: str) -> bool:
        """Check if line matches task start patterns."""
        patterns = self.get_compiled_patterns(self.task_start_patterns)
        return any(pattern.search(line) for pattern in patterns)

    def _matches_completion_patterns(self, line: str) -> bool:
        """Check if line matches task completion patterns."""
        patterns = self.get_compiled_patterns(self.task_completion_patterns)
        return any(pattern.search(line) for pattern in patterns)

    def _is_task_related(self, line: str) -> bool:
        """Check if line seems related to ongoing task."""
        task_keywords = [
            "file",
            "code",
            "function",
            "class",
            "implementation",
            "writing",
            "creating",
            "generating",
            "analyzing",
            "processing",
        ]

        line_lower = line.lower()
        return any(keyword in line_lower for keyword in task_keywords)

    def is_task_in_progress(self) -> bool:
        """Check if a task is currently in progress."""
        return self.status in [TaskStatus.TASK_DETECTED, TaskStatus.WAITING_COMPLETION]

    def set_task_in_progress(self, active: bool) -> None:
        """Manually toggle task-in-progress state (testing and overrides)."""
        if active:
            self.status = TaskStatus.WAITING_COMPLETION
            if self.task_start_time is None:
                self.task_start_time = datetime.now()
            self.last_activity_time = datetime.now()
        else:
            self.status = TaskStatus.COMPLETED
            self.completion_detected_time = datetime.now()

    def is_waiting_for_completion(self) -> bool:
        """Check if waiting for task completion."""
        return self.status == TaskStatus.WAITING_COMPLETION

    def is_task_completed(self) -> bool:
        """Check if task has been completed."""
        return self.status == TaskStatus.COMPLETED

    def has_timed_out(self) -> bool:
        """Check if task monitoring has timed out."""
        if self.task_start_time is None or not self.is_task_in_progress():
            return False

        elapsed = datetime.now() - self.task_start_time
        return elapsed.total_seconds() > self.timeout_seconds

    def get_task_duration(self) -> Optional[timedelta]:
        """Get duration of current or last task."""
        if self.task_start_time is None:
            return None

        end_time = self.completion_detected_time or datetime.now()
        return end_time - self.task_start_time

    def get_task_duration_seconds(self) -> float:
        """Get task duration in seconds."""
        duration = self.get_task_duration()
        return duration.total_seconds() if duration else 0.0

    def get_time_since_last_activity(self) -> Optional[timedelta]:
        """Get time since last task-related activity."""
        if self.last_activity_time is None:
            return None

        return datetime.now() - self.last_activity_time

    def should_wait_for_completion(self) -> bool:
        """Determine if system should wait for task completion."""
        if not self.is_task_in_progress():
            return False

        # Don't wait if timed out
        if self.has_timed_out():
            self.status = TaskStatus.TIMEOUT
            return False

        # Check if task seems abandoned (no activity for grace period)
        time_since_activity = self.get_time_since_last_activity()
        if (
            time_since_activity
            and time_since_activity.total_seconds() > self.grace_period_seconds
        ):
            if not self.require_explicit_completion:
                self.status = TaskStatus.COMPLETED
                return False

        return True

    def force_completion(self, reason: str = "Manual completion") -> None:
        """Force mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completion_detected_time = datetime.now()
        self.task_related_output.append(f"[FORCED COMPLETION] {reason}")

    def reset_for_new_task(self) -> None:
        """Reset monitor for a new task."""
        self.status = TaskStatus.MONITORING
        self.task_start_time = None
        self.last_activity_time = None
        self.completion_detected_time = None
        self.monitored_output_lines = 0
        self.task_related_output.clear()

    def get_task_summary(self) -> Dict[str, Any]:
        """Get summary of current task status."""
        return {
            "status": self.status,
            "is_task_active": self.is_task_in_progress(),
            "duration_seconds": self.get_task_duration_seconds(),
            "output_lines_monitored": self.monitored_output_lines,
            "task_related_lines": len(self.task_related_output),
            "has_timed_out": self.has_timed_out(),
            "should_wait": self.should_wait_for_completion(),
            "start_time": (
                self.task_start_time.isoformat() if self.task_start_time else None
            ),
            "completion_time": (
                self.completion_detected_time.isoformat()
                if self.completion_detected_time
                else None
            ),
        }

    def add_custom_pattern(self, pattern_type: str, pattern: str) -> None:
        """Add a custom pattern for detection."""
        try:
            re.compile(pattern, re.IGNORECASE)  # Validate pattern
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        if pattern_type == "start":
            self.task_start_patterns.append(pattern)
        elif pattern_type == "completion":
            self.task_completion_patterns.append(pattern)
        else:
            raise ValueError("Pattern type must be 'start' or 'completion'")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "monitor_id": self.monitor_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "task_start_patterns": self.task_start_patterns,
            "task_completion_patterns": self.task_completion_patterns,
            "timeout_seconds": self.timeout_seconds,
            "check_interval": self.check_interval,
            "grace_period_seconds": self.grace_period_seconds,
            "task_start_time": (
                self.task_start_time.isoformat() if self.task_start_time else None
            ),
            "last_activity_time": (
                self.last_activity_time.isoformat() if self.last_activity_time else None
            ),
            "last_check_time": (
                self.last_check_time.isoformat() if self.last_check_time else None
            ),
            "completion_detected_time": (
                self.completion_detected_time.isoformat()
                if self.completion_detected_time
                else None
            ),
            "monitored_output_lines": self.monitored_output_lines,
            "task_related_output": self.task_related_output,
            "confidence_threshold": self.confidence_threshold,
            "require_explicit_completion": self.require_explicit_completion,
            "ignore_system_messages": self.ignore_system_messages,
            "task_summary": self.get_task_summary(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskCompletionMonitor":
        """Create instance from dictionary."""
        # Convert datetime strings back to datetime objects
        datetime_fields = [
            "task_start_time",
            "last_activity_time",
            "last_check_time",
            "completion_detected_time",
        ]
        for field in datetime_fields:
            if isinstance(data.get(field), str):
                data[field] = datetime.fromisoformat(data[field])

        # Remove computed fields
        data.pop("task_summary", None)

        return cls(**data)

    def __str__(self) -> str:
        """String representation of the monitor."""
        return (
            f"TaskCompletionMonitor(id={self.monitor_id}, "
            f"status={self.status}, "
            f"active={self.is_task_in_progress()}, "
            f"duration={self.get_task_duration_seconds():.1f}s)"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"TaskCompletionMonitor("
            f"monitor_id='{self.monitor_id}', "
            f"session_id='{self.session_id}', "
            f"status={self.status}, "
            f"timeout_seconds={self.timeout_seconds}"
            f")"
        )
