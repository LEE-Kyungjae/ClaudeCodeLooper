# Remove queued tasks

Remove one or more queued tasks by their list numbers.

## Steps
1. Review the current queue if needed:
   ```bash
   python -m src.cli.main queue list
   ```
2. Remove the desired entries by specifying their numbers separated by spaces:
   ```bash
   python -m src.cli.main queue remove 1 3 5
   ```
3. Confirm the removal output and inform the user of deleted tasks (including template/memo information).
4. List numbers start from 1, same as in the list view. Recommend checking remaining items with `queue list` after removal.
