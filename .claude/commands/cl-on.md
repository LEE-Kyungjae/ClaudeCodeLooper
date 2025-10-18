# Claude Code Auto-Restart Monitor - Start

Start the automated Claude Code restart monitoring system.

## What to do:

1. **Check if already running**:
   ```bash
   python -m src.cli.main status --format json
   ```

2. **If not running, start monitoring**:
   ```bash
   python -m src.cli.main start \
     --claude-cmd "claude" \
     --work-dir "$PWD" \
     --daemon
   ```

3. **Verify it started**:
   ```bash
   python -m src.cli.main status
   ```

4. **Explain to user**:
   - Monitoring is now active
   - It will detect when Claude Code hits the 5-hour limit
   - Automatically restart after the cooldown period
   - Use `/cl:status` to check status
   - Use `/cl:off` to stop monitoring

## Notes:
- Runs in daemon mode (background)
- Monitors terminal output for limit messages
- Automatically restarts with configured commands
- Logs are saved to `logs/claude-restart-monitor.log`

Execute the commands above and report the results to the user.
