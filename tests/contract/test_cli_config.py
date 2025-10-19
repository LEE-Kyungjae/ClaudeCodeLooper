"""Contract tests for CLI config command.

These tests define the expected behavior and interface of the config command.
They MUST FAIL initially before implementation.
"""

import json
import pytest
from click.testing import CliRunner


class TestConfigCommandContract:
    """Test contract for claude-restart-monitor config command."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_config_command_exists(self):
        """Test that config command is available."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ["--help"])
        assert "config" in result.output

    def test_config_show_operation(self):
        """Test config show operation."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        # Should contain configuration information
        assert any(
            word in result.output.lower()
            for word in ["log_level", "detection_patterns", "config"]
        )

    def test_config_set_operation(self):
        """Test config set operation."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ["config", "set", "log_level", "DEBUG"])
        assert result.exit_code == 0
        assert "set" in result.output.lower() or "updated" in result.output.lower()

    def test_config_reset_operation(self):
        """Test config reset operation."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ["config", "reset"])
        assert result.exit_code == 0
        assert "reset" in result.output.lower() or "default" in result.output.lower()

    def test_config_validate_operation(self):
        """Test config validate operation."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ["config", "validate"])
        assert result.exit_code == 0
        assert any(
            word in result.output.lower() for word in ["valid", "invalid", "validation"]
        )

    def test_config_validate_with_file(self):
        """Test config validate with custom file."""
        from src.cli.main import cli

        result = self.runner.invoke(
            cli, ["config", "validate", "--file", "config.json"]
        )
        assert result.exit_code in [0, 1]  # Valid or invalid config

    def test_config_set_valid_values(self):
        """Test config set with valid configuration values."""
        from src.cli.main import cli

        valid_configs = [
            ("log_level", "INFO"),
            ("log_level", "DEBUG"),
            ("log_level", "WARN"),
            ("log_level", "ERROR"),
            ("max_log_size_mb", "50"),
            ("backup_count", "3"),
        ]

        for key, value in valid_configs:
            result = self.runner.invoke(cli, ["config", "set", key, value])
            assert result.exit_code == 0

    def test_config_set_invalid_values(self):
        """Test config set with invalid configuration values."""
        from src.cli.main import cli

        invalid_configs = [
            ("log_level", "INVALID"),
            ("max_log_size_mb", "-1"),
            ("backup_count", "not_a_number"),
        ]

        for key, value in invalid_configs:
            result = self.runner.invoke(cli, ["config", "set", key, value])
            assert result.exit_code != 0  # Should fail validation

    def test_config_show_json_format(self):
        """Test config show with JSON format."""
        from src.cli.main import cli

        # Check if JSON option exists in help
        help_result = self.runner.invoke(cli, ["config", "show", "--help"])
        if "--json" in help_result.output:
            result = self.runner.invoke(cli, ["config", "show", "--json"])
            assert result.exit_code == 0
            try:
                data = json.loads(result.output)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                pytest.fail("Output is not valid JSON")

    def test_config_detection_patterns(self):
        """Test config operations with detection patterns."""
        from src.cli.main import cli

        # Test setting detection patterns
        result = self.runner.invoke(
            cli,
            ["config", "set", "detection_patterns", '["usage limit", "5-hour limit"]'],
        )
        assert result.exit_code == 0

    def test_config_command_help_text(self):
        """Test config command help text content."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output
        assert "set" in result.output
        assert "reset" in result.output
        assert "validate" in result.output
