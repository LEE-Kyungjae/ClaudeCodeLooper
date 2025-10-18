# Queued Task - Remove ("/cl:큐딜리트")

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
3. Confirm the removal output and let the user know which tasks were deleted. If no tasks matched, tell the user nothing was removed.
