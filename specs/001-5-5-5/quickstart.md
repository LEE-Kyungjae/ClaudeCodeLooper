# Quickstart: Claude Code Automated Restart System

## Prerequisites

- Windows 10/11 or WSL environment
- Python 3.11 or higher
- Claude Code installed and accessible via command line
- Administrative permissions (for process monitoring)

## Installation

1. **Install the package**:
   ```bash
   pip install claude-restart-monitor
   ```

2. **Verify installation**:
   ```bash
   claude-restart-monitor --version
   ```

3. **Initialize configuration**:
   ```bash
   claude-restart-monitor config reset
   ```

## Quick Start (5 minutes)

### Step 1: Basic Monitoring
Start monitoring Claude Code with default settings:

```bash
# Start monitoring Claude Code in current directory
claude-restart-monitor start --claude-cmd "claude"
```

**Expected output**:
```
[INFO] Starting Claude Code monitoring...
[INFO] Session ID: sess_20250918_143022
[INFO] Monitoring active - watching for usage limits
[INFO] Claude Code process detected (PID: 12345)
```

### Step 2: Verify Monitoring Status
Check that monitoring is active:

```bash
claude-restart-monitor status
```

**Expected output**:
```
Status: ACTIVE
Session: sess_20250918_143022
Uptime: 5m 23s
Detection Count: 0
Current State: monitoring
Claude Code PID: 12345
```

### Step 3: Test Limit Detection (Simulation)
Configure test patterns for quick validation:

```bash
# Add a test pattern to configuration
claude-restart-monitor config set detection_patterns '["test limit message"]'

# The system will now detect "test limit message" in Claude Code output
```

### Step 4: Monitor Logs
Watch real-time system logs:

```bash
claude-restart-monitor logs --follow
```

**Expected log output**:
```
2025-09-18 14:30:22 [INFO] Monitoring started for session sess_20250918_143022
2025-09-18 14:30:22 [INFO] Process monitoring active (PID: 12345)
2025-09-18 14:30:23 [DEBUG] Output scan: no patterns matched
2025-09-18 14:30:24 [DEBUG] Output scan: no patterns matched
```

### Step 5: Stop Monitoring
Gracefully stop the monitoring system:

```bash
claude-restart-monitor stop
```

**Expected output**:
```
[INFO] Stopping monitoring session sess_20250918_143022
[INFO] Monitoring stopped gracefully
[INFO] Claude Code process continues running
```

## Advanced Configuration

### Custom Restart Commands
Configure specific commands to run when Claude Code restarts:

```bash
# Set restart commands
claude-restart-monitor config set restart_commands '["claude", "--project", "/my-project", "--task", "continue"]'
```

### Detection Pattern Tuning
Customize the patterns that trigger limit detection:

```bash
# View current patterns
claude-restart-monitor config show | grep detection_patterns

# Update patterns
claude-restart-monitor config set detection_patterns '["usage limit exceeded", "rate limit", "please wait 5 hours"]'
```

### Daemon Mode
Run monitoring as a background service:

```bash
# Start as daemon
claude-restart-monitor start --claude-cmd "claude" --daemon

# Check daemon status
claude-restart-monitor status

# Stop daemon
claude-restart-monitor stop
```

## Integration Test Scenarios

### Scenario 1: Complete Restart Cycle
Simulate a full detection-to-restart cycle:

1. **Start monitoring**:
   ```bash
   claude-restart-monitor start --claude-cmd "claude --project /test"
   ```

2. **Trigger detection** (manual test):
   ```bash
   # In another terminal, send test message to Claude Code output
   echo "usage limit exceeded - please wait 5 hours" | claude
   ```

3. **Verify detection**:
   ```bash
   claude-restart-monitor status
   # Should show: Current State: waiting
   # Should show: Waiting Period: 4h 59m remaining
   ```

4. **Monitor countdown**:
   ```bash
   claude-restart-monitor logs --follow --grep "waiting"
   ```

5. **Verify restart** (after 5-hour wait or time manipulation):
   ```bash
   claude-restart-monitor logs --grep "restart"
   # Should show restart attempt and success
   ```

### Scenario 2: Configuration Validation
Test configuration management:

1. **Create custom config**:
   ```json
   {
     "log_level": "DEBUG",
     "detection_patterns": ["custom limit pattern"],
     "max_log_size_mb": 25,
     "monitoring": {
       "check_interval": 2,
       "task_timeout": 600
     }
   }
   ```

2. **Validate config**:
   ```bash
   claude-restart-monitor config validate --file custom-config.json
   ```

3. **Apply config**:
   ```bash
   claude-restart-monitor config load --file custom-config.json
   ```

### Scenario 3: Error Recovery
Test system resilience:

1. **Start monitoring**:
   ```bash
   claude-restart-monitor start --claude-cmd "claude"
   ```

2. **Kill Claude Code manually**:
   ```bash
   # Find and terminate Claude Code process
   taskkill /IM claude.exe /F
   ```

3. **Verify recovery**:
   ```bash
   claude-restart-monitor logs --follow
   # Should show process termination detection and restart attempt
   ```

## Troubleshooting

### Common Issues

**Issue**: "Claude Code not found"
```bash
# Solution: Verify Claude Code is in PATH
where claude
# Or specify full path
claude-restart-monitor start --claude-cmd "C:\path\to\claude.exe"
```

**Issue**: "Permission denied for process monitoring"
```bash
# Solution: Run as administrator
# Right-click Command Prompt -> "Run as administrator"
```

**Issue**: "Configuration file not found"
```bash
# Solution: Initialize default config
claude-restart-monitor config reset
```

### Debug Mode
Enable verbose logging for troubleshooting:

```bash
claude-restart-monitor --verbose start --claude-cmd "claude"
# Or set in config
claude-restart-monitor config set log_level DEBUG
```

### Support Information
Get diagnostic information:

```bash
claude-restart-monitor --version
claude-restart-monitor config show
claude-restart-monitor logs --tail 20
```

## Success Criteria

After completing this quickstart, you should be able to:

- ✅ Start and stop Claude Code monitoring
- ✅ Configure detection patterns and restart commands
- ✅ Monitor system status and logs in real-time
- ✅ Handle basic configuration management
- ✅ Simulate and verify limit detection scenarios
- ✅ Troubleshoot common issues

**Next Steps**:
- Review the full CLI interface documentation
- Explore advanced configuration options
- Set up production monitoring with custom patterns