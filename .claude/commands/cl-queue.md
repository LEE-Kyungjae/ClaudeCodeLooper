# Queued Task - Add

Add a new post-restart task to the automation queue.

## Steps

1. Run the CLI queue add command (replace the placeholder with the task description):
   ```bash
   python -m src.cli.main queue add "<TASK DESCRIPTION>"
   ```
2. Confirm the command succeeded. You should see a check mark and the task listed.
3. Let the user know the task is now scheduled to run automatically after the next Claude Code restart.

### Example Usage
```bash
python -m src.cli.main queue add "코드 점검"
```
