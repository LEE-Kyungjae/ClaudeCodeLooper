"""QueuedTask model for post-restart task automation.

Represents a pending task that should be executed when Claude Code
resumes after hitting the usage limit cooldown.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

from pydantic import BaseModel, Field


class QueuedTask(BaseModel):
    """Serializable model representing a queued task."""

    task_id: str = Field(default_factory=lambda: f"queue_{uuid.uuid4().hex[:12]}")
    description: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    template_id: Optional[str] = Field(default=None)
    persona_prompt: Optional[str] = Field(default=None)
    guideline_prompt: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    post_commands: List[str] = Field(default_factory=list)

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda value: value.isoformat()}

    def to_dict(self) -> Dict[str, Any]:
        """Return JSON-serializable representation."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "template_id": self.template_id,
            "persona_prompt": self.persona_prompt,
            "guideline_prompt": self.guideline_prompt,
            "notes": self.notes,
            "post_commands": self.post_commands,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueuedTask":
        """Create QueuedTask from dictionary."""
        return cls(**data)
