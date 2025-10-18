"""PatternDetector service for Claude Code limit message detection.

Handles real-time detection of usage limit messages from Claude Code output
using configurable regex patterns with confidence scoring and context capture.
"""
import re
import time
from datetime import datetime
from typing import List, Dict, Optional, Pattern, Any
from dataclasses import dataclass
from collections import deque
import threading

from ..models.system_configuration import SystemConfiguration
from ..models.limit_detection_event import LimitDetectionEvent


@dataclass
class DetectionResult:
    """Result of pattern detection."""
    matched: bool
    pattern: Optional[str] = None
    matched_text: Optional[str] = None
    confidence: float = 0.0
    line_number: Optional[int] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None


class PatternDetector:
    """Service for detecting Claude Code usage limit patterns."""

    def __init__(self, config: SystemConfiguration):
        """Initialize the pattern detector."""
        self.config = config
        self.detection_patterns = config.detection_patterns.copy()
        self.case_sensitive = config.is_pattern_case_sensitive()
        self.detection_timeout = config.get_detection_timeout()

        # Compile patterns for performance
        self.compiled_patterns: List[Pattern] = []
        self._compile_patterns()

        # Output buffer for context
        self.output_buffer: deque = deque(maxlen=100)
        self.line_number = 0

        # Detection history
        self.detection_history: List[LimitDetectionEvent] = []
        self.last_detection_time: Optional[datetime] = None

        # Performance tracking
        self.detection_count = 0
        self.total_processing_time = 0.0

        # Thread safety
        self._lock = threading.RLock()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        self.compiled_patterns.clear()
        flags = 0 if self.case_sensitive else re.IGNORECASE

        for pattern in self.detection_patterns:
            try:
                compiled = re.compile(pattern, flags)
                self.compiled_patterns.append(compiled)
            except re.error as e:
                # Log error but continue with other patterns
                print(f"Warning: Invalid regex pattern '{pattern}': {e}")

    def detect_limit_message(self, text: str) -> Optional[LimitDetectionEvent]:
        """
        Detect usage limit messages in text.

        Args:
            text: Text to analyze for limit patterns

        Returns:
            LimitDetectionEvent if limit detected, None otherwise
        """
        start_time = time.time()

        try:
            with self._lock:
                # Add to buffer for context
                lines = text.split('\n')
                for line in lines:
                    self.line_number += 1
                    self.output_buffer.append((self.line_number, line.strip()))

                # Check each line for patterns
                for line_num, line in [(self.line_number, lines[-1])] if lines else []:
                    result = self._check_line_for_patterns(line, line_num)
                    if result.matched:
                        event = self._create_detection_event(result)
                        self.detection_history.append(event)
                        self.detection_count += 1
                        self.last_detection_time = datetime.now()
                        return event

                return None

        finally:
            # Track performance
            processing_time = time.time() - start_time
            self.total_processing_time += processing_time

    def _check_line_for_patterns(self, line: str, line_number: int) -> DetectionResult:
        """Check a single line against all patterns.

        Performance optimizations:
        - Early return on empty lines
        - Skip system messages before pattern matching
        - Early exit when high-confidence match found (>0.9)
        - Patterns ordered by priority (earlier = more specific)
        """
        if not line.strip():
            return DetectionResult(matched=False)

        # Skip if this looks like a system/debug message
        if self._is_system_message(line):
            return DetectionResult(matched=False)

        best_match = DetectionResult(matched=False)
        best_confidence = 0.0
        confidence_threshold = self.config.monitoring.get("confidence_threshold", 0.5)

        for i, pattern in enumerate(self.compiled_patterns):
            match = pattern.search(line)
            if match:
                confidence = self._calculate_confidence(
                    pattern.pattern,
                    match.group(),
                    line,
                    i
                )

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = DetectionResult(
                        matched=True,
                        pattern=pattern.pattern,
                        matched_text=match.group(),
                        confidence=confidence,
                        line_number=line_number,
                        context_before=self._get_context_before(line_number),
                        context_after=self._get_context_after(line_number)
                    )

                    # Early exit optimization: if very high confidence, no need to check more
                    if confidence > 0.9:
                        return best_match

        # Only return matches above confidence threshold
        if best_match.matched and best_match.confidence >= confidence_threshold:
            return best_match

        return DetectionResult(matched=False)

    def _calculate_confidence(self, pattern: str, matched_text: str, full_line: str, pattern_index: int) -> float:
        """Calculate confidence score for a pattern match."""
        confidence = 0.5  # Base confidence

        # Pattern specificity bonus
        if len(pattern) > 20:
            confidence += 0.2
        elif len(pattern) > 10:
            confidence += 0.1

        # Keyword presence bonus
        limit_keywords = ["limit", "exceeded", "wait", "hours", "quota", "rate"]
        keyword_count = sum(1 for keyword in limit_keywords if keyword.lower() in full_line.lower())
        confidence += min(0.3, keyword_count * 0.1)

        # Time-related patterns bonus
        time_patterns = [r"\d+\s*hours?", r"\d+:\d+:\d+", r"\d+\s*minutes?"]
        for time_pattern in time_patterns:
            if re.search(time_pattern, full_line, re.IGNORECASE):
                confidence += 0.1
                break

        # Number presence bonus (often indicates specific limits)
        if re.search(r'\b\d+\b', matched_text):
            confidence += 0.1

        # Pattern order bonus (earlier patterns are more specific)
        pattern_bonus = max(0, (len(self.compiled_patterns) - pattern_index) * 0.05)
        confidence += pattern_bonus

        # Error/warning context bonus
        error_indicators = ["error", "warning", "alert", "failed", "denied"]
        if any(indicator in full_line.lower() for indicator in error_indicators):
            confidence += 0.1

        # Length penalty for very short matches
        if len(matched_text) < 5:
            confidence -= 0.1

        return min(1.0, max(0.0, confidence))

    def _is_system_message(self, line: str) -> bool:
        """Check if line is a system message that should be ignored."""
        system_indicators = [
            "[DEBUG]", "[INFO]", "[WARN]", "[ERROR]", "[TRACE]",
            "claude-code:", "system:", "debug:", "log:",
            "timestamp:", "process id:", "thread:", "memory:",
            "loading", "initializing", "connecting"
        ]

        line_lower = line.lower().strip()
        return any(indicator.lower() in line_lower for indicator in system_indicators)

    def _get_context_before(self, line_number: int, lines: int = 3) -> str:
        """Get context lines before the matched line."""
        context_lines = []
        for stored_line_num, stored_line in reversed(list(self.output_buffer)):
            if stored_line_num < line_number and len(context_lines) < lines:
                context_lines.append(stored_line)

        return '\n'.join(reversed(context_lines))

    def _get_context_after(self, line_number: int, lines: int = 3) -> str:
        """Get context lines after the matched line."""
        context_lines = []
        for stored_line_num, stored_line in self.output_buffer:
            if stored_line_num > line_number and len(context_lines) < lines:
                context_lines.append(stored_line)

        return '\n'.join(context_lines)

    def _create_detection_event(self, result: DetectionResult) -> LimitDetectionEvent:
        """Create a LimitDetectionEvent from detection result."""
        return LimitDetectionEvent(
            detection_time=datetime.now(),
            matched_pattern=result.pattern,
            matched_text=result.matched_text,
            session_id="",  # Will be set by calling service
            line_number=result.line_number,
            confidence=result.confidence,
            context_before=result.context_before,
            context_after=result.context_after
        )

    def process_chunk(self, chunk: str) -> Optional[LimitDetectionEvent]:
        """
        Process a chunk of streaming output.

        Args:
            chunk: Text chunk from streaming output

        Returns:
            LimitDetectionEvent if limit detected in chunk
        """
        # For streaming, we need to handle partial lines
        if not hasattr(self, '_partial_line'):
            self._partial_line = ""

        self._partial_line += chunk

        # Process complete lines
        while '\n' in self._partial_line:
            line, self._partial_line = self._partial_line.split('\n', 1)
            detection = self.detect_limit_message(line)
            if detection:
                return detection

        # Check if partial line might contain a pattern (for immediate detection)
        if len(self._partial_line) > 20:  # Only check substantial partial lines
            temp_detection = self.detect_limit_message(self._partial_line)
            if temp_detection and temp_detection.confidence > 0.8:  # High confidence only
                self._partial_line = ""  # Clear to avoid duplicate detection
                return temp_detection

        return None

    def update_patterns(self, new_patterns: List[str]) -> None:
        """
        Update detection patterns during runtime.

        Args:
            new_patterns: New list of regex patterns
        """
        with self._lock:
            self.detection_patterns = new_patterns.copy()
            self._compile_patterns()

    def add_pattern(self, pattern: str) -> bool:
        """
        Add a new detection pattern.

        Args:
            pattern: Regex pattern to add

        Returns:
            True if pattern was added successfully
        """
        try:
            re.compile(pattern, 0 if self.case_sensitive else re.IGNORECASE)
            with self._lock:
                if pattern not in self.detection_patterns:
                    self.detection_patterns.append(pattern)
                    self._compile_patterns()
                    return True
            return False
        except re.error:
            return False

    def remove_pattern(self, pattern: str) -> bool:
        """
        Remove a detection pattern.

        Args:
            pattern: Pattern to remove

        Returns:
            True if pattern was removed
        """
        with self._lock:
            if pattern in self.detection_patterns:
                self.detection_patterns.remove(pattern)
                self._compile_patterns()
                return True
            return False

    def get_detection_history(self, limit: Optional[int] = None) -> List[LimitDetectionEvent]:
        """
        Get detection history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent detection events
        """
        with self._lock:
            if limit is None:
                return self.detection_history.copy()
            return self.detection_history[-limit:] if limit > 0 else []

    def clear_history(self) -> None:
        """Clear detection history."""
        with self._lock:
            self.detection_history.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Get detection statistics."""
        with self._lock:
            avg_processing_time = (
                self.total_processing_time / max(1, self.detection_count)
                if self.detection_count > 0 else 0.0
            )

            return {
                "total_detections": len(self.detection_history),
                "patterns_count": len(self.detection_patterns),
                "lines_processed": self.line_number,
                "average_processing_time_ms": avg_processing_time * 1000,
                "last_detection": self.last_detection_time.isoformat() if self.last_detection_time else None,
                "buffer_size": len(self.output_buffer),
                "detection_rate": len(self.detection_history) / max(1, self.line_number)
            }

    def test_pattern(self, pattern: str, test_text: str) -> DetectionResult:
        """
        Test a pattern against sample text.

        Args:
            pattern: Regex pattern to test
            test_text: Sample text to test against

        Returns:
            DetectionResult with match information
        """
        try:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            compiled_pattern = re.compile(pattern, flags)
            match = compiled_pattern.search(test_text)

            if match:
                confidence = self._calculate_confidence(pattern, match.group(), test_text, 0)
                return DetectionResult(
                    matched=True,
                    pattern=pattern,
                    matched_text=match.group(),
                    confidence=confidence,
                    line_number=1
                )
            else:
                return DetectionResult(matched=False)

        except re.error as e:
            return DetectionResult(matched=False)

    def __str__(self) -> str:
        """String representation of the detector."""
        return (
            f"PatternDetector("
            f"patterns={len(self.detection_patterns)}, "
            f"detections={len(self.detection_history)}, "
            f"lines_processed={self.line_number}"
            f")"
        )
