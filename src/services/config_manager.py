"""ConfigManager service for configuration management.

Handles loading, saving, validation, and migration of system configuration
with support for environment variable overrides and hot reloading.
"""

import json
import os
import threading
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from ..models.system_configuration import SystemConfiguration


class ConfigValidationResult:
    """Result of configuration validation."""

    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, error: str) -> None:
        """Add validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add validation warning."""
        self.warnings.append(warning)


class ConfigManager:
    """Service for managing system configuration."""

    def __init__(self, config_file: Optional[str] = None):
        """Initialize the config manager."""
        self.config_file = config_file
        self.current_config: Optional[SystemConfiguration] = None
        self._lock = threading.RLock()

        # Configuration schema for validation
        self.schema = self._get_configuration_schema()

        # Environment variable mapping
        self.env_var_mapping = {
            "CLAUDE_RESTART_LOG_LEVEL": ("log_level", str),
            "CLAUDE_RESTART_MAX_LOG_SIZE": ("max_log_size_mb", int),
            "CLAUDE_RESTART_BACKUP_COUNT": ("backup_count", int),
            "CLAUDE_RESTART_CHECK_INTERVAL": ("monitoring.check_interval", float),
            "CLAUDE_RESTART_TASK_TIMEOUT": ("monitoring.task_timeout", int),
            "CLAUDE_RESTART_COOLDOWN_HOURS": ("timing.default_cooldown_hours", float),
        }

    def load_default_config(self) -> SystemConfiguration:
        """Load default configuration."""
        with self._lock:
            self.current_config = SystemConfiguration.create_default()
            return self.current_config

    def load_config(self, file_path: Optional[str] = None) -> SystemConfiguration:
        """
        Load configuration from file.

        Args:
            file_path: Path to configuration file

        Returns:
            SystemConfiguration instance

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            ValueError: If configuration is invalid
        """
        config_path = file_path or self.config_file

        if not config_path or not os.path.exists(config_path):
            return self.load_default_config()

        with self._lock:
            try:
                self.current_config = SystemConfiguration.from_file(config_path)
                self.config_file = config_path

                # Validate loaded configuration
                validation = self.validate_config(self.current_config)
                if not validation.is_valid:
                    raise ValueError(f"Invalid configuration: {validation.errors}")

                return self.current_config

            except Exception as e:
                print(f"Error loading config from {config_path}: {e}")
                # Fall back to default configuration
                return self.load_default_config()

    def load_config_with_recovery(self, file_path: str) -> SystemConfiguration:
        """
        Load configuration with automatic recovery from corruption.

        Args:
            file_path: Path to configuration file

        Returns:
            SystemConfiguration instance
        """
        try:
            return self.load_config(file_path)
        except Exception as e:
            print(f"Config loading failed: {e}")

            # Try to create backup of corrupted file
            if os.path.exists(file_path):
                backup_path = f"{file_path}.corrupted.{int(datetime.now().timestamp())}"
                try:
                    os.rename(file_path, backup_path)
                    print(f"Corrupted config backed up to: {backup_path}")
                except Exception:
                    pass

            # Return default configuration
            return self.load_default_config()

    def load_config_with_env_override(self) -> SystemConfiguration:
        """
        Load configuration with environment variable overrides.

        Returns:
            SystemConfiguration with environment overrides applied
        """
        config = self.load_default_config()

        # Apply environment variable overrides
        for env_var, (config_path, value_type) in self.env_var_mapping.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    # Convert value to appropriate type
                    converted_value = value_type(env_value)

                    # Apply to configuration
                    if "." in config_path:
                        section, key = config_path.split(".", 1)
                        config.update_setting(section, key, converted_value)
                    else:
                        setattr(config, config_path, converted_value)

                except (ValueError, AttributeError) as e:
                    print(f"Error applying environment override {env_var}: {e}")

        return config

    def save_config(
        self, config: SystemConfiguration, file_path: Optional[str] = None
    ) -> bool:
        """
        Save configuration to file.

        Args:
            config: Configuration to save
            file_path: Target file path

        Returns:
            True if saved successfully
        """
        target_path = file_path or self.config_file

        if not target_path:
            raise ValueError("No configuration file path specified")

        with self._lock:
            try:
                # Validate before saving
                validation = self.validate_config(config)
                if not validation.is_valid:
                    raise ValueError(f"Cannot save invalid config: {validation.errors}")

                # Create backup if file exists
                if os.path.exists(target_path):
                    backup_path = f"{target_path}.backup"
                    try:
                        os.rename(target_path, backup_path)
                    except Exception:
                        pass

                # Save configuration
                config.to_file(target_path)
                self.current_config = config
                self.config_file = target_path

                return True

            except Exception as e:
                print(f"Error saving config to {target_path}: {e}")
                return False

    def validate_config(self, config: SystemConfiguration) -> ConfigValidationResult:
        """
        Validate configuration against schema and business rules.

        Args:
            config: Configuration to validate

        Returns:
            ConfigValidationResult with validation details
        """
        result = ConfigValidationResult()

        try:
            # Validate directories
            directory_errors = config.validate_directories()
            for error in directory_errors:
                result.add_error(f"Directory validation: {error}")

            # Validate detection patterns
            if not config.detection_patterns:
                result.add_error("Detection patterns cannot be empty")

            # Validate monitoring settings
            monitoring = config.monitoring
            if monitoring.get("check_interval", 0) <= 0:
                result.add_error("Check interval must be positive")

            if monitoring.get("task_timeout", 0) <= 0:
                result.add_error("Task timeout must be positive")

            # Validate timing settings
            timing = config.timing
            if timing.get("default_cooldown_hours", 0) <= 0:
                result.add_error("Default cooldown hours must be positive")

            # Validate performance settings
            performance = config.performance
            max_memory = performance.get("max_memory_mb", 0)
            if max_memory > 0 and max_memory < 50:
                result.add_warning("Max memory setting is very low (< 50MB)")

            # Validate security settings
            security = config.security
            if security.get("allow_shell_commands", False):
                result.add_warning("Shell command execution is enabled - security risk")

            # Validate Windows settings
            if os.name == "nt":
                windows = config.windows
                if windows.get("service_mode", False) and not windows.get(
                    "use_wmi", True
                ):
                    result.add_warning(
                        "Service mode without WMI may have limited functionality"
                    )

        except Exception as e:
            result.add_error(f"Validation error: {e}")

        return result

    def validate_against_schema(self, config_data: Dict[str, Any]) -> bool:
        """
        Validate configuration data against JSON schema.

        Args:
            config_data: Configuration data as dictionary

        Returns:
            True if valid according to schema
        """
        # Simplified schema validation
        # In production, would use jsonschema library
        required_fields = ["log_level", "detection_patterns", "monitoring", "timing"]

        for field in required_fields:
            if field not in config_data:
                return False

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        if config_data["log_level"] not in valid_log_levels:
            return False

        # Validate detection patterns
        if (
            not isinstance(config_data["detection_patterns"], list)
            or not config_data["detection_patterns"]
        ):
            return False

        return True

    def migrate_config(self, file_path: str) -> SystemConfiguration:
        """
        Migrate configuration from older version.

        Args:
            file_path: Path to old configuration file

        Returns:
            Migrated SystemConfiguration
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)

            # Start with default configuration
            new_config = SystemConfiguration.create_default()

            # Migrate known fields
            if "log_level" in old_data:
                new_config.log_level = old_data["log_level"]

            if "detection_patterns" in old_data:
                new_config.detection_patterns = old_data["detection_patterns"]

            if "max_log_size_mb" in old_data:
                new_config.max_log_size_mb = old_data["max_log_size_mb"]

            # Migrate monitoring settings
            if "monitoring" in old_data:
                new_config.monitoring.update(old_data["monitoring"])

            # Save migrated configuration
            migrated_path = f"{file_path}.migrated"
            new_config.to_file(migrated_path)

            return new_config

        except Exception as e:
            print(f"Error migrating config: {e}")
            return SystemConfiguration.create_default()

    def create_backup(self, config_file: str) -> str:
        """
        Create backup of configuration file.

        Args:
            config_file: Path to configuration file

        Returns:
            Path to backup file
        """
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{config_file}.backup.{timestamp}"

        try:
            import shutil

            shutil.copy2(config_file, backup_path)
            return backup_path
        except Exception as e:
            raise RuntimeError(f"Failed to create backup: {e}")

    def restore_from_backup(self, backup_path: str, target_path: str) -> bool:
        """
        Restore configuration from backup.

        Args:
            backup_path: Path to backup file
            target_path: Target configuration file path

        Returns:
            True if restoration was successful
        """
        try:
            if not os.path.exists(backup_path):
                return False

            import shutil

            shutil.copy2(backup_path, target_path)

            # Reload configuration
            self.load_config(target_path)
            return True

        except Exception as e:
            print(f"Error restoring from backup: {e}")
            return False

    def get_current_config(self) -> Optional[SystemConfiguration]:
        """Get currently loaded configuration."""
        with self._lock:
            return self.current_config

    def update_config_setting(
        self, section: str, key: str, value: Any, save_immediately: bool = True
    ) -> bool:
        """
        Update a specific configuration setting.

        Args:
            section: Configuration section
            key: Setting key
            value: New value
            save_immediately: Whether to save config immediately

        Returns:
            True if update was successful
        """
        with self._lock:
            if self.current_config is None:
                return False

            try:
                self.current_config.update_setting(section, key, value)

                if save_immediately and self.config_file:
                    return self.save_config(self.current_config)

                return True

            except Exception as e:
                print(f"Error updating config setting {section}.{key}: {e}")
                return False

    def reset_to_defaults(self, save_immediately: bool = True) -> SystemConfiguration:
        """
        Reset configuration to defaults.

        Args:
            save_immediately: Whether to save immediately

        Returns:
            Default SystemConfiguration
        """
        with self._lock:
            self.current_config = SystemConfiguration.create_default()

            if save_immediately and self.config_file:
                self.save_config(self.current_config)

            return self.current_config

    def _get_configuration_schema(self) -> Dict[str, Any]:
        """Get JSON schema for configuration validation."""
        return {
            "type": "object",
            "required": ["log_level", "detection_patterns", "monitoring", "timing"],
            "properties": {
                "log_level": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARN", "ERROR"],
                },
                "detection_patterns": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "max_log_size_mb": {"type": "integer", "minimum": 1, "maximum": 1000},
                "backup_count": {"type": "integer", "minimum": 0, "maximum": 10},
                "monitoring": {
                    "type": "object",
                    "required": ["check_interval", "task_timeout"],
                    "properties": {
                        "check_interval": {"type": "number", "minimum": 0.1},
                        "task_timeout": {"type": "integer", "minimum": 60},
                    },
                },
                "timing": {
                    "type": "object",
                    "required": ["default_cooldown_hours"],
                    "properties": {
                        "default_cooldown_hours": {"type": "number", "minimum": 0.1}
                    },
                },
            },
        }

    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration."""
        if self.current_config is None:
            return {"status": "no_config_loaded"}

        return {
            "config_file": self.config_file,
            "log_level": self.current_config.log_level,
            "pattern_count": len(self.current_config.detection_patterns),
            "monitoring_interval": self.current_config.monitoring.get("check_interval"),
            "cooldown_hours": self.current_config.timing.get("default_cooldown_hours"),
            "last_modified": self.current_config.last_modified,
        }

    def __str__(self) -> str:
        """String representation of the config manager."""
        config_file = os.path.basename(self.config_file) if self.config_file else "None"
        has_config = self.current_config is not None

        return f"ConfigManager(" f"file={config_file}, " f"loaded={has_config}" f")"
