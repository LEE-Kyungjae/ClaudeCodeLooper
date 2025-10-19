"""Custom exceptions for Claude Code Restart Monitor.

Provides a hierarchical exception structure for different error domains,
enabling precise error handling and clear error messaging.
"""

from typing import Optional, Any


class MonitoringException(Exception):
    """Base exception for all monitoring-related errors."""

    def __init__(self, message: str, details: Optional[Any] = None):
        """Initialize with message and optional details."""
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        """String representation with details if available."""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ProcessException(MonitoringException):
    """Exceptions related to process management and monitoring."""

    pass


class ProcessStartError(ProcessException):
    """Failed to start a monitored process."""

    pass


class ProcessStopError(ProcessException):
    """Failed to stop a monitored process."""

    pass


class ProcessNotFoundError(ProcessException):
    """Referenced process does not exist or is not monitored."""

    pass


class ProcessHealthError(ProcessException):
    """Process health check failed or process is unhealthy."""

    pass


class DetectionException(MonitoringException):
    """Exceptions related to pattern detection."""

    pass


class PatternCompilationError(DetectionException):
    """Failed to compile regex pattern."""

    pass


class DetectionTimeoutError(DetectionException):
    """Pattern detection exceeded timeout."""

    pass


class ConfigurationException(MonitoringException):
    """Exceptions related to configuration management."""

    pass


class InvalidConfigError(ConfigurationException):
    """Configuration file is invalid or malformed."""

    pass


class MissingConfigError(ConfigurationException):
    """Required configuration setting is missing."""

    pass


class ConfigValidationError(ConfigurationException):
    """Configuration validation failed."""

    pass


class StateException(MonitoringException):
    """Exceptions related to state management."""

    pass


class StateLoadError(StateException):
    """Failed to load persisted state."""

    pass


class StateSaveError(StateException):
    """Failed to save state to persistence."""

    pass


class StateCorruptionError(StateException):
    """Persisted state is corrupted or invalid."""

    pass


class TimingException(MonitoringException):
    """Exceptions related to timing and scheduling."""

    pass


class WaitingPeriodError(TimingException):
    """Error during waiting period management."""

    pass


class SchedulingError(TimingException):
    """Failed to schedule or execute timed operation."""

    pass


class RestartException(MonitoringException):
    """Exceptions related to restart operations."""

    pass


class RestartFailedError(RestartException):
    """Restart operation failed."""

    pass


class RestartTimeoutError(RestartException):
    """Restart operation exceeded timeout."""

    pass


class TaskException(MonitoringException):
    """Exceptions related to task completion monitoring."""

    pass


class TaskTimeoutError(TaskException):
    """Task completion monitoring timed out."""

    pass


class TaskValidationError(TaskException):
    """Task validation or pattern matching failed."""

    pass


# Error severity levels
class CriticalError(MonitoringException):
    """Critical error requiring immediate attention."""

    pass


class RecoverableError(MonitoringException):
    """Error that can be recovered from automatically."""

    pass


# Utility function for error context
def with_context(exception: Exception, context: dict) -> Exception:
    """Add context information to an exception.

    Args:
        exception: The exception to enhance
        context: Dictionary of contextual information

    Returns:
        The same exception with added context
    """
    if isinstance(exception, MonitoringException):
        exception.details = {**(exception.details or {}), **context}
    return exception
