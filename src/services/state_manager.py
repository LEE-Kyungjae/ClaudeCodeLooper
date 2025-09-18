"""StateManager service for persistence and recovery.

Handles saving and loading system state, backup management,
and recovery across system restarts.
"""
import json
import os
import shutil
import threading
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from ..models.system_configuration import SystemConfiguration
from ..models.monitoring_session import MonitoringSession
from ..models.waiting_period import WaitingPeriod
from ..models.limit_detection_event import LimitDetectionEvent


class StateManager:
    """Service for managing system state persistence."""

    def __init__(self, config: SystemConfiguration, state_dir: Optional[str] = None):
        """Initialize the state manager."""
        self.config = config
        self.state_dir = state_dir or os.path.dirname(config.get_persistence_file_path())
        self.state_file = config.get_persistence_file_path()
        self.backup_dir = config.get_backup_directory_path()

        # Ensure directories exist
        os.makedirs(self.state_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

        # Thread safety
        self._lock = threading.RLock()

        # Auto-save settings
        self.auto_save_enabled = True
        self.auto_save_interval = 300  # 5 minutes
        self.last_save_time = datetime.now()

        # Backup settings
        self.max_backups = config.backup_count
        self.backup_on_save = True

        # State cache
        self._cached_state: Optional[Dict[str, Any]] = None
        self._state_dirty = False

    def save_state(self, state_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save current system state to file.

        Args:
            state_data: State data to save (uses cached if None)

        Returns:
            True if state was saved successfully
        """
        if state_data is None and self._cached_state is None:
            return False

        with self._lock:
            try:
                # Use provided data or cached state
                data_to_save = state_data or self._cached_state

                # Add metadata
                save_data = {
                    "metadata": {
                        "version": "1.0.0",
                        "saved_at": datetime.now().isoformat(),
                        "config_version": self.config.config_version
                    },
                    "state": data_to_save
                }

                # Create backup if enabled
                if self.backup_on_save and os.path.exists(self.state_file):
                    self._create_backup()

                # Write to temporary file first (atomic operation)
                temp_file = self.state_file + ".tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)

                # Atomic move
                if os.name == 'nt':  # Windows
                    if os.path.exists(self.state_file):
                        os.remove(self.state_file)
                os.rename(temp_file, self.state_file)

                # Update cache and timestamps
                self._cached_state = data_to_save
                self._state_dirty = False
                self.last_save_time = datetime.now()

                return True

            except Exception as e:
                print(f"Error saving state: {e}")
                # Cleanup temp file if it exists
                temp_file = self.state_file + ".tmp"
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
                return False

    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        Load system state from file.

        Returns:
            State data dictionary or None if load failed
        """
        with self._lock:
            try:
                if not os.path.exists(self.state_file):
                    return None

                with open(self.state_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)

                # Validate structure
                if not isinstance(loaded_data, dict) or "state" not in loaded_data:
                    return None

                # Check version compatibility
                metadata = loaded_data.get("metadata", {})
                if self._is_compatible_version(metadata.get("version")):
                    state_data = loaded_data["state"]
                    self._cached_state = state_data
                    self._state_dirty = False
                    return state_data
                else:
                    # Handle version migration if needed
                    return self._migrate_state(loaded_data)

            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading state: {e}")
                # Try to load from backup
                return self._load_from_backup()

    def save_state_with_fallback(self, state_data: Dict[str, Any]) -> bool:
        """
        Save state with fallback to alternative locations.

        Args:
            state_data: State data to save

        Returns:
            True if state was saved successfully
        """
        # Try primary location first
        if self.save_state(state_data):
            return True

        # Try fallback locations
        fallback_locations = [
            os.path.join(tempfile.gettempdir(), "claude-restart-state.json"),
            os.path.expanduser("~/claude-restart-state-backup.json")
        ]

        for fallback_path in fallback_locations:
            try:
                temp_state_file = self.state_file
                self.state_file = fallback_path

                if self.save_state(state_data):
                    print(f"State saved to fallback location: {fallback_path}")
                    return True

            except Exception:
                pass
            finally:
                self.state_file = temp_state_file

        return False

    def _create_backup(self) -> str:
        """
        Create a backup of the current state file.

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"state_backup_{timestamp}.json"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        try:
            shutil.copy2(self.state_file, backup_path)
            self._cleanup_old_backups()
            return backup_path
        except Exception as e:
            print(f"Error creating backup: {e}")
            return ""

    def _cleanup_old_backups(self) -> None:
        """Remove old backup files beyond the retention limit."""
        try:
            backup_files = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("state_backup_") and filename.endswith(".json"):
                    filepath = os.path.join(self.backup_dir, filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # Remove excess backups
            for filepath, _ in backup_files[self.max_backups:]:
                try:
                    os.remove(filepath)
                except Exception:
                    pass

        except Exception as e:
            print(f"Error cleaning up backups: {e}")

    def _load_from_backup(self) -> Optional[Dict[str, Any]]:
        """Load state from the most recent backup."""
        try:
            backup_files = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("state_backup_") and filename.endswith(".json"):
                    filepath = os.path.join(self.backup_dir, filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))

            if not backup_files:
                return None

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # Try loading from most recent backup
            most_recent_backup = backup_files[0][0]
            with open(most_recent_backup, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

            if "state" in loaded_data:
                print(f"State loaded from backup: {most_recent_backup}")
                return loaded_data["state"]

        except Exception as e:
            print(f"Error loading from backup: {e}")

        return None

    def _is_compatible_version(self, version: Optional[str]) -> bool:
        """Check if state version is compatible."""
        if not version:
            return False

        # Simple version compatibility check
        # In practice, this would be more sophisticated
        compatible_versions = ["1.0.0", "1.0.1", "1.1.0"]
        return version in compatible_versions

    def _migrate_state(self, old_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Migrate state from older version."""
        try:
            # Implement migration logic here
            # For now, just return the state part if it exists
            if "state" in old_data:
                return old_data["state"]
            return old_data
        except Exception:
            return None

    def update_cached_state(self, updates: Dict[str, Any]) -> None:
        """
        Update cached state data.

        Args:
            updates: Dictionary of updates to apply
        """
        with self._lock:
            if self._cached_state is None:
                self._cached_state = {}

            self._cached_state.update(updates)
            self._state_dirty = True

    def get_cached_state(self) -> Optional[Dict[str, Any]]:
        """Get cached state data."""
        with self._lock:
            return self._cached_state.copy() if self._cached_state else None

    def is_state_saved(self) -> bool:
        """Check if current state is saved."""
        with self._lock:
            return not self._state_dirty

    def should_auto_save(self) -> bool:
        """Check if auto-save should be triggered."""
        if not self.auto_save_enabled or not self._state_dirty:
            return False

        time_since_save = datetime.now() - self.last_save_time
        return time_since_save.total_seconds() >= self.auto_save_interval

    def save_sessions(self, sessions: Dict[str, MonitoringSession]) -> bool:
        """Save monitoring sessions to state."""
        session_data = {
            session_id: session.to_dict()
            for session_id, session in sessions.items()
        }

        self.update_cached_state({"sessions": session_data})
        return self.save_state()

    def load_sessions(self) -> Dict[str, MonitoringSession]:
        """Load monitoring sessions from state."""
        state = self.load_state()
        if not state or "sessions" not in state:
            return {}

        sessions = {}
        for session_id, session_data in state["sessions"].items():
            try:
                session = MonitoringSession.from_dict(session_data)
                sessions[session_id] = session
            except Exception as e:
                print(f"Error loading session {session_id}: {e}")

        return sessions

    def save_waiting_periods(self, periods: Dict[str, WaitingPeriod]) -> bool:
        """Save waiting periods to state."""
        period_data = {
            period_id: period.to_dict()
            for period_id, period in periods.items()
        }

        self.update_cached_state({"waiting_periods": period_data})
        return self.save_state()

    def load_waiting_periods(self) -> Dict[str, WaitingPeriod]:
        """Load waiting periods from state."""
        state = self.load_state()
        if not state or "waiting_periods" not in state:
            return {}

        periods = {}
        for period_id, period_data in state["waiting_periods"].items():
            try:
                period = WaitingPeriod.from_dict(period_data)
                periods[period_id] = period
            except Exception as e:
                print(f"Error loading waiting period {period_id}: {e}")

        return periods

    def save_detection_events(self, events: List[LimitDetectionEvent]) -> bool:
        """Save detection events to state."""
        event_data = [event.to_dict() for event in events]
        self.update_cached_state({"detection_events": event_data})
        return self.save_state()

    def load_detection_events(self) -> List[LimitDetectionEvent]:
        """Load detection events from state."""
        state = self.load_state()
        if not state or "detection_events" not in state:
            return []

        events = []
        for event_data in state["detection_events"]:
            try:
                event = LimitDetectionEvent.from_dict(event_data)
                events.append(event)
            except Exception as e:
                print(f"Error loading detection event: {e}")

        return events

    def get_backup_files(self) -> List[Dict[str, Any]]:
        """Get list of available backup files."""
        backups = []
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("state_backup_") and filename.endswith(".json"):
                    filepath = os.path.join(self.backup_dir, filename)
                    stat = os.stat(filepath)
                    backups.append({
                        "filename": filename,
                        "path": filepath,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })

            backups.sort(key=lambda x: x["modified"], reverse=True)
        except Exception as e:
            print(f"Error listing backups: {e}")

        return backups

    def restore_from_backup(self, backup_path: str) -> bool:
        """
        Restore state from a specific backup file.

        Args:
            backup_path: Path to backup file

        Returns:
            True if restore was successful
        """
        try:
            if not os.path.exists(backup_path):
                return False

            # Create backup of current state first
            if os.path.exists(self.state_file):
                current_backup = self.state_file + ".before_restore"
                shutil.copy2(self.state_file, current_backup)

            # Restore from backup
            shutil.copy2(backup_path, self.state_file)

            # Clear cache to force reload
            with self._lock:
                self._cached_state = None
                self._state_dirty = False

            return True

        except Exception as e:
            print(f"Error restoring from backup: {e}")
            return False

    def get_state_statistics(self) -> Dict[str, Any]:
        """Get state management statistics."""
        try:
            state_size = os.path.getsize(self.state_file) if os.path.exists(self.state_file) else 0
            backup_count = len(self.get_backup_files())

            return {
                "state_file_size": state_size,
                "state_file_exists": os.path.exists(self.state_file),
                "backup_count": backup_count,
                "auto_save_enabled": self.auto_save_enabled,
                "last_save_time": self.last_save_time.isoformat(),
                "state_dirty": self._state_dirty,
                "cache_size": len(self._cached_state) if self._cached_state else 0
            }
        except Exception:
            return {"error": "Failed to get statistics"}

    def __str__(self) -> str:
        """String representation of the state manager."""
        return (
            f"StateManager("
            f"file={os.path.basename(self.state_file)}, "
            f"dirty={self._state_dirty}, "
            f"auto_save={self.auto_save_enabled}"
            f")"
        )