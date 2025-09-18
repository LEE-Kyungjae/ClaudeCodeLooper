"""Start command for Claude Code monitoring.

Implements the 'start' command that begins monitoring a Claude Code process
with automatic restart capabilities.
"""
import click
import sys
import os
from typing import List, Optional


@click.command()
@click.option('--claude-cmd',
              required=True,
              help='Command to start Claude Code (required)')
@click.option('--work-dir',
              type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help='Working directory for Claude Code')
@click.option('--restart-args',
              multiple=True,
              help='Additional arguments for restart (can be specified multiple times)')
@click.option('--config-file',
              type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--daemon',
              is_flag=True,
              help='Run as background daemon')
@click.option('--session-id',
              help='Custom session identifier')
@click.pass_context
def start(ctx, claude_cmd: str, work_dir: Optional[str], restart_args: tuple,
          config_file: Optional[str], daemon: bool, session_id: Optional[str]):
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
        # Validate Claude Code command
        if not claude_cmd.strip():
            click.echo("Error: Claude command cannot be empty", err=True)
            sys.exit(1)

        # Check if Claude Code command exists
        claude_executable = claude_cmd.split()[0]
        if not _command_exists(claude_executable):
            click.echo(f"Error: Claude Code command not found: {claude_executable}", err=True)
            click.echo("Make sure Claude Code is installed and accessible in PATH", err=True)
            sys.exit(2)

        # Validate working directory
        if work_dir:
            work_dir = os.path.abspath(work_dir)
            if not os.path.exists(work_dir):
                click.echo(f"Error: Working directory does not exist: {work_dir}", err=True)
                sys.exit(1)
            elif not os.access(work_dir, os.R_OK | os.X_OK):
                click.echo(f"Error: No access to working directory: {work_dir}", err=True)
                sys.exit(3)

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
                session_id=session_id
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

            # Handle daemon mode
            if daemon:
                if not cli_ctx.quiet:
                    click.echo("Running in daemon mode...")
                    click.echo("Use 'claude-restart-monitor stop' to stop monitoring")
                    click.echo("Use 'claude-restart-monitor status' to check status")

                # In daemon mode, we would typically detach from terminal
                # For now, we'll just indicate daemon mode is active
                _run_daemon_mode(cli_ctx, session)
            else:
                if not cli_ctx.quiet:
                    click.echo()
                    click.echo("Monitoring active. Press Ctrl+C to stop.")
                    click.echo("The system will detect usage limits and restart automatically.")

                # Run in foreground mode
                _run_foreground_mode(cli_ctx, session)

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


def _run_daemon_mode(cli_ctx, session):
    """Run in daemon mode (background)."""
    import time
    import signal

    def signal_handler(sig, frame):
        if not cli_ctx.quiet:
            click.echo("\nReceived signal, stopping monitoring...")
        cli_ctx.controller.stop_monitoring()
        sys.exit(0)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Keep running until stopped
        while True:
            # Check if session is still active
            current_session = cli_ctx.controller.get_session(session.session_id)
            if not current_session or current_session.is_stopped():
                if not cli_ctx.quiet:
                    click.echo("Session ended, stopping daemon")
                break

            time.sleep(5)  # Check every 5 seconds

    except Exception as e:
        if not cli_ctx.quiet:
            click.echo(f"Daemon error: {e}", err=True)
        sys.exit(1)


def _run_foreground_mode(cli_ctx, session):
    """Run in foreground mode with status updates."""
    import time

    try:
        last_status = session.status
        last_detection_count = session.detection_count

        while True:
            # Get updated session
            current_session = cli_ctx.controller.get_session(session.session_id)
            if not current_session:
                click.echo("Session ended")
                break

            # Check for status changes
            if current_session.status != last_status:
                if not cli_ctx.quiet:
                    click.echo(f"Status changed: {last_status.value} → {current_session.status.value}")
                last_status = current_session.status

            # Check for new detections
            if current_session.detection_count > last_detection_count:
                if not cli_ctx.quiet:
                    click.echo(f"🚨 Usage limit detected! Entering waiting period...")

                    # Find active waiting period
                    for period in cli_ctx.controller.waiting_periods.values():
                        if period.session_id == session.session_id and period.is_active():
                            remaining = period.get_remaining_time()
                            if remaining:
                                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                                minutes, seconds = divmod(remainder, 60)
                                click.echo(f"⏰ Waiting period: {hours}h {minutes}m {seconds}s remaining")
                            break

                last_detection_count = current_session.detection_count

            # Show periodic status if verbose
            if cli_ctx.verbose:
                uptime = current_session.get_uptime_seconds()
                click.echo(f"Uptime: {uptime:.0f}s | Detections: {current_session.detection_count} | Status: {current_session.status.value}")

            # Stop if session is stopped
            if current_session.is_stopped():
                click.echo("Monitoring stopped")
                break

            time.sleep(10)  # Update every 10 seconds

    except KeyboardInterrupt:
        if not cli_ctx.quiet:
            click.echo("\nStopping monitoring...")
        cli_ctx.controller.stop_monitoring(session.session_id)
        click.echo("Monitoring stopped")
    except Exception as e:
        if not cli_ctx.quiet:
            click.echo(f"Monitoring error: {e}", err=True)
        sys.exit(1)