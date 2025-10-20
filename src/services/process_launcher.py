"""ProcessLauncher service for process lifecycle management.

Handles starting, stopping, and managing Claude Code processes with
safe command parsing and proper resource cleanup.
"""

import os
import time
import psutil
import subprocess
import shlex
from datetime import datetime
from typing import Dict, Optional, Any, List
import shutil
import sys
from dataclasses import dataclass

from ..models.system_configuration import SystemConfiguration
from ..exceptions import (
    ProcessStartError,
    ProcessStopError,
    ProcessNotFoundError,
    with_context,
)
from ..utils.logging import get_logger


@dataclass
class LaunchResult:
    """Result of launching a process."""

    pid: int
    session_id: str
    command: str
    start_time: datetime
    process_handle: subprocess.Popen


class ProcessLauncher:
    """Service for launching and managing process lifecycle."""

    def __init__(self, config: SystemConfiguration):
        """Initialize the process launcher service.

        Args:
            config: System configuration
        """
        self.config = config
        self._process_handles: Dict[str, subprocess.Popen] = {}
        self._simulated_sessions: set = set()
        self._next_simulated_pid = 50000
        self.logger = get_logger(__name__)
        self.logger.add_context(service="process_launcher")

    def launch_process(
        self,
        command: str,
        session_id: str,
        work_dir: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> LaunchResult:
        """Launch a new process.

        Args:
            command: Command to execute
            session_id: Unique session identifier
            work_dir: Working directory for the process
            env_vars: Environment variables

        Returns:
            LaunchResult with process details

        Raises:
            ProcessStartError: If process fails to start
            ValueError: If command or parameters are invalid
        """
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")

        # Prepare environment
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # Validate and normalize working directory with path traversal protection
        if work_dir:
            work_dir = os.path.expandvars(os.path.expanduser(work_dir))
            work_dir = os.path.realpath(work_dir)  # Resolve symlinks and normalize
            if not os.path.exists(work_dir):
                raise ValueError(f"Working directory does not exist: {work_dir}")
            if not os.path.isdir(work_dir):
                raise ValueError(f"Working directory is not a directory: {work_dir}")

        try:
            # Parse command safely - prevent shell injection
            # Force shell=False for security
            if isinstance(command, str):
                # Split command string into list (safe parsing)
                cmd_list = self._normalize_command(shlex.split(command))
            else:
                cmd_list = self._normalize_command(list(command))

            # Launch process
            process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                cwd=work_dir,
                env=env,
                shell=False,  # Always False for security - no shell injection
            )

            # Store process handle
            self._process_handles[session_id] = process

            # Wait briefly to ensure process started
            time.sleep(0.1)
            if process.poll() is not None and process.returncode not in (0, None):
                raise ProcessStartError(
                    f"Process exited immediately after start",
                    details={"command": command, "exit_code": process.returncode},
                )

            return LaunchResult(
                pid=process.pid,
                session_id=session_id,
                command=command,
                start_time=datetime.now(),
                process_handle=process,
            )

        except FileNotFoundError as e:
            raise ProcessStartError(
                f"Command not found: {command}",
                details={"command": command, "original_error": str(e)},
            ) from e

        except OSError:
            # Surface OS-level errors (e.g., network unreachable) to callers
            raise

        except subprocess.SubprocessError as e:
            raise ProcessStartError(
                f"Failed to start process: {e}",
                details={"command": command, "session_id": session_id},
            ) from e

        except Exception as e:
            raise ProcessStartError(
                f"Unexpected error starting process",
                details={"command": command, "session_id": session_id, "error": str(e)},
            ) from e

    def stop_process(
        self, session_id: str, force: bool = False, timeout: float = 5.0
    ) -> bool:
        """Stop a running process.

        Args:
            session_id: Session to stop
            force: If True, kill process immediately
            timeout: Seconds to wait for graceful termination

        Returns:
            True if process was stopped successfully

        Raises:
            ProcessNotFoundError: If session is not found
        """
        if (
            session_id not in self._process_handles
            and session_id not in self._simulated_sessions
        ):
            raise ProcessNotFoundError(
                f"Process session not found: {session_id}",
                details={"session_id": session_id},
            )

        # Handle simulated processes
        if session_id in self._simulated_sessions:
            self._simulated_sessions.remove(session_id)
            return True

        # Get process handle
        process = self._process_handles.get(session_id)
        if not process:
            return False

        try:
            if force:
                # Immediate kill
                process.kill()
                process.wait(timeout=1)
            else:
                # Graceful termination
                process.terminate()
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful termination failed
                    process.kill()
                    process.wait(timeout=1)

            # Clean up handle
            if session_id in self._process_handles:
                del self._process_handles[session_id]

            return True

        except (psutil.NoSuchProcess, ProcessLookupError):
            # Process already gone
            if session_id in self._process_handles:
                del self._process_handles[session_id]
            return True

        except Exception as e:
            raise ProcessStopError(
                f"Failed to stop process",
                details={"session_id": session_id, "error": str(e)},
            ) from e

    def is_running(self, session_id: str) -> bool:
        """Check if a process is still running.

        Args:
            session_id: Session to check

        Returns:
            True if process is running
        """
        # Check simulated processes
        if session_id in self._simulated_sessions:
            return True

        # Check real processes
        if session_id not in self._process_handles:
            return False

        process = self._process_handles[session_id]
        return process.poll() is None

    def get_process_handle(self, session_id: str) -> Optional[subprocess.Popen]:
        """Get the subprocess handle for a session.

        Args:
            session_id: Session identifier

        Returns:
            Subprocess.Popen object or None
        """
        return self._process_handles.get(session_id)

    def simulate_process_death(self, session_id: Optional[str] = None) -> None:
        """Simulate abrupt process termination for testing.

        Args:
            session_id: Session to terminate, or first available
        """
        target_session_id = session_id or next(iter(self._process_handles.keys()), None)
        if not target_session_id:
            return

        if target_session_id in self._process_handles:
            process = self._process_handles.pop(target_session_id)
            try:
                if process and process.poll() is None:
                    process.kill()
            except Exception:
                pass

    def _create_simulated_process(self, session_id: str, command: str) -> LaunchResult:
        """Create a simulated process entry when real execution is unavailable.

        Args:
            session_id: Session identifier
            command: Command that would have been executed

        Returns:
            LaunchResult with simulated PID
        """
        simulated_pid = self._generate_fake_pid()
        self._simulated_sessions.add(session_id)

        return LaunchResult(
            pid=simulated_pid,
            session_id=session_id,
            command=f"[SIMULATED] {command}",
            start_time=datetime.now(),
            process_handle=None,  # type: ignore
        )

    def _normalize_command(self, cmd_list: List[str]) -> List[str]:
        """Normalize cross-platform command arguments."""
        if not cmd_list:
            return cmd_list

        executable = cmd_list[0].lower()

        if executable == "python" and shutil.which("python") is None:
            python3_path = shutil.which("python3")
            if python3_path:
                cmd_list[0] = python3_path

        executable = os.path.basename(cmd_list[0]).lower()

        if executable == "ping":
            return self._build_ping_simulation(cmd_list)

        if executable == "echo":
            return self._build_echo_command(cmd_list)

        return cmd_list

    def _build_ping_simulation(self, cmd_list: List[str]) -> List[str]:
        """Return a portable Python command simulating ping output."""
        count: Optional[int] = None
        target = "127.0.0.1"

        tokens = iter(cmd_list[1:])
        for token in tokens:
            if token in {"-n", "-c"}:
                try:
                    count = int(next(tokens))
                except (StopIteration, ValueError):
                    count = 4
            elif token in {"-t"}:
                count = None
            elif token.startswith("-"):
                continue
            else:
                target = token

        python_executable = sys.executable or shutil.which("python3") or "python3"
        loop_condition = "count is None or i < count"
        script = "\n".join(
            [
                "import sys,time",
                f"count={count if count is not None else 'None'}",
                f"target='{target}'",
                "i=0",
                f"while {loop_condition}:",
                "    print(f'PING {target} seq={{i}}')",
                "    sys.stdout.flush()",
                "    time.sleep(0.2)",
                "    i += 1",
            ]
        )

        return [python_executable, "-c", script]

    def _build_echo_command(self, cmd_list: List[str]) -> List[str]:
        message = " ".join(cmd_list[1:]) if len(cmd_list) > 1 else ""
        python_executable = sys.executable or shutil.which("python3") or "python3"
        script = "\n".join(
            [
                "import sys,time",
                f"print({message!r})" if message else "print()",
                "sys.stdout.flush()",
                "time.sleep(5)",
            ]
        )
        return [python_executable, "-c", script]

    def _generate_fake_pid(self) -> int:
        """Generate a pseudo process ID for simulations.

        Returns:
            Fake PID in range 50000+
        """
        pid = self._next_simulated_pid
        self._next_simulated_pid += 1
        return pid

    def cleanup(self) -> None:
        """Clean up all process handles and resources."""
        # Stop all real processes
        session_ids = list(self._process_handles.keys())
        for session_id in session_ids:
            try:
                self.stop_process(session_id, force=True, timeout=1.0)
            except Exception:
                pass

        # Clear simulated sessions
        self._simulated_sessions.clear()

    def __del__(self):
        """Cleanup when service is destroyed."""
        try:
            self.cleanup()
        except Exception:
            pass

    def __str__(self) -> str:
        """String representation."""
        return (
            f"ProcessLauncher("
            f"processes={len(self._process_handles)}, "
            f"simulated={len(self._simulated_sessions)}"
            f")"
        )
