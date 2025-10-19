"""Config command for configuration management."""

import click
import json
import sys
import os


@click.group()
@click.pass_context
def config(ctx):
    """Manage system configuration.

    Examples:
      claude-restart-monitor config show
      claude-restart-monitor config set log_level DEBUG
      claude-restart-monitor config reset
    """
    pass


@config.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.pass_context
def show(ctx, output_json: bool):
    """Display current configuration."""
    cli_ctx = ctx.find_root().obj

    try:
        current_config = cli_ctx.config_manager.get_current_config()
        if not current_config:
            click.echo("No configuration loaded", err=True)
            sys.exit(1)

        if output_json:
            config_dict = current_config.dict()
            click.echo(json.dumps(config_dict, indent=2, default=str))
        else:
            click.echo("=== Current Configuration ===")
            click.echo(f"Version: {current_config.config_version}")
            click.echo(f"Log Level: {current_config.log_level.value}")
            click.echo(f"Max Log Size: {current_config.max_log_size_mb} MB")
            click.echo(f"Backup Count: {current_config.backup_count}")
            click.echo()
            click.echo("Detection Patterns:")
            for i, pattern in enumerate(current_config.detection_patterns, 1):
                click.echo(f"  {i}. {pattern}")
            click.echo()
            click.echo("Monitoring Settings:")
            for key, value in current_config.monitoring.items():
                click.echo(f"  {key}: {value}")
            click.echo()
            click.echo("Timing Settings:")
            for key, value in current_config.timing.items():
                click.echo(f"  {key}: {value}")

    except Exception as e:
        click.echo(f"Error showing configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx, key: str, value: str):
    """Set a configuration value.

    Examples:
      claude-restart-monitor config set log_level DEBUG
      claude-restart-monitor config set max_log_size_mb 100
      claude-restart-monitor config set detection_patterns '["pattern1", "pattern2"]'
    """
    cli_ctx = ctx.find_root().obj

    try:
        # Parse value based on key
        parsed_value = _parse_config_value(key, value)

        # Determine section and setting
        if "." in key:
            section, setting = key.split(".", 1)
        else:
            section = None
            setting = key

        # Update configuration
        success = cli_ctx.config_manager.update_config_setting(
            section or "root", setting, parsed_value
        )

        if success:
            if not cli_ctx.quiet:
                click.echo(f"✓ Configuration updated: {key} = {value}")

            # Reload controller configuration
            cli_ctx.controller.reload_config()
        else:
            click.echo(
                f"Error: Failed to update configuration setting: {key}", err=True
            )
            sys.exit(1)

    except ValueError as e:
        click.echo(f"Error: Invalid value for {key}: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error setting configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.option("--confirm", is_flag=True, help="Confirm reset without prompt")
@click.pass_context
def reset(ctx, confirm: bool):
    """Reset configuration to defaults."""
    cli_ctx = ctx.find_root().obj

    if not confirm and not cli_ctx.quiet and not getattr(cli_ctx, "test_mode", False):
        if not click.confirm(
            "This will reset all configuration to defaults. Continue?"
        ):
            click.echo("Reset cancelled")
            return

    try:
        cli_ctx.config_manager.reset_to_defaults()
        cli_ctx.config = cli_ctx.config_manager.get_current_config()
        cli_ctx.controller.config = cli_ctx.config

        if not cli_ctx.quiet:
            click.echo("✓ Configuration reset to defaults")

    except Exception as e:
        click.echo(f"Error resetting configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.option("--file", type=click.Path(), help="Validate specific configuration file")
@click.pass_context
def validate(ctx, file: str):
    """Validate configuration."""
    cli_ctx = ctx.find_root().obj

    try:
        if file and not os.path.exists(file):
            click.echo(f"Configuration file not found: {file}", err=True)
            sys.exit(1)

        if file:
            # Validate specific file
            config_to_validate = cli_ctx.config_manager.load_config(file)
        else:
            # Validate current configuration
            config_to_validate = cli_ctx.config_manager.get_current_config()

        if not config_to_validate:
            click.echo("No configuration to validate", err=True)
            sys.exit(1)

        validation_result = cli_ctx.config_manager.validate_config(config_to_validate)

        if validation_result.is_valid:
            click.echo("✓ Configuration is valid")
        else:
            click.echo("✗ Configuration validation failed:", err=True)
            for error in validation_result.errors:
                click.echo(f"  Error: {error}", err=True)
            sys.exit(1)

        if validation_result.warnings:
            click.echo("\nWarnings:")
            for warning in validation_result.warnings:
                click.echo(f"  Warning: {warning}")

    except Exception as e:
        click.echo(f"Error validating configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.option("--output", type=click.Path(), help="Output file path")
@click.pass_context
def export(ctx, output: str):
    """Export current configuration to file."""
    cli_ctx = ctx.find_root().obj

    try:
        current_config = cli_ctx.config_manager.get_current_config()
        if not current_config:
            click.echo("No configuration to export", err=True)
            sys.exit(1)

        if not output:
            output = f"claude-restart-config-{current_config.config_version}.json"

        current_config.to_file(output)

        if not cli_ctx.quiet:
            click.echo(f"✓ Configuration exported to: {output}")

    except Exception as e:
        click.echo(f"Error exporting configuration: {e}", err=True)
        sys.exit(1)


@config.command()
@click.argument("file", type=click.Path(exists=True))
@click.pass_context
def load(ctx, file: str):
    """Load configuration from file."""
    cli_ctx = ctx.find_root().obj

    try:
        new_config = cli_ctx.config_manager.load_config(file)
        cli_ctx.config = new_config
        cli_ctx.controller.config = new_config

        if not cli_ctx.quiet:
            click.echo(f"✓ Configuration loaded from: {file}")

    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)


def _parse_config_value(key: str, value: str):
    """Parse configuration value based on key type."""
    # Handle JSON values
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    # Handle boolean values
    if value.lower() in ("true", "false"):
        return value.lower() == "true"

    # Handle numeric values
    if key.endswith(("_mb", "_count", "_seconds", "_hours", "_percent")):
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            raise ValueError(f"Expected numeric value for {key}")

    # Handle log level
    if key == "log_level":
        valid_levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        if value.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return value.upper()

    # Default to string
    return value
