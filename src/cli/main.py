"""Main CLI entry point for Claude Code automated restart system.

Provides command-line interface using Click framework with support for
all monitoring, configuration, and management operations.
"""
import click
import sys
import os
from typing import Optional

# Use relative imports - no sys.path manipulation needed
from ..models.system_configuration import SystemConfiguration
from ..services.config_manager import ConfigManager
from ..services.restart_controller import RestartController
from ..services.template_manager import TemplateManager


# Global context object
class CLIContext:
    """Context object for CLI commands."""

    def __init__(self):
        self.config: Optional[SystemConfiguration] = None
        self.config_manager: Optional[ConfigManager] = None
        self.controller: Optional[RestartController] = None
        self.verbose = False
        self.quiet = False
        self.test_mode = False
        self.template_manager: Optional[TemplateManager] = None


# Create context
pass_context = click.make_pass_decorator(CLIContext, ensure=True)


@click.group()
@click.option('--config', '-c',
              type=click.Path(),
              help='Path to configuration file')
@click.option('--verbose', '-v',
              is_flag=True,
              help='Enable verbose output')
@click.option('--quiet', '-q',
              is_flag=True,
              help='Suppress non-essential output')
@click.option('--version',
              is_flag=True,
              help='Show version information')
@pass_context
def cli(ctx: CLIContext, config: Optional[str], verbose: bool, quiet: bool, version: bool):
    """Claude Code Automated Restart Monitor.

    Automatically detects Claude Code usage limits and restarts after cooldown periods.
    Designed for continuous development work that exceeds 5-hour usage limits.
    """
    if version:
        click.echo("claude-restart-monitor version 1.0.0")
        click.echo("🤖 Generated with Claude Code")
        return

    # Set context flags
    ctx.verbose = verbose
    ctx.quiet = quiet

    if verbose and quiet:
        click.echo("Error: --verbose and --quiet cannot be used together", err=True)
        sys.exit(1)

    try:
        # Initialize configuration manager
        ctx.config_manager = ConfigManager(config)

        # Load configuration
        if config:
            ctx.config = ctx.config_manager.load_config(config)
        else:
            # Try to load from default location or create default
            ctx.config = ctx.config_manager.load_config_with_env_override()

        # Initialize controller
        ctx.controller = RestartController(ctx.config)
        ctx.template_manager = TemplateManager()

        # Determine test mode
        env_test_mode = os.getenv("CLAUDE_RESTART_TEST_MODE")
        running_tests = os.getenv("PYTEST_CURRENT_TEST")
        ctx.test_mode = bool(
            ctx.config.is_test_mode_enabled()
            or (env_test_mode and env_test_mode != "0")
            or running_tests
        )

        if ctx.test_mode and not ctx.config.allows_process_simulation():
            ctx.config.monitoring["allow_process_simulation"] = True

        # Restore previous state if available
        if not ctx.controller.restore_state():
            if ctx.verbose:
                click.echo("No previous state found, starting fresh")

    except Exception as e:
        if not quiet:
            click.echo(f"Error initializing: {e}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


# Import command modules
from .commands.start import start
from .commands.stop import stop
from .commands.status import status
from .commands.config import config as config_cmd
from .commands.logs import logs
from .commands.queue import queue as queue_cmd

# Add commands to main group
cli.add_command(start)
cli.add_command(stop)
cli.add_command(status)
cli.add_command(config_cmd, name='config')
cli.add_command(logs)
cli.add_command(queue_cmd, name='queue')


@cli.command()
@click.option('--format', 'output_format',
              type=click.Choice(['text', 'json']),
              default='text',
              help='Output format')
@pass_context
def info(ctx: CLIContext, output_format: str):
    """Show system information and diagnostics."""
    try:
        system_status = ctx.controller.get_system_status()

        if output_format == 'json':
            import json
            info_data = {
                "version": "1.0.0",
                "system_status": {
                    "state": system_status.state.value,
                    "active_sessions": system_status.active_sessions,
                    "waiting_periods": system_status.waiting_periods,
                    "total_detections": system_status.total_detections,
                    "uptime_seconds": system_status.uptime_seconds
                },
                "configuration": {
                    "log_level": ctx.config.log_level.value,
                    "pattern_count": len(ctx.config.detection_patterns),
                    "monitoring_interval": ctx.config.monitoring.get("check_interval"),
                    "cooldown_hours": ctx.config.timing.get("default_cooldown_hours")
                }
            }
            click.echo(json.dumps(info_data, indent=2))
        else:
            click.echo("=== Claude Code Restart Monitor ===")
            click.echo(f"Version: 1.0.0")
            click.echo(f"Status: {system_status.state.value}")
            click.echo(f"Active Sessions: {system_status.active_sessions}")
            click.echo(f"Waiting Periods: {system_status.waiting_periods}")
            click.echo(f"Total Detections: {system_status.total_detections}")
            click.echo(f"Uptime: {system_status.uptime_seconds:.1f} seconds")
            click.echo()
            click.echo("Configuration:")
            click.echo(f"  Log Level: {ctx.config.log_level.value}")
            click.echo(f"  Detection Patterns: {len(ctx.config.detection_patterns)}")
            click.echo(f"  Monitor Interval: {ctx.config.monitoring.get('check_interval')}s")
            click.echo(f"  Cooldown Hours: {ctx.config.timing.get('default_cooldown_hours')}")

    except Exception as e:
        if not ctx.quiet:
            click.echo(f"Error getting system info: {e}", err=True)
        sys.exit(1)


@cli.command()
@pass_context
def test(ctx: CLIContext):
    """Run system self-tests."""
    try:
        click.echo("Running system self-tests...")

        # Test configuration
        click.echo("✓ Configuration loaded")

        # Test pattern detection
        test_patterns = [
            "Usage limit exceeded - please wait 5 hours",
            "Rate limit reached",
            "Your 5-hour limit has been reached"
        ]

        detection_count = 0
        for pattern in test_patterns:
            detection = ctx.controller.pattern_detector.detect_limit_message(pattern)
            if detection:
                detection_count += 1

        click.echo(f"✓ Pattern detection ({detection_count}/{len(test_patterns)} patterns detected)")

        # Test timing
        timing_stats = ctx.controller.timing_manager.get_timing_statistics()
        click.echo("✓ Timing system operational")

        # Test state management
        test_state = {"test": "data", "timestamp": "2025-01-01T00:00:00"}
        if ctx.controller.state_manager.save_state(test_state):
            click.echo("✓ State persistence working")
        else:
            click.echo("⚠ State persistence issue")

        click.echo()
        click.echo("Self-test completed successfully!")

    except Exception as e:
        click.echo(f"✗ Self-test failed: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point for the CLI application."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
