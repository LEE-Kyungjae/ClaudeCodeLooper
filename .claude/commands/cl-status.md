---
command: "/cl:status"
title: "Show Monitor Status"
description: "Display ClaudeCodeLooper status, waiting periods, and detections."
---

# Claude Code Auto-Restart Monitor - Status

Check the current status of the automated restart monitoring system.

## What to do:

1. **Get detailed status**:
   ```bash
   python -m src.cli.main status --verbose
   ```

2. **Parse and display**:
   - Active monitoring sessions
   - Current waiting periods
   - Total detections count
   - System uptime
   - Health metrics

3. **Explain to user**:
   Show a clear summary of:
   - Whether monitoring is active or stopped
   - Number of limit detections so far
   - Current state (monitoring / waiting / idle)
   - Time until next restart (if waiting)

## Output Format:

```
📊 Claude Code Monitor Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: [ACTIVE / STOPPED / WAITING]
Active Sessions: X
Limit Detections: X
Uptime: X hours

[If waiting]
⏳ Waiting Period Active
   Started: [timestamp]
   Remaining: X hours Y minutes
   Next Restart: [estimated time]

[If active]
👁️  Monitoring Claude Code output
   Started: [timestamp]
   Monitoring: [command]
```

Execute the commands above and present the results in a user-friendly format.
