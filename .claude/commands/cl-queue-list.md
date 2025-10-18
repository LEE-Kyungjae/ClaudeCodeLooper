# Queued Task - List ("/cl:큐리스트")

Display the tasks currently scheduled to run after the cooldown restart.

## Steps
1. Run:
   ```bash
   python -m src.cli.main queue list
   ```
2. Read out the numbered entries to the user in order of execution.
3. If there are no tasks, report that the queue is empty.
