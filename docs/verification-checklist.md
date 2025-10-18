# CLI Verification Checklist

## Manual Smoke
- `CLAUDE_RESTART_TEST_MODE=1 python -m pytest tests/contract/test_cli_start.py -k start_command`
- Run `claude-restart-monitor start --claude-cmd claude --daemon` to confirm simulation warning and background message.
- Execute `claude-restart-monitor status --json` and verify `waiting_period` and `session_id` fields.
- Stop the session via `claude-restart-monitor stop --force --kill-claude` ensuring exit code 0 and "stopped" text.

## Follow-up Actions
1. Ensure pytest dependencies are installed locally (`pip install -r requirements.txt`).
2. Add CI job to execute contract suites with `CLAUDE_RESTART_TEST_MODE=1` and process simulation enabled.
3. Implement real log streaming for `logs --follow` once logging pipeline is active.
