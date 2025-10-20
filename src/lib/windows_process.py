"""Windows-specific process monitoring stubs."""

class WindowsProcessMonitor:
    """Minimal stub used in non-Windows environments for testing."""

    def __init__(self) -> None:  # pragma: no cover - simple stub
        self.initialized = True

    def get_process_tree(self, pid: int):  # pragma: no cover - stub
        return {"pid": pid, "children": []}

    def get_performance_counters(self, pid: int):  # pragma: no cover - stub
        return {"handle_count": 0, "thread_count": 0}
