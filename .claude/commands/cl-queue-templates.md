---
command: "/cl:queue:templates"
title: "List Task Templates"
description: "Display reusable queue templates and their guidance."
---

# List task queue templates

List the predefined task templates and their guidelines.

## Steps
1. Execute the templates command:
   ```bash
   python -m src.cli.main queue templates
   ```
2. Read out the available template IDs and share summary information (persona/quality checks).
3. If needed, help the user decide which template to use, then add to queue with `/cl:queue` command.
