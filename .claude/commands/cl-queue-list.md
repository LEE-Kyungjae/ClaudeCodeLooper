---
command: "/cl:queue:list"
title: "List Queued Tasks"
description: "Show queued tasks waiting for the next Claude restart cycle."
---

# List queued tasks

Display the tasks currently scheduled to run after the cooldown restart.

## Steps
1. Run:
   ```bash
   python -m src.cli.main queue list
   ```
2. Share the template (label in `[]`) and memo shown for each item.
3. If follow-up commands are needed, inform that tasks can be added with `queue add --post`.
4. If no items exist, inform the user that the queue is empty.
