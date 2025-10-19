"""Integration test for configuration validation.

This test validates configuration management and validation scenarios
across the entire system.

This test MUST FAIL initially before implementation.
"""

import json
import pytest
import tempfile
import os
from pathlib import Path


class TestConfigurationValidation:
    """Integration test for configuration validation scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @pytest.mark.integration
    def test_default_configuration_loading(self):
        """Test that default configuration loads successfully."""
        from src.services.config_manager import ConfigManager
        from src.models.system_configuration import SystemConfiguration

        config_manager = ConfigManager()
        config = config_manager.load_default_config()

        assert isinstance(config, SystemConfiguration)
        assert config.log_level in ["DEBUG", "INFO", "WARN", "ERROR"]
        assert len(config.detection_patterns) > 0
        assert config.max_log_size_mb > 0
        assert config.backup_count >= 0

    @pytest.mark.integration
    def test_custom_configuration_file_loading(self):
        """Test loading configuration from custom file."""
        from src.services.config_manager import ConfigManager

        # Create test config file
        test_config = {
            "log_level": "DEBUG",
            "detection_patterns": ["custom pattern 1", "custom pattern 2"],
            "max_log_size_mb": 25,
            "backup_count": 5,
            "monitoring": {"check_interval": 2, "task_timeout": 600},
        }

        with open(self.config_file, "w") as f:
            json.dump(test_config, f)

        config_manager = ConfigManager()
        config = config_manager.load_config(self.config_file)

        assert config.log_level == "DEBUG"
        assert "custom pattern 1" in config.detection_patterns
        assert config.max_log_size_mb == 25
        assert config.backup_count == 5

    @pytest.mark.integration
    def test_configuration_validation_valid_values(self):
        """Test configuration validation with valid values."""
        from src.services.config_manager import ConfigManager

        valid_configs = [
            {
                "log_level": "INFO",
                "detection_patterns": ["usage limit", "5-hour limit"],
                "max_log_size_mb": 50,
                "backup_count": 3,
            },
            {
                "log_level": "ERROR",
                "detection_patterns": ["rate limit exceeded"],
                "max_log_size_mb": 100,
                "backup_count": 0,
            },
        ]

        config_manager = ConfigManager()

        for test_config in valid_configs:
            with open(self.config_file, "w") as f:
                json.dump(test_config, f)

            # Should not raise exception
            config = config_manager.load_config(self.config_file)
            validation_result = config_manager.validate_config(config)
            assert validation_result.is_valid
            assert len(validation_result.errors) == 0

    @pytest.mark.integration
    def test_configuration_validation_invalid_values(self):
        """Test configuration validation with invalid values."""
        from src.services.config_manager import ConfigManager

        invalid_configs = [
            {
                "log_level": "INVALID_LEVEL",
                "detection_patterns": [],
                "max_log_size_mb": -1,
                "backup_count": -5,
            },
            {
                "log_level": "DEBUG",
                "detection_patterns": None,
                "max_log_size_mb": "not_a_number",
                "backup_count": 15,  # Too high
            },
        ]

        config_manager = ConfigManager()

        for test_config in invalid_configs:
            with open(self.config_file, "w") as f:
                json.dump(test_config, f)

            with pytest.raises(Exception):
                config_manager.load_config(self.config_file)

    @pytest.mark.integration
    def test_configuration_hot_reload(self):
        """Test hot reloading of configuration during runtime."""
        from src.services.config_manager import ConfigManager
        from src.services.restart_controller import RestartController

        # Initial config
        initial_config = {
            "log_level": "INFO",
            "detection_patterns": ["initial pattern"],
            "max_log_size_mb": 25,
        }

        with open(self.config_file, "w") as f:
            json.dump(initial_config, f)

        config_manager = ConfigManager()
        controller = RestartController(config_manager.load_config(self.config_file))

        # Verify initial config
        assert controller.config.log_level == "INFO"
        assert "initial pattern" in controller.config.detection_patterns

        # Update config file
        updated_config = {
            "log_level": "DEBUG",
            "detection_patterns": ["updated pattern", "new pattern"],
            "max_log_size_mb": 50,
        }

        with open(self.config_file, "w") as f:
            json.dump(updated_config, f)

        # Reload config
        controller.reload_config(self.config_file)

        # Verify updated config
        assert controller.config.log_level == "DEBUG"
        assert "updated pattern" in controller.config.detection_patterns
        assert "new pattern" in controller.config.detection_patterns
        assert controller.config.max_log_size_mb == 50

    @pytest.mark.integration
    def test_configuration_backup_and_restore(self):
        """Test configuration backup and restore functionality."""
        from src.services.config_manager import ConfigManager

        original_config = {
            "log_level": "INFO",
            "detection_patterns": ["original pattern"],
            "max_log_size_mb": 50,
            "backup_count": 3,
        }

        with open(self.config_file, "w") as f:
            json.dump(original_config, f)

        config_manager = ConfigManager()

        # Create backup
        backup_path = config_manager.create_backup(self.config_file)
        assert os.path.exists(backup_path)

        # Modify original
        modified_config = {
            "log_level": "ERROR",
            "detection_patterns": ["modified pattern"],
            "max_log_size_mb": 25,
            "backup_count": 1,
        }

        with open(self.config_file, "w") as f:
            json.dump(modified_config, f)

        # Restore from backup
        config_manager.restore_from_backup(backup_path, self.config_file)

        # Verify restoration
        with open(self.config_file, "r") as f:
            restored_config = json.load(f)

        assert restored_config["log_level"] == "INFO"
        assert "original pattern" in restored_config["detection_patterns"]
        assert restored_config["max_log_size_mb"] == 50

    @pytest.mark.integration
    def test_configuration_migration(self):
        """Test configuration migration between versions."""
        from src.services.config_manager import ConfigManager

        # Old version config (missing new fields)
        old_config = {
            "log_level": "INFO",
            "detection_patterns": ["old pattern"],
            # Missing: max_log_size_mb, backup_count, monitoring section
        }

        with open(self.config_file, "w") as f:
            json.dump(old_config, f)

        config_manager = ConfigManager()

        # Should migrate to new format
        migrated_config = config_manager.migrate_config(self.config_file)

        assert migrated_config.log_level == "INFO"
        assert "old pattern" in migrated_config.detection_patterns
        # Should have default values for missing fields
        assert migrated_config.max_log_size_mb > 0
        assert migrated_config.backup_count >= 0

    @pytest.mark.integration
    def test_configuration_environment_variables(self):
        """Test configuration override via environment variables."""
        from src.services.config_manager import ConfigManager
        import os

        # Set environment variables
        os.environ["CLAUDE_RESTART_LOG_LEVEL"] = "ERROR"
        os.environ["CLAUDE_RESTART_MAX_LOG_SIZE"] = "75"

        try:
            config_manager = ConfigManager()
            config = config_manager.load_config_with_env_override()

            assert config.log_level == "ERROR"
            assert config.max_log_size_mb == 75

        finally:
            # Clean up environment variables
            os.environ.pop("CLAUDE_RESTART_LOG_LEVEL", None)
            os.environ.pop("CLAUDE_RESTART_MAX_LOG_SIZE", None)

    @pytest.mark.integration
    def test_configuration_schema_validation(self):
        """Test configuration against JSON schema."""
        from src.services.config_manager import ConfigManager

        # Valid according to schema
        valid_config = {
            "log_level": "INFO",
            "detection_patterns": ["pattern1", "pattern2"],
            "max_log_size_mb": 50,
            "backup_count": 3,
            "monitoring": {"check_interval": 1, "task_timeout": 300},
        }

        # Invalid according to schema
        invalid_config = {
            "log_level": 123,  # Should be string
            "detection_patterns": "not_an_array",  # Should be array
            "max_log_size_mb": "fifty",  # Should be number
            "extra_field": "not_allowed",  # Not in schema
        }

        config_manager = ConfigManager()

        # Valid config should pass
        assert config_manager.validate_against_schema(valid_config)

        # Invalid config should fail
        assert not config_manager.validate_against_schema(invalid_config)

    @pytest.mark.integration
    def test_configuration_concurrent_access(self):
        """Test configuration access from multiple threads."""
        from src.services.config_manager import ConfigManager
        import threading
        import time

        config = {
            "log_level": "INFO",
            "detection_patterns": ["thread test"],
            "max_log_size_mb": 50,
        }

        with open(self.config_file, "w") as f:
            json.dump(config, f)

        config_manager = ConfigManager()
        results = []

        def load_config_thread():
            try:
                loaded_config = config_manager.load_config(self.config_file)
                results.append(loaded_config.log_level)
            except Exception as e:
                results.append(f"Error: {e}")

        # Start multiple threads
        threads = [threading.Thread(target=load_config_thread) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should succeed
        assert len(results) == 5
        assert all(result == "INFO" for result in results)
