"""RestartCommandConfiguration model for Claude Code restart settings.

Represents user-defined commands and parameters that should be executed
when Claude Code is restarted after cooldown periods.
"""

import uuid
import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pathlib import Path


class RestartCommandConfiguration(BaseModel):
    """Model representing restart command configuration."""

    config_id: str = Field(default_factory=lambda: f"cfg_{uuid.uuid4().hex[:12]}")
    command_template: str = Field(..., min_length=1)
    arguments: List[str] = Field(default_factory=list)
    working_directory: Optional[str] = Field(default=None)
    environment_variables: Dict[str, str] = Field(default_factory=dict)

    # Retry configuration
    retry_count: int = Field(default=3, ge=0, le=10)
    retry_delay: int = Field(default=5, ge=1, le=300)

    # Execution options
    shell: bool = Field(default=False)
    timeout_seconds: Optional[int] = Field(default=None, ge=1)
    capture_output: bool = Field(default=True)

    # Pre/post execution hooks
    pre_restart_commands: List[str] = Field(default_factory=list)
    post_restart_commands: List[str] = Field(default_factory=list)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("command_template")
    def validate_command_template(cls, v):
        """Validate the command template is not empty."""
        if not v or not v.strip():
            raise ValueError("Command template cannot be empty")
        return v.strip()

    @field_validator("working_directory")
    def validate_working_directory(cls, v):
        """Validate working directory exists or can be created."""
        if v is None:
            return v

        v = v.strip()
        if not v:
            return None

        # Expand environment variables and user directory
        expanded_path = os.path.expandvars(os.path.expanduser(v))

        # Check if path is absolute or relative
        if not os.path.isabs(expanded_path):
            # For relative paths, we'll validate later when we know the context
            return expanded_path

        # For absolute paths, check if they exist or can be created
        path_obj = Path(expanded_path)
        if not path_obj.exists():
            # Try to create parent directories if they don't exist
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                raise ValueError(f"Cannot access or create directory: {expanded_path}")

        return expanded_path

    @field_validator("retry_count")
    def validate_retry_count(cls, v):
        """Validate retry count is within reasonable bounds."""
        if not 0 <= v <= 10:
            raise ValueError("Retry count must be between 0 and 10")
        return v

    @field_validator("retry_delay")
    def validate_retry_delay(cls, v):
        """Validate retry delay is reasonable."""
        if not 1 <= v <= 300:
            raise ValueError("Retry delay must be between 1 and 300 seconds")
        return v

    @field_validator("timeout_seconds")
    def validate_timeout(cls, v):
        """Validate timeout is reasonable."""
        if v is not None and v < 1:
            raise ValueError("Timeout must be at least 1 second")
        return v

    @field_validator("environment_variables")
    def validate_environment_variables(cls, v):
        """Validate environment variables."""
        if not isinstance(v, dict):
            raise ValueError("Environment variables must be a dictionary")

        # Check for invalid environment variable names
        for key in v.keys():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("Environment variable names must be non-empty strings")
            if "=" in key:
                raise ValueError("Environment variable names cannot contain '='")

        return v

    def build_full_command(self) -> List[str]:
        """Build the complete command with arguments."""
        if self.shell:
            # For shell execution, return as single string
            command_parts = [self.command_template] + self.arguments
            return [" ".join(command_parts)]
        else:
            # For direct execution, return as list
            return [self.command_template] + self.arguments

    def get_working_directory(self) -> Optional[str]:
        """Get the resolved working directory."""
        if self.working_directory is None:
            return None

        # Expand environment variables and user directory
        return os.path.expandvars(os.path.expanduser(self.working_directory))

    def get_environment(self) -> Dict[str, str]:
        """Get the complete environment including system variables."""
        env = os.environ.copy()
        env.update(self.environment_variables)
        return env

    def validate_execution_context(self) -> List[str]:
        """Validate that the command can be executed in the current context."""
        errors = []

        # Check if command exists (for non-shell commands)
        if not self.shell:
            import shutil

            if not shutil.which(self.command_template):
                errors.append(f"Command not found: {self.command_template}")

        # Check working directory accessibility
        work_dir = self.get_working_directory()
        if work_dir:
            if not os.path.exists(work_dir):
                errors.append(f"Working directory does not exist: {work_dir}")
            elif not os.access(work_dir, os.R_OK | os.X_OK):
                errors.append(f"No access to working directory: {work_dir}")

        return errors

    def add_argument(self, argument: str) -> None:
        """Add an argument to the command."""
        if argument and argument.strip():
            self.arguments.append(argument.strip())

    def remove_argument(self, argument: str) -> bool:
        """Remove an argument from the command. Returns True if removed."""
        try:
            self.arguments.remove(argument)
            return True
        except ValueError:
            return False

    def set_environment_variable(self, key: str, value: str) -> None:
        """Set an environment variable."""
        if not key or not key.strip():
            raise ValueError("Environment variable key cannot be empty")
        self.environment_variables[key.strip()] = str(value)

    def remove_environment_variable(self, key: str) -> bool:
        """Remove an environment variable. Returns True if removed."""
        return self.environment_variables.pop(key, None) is not None

    def clone(self) -> "RestartCommandConfiguration":
        """Create a copy of this configuration with a new ID."""
        data = self.model_dump(mode="json")
        data["config_id"] = f"cfg_{uuid.uuid4().hex[:12]}"
        return RestartCommandConfiguration(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "config_id": self.config_id,
            "command_template": self.command_template,
            "arguments": self.arguments,
            "working_directory": self.working_directory,
            "environment_variables": self.environment_variables,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "shell": self.shell,
            "timeout_seconds": self.timeout_seconds,
            "capture_output": self.capture_output,
            "pre_restart_commands": self.pre_restart_commands,
            "post_restart_commands": self.post_restart_commands,
            "full_command": self.build_full_command(),
            "resolved_working_directory": self.get_working_directory(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RestartCommandConfiguration":
        """Create instance from dictionary."""
        # Remove computed fields
        computed_fields = ["full_command", "resolved_working_directory"]
        for field in computed_fields:
            data.pop(field, None)

        return cls(**data)

    @classmethod
    def create_default(cls, claude_command: str) -> "RestartCommandConfiguration":
        """Create a default configuration for a Claude Code command."""
        return cls(
            command_template=claude_command,
            arguments=[],
            retry_count=3,
            retry_delay=5,
            capture_output=True,
        )

    def __str__(self) -> str:
        """String representation of the configuration."""
        cmd = self.build_full_command()
        return f"RestartCommandConfiguration(id={self.config_id}, cmd={cmd[0] if cmd else 'None'})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"RestartCommandConfiguration("
            f"config_id='{self.config_id}', "
            f"command_template='{self.command_template}', "
            f"arguments={self.arguments}, "
            f"working_directory='{self.working_directory}', "
            f"retry_count={self.retry_count}"
            f")"
        )
