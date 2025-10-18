# Claude Code Auto-Restart Monitor - Stop

Stop the automated Claude Code restart monitoring system.

## What to do:

1. **Check current status**:
   ```bash
   python -m src.cli.main status
   ```

2. **Stop all monitoring**:
   ```bash
   python -m src.cli.main stop --all
   ```

3. **Verify it stopped**:
   ```bash
   python -m src.cli.main status
   ```

4. **Explain to user**:
   - Monitoring has been stopped
   - All active sessions terminated
   - Claude Code will no longer auto-restart
   - Use `/cl:on` to start monitoring again

## Notes:
- Stops all monitoring gracefully
- Cleans up resources and processes
- State is saved for future sessions

Execute the commands above and report the results to the user.
