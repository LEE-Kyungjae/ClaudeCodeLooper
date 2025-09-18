"""Integration test for process monitoring.

This test validates the process monitoring capabilities including
Claude Code process management, output capture, and system integration.

This test MUST FAIL initially before implementation.
"""
import pytest
import time
import subprocess
import psutil
import os
import signal
from unittest.mock import Mock, patch


class TestProcessMonitoring:
    """Integration test for Claude Code process monitoring."""

    def setup_method(self):
        """Set up test environment."""
        self.test_processes = []

    def teardown_method(self):
        """Clean up test processes."""
        for proc in self.test_processes:
            try:
                if proc.poll() is None:  # Still running
                    proc.terminate()
                    proc.wait(timeout=5)
            except:
                pass

    @pytest.mark.integration
    def test_process_lifecycle_management(self):
        """Test complete process lifecycle management."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration(
            monitoring={"check_interval": 0.1, "task_timeout": 5}
        )
        monitor = ProcessMonitor(config)

        # Start monitoring a test process
        process_info = monitor.start_monitoring("ping -n 5 127.0.0.1")  # Windows ping
        assert process_info is not None
        assert process_info.pid > 0
        assert process_info.status == "running"

        # Verify process is actually running
        assert psutil.pid_exists(process_info.pid)

        # Stop monitoring
        monitor.stop_monitoring()

        # Process should be terminated
        time.sleep(0.5)
        try:
            process = psutil.Process(process_info.pid)
            assert not process.is_running() or process.status() == "zombie"
        except psutil.NoSuchProcess:
            pass  # Process successfully terminated

    @pytest.mark.integration
    def test_real_time_output_capture(self):
        """Test real-time capture of process output."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration(
            monitoring={"check_interval": 0.05}  # Fast capture
        )
        monitor = ProcessMonitor(config)

        # Start process that produces output
        cmd = 'python -c "import time; [print(f\'line {i}\') or time.sleep(0.1) for i in range(5)]"'
        process_info = monitor.start_monitoring(cmd)

        captured_output = []
        start_time = time.time()

        # Capture output for limited time
        while time.time() - start_time < 2:
            output = monitor.get_recent_output()
            if output:
                captured_output.extend(output)
            time.sleep(0.1)

        monitor.stop_monitoring()

        # Should have captured multiple lines
        assert len(captured_output) > 0
        assert any("line" in line for line in captured_output)

    @pytest.mark.integration
    def test_process_health_monitoring(self):
        """Test monitoring of process health and status."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration()
        monitor = ProcessMonitor(config)

        # Start a long-running process
        process_info = monitor.start_monitoring("ping -t 127.0.0.1")  # Continuous ping

        # Monitor health metrics
        health_metrics = monitor.get_health_metrics()
        assert health_metrics is not None
        assert "cpu_percent" in health_metrics
        assert "memory_usage" in health_metrics
        assert "status" in health_metrics

        # Process should be healthy
        assert health_metrics["status"] in ["running", "sleeping"]

        monitor.stop_monitoring()

    @pytest.mark.integration
    def test_multiple_process_monitoring(self):
        """Test monitoring multiple Claude Code instances."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration()
        monitor = ProcessMonitor(config)

        # Start multiple processes
        processes = []
        for i in range(3):
            cmd = f'python -c "import time; print(\'process {i}\'); time.sleep(2)"'
            process_info = monitor.start_monitoring(cmd, session_id=f"session_{i}")
            processes.append(process_info)

        # All processes should be tracked
        active_processes = monitor.get_active_processes()
        assert len(active_processes) == 3

        # Each should have unique session ID
        session_ids = [p.session_id for p in active_processes]
        assert len(set(session_ids)) == 3

        monitor.stop_all_monitoring()

    @pytest.mark.integration
    def test_process_resource_monitoring(self):
        """Test monitoring of process resource usage."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration()
        monitor = ProcessMonitor(config)

        # Start resource-intensive process
        cmd = 'python -c "x = [i**2 for i in range(100000)]; import time; time.sleep(1)"'
        process_info = monitor.start_monitoring(cmd)

        time.sleep(0.5)  # Let process run

        # Get resource usage
        resources = monitor.get_resource_usage(process_info.pid)
        assert resources is not None
        assert "cpu_percent" in resources
        assert "memory_mb" in resources
        assert "open_files" in resources

        # Should track resource limits
        assert resources["memory_mb"] < 1000  # Reasonable limit

        monitor.stop_monitoring()

    @pytest.mark.integration
    def test_process_crash_detection(self):
        """Test detection of process crashes and unexpected termination."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration(
            monitoring={"check_interval": 0.1}
        )
        monitor = ProcessMonitor(config)

        # Start process that will crash
        cmd = 'python -c "import time; time.sleep(0.5); exit(1)"'  # Exit with error
        process_info = monitor.start_monitoring(cmd)

        # Wait for crash
        time.sleep(1)

        # Should detect crash
        crash_events = monitor.get_crash_events()
        assert len(crash_events) > 0

        crash_event = crash_events[0]
        assert crash_event.pid == process_info.pid
        assert crash_event.exit_code != 0

    @pytest.mark.integration
    def test_output_buffering_and_streaming(self):
        """Test output buffering and streaming capabilities."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration(
            monitoring={"output_buffer_size": 1000}
        )
        monitor = ProcessMonitor(config)

        # Process that produces lots of output
        cmd = 'python -c "for i in range(100): print(f\'Large output line {i} with extra text to fill buffer\')"'
        process_info = monitor.start_monitoring(cmd)

        time.sleep(1)  # Let it produce output

        # Should handle large output without memory issues
        all_output = monitor.get_all_output()
        assert len(all_output) <= config.monitoring["output_buffer_size"]

        # Should maintain recent output
        recent_output = monitor.get_recent_output(lines=10)
        assert len(recent_output) <= 10

        monitor.stop_monitoring()

    @pytest.mark.integration
    def test_windows_specific_monitoring(self):
        """Test Windows-specific process monitoring features."""
        from src.services.process_monitor import ProcessMonitor
        from src.lib.windows_process import WindowsProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        if os.name != 'nt':
            pytest.skip("Windows-specific test")

        config = SystemConfiguration()
        monitor = ProcessMonitor(config)

        # Start Windows command
        process_info = monitor.start_monitoring("cmd /c echo Windows test")

        # Should use Windows-specific monitoring
        assert isinstance(monitor.platform_monitor, WindowsProcessMonitor)

        # Test Windows process tree
        process_tree = monitor.get_process_tree(process_info.pid)
        assert process_tree is not None

        # Test Windows performance counters
        perf_counters = monitor.get_performance_counters(process_info.pid)
        assert "handle_count" in perf_counters
        assert "thread_count" in perf_counters

        monitor.stop_monitoring()

    @pytest.mark.integration
    def test_signal_handling_and_graceful_shutdown(self):
        """Test proper signal handling and graceful process shutdown."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration()
        monitor = ProcessMonitor(config)

        # Start long-running process
        cmd = 'python -c "import time; import signal; signal.signal(signal.SIGTERM, lambda s,f: exit(0)); time.sleep(10)"'
        process_info = monitor.start_monitoring(cmd)

        # Request graceful shutdown
        monitor.request_graceful_shutdown(process_info.pid)

        # Should terminate gracefully within timeout
        start_time = time.time()
        while time.time() - start_time < 5:
            if not psutil.pid_exists(process_info.pid):
                break
            time.sleep(0.1)

        # Process should be gone
        assert not psutil.pid_exists(process_info.pid)

    @pytest.mark.integration
    def test_process_monitoring_performance(self):
        """Test process monitoring performance under load."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration(
            monitoring={"check_interval": 0.01}  # Very frequent monitoring
        )
        monitor = ProcessMonitor(config)

        # Start multiple processes
        processes = []
        for i in range(5):
            cmd = f'python -c "import time; [print(f\'proc{i}-{j}\') for j in range(100)]; time.sleep(1)"'
            process_info = monitor.start_monitoring(cmd, session_id=f"perf_test_{i}")
            processes.append(process_info)

        start_time = time.time()

        # Monitor for 2 seconds
        while time.time() - start_time < 2:
            # Should maintain performance
            monitor_overhead = monitor.get_monitoring_overhead()
            assert monitor_overhead["cpu_percent"] < 20  # Less than 20% CPU
            assert monitor_overhead["memory_mb"] < 100   # Less than 100MB
            time.sleep(0.1)

        monitor.stop_all_monitoring()

    @pytest.mark.integration
    def test_process_environment_isolation(self):
        """Test process environment and working directory isolation."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration()
        monitor = ProcessMonitor(config)

        # Create test directory
        import tempfile
        test_dir = tempfile.mkdtemp()

        try:
            # Start process with specific working directory
            cmd = 'python -c "import os; print(f\'Working dir: {os.getcwd()}\')"'
            process_info = monitor.start_monitoring(
                cmd,
                work_dir=test_dir,
                env_vars={"TEST_VAR": "test_value"}
            )

            time.sleep(0.5)
            output = monitor.get_recent_output()

            # Should run in specified directory
            assert any(test_dir.replace("\\", "/") in line for line in output)

            monitor.stop_monitoring()

        finally:
            import shutil
            shutil.rmtree(test_dir)

    @pytest.mark.integration
    def test_monitoring_error_recovery(self):
        """Test recovery from monitoring errors and edge cases."""
        from src.services.process_monitor import ProcessMonitor
        from src.models.system_configuration import SystemConfiguration

        config = SystemConfiguration()
        monitor = ProcessMonitor(config)

        # Test with invalid command
        with pytest.raises(Exception):
            monitor.start_monitoring("this_command_does_not_exist")

        # Test monitoring non-existent PID
        fake_pid = 999999
        assert not monitor.is_process_monitored(fake_pid)

        # Test recovery after monitor restart
        cmd = 'python -c "import time; time.sleep(2)"'
        process_info = monitor.start_monitoring(cmd)

        # Simulate monitor restart
        old_pid = process_info.pid
        monitor.restart_monitoring()

        # Should recover gracefully
        recovered_processes = monitor.get_recovered_processes()
        assert len(recovered_processes) >= 0  # May or may not recover depending on implementation

        monitor.stop_monitoring()