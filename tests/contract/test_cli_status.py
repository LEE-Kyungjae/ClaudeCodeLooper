"""Contract tests for CLI status command.

These tests define the expected behavior and interface of the status command.
They MUST FAIL initially before implementation.
"""
import json
import pytest
from click.testing import CliRunner


class TestStatusCommandContract:
    """Test contract for claude-restart-monitor status command."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_status_command_exists(self):
        """Test that status command is available."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ['--help'])
        assert 'status' in result.output

    def test_status_command_basic(self):
        """Test basic status command functionality."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ['status'])
        assert result.exit_code == 0
        assert 'status' in result.output.lower()

    def test_status_command_json_output(self):
        """Test status command with JSON output."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ['status', '--json'])
        assert result.exit_code == 0

        # Should be valid JSON
        try:
            data = json.loads(result.output)
            assert isinstance(data, dict)
            assert 'status' in data
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_status_command_verbose_output(self):
        """Test status command with verbose output."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ['status', '--verbose'])
        assert result.exit_code == 0
        # Verbose should have more detailed information
        assert len(result.output) > 100  # Assume verbose is longer

    def test_status_command_watch_mode(self):
        """Test status command with watch mode."""
        from src.cli.main import cli

        # Note: In real implementation, this would need timeout or mocking
        # For contract test, we just verify the option is accepted
        result = self.runner.invoke(cli, ['status', '--help'])
        assert '--watch' in result.output

    def test_status_command_output_contains_required_fields(self):
        """Test that status output contains required information."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ['status', '--json'])
        assert result.exit_code == 0

        try:
            data = json.loads(result.output)
            # Required fields per contract
            expected_fields = ['status', 'session_id', 'uptime']
            for field in expected_fields:
                assert field in data or any(field in str(v) for v in data.values())
        except json.JSONDecodeError:
            # If not JSON, check text output for key information
            assert any(word in result.output.lower()
                      for word in ['active', 'inactive', 'waiting', 'stopped'])

    def test_status_command_with_waiting_period(self):
        """Test status command when system is in waiting period."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ['status', '--json'])
        assert result.exit_code == 0

        # Should handle waiting period information
        try:
            data = json.loads(result.output)
            if 'waiting_period' in data:
                waiting = data['waiting_period']
                assert 'remaining' in waiting
                assert 'end_time' in waiting
        except json.JSONDecodeError:
            pass  # Text output is also acceptable

    def test_status_command_help_text(self):
        """Test status command help text content."""
        from src.cli.main import cli

        result = self.runner.invoke(cli, ['status', '--help'])
        assert result.exit_code == 0
        assert '--json' in result.output
        assert '--verbose' in result.output
        assert '--watch' in result.output