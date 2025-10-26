"""Integration test for complete restart cycle.

This test validates the full end-to-end restart workflow:
1. Start monitoring Claude Code
2. Detect usage limit
3. Enter waiting period
4. Restart after countdown
5. Resume monitoring

This test MUST FAIL initially before implementation.
"""

import os
import shutil
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest


class TestCompleteRestartCycle:
    """Integration test for complete Claude Code restart cycle."""

    def setup_method(self):
        """Set up test environment."""
        self.mock_processes = []
        self.test_work_dir = tempfile.mkdtemp()
        self.test_config = {
            "log_level": "DEBUG",
            "detection_patterns": ["test limit message"],
            "max_log_size_mb": 10,
            "monitoring": {
                "check_interval": 0.1,  # Fast for testing
                "task_timeout": 5,
            },
        }

    def teardown_method(self):
        """Clean up test environment."""
        for process in self.mock_processes:
            try:
                process.terminate()
            except:
                pass
        if getattr(self, "test_work_dir", None) and os.path.isdir(self.test_work_dir):
            shutil.rmtree(self.test_work_dir, ignore_errors=True)

    def wait_for(self, condition, *, timeout: float = 5.0, interval: float = 0.05):
        """Poll until condition is true or timeout expires."""
        start = time.time()
        while time.time() - start < timeout:
            if condition():
                return True
            time.sleep(interval)
        return False

    @pytest.mark.integration
    def test_complete_restart_cycle_end_to_end(self):
        """Test complete restart cycle from start to finish."""
        # This test will fail until full implementation is complete
        from src.models.monitoring_session import MonitoringSession
        from src.models.system_configuration import SystemConfiguration
        from src.services.restart_controller import RestartController

        # 1. Initialize system with test configuration
        config = SystemConfiguration(**self.test_config)
        controller = RestartController(config)

        # 2. Start monitoring with mock Claude Code process
        session = controller.start_monitoring(
            claude_cmd="echo 'test process'",
            work_dir=self.test_work_dir,
            restart_commands=["echo 'restart'"],
        )

        assert session.status == "active"
        assert session.claude_process_id is not None

        # 3. Simulate limit detection
        controller.process_monitor.inject_output("test limit message")

        # 4. Verify transition to waiting period
        assert self.wait_for(
            lambda: session.status == "waiting"
        ), "Session should enter waiting state"
        assert controller.waiting_period is not None
        assert controller.waiting_period.status == "active"

        # 5. Fast-forward time simulation (mock the 5-hour wait)
        with patch("src.services.timing_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(
                hours=5, minutes=1
            )
            controller.timing_manager.check_waiting_period()

        # 6. Verify restart occurs
        assert self.wait_for(
            lambda: session.status == "active"
        ), "Session should resume after waiting period"
        assert controller.waiting_period.status == "completed"

        # 7. Cleanup
        controller.stop_monitoring()
        assert session.status == "stopped"

    @pytest.mark.integration
    def test_restart_cycle_with_task_completion(self):
        """Test restart cycle respects ongoing task completion."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.restart_controller import RestartController

        config = SystemConfiguration(**self.test_config)
        controller = RestartController(config)

        # Start monitoring
        session = controller.start_monitoring(
            claude_cmd="echo 'ongoing task'", work_dir=self.test_work_dir
        )

        # Simulate ongoing task
        controller.task_monitor.set_task_in_progress(True)

        # Trigger limit detection
        controller.process_monitor.inject_output("test limit message")
        assert self.wait_for(
            lambda: session.status == "active"
        ), "Session should remain active while task in progress"

        # Complete the task
        controller.task_monitor.set_task_in_progress(False)
        assert self.wait_for(
            lambda: session.status == "waiting"
        ), "Session should enter waiting once task completes"

        controller.stop_monitoring()

    @pytest.mark.integration
    def test_restart_cycle_with_custom_commands(self):
        """Test restart cycle with custom restart commands."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.restart_controller import RestartController

        config = SystemConfiguration(**self.test_config)
        controller = RestartController(config)

        custom_commands = [
            "echo 'custom restart'",
            "--project /my-project",
            "--task continue",
        ]

        session = controller.start_monitoring(
            claude_cmd="echo 'test'", restart_commands=custom_commands
        )

        # Verify custom commands are stored
        assert session.restart_config.command_template == custom_commands[0]
        assert custom_commands[1] in session.restart_config.arguments
        assert custom_commands[2] in session.restart_config.arguments

        controller.stop_monitoring()

    @pytest.mark.integration
    def test_restart_cycle_state_persistence(self):
        """Test that restart cycle state persists across system restarts."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.restart_controller import RestartController

        config = SystemConfiguration(**self.test_config)

        # First instance - start monitoring and trigger limit
        controller1 = RestartController(config)
        session = controller1.start_monitoring(claude_cmd="echo 'test'")

        controller1.process_monitor.inject_output("test limit message")
        assert self.wait_for(
            lambda: session.status == "waiting"
        ), "Session should enter waiting before persisting state"

        session_id = session.session_id

        # Simulate system restart
        controller1.state_manager.save_state()
        del controller1

        # Second instance - should recover state
        controller2 = RestartController(config)
        controller2.state_manager.load_state()

        recovered_session = controller2.get_session(session_id)
        assert recovered_session is not None
        assert recovered_session.status == "waiting"

        controller2.stop_monitoring()

    @pytest.mark.integration
    def test_restart_cycle_multiple_detections(self):
        """Test handling of multiple limit detections."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.restart_controller import RestartController

        config = SystemConfiguration(**self.test_config)
        controller = RestartController(config)

        session = controller.start_monitoring(claude_cmd="echo 'test'")

        # First detection
        controller.process_monitor.inject_output("test limit message")
        assert self.wait_for(
            lambda: session.status == "waiting"
        ), "Session should enter waiting after detection"

        first_detection_count = session.detection_count

        # Second detection while waiting (should be handled gracefully)
        controller.process_monitor.inject_output("test limit message")
        assert self.wait_for(
            lambda: session.detection_count == first_detection_count + 1
        ), "Detection count should increment once"

        # Should not create duplicate waiting periods
        assert session.detection_count == first_detection_count + 1
        assert len(controller.waiting_periods) == 1

        controller.stop_monitoring()

    @pytest.mark.integration
    def test_restart_cycle_performance_requirements(self):
        """Test that restart cycle meets performance requirements."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.restart_controller import RestartController

        config = SystemConfiguration(**self.test_config)
        controller = RestartController(config)

        session = controller.start_monitoring(claude_cmd="echo 'test'")

        # Test detection speed (< 1 second)
        start_time = time.time()
        controller.process_monitor.inject_output("test limit message")

        # Wait for detection
        while session.status != "waiting" and time.time() - start_time < 2:
            time.sleep(0.01)

        detection_time = time.time() - start_time
        assert detection_time < 1.0, f"Detection took {detection_time}s, should be < 1s"

        # Test restart responsiveness
        with patch("src.services.timing_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now() + timedelta(
                hours=5, minutes=1
            )

            start_time = time.time()
            controller.timing_manager.check_waiting_period()

            while session.status != "active" and time.time() - start_time < 2:
                time.sleep(0.01)

            restart_time = time.time() - start_time
            assert restart_time < 1.0, f"Restart took {restart_time}s, should be < 1s"

        controller.stop_monitoring()

    @pytest.mark.integration
    def test_restart_cycle_error_scenarios(self):
        """Test restart cycle handles error scenarios gracefully."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.restart_controller import RestartController

        config = SystemConfiguration(**self.test_config)
        controller = RestartController(config)

        # Test with invalid Claude Code command
        with pytest.raises(Exception):
            controller.start_monitoring(claude_cmd="nonexistent_command")

        # Test with valid command but process dies
        session = controller.start_monitoring(claude_cmd="echo 'test'")

        # Simulate process death
        controller.process_monitor.simulate_process_death()
        assert self.wait_for(
            lambda: session.status in {"stopped", "active"}
        ), "Session should recover or stop after simulated crash"

        controller.stop_monitoring()
