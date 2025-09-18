"""Stop command for Claude Code monitoring."""
import click
import sys


@click.command()
@click.option('--session-id',
              help='Specific session ID to stop')
@click.option('--force',
              is_flag=True,
              help='Force stop even during waiting period')
@click.option('--kill-claude',
              is_flag=True,
              help='Also terminate Claude Code process')
@click.pass_context
def stop(ctx, session_id: str, force: bool, kill_claude: bool):
    """Stop monitoring and optionally terminate Claude Code.

    Examples:
      claude-restart-monitor stop
      claude-restart-monitor stop --session-id sess_123456789
      claude-restart-monitor stop --force --kill-claude
    """
    cli_ctx = ctx.find_root().obj

    try:
        if session_id:
            # Stop specific session
            session = cli_ctx.controller.get_session(session_id)
            if not session:
                click.echo(f"Error: Session not found: {session_id}", err=True)
                sys.exit(1)

            # Check if in waiting period and not forced
            if session.is_waiting() and not force:
                click.echo("Session is in waiting period. Use --force to stop anyway.", err=True)
                sys.exit(4)

            success = cli_ctx.controller.stop_monitoring(session_id)
            if success:
                if not cli_ctx.quiet:
                    click.echo(f"✓ Session {session_id} stopped successfully")
            else:
                click.echo(f"Error: Failed to stop session {session_id}", err=True)
                sys.exit(1)

        else:
            # Stop all sessions
            system_status = cli_ctx.controller.get_system_status()
            if system_status.active_sessions == 0:
                if not cli_ctx.quiet:
                    click.echo("No active monitoring sessions")
                return

            # Check for waiting periods
            if system_status.waiting_periods > 0 and not force:
                click.echo(f"Warning: {system_status.waiting_periods} waiting period(s) active.")
                click.echo("Use --force to stop anyway.")
                sys.exit(4)

            success = cli_ctx.controller.stop_monitoring()
            if success:
                if not cli_ctx.quiet:
                    click.echo("✓ All monitoring stopped successfully")
            else:
                click.echo("Error: Failed to stop monitoring", err=True)
                sys.exit(1)

    except Exception as e:
        click.echo(f"Error stopping monitoring: {e}", err=True)
        sys.exit(1)