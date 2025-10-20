"""SystemConfiguration model for Claude Code restart system.

Represents global system settings and preferences for the automated
restart monitoring system.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum
from pathlib import Path
import os


class LogLevel(str, Enum):
    """Available log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


def _default_monitoring() -> Dict[str, Any]:
    return {
        "check_interval": 1.0,
        "task_timeout": 300,
        "output_buffer_size": 1000,
        "max_processes": 5,
        "allow_process_simulation": True,
        "test_mode": False,
    }


class SystemConfiguration(BaseModel):
    """Model representing system configuration settings."""

    # Version and metadata
    config_version: str = Field(default="1.0.0")
    created_at: Optional[str] = Field(default=None)
    last_modified: Optional[str] = Field(default=None)

    # Logging configuration
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_file_path: Optional[str] = Field(default=None)
    max_log_size_mb: int = Field(default=50, ge=1, le=1000)
    backup_count: int = Field(default=3, ge=0, le=10)

    # Detection patterns
    detection_patterns: List[str] = Field(
        default_factory=lambda: [
            "usage limit exceeded",
            "5-hour limit",
            "please wait",
            r"rate.*limit.*\d+.*hours?",
            "quota exceeded",
        ]
    )

    # File paths
    persistence_file: str = Field(default="state.json")
    config_file: Optional[str] = Field(default=None)
    backup_directory: str = Field(default="backups")

    # Monitoring settings
    monitoring: Dict[str, Any] = Field(default_factory=_default_monitoring)

    # Timing configuration
    timing: Dict[str, Any] = Field(
        default_factory=lambda: {
            "default_cooldown_hours": 5.0,
            "check_frequency_seconds": 60,
            "grace_period_seconds": 10,
            "clock_drift_tolerance_seconds": 30,
        }
    )

    # Notification settings
    notifications: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": True,
            "show_progress": True,
            "notification_intervals": [0.5, 0.25, 0.1],  # Fractions remaining
            "sound_enabled": False,
            "desktop_notifications": True,
        }
    )

    # Performance settings
    performance: Dict[str, Any] = Field(
        default_factory=lambda: {
            "max_memory_mb": 500,
            "cpu_limit_percent": 20,
            "io_priority": "normal",
            "process_priority": "normal",
        }
    )

    # Security and reliability
    security: Dict[str, Any] = Field(
        default_factory=lambda: {
            "allow_shell_commands": False,
            "restricted_directories": [],
            "max_command_length": 1000,
            "validate_commands": True,
        }
    )

    # Windows-specific settings
    windows: Dict[str, Any] = Field(
        default_factory=lambda: {
            "use_wmi": True,
            "service_mode": False,
            "hide_console": False,
            "startup_delay_seconds": 5,
        }
    )

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("detection_patterns")
    def validate_detection_patterns(cls, v):
        """Validate detection patterns are not empty and compilable."""
        if not v:
            raise ValueError("Detection patterns cannot be empty")

        import re

        for pattern in v:
            if not pattern or not pattern.strip():
                raise ValueError("Detection patterns cannot contain empty strings")
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

        return [p.strip() for p in v]

    @field_validator("max_log_size_mb")
    def validate_log_size(cls, v):
        """Validate log size is reasonable."""
        if not 1 <= v <= 1000:
            raise ValueError("Log size must be between 1 and 1000 MB")
        return v

    @field_validator("log_level", mode="before")
    def normalize_log_level(cls, value: Any) -> LogLevel:
        """Ensure log level values resolve to LogLevel enum members."""
        if isinstance(value, LogLevel):
            return value
        if isinstance(value, str):
            try:
                return LogLevel(value.upper())
            except ValueError as exc:
                raise ValueError(f"Invalid log level: {value}") from exc
        raise ValueError("Log level must be a string or LogLevel enum")

    @field_validator("backup_count")
    def validate_backup_count(cls, v):
        """Validate backup count is reasonable."""
        if not 0 <= v <= 10:
            raise ValueError("Backup count must be between 0 and 10")
        return v

    @field_validator("monitoring", mode="before")
    def merge_monitoring_defaults(cls, v: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged = _default_monitoring()
        if isinstance(v, dict):
            merged.update(v)
        return merged

    @field_validator("monitoring")
    def validate_monitoring_settings(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate monitoring configuration."""
        required_keys = [
            "check_interval",
            "task_timeout",
            "output_buffer_size",
            "max_processes",
        ]
        for key in required_keys:
            if key not in v:
                raise ValueError(f"Missing required monitoring setting: {key}")

        # Validate ranges
        if not 0.001 <= v["check_interval"] <= 60:
            raise ValueError("Check interval must be between 0.001 and 60 seconds")
        if not 1 <= v["task_timeout"] <= 3600:
            raise ValueError("Task timeout must be between 1 and 3600 seconds")
        if not 100 <= v["output_buffer_size"] <= 10000:
            raise ValueError("Output buffer size must be between 100 and 10000 lines")
        if not 1 <= v["max_processes"] <= 20:
            raise ValueError("Max processes must be between 1 and 20")

        return v

    @field_validator("timing")
    def validate_timing_settings(cls, v):
        """Validate timing configuration."""
        required_keys = ["default_cooldown_hours", "check_frequency_seconds"]
        for key in required_keys:
            if key not in v:
                raise ValueError(f"Missing required timing setting: {key}")

        if not 0.1 <= v["default_cooldown_hours"] <= 24:
            raise ValueError("Default cooldown must be between 0.1 and 24 hours")
        if not 1 <= v["check_frequency_seconds"] <= 3600:
            raise ValueError("Check frequency must be between 1 and 3600 seconds")

        return v

    @field_validator("performance")
    def validate_performance_settings(cls, v):
        """Validate performance configuration."""
        if "max_memory_mb" in v and not 50 <= v["max_memory_mb"] <= 2000:
            raise ValueError("Max memory must be between 50 and 2000 MB")
        if "cpu_limit_percent" in v and not 1 <= v["cpu_limit_percent"] <= 100:
            raise ValueError("CPU limit must be between 1 and 100 percent")

        return v

    def get_log_file_path(self) -> str:
        """Get the resolved log file path."""
        if self.log_file_path:
            return os.path.expandvars(os.path.expanduser(self.log_file_path))

        # Default log file location
        if os.name == "nt":  # Windows
            log_dir = os.path.expandvars("%LOCALAPPDATA%\\claude-restart-monitor")
        else:
            log_dir = os.path.expanduser("~/.claude-restart-monitor")

        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, "claude-restart-monitor.log")

    def get_persistence_file_path(self) -> str:
        """Get the resolved persistence file path."""
        if os.path.isabs(self.persistence_file):
            return self.persistence_file

        # Relative to default directory
        if os.name == "nt":  # Windows
            data_dir = os.path.expandvars("%LOCALAPPDATA%\\claude-restart-monitor")
        else:
            data_dir = os.path.expanduser("~/.claude-restart-monitor")

        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, self.persistence_file)

    def get_backup_directory_path(self) -> str:
        """Get the resolved backup directory path."""
        if os.path.isabs(self.backup_directory):
            return self.backup_directory

        # Relative to default directory
        data_dir = os.path.dirname(self.get_persistence_file_path())
        backup_path = os.path.join(data_dir, self.backup_directory)
        os.makedirs(backup_path, exist_ok=True)
        return backup_path

    def is_pattern_case_sensitive(self) -> bool:
        """Check if pattern matching should be case sensitive."""
        return self.monitoring.get("case_sensitive_patterns", False)

    def get_detection_timeout(self) -> float:
        """Get timeout for pattern detection in seconds."""
        return self.timing.get("detection_timeout_seconds", 1.0)

    def should_validate_commands(self) -> bool:
        """Check if commands should be validated before execution."""
        return self.security.get("validate_commands", True)

    def is_shell_allowed(self) -> bool:
        """Check if shell command execution is allowed."""
        return self.security.get("allow_shell_commands", False)

    def get_max_command_length(self) -> int:
        """Get maximum allowed command length."""
        return self.security.get("max_command_length", 1000)

    def is_directory_restricted(self, directory: str) -> bool:
        """Check if a directory is restricted."""
        restricted = self.security.get("restricted_directories", [])
        abs_dir = os.path.abspath(directory)

        for restricted_dir in restricted:
            abs_restricted = os.path.abspath(restricted_dir)
            if abs_dir.startswith(abs_restricted):
                return True

        return False

    def get_notification_settings(self) -> Dict[str, Any]:
        """Get notification configuration."""
        return self.notifications.copy()

    def allows_process_simulation(self) -> bool:
        """Check if process simulation is permitted."""
        return bool(self.monitoring.get("allow_process_simulation", True))

    def is_test_mode_enabled(self) -> bool:
        """Check if test mode is enabled."""
        return bool(self.monitoring.get("test_mode", False))

    def update_setting(self, section: str, key: str, value: Any) -> None:
        """Update a configuration setting."""
        if section == "monitoring":
            self.monitoring[key] = value
        elif section == "timing":
            self.timing[key] = value
        elif section == "notifications":
            self.notifications[key] = value
        elif section == "performance":
            self.performance[key] = value
        elif section == "security":
            self.security[key] = value
        elif section == "windows":
            self.windows[key] = value
        else:
            # Direct attribute
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown setting: {section}.{key}")

    def create_backup_config(self) -> Dict[str, Any]:
        """Create a backup-safe version of configuration."""
        backup_config = self.model_dump(mode="json")

        # Remove sensitive or temporary data
        sensitive_keys = ["config_file", "last_modified"]
        for key in sensitive_keys:
            backup_config.pop(key, None)

        return backup_config

    def validate_directories(self) -> List[str]:
        """Validate all configured directories and return any errors."""
        errors = []

        # Check log file directory
        try:
            log_path = self.get_log_file_path()
            log_dir = os.path.dirname(log_path)
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            errors.append(f"Log directory error: {e}")

        # Check persistence file directory
        try:
            persistence_path = self.get_persistence_file_path()
            persistence_dir = os.path.dirname(persistence_path)
            if not os.path.exists(persistence_dir):
                os.makedirs(persistence_dir, exist_ok=True)
        except Exception as e:
            errors.append(f"Persistence directory error: {e}")

        # Check backup directory
        try:
            self.get_backup_directory_path()
        except Exception as e:
            errors.append(f"Backup directory error: {e}")

        return errors

    @classmethod
    def create_default(cls) -> "SystemConfiguration":
        """Create a default configuration instance."""
        return cls()

    def to_file(self, file_path: str) -> None:
        """Save configuration to JSON file."""
        import json
        from datetime import datetime

        # Update metadata
        self.last_modified = datetime.now().isoformat()
        self.config_file = file_path

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def __str__(self) -> str:
        """String representation of the configuration."""
        return (
            f"SystemConfiguration("
            f"version={self.config_version}, "
            f"log_level={self.log_level}, "
            f"patterns={len(self.detection_patterns)}, "
            f"monitoring_interval={self.monitoring['check_interval']}s"
            f")"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"SystemConfiguration("
            f"config_version='{self.config_version}', "
            f"log_level={self.log_level}, "
            f"max_log_size_mb={self.max_log_size_mb}, "
            f"detection_patterns={len(self.detection_patterns)} patterns"
            f")"
        )

    @staticmethod
    def _merge_dict(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge helper for configuration dictionaries."""
        result = base.copy()
        for key, value in overrides.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = SystemConfiguration._merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    @classmethod
    def from_file(cls, file_path: str) -> "SystemConfiguration":
        """Load configuration from JSON file with default merge."""
        import json

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        default_dict = cls.create_default().model_dump(mode="json")
        merged = cls._merge_dict(default_dict, data)

        # Ensure enum fields maintain their enum types after merging
        log_level = merged.get("log_level")
        if isinstance(log_level, str):
            normalized_level = log_level.upper()
            try:
                merged["log_level"] = LogLevel(normalized_level)
            except ValueError:
                merged["log_level"] = LogLevel.INFO

        return cls(**merged)
