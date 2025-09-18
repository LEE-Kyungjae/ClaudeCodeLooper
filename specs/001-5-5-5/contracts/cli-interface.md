# CLI Interface Contract

## Command Structure

### Base Command
```bash
claude-restart-monitor [SUBCOMMAND] [OPTIONS]
```

## Subcommands

### start
Start monitoring Claude Code process with automatic restart capability.

**Syntax**:
```bash
claude-restart-monitor start [OPTIONS]
```

**Options**:
- `--claude-cmd TEXT`: Command to start Claude Code (required)
- `--work-dir PATH`: Working directory for Claude Code (optional)
- `--restart-args TEXT`: Additional arguments for restart (multiple allowed)
- `--config PATH`: Path to configuration file (optional)
- `--daemon`: Run as background daemon (optional)

**Example**:
```bash
claude-restart-monitor start --claude-cmd "claude-code" --work-dir "/project" --daemon
```

**Exit Codes**:
- `0`: Success - monitoring started
- `1`: Error - invalid arguments
- `2`: Error - Claude Code not found
- `3`: Error - permission denied

### stop
Stop monitoring and optionally terminate Claude Code.

**Syntax**:
```bash
claude-restart-monitor stop [OPTIONS]
```

**Options**:
- `--session-id TEXT`: Specific session to stop (optional)
- `--force`: Force stop even during waiting period (optional)
- `--kill-claude`: Also terminate Claude Code process (optional)

**Example**:
```bash
claude-restart-monitor stop --force
```

**Exit Codes**:
- `0`: Success - monitoring stopped
- `1`: Error - session not found
- `4`: Error - cannot stop during critical operation

### status
Display current monitoring status and statistics.

**Syntax**:
```bash
claude-restart-monitor status [OPTIONS]
```

**Options**:
- `--json`: Output in JSON format (optional)
- `--verbose`: Include detailed information (optional)
- `--watch`: Continuously update status (optional)

**Example**:
```bash
claude-restart-monitor status --json
```

**Sample Output**:
```json
{
  "status": "active",
  "session_id": "sess_123456789",
  "uptime": "2h 34m",
  "detection_count": 1,
  "current_state": "waiting",
  "waiting_period": {
    "remaining": "2h 26m 14s",
    "end_time": "2025-09-18T15:30:00Z"
  }
}
```

### config
Manage system configuration.

**Syntax**:
```bash
claude-restart-monitor config [OPERATION] [OPTIONS]
```

**Operations**:
- `show`: Display current configuration
- `set KEY VALUE`: Set configuration value
- `reset`: Reset to default configuration
- `validate`: Validate configuration file

**Examples**:
```bash
claude-restart-monitor config show
claude-restart-monitor config set log_level DEBUG
claude-restart-monitor config validate --file config.json
```

### logs
Access and manage system logs.

**Syntax**:
```bash
claude-restart-monitor logs [OPTIONS]
```

**Options**:
- `--tail N`: Show last N lines (default: 50)
- `--follow`: Follow log output (like tail -f)
- `--level LEVEL`: Filter by log level
- `--since DATETIME`: Show logs since timestamp
- `--grep PATTERN`: Filter logs by pattern

**Example**:
```bash
claude-restart-monitor logs --follow --level INFO
```

## Global Options

Available for all subcommands:

- `--help`: Show help message
- `--version`: Show version information
- `--quiet`: Suppress non-essential output
- `--verbose`: Enable verbose output

## Environment Variables

- `CLAUDE_RESTART_CONFIG`: Default configuration file path
- `CLAUDE_RESTART_LOG_LEVEL`: Default log level
- `CLAUDE_CODE_PATH`: Default path to Claude Code executable

## Configuration File Format

**Default location**: `~/.claude-restart-monitor/config.json`

**Structure**:
```json
{
  "log_level": "INFO",
  "detection_patterns": [
    "usage limit",
    "5-hour limit",
    "please wait"
  ],
  "restart_commands": [],
  "max_log_size_mb": 50,
  "backup_count": 3,
  "monitoring": {
    "check_interval": 1,
    "task_timeout": 300
  }
}
```

## Signal Handling

- `SIGINT` (Ctrl+C): Graceful shutdown
- `SIGTERM`: Graceful shutdown
- `SIGUSR1`: Reload configuration (Unix only)
- `SIGUSR2`: Rotate logs (Unix only)

## Exit Codes Summary

- `0`: Success
- `1`: General error or invalid arguments
- `2`: File/process not found
- `3`: Permission denied
- `4`: Operation not allowed in current state
- `5`: Configuration error
- `6`: Network/communication error

## Error Output Format

All errors are written to stderr in structured format:

```json
{
  "error": "error_code",
  "message": "Human readable message",
  "details": "Additional context if available"
}
```