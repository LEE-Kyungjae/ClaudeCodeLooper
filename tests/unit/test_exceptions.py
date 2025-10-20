"""Unit tests for custom exceptions."""

import pytest

from src.exceptions import (
    ConfigurationException,
    DetectionException,
    MonitoringException,
    ProcessException,
    ProcessStartError,
    with_context,
)


class TestMonitoringException:
    """Test base MonitoringException class."""

    def test_exception_with_message_only(self):
        """Test exception creation with message only."""
        exc = MonitoringException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.details is None

    def test_exception_with_details(self):
        """Test exception creation with details."""
        details = {"key": "value", "count": 42}
        exc = MonitoringException("Test error", details=details)
        assert exc.message == "Test error"
        assert exc.details == details
        assert "Details:" in str(exc)
        assert "key" in str(exc)

    def test_exception_inheritance(self):
        """Test exception can be caught as base Exception."""
        exc = MonitoringException("Test")
        assert isinstance(exc, Exception)


class TestProcessExceptions:
    """Test process-related exceptions."""

    def test_process_exception_hierarchy(self):
        """Test ProcessException inherits from MonitoringException."""
        exc = ProcessException("Process error")
        assert isinstance(exc, MonitoringException)
        assert isinstance(exc, Exception)

    def test_process_start_error(self):
        """Test ProcessStartError with context."""
        exc = ProcessStartError(
            "Failed to start", details={"command": "claude", "exit_code": 1}
        )
        assert exc.message == "Failed to start"
        assert exc.details["command"] == "claude"
        assert exc.details["exit_code"] == 1


class TestExceptionContext:
    """Test exception context enhancement."""

    def test_with_context_adds_details(self):
        """Test with_context adds context to MonitoringException."""
        exc = MonitoringException("Error")
        enhanced = with_context(exc, {"session_id": "sess_123", "pid": 456})

        assert enhanced.details["session_id"] == "sess_123"
        assert enhanced.details["pid"] == 456

    def test_with_context_merges_existing_details(self):
        """Test with_context merges with existing details."""
        exc = MonitoringException("Error", details={"original": "value"})
        enhanced = with_context(exc, {"added": "new_value"})

        assert enhanced.details["original"] == "value"
        assert enhanced.details["added"] == "new_value"

    def test_with_context_on_standard_exception(self):
        """Test with_context on non-MonitoringException returns unchanged."""
        exc = ValueError("Standard error")
        result = with_context(exc, {"key": "value"})

        # Should return the same exception without modification
        assert result is exc
        assert not hasattr(result, "details")


class TestDetectionException:
    """Test detection-related exceptions."""

    def test_detection_exception_inheritance(self):
        """Test DetectionException inherits correctly."""
        exc = DetectionException("Detection failed")
        assert isinstance(exc, MonitoringException)


class TestConfigurationException:
    """Test configuration-related exceptions."""

    def test_configuration_exception(self):
        """Test ConfigurationException with details."""
        exc = ConfigurationException(
            "Invalid config", details={"file": "config.json", "line": 42}
        )
        assert "Invalid config" in str(exc)
        assert exc.details["file"] == "config.json"
