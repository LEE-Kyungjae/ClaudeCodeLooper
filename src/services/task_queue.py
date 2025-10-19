"""TaskQueueManager service for queued post-restart tasks."""

from __future__ import annotations

from typing import List, Iterable, Optional
from datetime import datetime

from ..models.queued_task import QueuedTask


class TaskQueueManager:
    """In-memory manager for queued tasks."""

    def __init__(self, tasks: Optional[Iterable[QueuedTask]] = None):
        self._tasks: List[QueuedTask] = list(tasks) if tasks is not None else []

    def __len__(self) -> int:
        return len(self._tasks)

    def add_task(
        self,
        description: str,
        *,
        template_id: Optional[str] = None,
        persona_prompt: Optional[str] = None,
        guideline_prompt: Optional[str] = None,
        notes: Optional[str] = None,
        post_commands: Optional[List[str]] = None,
    ) -> QueuedTask:
        """Add a task to the end of the queue."""
        description = description.strip()
        if not description:
            raise ValueError("Task description cannot be empty")

        task = QueuedTask(
            description=description,
            template_id=template_id,
            persona_prompt=persona_prompt,
            guideline_prompt=guideline_prompt,
            notes=notes,
            post_commands=list(post_commands or []),
        )
        self._tasks.append(task)
        return task

    def list_tasks(self) -> List[QueuedTask]:
        """Return current tasks in queue order."""
        return list(self._tasks)

    def remove_indices(self, indices: Iterable[int]) -> List[QueuedTask]:
        """Remove tasks by 1-based indices, returning removed tasks."""
        unique_indices = sorted(
            {idx for idx in indices if isinstance(idx, int)}, reverse=True
        )
        removed_with_index = []

        for idx in unique_indices:
            if 1 <= idx <= len(self._tasks):
                removed_task = self._tasks.pop(idx - 1)
                removed_with_index.append((idx, removed_task))

        # Return removed tasks in ascending index order
        removed_with_index.sort(key=lambda item: item[0])
        return [task for _, task in removed_with_index]

    def clear(self) -> int:
        """Clear the queue, returning number of removed tasks."""
        count = len(self._tasks)
        self._tasks.clear()
        return count

    def pop_all(self) -> List[QueuedTask]:
        """Remove and return all queued tasks."""
        tasks = list(self._tasks)
        self._tasks.clear()
        return tasks

    def prepend(self, tasks: Iterable[QueuedTask]) -> None:
        """Prepend tasks back to the queue preserving existing order."""
        tasks_list = list(tasks)
        if tasks_list:
            self._tasks = tasks_list + self._tasks

    def to_serializable(self) -> List[dict]:
        """Serialize tasks for persistence."""
        return [task.to_dict() for task in self._tasks]

    def load_serialized(self, data: Iterable[dict]) -> None:
        """Load tasks from serialized representation."""
        self._tasks = [QueuedTask.from_dict(item) for item in data]

    def next_scheduled_time(self) -> Optional[datetime]:
        """Return earliest creation timestamp, if any."""
        if not self._tasks:
            return None
        return min(task.created_at for task in self._tasks)
