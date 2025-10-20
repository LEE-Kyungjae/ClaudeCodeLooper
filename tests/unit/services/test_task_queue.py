"""Tests for TaskQueueManager."""

from __future__ import annotations

from src.models.queued_task import QueuedTask
from src.services.task_queue import TaskQueueManager


def test_add_list_remove_tasks():
    manager = TaskQueueManager()

    # Add tasks with metadata
    manager.add_task(
        "First task",
        template_id="backend_feature",
        persona_prompt="persona",
        guideline_prompt="guideline",
        notes="note",
        post_commands=["pytest"],
    )
    manager.add_task("Second task")

    tasks = manager.list_tasks()
    assert len(tasks) == 2
    assert tasks[0].template_id == "backend_feature"
    assert tasks[0].post_commands == ["pytest"]

    removed = manager.remove_indices([1])
    assert len(removed) == 1
    assert removed[0].description == "First task"
    assert len(manager) == 1


def test_clear_prepend_and_serialization():
    original = [
        QueuedTask(description="existing-1"),
        QueuedTask(description="existing-2"),
    ]
    manager = TaskQueueManager(original)

    # Pop all tasks and re-load from serialization
    serialized = manager.to_serializable()
    assert len(serialized) == 2

    manager.clear()
    assert len(manager) == 0

    manager.load_serialized(serialized)
    assert len(manager) == 2

    new_tasks = [
        QueuedTask(description="prepended-1"),
        QueuedTask(description="prepended-2"),
    ]
    manager.prepend(new_tasks)
    assert manager.list_tasks()[0].description == "prepended-1"
