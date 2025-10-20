"""Status command for monitoring information."""

import json
from datetime import datetime

import click


@click.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.option("--verbose", is_flag=True, help="Include detailed information")
@click.option("--watch", is_flag=True, help="Continuously update status")
@click.pass_context
def status(ctx, output_json: bool, verbose: bool, watch: bool):
    """Display current monitoring status and statistics.

    Examples:
      claude-restart-monitor status
      claude-restart-monitor status --json
      claude-restart-monitor status --verbose --watch
    """
    cli_ctx = ctx.find_root().obj

    try:
        if watch:
            _watch_status(cli_ctx, output_json, verbose)
        else:
            _show_status_once(cli_ctx, output_json, verbose)

    except KeyboardInterrupt:
        if not cli_ctx.quiet:
            click.echo("\nStatus monitoring stopped")
    except Exception as e:
        click.echo(f"Error getting status: {e}", err=True)


def _show_status_once(cli_ctx, output_json: bool, verbose: bool):
    """Show status information once."""
    system_status = cli_ctx.controller.get_system_status()
    primary_session = next(iter(cli_ctx.controller.active_sessions.values()), None)
    primary_waiting_period = cli_ctx.controller.waiting_period

    if output_json:
        status_data = {
            "status": system_status.state.value,
            "session_id": primary_session.session_id if primary_session else None,
            "uptime": f"{system_status.uptime_seconds:.1f}s",
            "active_sessions": system_status.active_sessions,
            "waiting_periods": system_status.waiting_periods,
            "total_detections": system_status.total_detections,
            "last_activity": (
                system_status.last_activity.isoformat()
                if system_status.last_activity
                else None
            ),
        }

        # Add session details if available
        if system_status.active_sessions > 0:
            sessions = []
            for session in cli_ctx.controller.active_sessions.values():
                session_state = getattr(session.status, "value", session.status)
                sessions.append(
                    {
                        "session_id": session.session_id,
                        "status": session_state,
                        "claude_process_id": session.claude_process_id,
                        "detection_count": session.detection_count,
                        "uptime_seconds": session.get_uptime_seconds(),
                        "command": session.claude_command,
                    }
                )
            status_data["sessions"] = sessions

        # Add waiting period details
        if system_status.waiting_periods > 0:
            waiting_periods = []
            for period in cli_ctx.controller.waiting_periods.values():
                waiting_periods.append(
                    {
                        "period_id": period.period_id,
                        "session_id": period.session_id,
                        "remaining_seconds": period.get_remaining_seconds(),
                        "progress": period.get_progress(),
                        "formatted_remaining": period.format_remaining_time(),
                    }
                )
            status_data["waiting_periods"] = waiting_periods

        if primary_waiting_period:
            status_data["waiting_period"] = {
                "period_id": primary_waiting_period.period_id,
                "session_id": primary_waiting_period.session_id,
                "remaining": primary_waiting_period.format_remaining_time(),
                "end_time": (
                    primary_waiting_period.end_time.isoformat()
                    if primary_waiting_period.end_time
                    else None
                ),
            }

        click.echo(json.dumps(status_data, indent=2))
    else:
        # Text output
        click.echo("=== Claude Code Restart Monitor Status ===")
        click.echo(f"System Status: {system_status.state.value}")
        click.echo(f"Active Sessions: {system_status.active_sessions}")
        click.echo(f"Waiting Periods: {system_status.waiting_periods}")
        click.echo(f"Total Detections: {system_status.total_detections}")
        click.echo(f"System Uptime: {system_status.uptime_seconds:.1f} seconds")

        if system_status.last_activity:
            click.echo(
                f"Last Activity: {system_status.last_activity.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # Show session details
        if system_status.active_sessions > 0:
            click.echo("\n=== Active Sessions ===")
            for session in cli_ctx.controller.active_sessions.values():
                click.echo(f"Session: {session.session_id}")
                session_state = getattr(session.status, "value", session.status)
                click.echo(f"  Status: {session_state}")
                click.echo(f"  PID: {session.claude_process_id}")
                click.echo(f"  Detections: {session.detection_count}")
                click.echo(f"  Uptime: {session.get_uptime_seconds():.1f}s")
                if verbose:
                    click.echo(f"  Command: {session.claude_command}")
                    if session.working_directory:
                        click.echo(f"  Work Dir: {session.working_directory}")
                    if session.restart_commands:
                        click.echo(f"  Restart Args: {session.restart_commands}")

        # Show waiting periods
        if system_status.waiting_periods > 0:
            click.echo("\n=== Waiting Periods ===")
            for period in cli_ctx.controller.waiting_periods.values():
                click.echo(f"Period: {period.period_id}")
                click.echo(f"  Session: {period.session_id}")
                click.echo(f"  Remaining: {period.format_remaining_time()}")
                click.echo(f"  Progress: {period.get_progress_percentage():.1f}%")

        if verbose:
            click.echo("\n=== Configuration Summary ===")
            click.echo(f"Log Level: {cli_ctx.config.log_level.value}")
            click.echo(
                f"Monitor Interval: {cli_ctx.config.monitoring.get('check_interval')}s"
            )
            click.echo(
                f"Default Cooldown: {cli_ctx.config.timing.get('default_cooldown_hours')}h"
            )
            click.echo(
                f"Simulation Enabled: {cli_ctx.config.allows_process_simulation()}"
            )
            click.echo(
                f"Detection Patterns: {len(cli_ctx.config.detection_patterns)} registered"
            )

        if system_status.active_sessions == 0 and system_status.waiting_periods == 0:
            click.echo("\nNo active monitoring sessions")


def _watch_status(cli_ctx, output_json: bool, verbose: bool):
    """Continuously watch and update status."""
    import os
    import subprocess
    import time

    try:
        while True:
            # Clear screen (cross-platform, secure)
            if os.name == "nt":
                subprocess.run(["cmd", "/c", "cls"], check=False)
            else:
                subprocess.run(["clear"], check=False)

            # Show current time
            if not output_json:
                click.echo(
                    f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                click.echo("=" * 50)

            _show_status_once(cli_ctx, output_json, verbose)

            if not output_json:
                click.echo("\nPress Ctrl+C to stop watching...")

            # Wait before next update
            time.sleep(5)

    except KeyboardInterrupt:
        pass
