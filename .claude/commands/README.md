# Claude Code Slash Commands for ClaudeCodeLooper

Convenient slash commands to control the Claude Code automated restart monitoring system directly from Claude Code.

## Available Commands

### `/cl:on` - Start Monitoring
Start the automated restart monitoring system in daemon mode.

**What it does:**
- Checks if monitoring is already running
- Starts monitoring Claude Code usage in background (daemon mode)
- Detects when usage limits are hit
- Automatically restarts after cooldown period

**Usage:**
```
/cl:on
```

**Example Output:**
```
✅ Monitoring Started
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Session ID: sess_abc123
Monitoring: claude
Working Directory: /Users/ze/work/ClaudeCodeLooper
Mode: Daemon (background)

The system will:
- Monitor Claude Code output for limit messages
- Detect usage limit events automatically
- Wait 5 hours after limit detection
- Restart Claude Code automatically

Use /cl:status to check status
Use /cl:off to stop monitoring
```

---

### `/cl:off` - Stop Monitoring
Stop all active monitoring sessions gracefully.

**What it does:**
- Checks current monitoring status
- Stops all active sessions
- Cleans up resources and processes
- Preserves state for future sessions

**Usage:**
```
/cl:off
```

**Example Output:**
```
🛑 Monitoring Stopped
━━━━━━━━━━━━━━━━━━━━━━━━━━━

All monitoring sessions terminated gracefully.
Resources cleaned up.
State saved for future sessions.

Claude Code will no longer auto-restart.
Use /cl:on to start monitoring again.
```

---

### `/cl:status` - Check Status
Display current monitoring status and active sessions.

**What it does:**
- Shows active monitoring sessions
- Displays current waiting periods
- Reports total detections count
- Shows system uptime and health metrics

**Usage:**
```
/cl:status
```

**Example Output:**
```
📊 Claude Code Monitor Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: ACTIVE
Active Sessions: 1
Limit Detections: 3
Uptime: 12 hours

👁️  Monitoring Claude Code output
   Started: 2025-10-18 08:00:00
   Monitoring: claude
   Session: sess_abc123

[If waiting period active]
⏳ Waiting Period Active
   Started: 2025-10-18 19:30:15
   Remaining: 4 hours 23 minutes
   Next Restart: 2025-10-19 00:30:15
```

---

### `/cl:logs` - View Logs
Display recent logs and events from the monitoring system.

**What it does:**
- Shows last 50 log lines (default)
- Highlights limit detection events
- Displays restart actions
- Shows errors and warnings

**Usage:**
```
/cl:logs
```

**With filters:**
```
/cl:logs --filter detection  # Detection events only
/cl:logs --filter error      # Errors only
/cl:logs --follow            # Live log streaming
```

**Example Output:**
```
📜 Recent Logs (last 50 lines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━

2025-10-18 14:30:15 [INFO] Monitoring started (session: sess_abc123)
2025-10-18 15:45:22 [INFO] Process health check: CPU 5%, Memory 120MB
2025-10-18 19:30:15 [WARN] Limit detection: usage limit exceeded
2025-10-18 19:30:16 [INFO] Waiting period started (5 hours)
2025-10-18 19:30:16 [INFO] Process stopped gracefully
```

---

## Common Workflows

### Basic Usage Flow
```
1. /cl:on        # Start monitoring
2. /cl:status    # Verify it's running
3. [work with Claude Code normally]
4. /cl:logs      # Check for any limit detections
5. /cl:off       # Stop when done
```

### Monitoring During Long Sessions
```
1. /cl:on        # Start at beginning of work session
2. [Continue working - system monitors in background]
3. [When limit hit, system automatically waits 5 hours]
4. [System restarts Claude Code after cooldown]
5. /cl:status    # Check how many detections occurred
6. /cl:off       # Stop at end of day
```

### Troubleshooting
```
1. /cl:status    # Check if system is running
2. /cl:logs      # Review recent events
3. /cl:logs --filter error  # Check for errors
4. /cl:off       # Stop if issues
5. /cl:on        # Restart fresh
```

---

## Technical Details

### System Requirements
- Python 3.11+
- psutil library
- ClaudeCodeLooper installed in project directory

### Configuration
Default configuration is stored in:
- `config/default.json` - System defaults
- `.claude-restart-config.json` - User overrides

### Logs Location
Logs are saved to: `logs/claude-restart-monitor.log`

### State Persistence
System state is persisted across restarts, so you can:
- Resume monitoring after system reboot
- Check historical detection events
- Review past session data

---

## Tips

**Best Practices:**
- Start monitoring at the beginning of your work session with `/cl:on`
- Use `/cl:status` periodically to check for limit detections
- Review `/cl:logs` to understand system behavior
- Stop monitoring with `/cl:off` when done to free resources

**When to Use:**
- Long coding sessions where you might hit usage limits
- Automated workflows requiring continuous Claude Code availability
- Production environments needing resilient AI assistance

**When NOT to Use:**
- Short, one-off tasks
- When you want to manually manage restarts
- Testing or debugging Claude Code itself

---

## Support

For issues or questions:
1. Check `/cl:logs` for error messages
2. Review logs at `logs/claude-restart-monitor.log`
3. Check GitHub issues at: https://github.com/your-repo/ClaudeCodeLooper

---

**Last Updated:** 2025-10-18
**Version:** 1.0.0
