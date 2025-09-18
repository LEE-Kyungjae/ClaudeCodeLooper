"""Logs command for accessing system logs."""
import click
import sys
import os
import re
from datetime import datetime
from typing import List, Optional


@click.command()
@click.option('--tail',
              type=int,
              default=50,
              help='Number of lines to show (default: 50)')
@click.option('--follow',
              is_flag=True,
              help='Follow log output (like tail -f)')
@click.option('--level',
              type=click.Choice(['DEBUG', 'INFO', 'WARN', 'ERROR'], case_sensitive=False),
              help='Filter by log level')
@click.option('--since',
              help='Show logs since timestamp (ISO format)')
@click.option('--grep',
              help='Filter logs by pattern (regex)')
@click.pass_context
def logs(ctx, tail: int, follow: bool, level: Optional[str], since: Optional[str], grep: Optional[str]):
    """Access and manage system logs.

    Examples:
      claude-restart-monitor logs
      claude-restart-monitor logs --tail 100
      claude-restart-monitor logs --follow --level INFO
      claude-restart-monitor logs --since "2025-09-18T10:00:00" --grep "detection"
    """
    cli_ctx = ctx.find_root().obj

    try:
        # Validate parameters
        if tail < 1:
            click.echo("Error: tail count must be positive", err=True)
            sys.exit(1)

        # Parse since timestamp if provided
        since_datetime = None
        if since:
            try:
                since_datetime = datetime.fromisoformat(since)
            except ValueError:
                click.echo("Error: Invalid since timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS)", err=True)
                sys.exit(1)

        # Compile grep pattern if provided
        grep_pattern = None
        if grep:
            try:
                grep_pattern = re.compile(grep, re.IGNORECASE)
            except re.error as e:
                click.echo(f"Error: Invalid grep pattern: {e}", err=True)
                sys.exit(1)

        # Get log file path
        log_file_path = cli_ctx.config.get_log_file_path()

        if not os.path.exists(log_file_path):
            if not cli_ctx.quiet:
                click.echo("No log file found. Start monitoring to generate logs.")
            return

        if follow:
            _follow_logs(log_file_path, level, grep_pattern, cli_ctx.verbose)
        else:
            _show_logs(log_file_path, tail, level, since_datetime, grep_pattern)

    except KeyboardInterrupt:
        if not cli_ctx.quiet:
            click.echo("\nLog monitoring stopped")
    except Exception as e:
        click.echo(f"Error accessing logs: {e}", err=True)
        sys.exit(1)


def _show_logs(log_file_path: str, tail: int, level: Optional[str],
               since_datetime: Optional[datetime], grep_pattern: Optional[re.Pattern]) -> None:
    """Show logs with filtering."""
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Apply filters
        filtered_lines = []
        for line in lines:
            if not _line_matches_filters(line, level, since_datetime, grep_pattern):
                continue
            filtered_lines.append(line.rstrip())

        # Apply tail limit
        if tail > 0 and len(filtered_lines) > tail:
            filtered_lines = filtered_lines[-tail:]

        # Output lines
        for line in filtered_lines:
            click.echo(line)

        if not filtered_lines:
            click.echo("No matching log entries found")

    except FileNotFoundError:
        click.echo("Log file not found")
    except PermissionError:
        click.echo("Permission denied accessing log file", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error reading log file: {e}", err=True)
        sys.exit(1)


def _follow_logs(log_file_path: str, level: Optional[str],
                grep_pattern: Optional[re.Pattern], verbose: bool) -> None:
    """Follow logs in real-time."""
    import time

    try:
        # Start from end of file
        with open(log_file_path, 'r', encoding='utf-8') as f:
            # Seek to end
            f.seek(0, 2)

            click.echo(f"Following logs: {log_file_path}")
            click.echo("Press Ctrl+C to stop...")
            click.echo("-" * 50)

            while True:
                line = f.readline()
                if line:
                    if _line_matches_filters(line, level, None, grep_pattern):
                        click.echo(line.rstrip())
                else:
                    time.sleep(0.1)  # Brief pause when no new lines

    except FileNotFoundError:
        click.echo("Log file not found", err=True)
        sys.exit(1)
    except PermissionError:
        click.echo("Permission denied accessing log file", err=True)
        sys.exit(1)


def _line_matches_filters(line: str, level: Optional[str],
                         since_datetime: Optional[datetime],
                         grep_pattern: Optional[re.Pattern]) -> bool:
    """Check if log line matches all filters."""
    # Level filter
    if level:
        level_upper = level.upper()
        if f"[{level_upper}]" not in line and level_upper not in line:
            return False

    # Timestamp filter
    if since_datetime:
        timestamp = _extract_timestamp(line)
        if timestamp and timestamp < since_datetime:
            return False

    # Grep pattern filter
    if grep_pattern:
        if not grep_pattern.search(line):
            return False

    return True


def _extract_timestamp(line: str) -> Optional[datetime]:
    """Extract timestamp from log line."""
    # Common log timestamp patterns
    patterns = [
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})',  # ISO format
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',  # Space separated
        r'(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})',  # US format
    ]

    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            timestamp_str = match.group(1)
            try:
                # Try different parsing formats
                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M:%S']:
                    try:
                        return datetime.strptime(timestamp_str, fmt)
                    except ValueError:
                        continue
            except Exception:
                pass

    return None


@click.command()
@click.option('--max-size',
              type=int,
              help='Maximum size in MB before rotation')
@click.option('--backup-count',
              type=int,
              help='Number of backup files to keep')
@click.pass_context
def rotate(ctx, max_size: Optional[int], backup_count: Optional[int]):
    """Rotate log files manually.

    Examples:
      claude-restart-monitor logs rotate
      claude-restart-monitor logs rotate --max-size 100 --backup-count 5
    """
    cli_ctx = ctx.find_root().obj

    try:
        log_file_path = cli_ctx.config.get_log_file_path()

        if not os.path.exists(log_file_path):
            click.echo("No log file to rotate")
            return

        # Get current file size
        file_size_mb = os.path.getsize(log_file_path) / (1024 * 1024)

        # Use provided values or config defaults
        max_size = max_size or cli_ctx.config.max_log_size_mb
        backup_count = backup_count or cli_ctx.config.backup_count

        if file_size_mb < max_size:
            if not cli_ctx.quiet:
                click.echo(f"Log file ({file_size_mb:.1f} MB) is smaller than max size ({max_size} MB)")
                click.echo("Rotation not needed")
            return

        # Perform rotation
        _rotate_log_file(log_file_path, backup_count)

        if not cli_ctx.quiet:
            click.echo(f"✓ Log file rotated (was {file_size_mb:.1f} MB)")

    except Exception as e:
        click.echo(f"Error rotating logs: {e}", err=True)
        sys.exit(1)


def _rotate_log_file(log_file_path: str, backup_count: int) -> None:
    """Rotate log file with backup."""
    import shutil

    # Move existing backups
    for i in range(backup_count - 1, 0, -1):
        old_backup = f"{log_file_path}.{i}"
        new_backup = f"{log_file_path}.{i + 1}"

        if os.path.exists(old_backup):
            if os.path.exists(new_backup):
                os.remove(new_backup)
            shutil.move(old_backup, new_backup)

    # Move current log to .1
    if backup_count > 0:
        backup_path = f"{log_file_path}.1"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        shutil.move(log_file_path, backup_path)

    # Create new empty log file
    open(log_file_path, 'w').close()


# Add rotate as subcommand to logs
logs.add_command(rotate)