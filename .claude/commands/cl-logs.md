# Claude Code Auto-Restart Monitor - Logs

View recent logs and events from the monitoring system.

## What to do:

1. **Get recent logs** (default: last 50 lines):
   ```bash
   python -m src.cli.main logs --tail 50
   ```

2. **Show log analysis**:
   - Highlight limit detection events
   - Show restart actions
   - Display any errors or warnings

3. **Optional: Filter by type** (if user specifies):
   ```bash
   # All detection events
   python -m src.cli.main logs --filter detection

   # Errors only
   python -m src.cli.main logs --filter error

   # Watch live logs (follow mode)
   python -m src.cli.main logs --follow
   ```

4. **Present to user**:
   Format the output to show:
   - Timestamp
   - Event type (INFO/WARNING/ERROR)
   - Message
   - Relevant context (session_id, pid, etc.)

## Example Output:

```
📜 Recent Logs (last 50 lines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━

2025-10-18 14:30:15 [INFO] Monitoring started (session: sess_abc123)
2025-10-18 15:45:22 [INFO] Process health check: CPU 5%, Memory 120MB
2025-10-18 19:30:15 [WARN] Limit detection: usage limit exceeded
2025-10-18 19:30:16 [INFO] Waiting period started (5 hours)
2025-10-18 19:30:16 [INFO] Process stopped gracefully
```

Execute the commands above and format the output for readability.
