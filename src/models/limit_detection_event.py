"""LimitDetectionEvent model for Claude Code usage limit detection.

Represents a detected usage limit notification, including detection timestamp,
matched pattern, and subsequent actions taken.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class LimitDetectionEvent(BaseModel):
    """Model representing a detected usage limit event."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    detection_time: datetime = Field(default_factory=datetime.now)
    matched_pattern: str = Field(..., min_length=1)
    matched_text: str = Field(..., min_length=1)
    session_id: Optional[str] = Field(default=None)

    # Waiting period information
    cooldown_start: Optional[datetime] = Field(default=None)
    cooldown_end: Optional[datetime] = Field(default=None)
    cooldown_duration_hours: float = Field(default=5.0, gt=0)

    # Detection context
    line_number: Optional[int] = Field(default=None, ge=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    context_before: Optional[str] = Field(default=None)
    context_after: Optional[str] = Field(default=None)

    # Processing status
    processed: bool = Field(default=False)
    action_taken: Optional[str] = Field(default=None)
    error_occurred: bool = Field(default=False)
    error_message: Optional[str] = Field(default=None)

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @validator('matched_pattern', 'matched_text')
    def validate_non_empty_strings(cls, v):
        """Ensure required strings are not empty."""
        if not v or not v.strip():
            raise ValueError("Pattern and text cannot be empty")
        return v.strip()

    @validator('session_id', pre=True, always=True)
    def validate_session_id(cls, v):
        """Allow session_id to be assigned lazily."""
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    @validator('cooldown_duration_hours')
    def validate_duration(cls, v):
        """Validate cooldown duration is reasonable."""
        if v <= 0:
            raise ValueError("Cooldown duration must be positive")
        if v > 24:  # More than 24 hours seems unreasonable
            raise ValueError("Cooldown duration cannot exceed 24 hours")
        return v

    @validator('confidence')
    def validate_confidence(cls, v):
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @validator('cooldown_end')
    def validate_cooldown_end(cls, v, values):
        """Validate cooldown end time is after start time."""
        if v is not None and 'cooldown_start' in values:
            cooldown_start = values['cooldown_start']
            if cooldown_start is not None and v <= cooldown_start:
                raise ValueError("Cooldown end must be after start")
        return v

    def start_cooldown(self) -> None:
        """Start the cooldown period."""
        if self.cooldown_start is not None:
            raise ValueError("Cooldown has already been started")

        self.cooldown_start = datetime.now()
        self.cooldown_end = self.cooldown_start + timedelta(hours=self.cooldown_duration_hours)

    def is_cooldown_active(self) -> bool:
        """Check if cooldown period is currently active."""
        if self.cooldown_start is None or self.cooldown_end is None:
            return False

        now = datetime.now()
        return self.cooldown_start <= now < self.cooldown_end

    def is_cooldown_expired(self) -> bool:
        """Check if cooldown period has expired."""
        if self.cooldown_end is None:
            return False

        return datetime.now() >= self.cooldown_end

    def get_remaining_cooldown(self) -> Optional[timedelta]:
        """Get remaining cooldown time."""
        if not self.is_cooldown_active():
            return None

        return self.cooldown_end - datetime.now()

    def get_remaining_cooldown_seconds(self) -> float:
        """Get remaining cooldown time in seconds."""
        remaining = self.get_remaining_cooldown()
        if remaining is None:
            return 0.0
        return remaining.total_seconds()

    @property
    def is_limit_hit(self) -> bool:
        """Heuristic flag indicating whether detection represents a real limit hit."""
        return self.confidence >= 0.8

    def mark_processed(self, action: str) -> None:
        """Mark the event as processed with action taken."""
        self.processed = True
        self.action_taken = action

    def mark_error(self, error_message: str) -> None:
        """Mark that an error occurred processing this event."""
        self.error_occurred = True
        self.error_message = error_message

    def get_cooldown_progress(self) -> float:
        """Get cooldown progress as percentage (0.0 to 1.0)."""
        if not self.is_cooldown_active():
            return 1.0 if self.is_cooldown_expired() else 0.0

        total_duration = self.cooldown_end - self.cooldown_start
        elapsed = datetime.now() - self.cooldown_start

        return min(1.0, elapsed.total_seconds() / total_duration.total_seconds())

    def format_remaining_time(self) -> str:
        """Format remaining cooldown time as human-readable string."""
        remaining = self.get_remaining_cooldown()
        if remaining is None:
            return "No cooldown active"

        total_seconds = int(remaining.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "detection_time": self.detection_time.isoformat(),
            "matched_pattern": self.matched_pattern,
            "matched_text": self.matched_text,
            "session_id": self.session_id,
            "cooldown_start": self.cooldown_start.isoformat() if self.cooldown_start else None,
            "cooldown_end": self.cooldown_end.isoformat() if self.cooldown_end else None,
            "cooldown_duration_hours": self.cooldown_duration_hours,
            "line_number": self.line_number,
            "confidence": self.confidence,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "processed": self.processed,
            "action_taken": self.action_taken,
            "error_occurred": self.error_occurred,
            "error_message": self.error_message,
            "is_cooldown_active": self.is_cooldown_active(),
            "remaining_cooldown_seconds": self.get_remaining_cooldown_seconds(),
            "cooldown_progress": self.get_cooldown_progress()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LimitDetectionEvent":
        """Create instance from dictionary."""
        # Convert datetime strings back to datetime objects
        datetime_fields = ["detection_time", "cooldown_start", "cooldown_end"]
        for field in datetime_fields:
            if isinstance(data.get(field), str):
                data[field] = datetime.fromisoformat(data[field])

        # Remove computed fields
        computed_fields = ["is_cooldown_active", "remaining_cooldown_seconds", "cooldown_progress"]
        for field in computed_fields:
            data.pop(field, None)

        return cls(**data)

    def __str__(self) -> str:
        """String representation of the event."""
        return (
            f"LimitDetectionEvent(id={self.event_id}, "
            f"pattern='{self.matched_pattern}', "
            f"session={self.session_id}, "
            f"processed={self.processed})"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"LimitDetectionEvent("
            f"event_id='{self.event_id}', "
            f"detection_time={self.detection_time}, "
            f"matched_pattern='{self.matched_pattern}', "
            f"matched_text='{self.matched_text[:50]}...', "
            f"session_id='{self.session_id}', "
            f"cooldown_active={self.is_cooldown_active()}"
            f")"
        )
