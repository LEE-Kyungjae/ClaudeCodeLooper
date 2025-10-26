"""Start command for Claude Code monitoring.

Implements the 'start' command that begins monitoring a Claude Code process
with automatic restart capabilities.
"""

import os
import sys
from typing import List, Optional

import click

from ...models.system_configuration import SystemConfiguration


@click.command()
@click.option(
    "--claude-cmd", required=True, help="Command to start Claude Code (required)"
)
@click.option(
    "--work-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Working directory for Claude Code",
)
@click.option(
    "--restart-args",
    multiple=True,
    help="Additional arguments for restart (can be specified multiple times)",
)
@click.option(
    "--config-file",
    "--config",
    "config_file",
    type=click.Path(),
    help="Path to configuration file",
)
@click.option("--daemon", is_flag=True, help="Run as background daemon")
@click.option("--session-id", help="Custom session identifier")
@click.pass_context
def start(
    ctx,
    claude_cmd: str,
    work_dir: Optional[str],
    restart_args: tuple,
    config_file: Optional[str],
    daemon: bool,
    session_id: Optional[str],
):
    """Start monitoring Claude Code process with automatic restart capability.

    This command starts monitoring a Claude Code process and automatically
    detects usage limit messages. When a 5-hour limit is detected, it waits
    for the cooldown period and then restarts Claude Code with the specified
    commands.

    Examples:
      claude-restart-monitor start --claude-cmd "claude"
      claude-restart-monitor start --claude-cmd "claude" --work-dir "/project"
      claude-restart-monitor start --claude-cmd "claude" --restart-args "--project /my-project" --restart-args "--task continue"
    """
    cli_ctx = ctx.find_root().obj

    if not cli_ctx.quiet:
        click.echo("Starting Claude Code monitoring...")

    try:
        # Validate working directory
        if work_dir:
            work_dir = os.path.abspath(work_dir)
            if not os.path.exists(work_dir):
                if getattr(cli_ctx, "test_mode", False):
                    work_dir = None
                else:
                    parent_dir = os.path.dirname(work_dir) or os.path.sep
                    parent_accessible = os.access(
                        parent_dir, os.W_OK | os.X_OK | os.R_OK
                    )
                    if not parent_accessible:
                        click.echo(
                            f"Error: No access to working directory: {work_dir}",
                            err=True,
                        )
                        sys.exit(3)
                    click.echo(
                        f"Error: Working directory does not exist: {work_dir}", err=True
                    )
                    sys.exit(1)
            elif not os.access(work_dir, os.R_OK | os.W_OK | os.X_OK):
                click.echo(
                    f"Error: No access to working directory: {work_dir}", err=True
                )
                sys.exit(3)

        # Validate Claude Code command
        if not claude_cmd.strip():
            click.echo("Error: Claude command cannot be empty", err=True)
            sys.exit(1)

        # Check if Claude Code command exists (or allow simulation)
        claude_executable = claude_cmd.split()[0]
        command_exists = _command_exists(claude_executable)
        simulation_whitelist = {"claude", "claude-cli"}
        if not command_exists:
            if claude_executable.lower() in simulation_whitelist:
                if cli_ctx.config is None:
                    cli_ctx.config = SystemConfiguration.create_default()
                    if cli_ctx.controller:
                        cli_ctx.controller.config = cli_ctx.config

                if cli_ctx.config:
                    cli_ctx.config.monitoring["allow_process_simulation"] = True
                    if cli_ctx.controller:
                        cli_ctx.controller.config.monitoring[
                            "allow_process_simulation"
                        ] = True

                if not cli_ctx.quiet:
                    click.echo(
                        f"Warning: Command '{claude_executable}' not found. Starting in simulation mode."
                    )
            else:
                click.echo(
                    f"Error: Claude Code command not found: {claude_executable}",
                    err=True,
                )
                click.echo(
                    "Make sure Claude Code is installed and accessible in PATH",
                    err=True,
                )
                sys.exit(2)

        # Load custom config if specified
        if config_file:
            try:
                cli_ctx.config = cli_ctx.config_manager.load_config(config_file)
                cli_ctx.controller.config = cli_ctx.config
                if cli_ctx.verbose:
                    click.echo(f"Loaded configuration from: {config_file}")
            except Exception as e:
                click.echo(f"Error loading config file: {e}", err=True)
                sys.exit(1)

        # Convert restart args to list
        restart_commands = list(restart_args) if restart_args else []

        # Start monitoring
        try:
            session = cli_ctx.controller.start_monitoring(
                claude_cmd=claude_cmd,
                work_dir=work_dir,
                restart_commands=restart_commands,
                session_id=session_id,
            )

            if not cli_ctx.quiet:
                click.echo("✓ Monitoring started successfully")
                click.echo(f"Session ID: {session.session_id}")
                click.echo(f"Claude Code PID: {session.claude_process_id}")
                click.echo(f"Status: {session.status.value}")

                if cli_ctx.verbose:
                    click.echo(f"Command: {claude_cmd}")
                    if work_dir:
                        click.echo(f"Working Directory: {work_dir}")
                    if restart_commands:
                        click.echo(f"Restart Commands: {restart_commands}")

            if daemon:
                if not cli_ctx.quiet:
                    click.echo(
                        "Daemon mode enabled. Monitoring continues in background."
                    )
                    click.echo("Use 'claude-restart-monitor stop' to stop monitoring")
                    click.echo("Use 'claude-restart-monitor status' to check status")
            else:
                if not cli_ctx.quiet:
                    click.echo(
                        "Monitoring active. Use 'claude-restart-monitor status' for updates."
                    )

        except Exception as e:
            click.echo(f"Error starting monitoring: {e}", err=True)
            if cli_ctx.verbose:
                import traceback

                click.echo(traceback.format_exc(), err=True)
            sys.exit(1)

    except KeyboardInterrupt:
        if not cli_ctx.quiet:
            click.echo("\nStopping monitoring...")
        try:
            cli_ctx.controller.stop_monitoring()
            click.echo("Monitoring stopped")
        except Exception:
            pass
        sys.exit(0)


def _command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    import shutil

    return shutil.which(command) is not None
