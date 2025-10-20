"""Integration test for limit detection patterns.

This test validates the pattern detection engine and its ability to
accurately identify Claude Code usage limits from terminal output.

This test MUST FAIL initially before implementation.
"""

import re
import time
from unittest.mock import Mock, patch

import pytest


class TestLimitDetectionPatterns:
    """Integration test for Claude Code limit detection."""

    def setup_method(self):
        """Set up test environment."""
        self.test_patterns = [
            "usage limit exceeded",
            "5-hour limit reached",
            "please wait",
            r"rate limit.*5\s*hours?",
            "quota exceeded",
        ]

    @pytest.mark.integration
    def test_default_pattern_detection(self):
        """Test detection with default patterns."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        config = SystemConfiguration()
        detector = PatternDetector(config)

        # Test default patterns from configuration
        test_outputs = [
            "Error: Usage limit exceeded. Please wait 5 hours.",
            "Rate limit reached - please wait 5 hours before continuing",
            "You have exceeded your 5-hour usage limit",
            "Please wait 5 hours before using Claude Code again",
        ]

        for output in test_outputs:
            detection = detector.detect_limit_message(output)
            assert detection is not None
            assert detection.matched_text in output
            assert detection.matched_pattern is not None

    @pytest.mark.integration
    def test_custom_pattern_detection(self):
        """Test detection with custom user patterns."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        config = SystemConfiguration(detection_patterns=self.test_patterns)
        detector = PatternDetector(config)

        # Test each custom pattern
        test_cases = [
            ("Your usage limit exceeded for today", "usage limit exceeded"),
            ("5-hour limit reached, comeback later", "5-hour limit reached"),
            ("Please wait before making more requests", "please wait"),
            ("Rate limit active for 5 hours", r"rate limit.*5\s*hours?"),
            ("Quota exceeded - try again later", "quota exceeded"),
        ]

        for output, expected_pattern in test_cases:
            detection = detector.detect_limit_message(output)
            assert detection is not None
            assert detection.matched_text in output

    @pytest.mark.integration
    def test_regex_pattern_detection(self):
        """Test detection with complex regex patterns."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        regex_patterns = [
            r"limit.*(\d+)\s*hours?",
            r"wait.*(\d+):\d+:\d+",  # Wait HH:MM:SS format
            r"exceeded.*limit.*(\d+)",
            r"rate.*limit.*(\d+)",
            r"quota.*(\d+).*exceeded",
        ]

        config = SystemConfiguration(detection_patterns=regex_patterns)
        detector = PatternDetector(config)

        test_outputs = [
            "Usage limit for 5 hours has been reached",
            "Please wait 04:59:30 before continuing",
            "You have exceeded limit 100 for today",
            "Rate limit 50 requests exceeded",
            "Quota 1000 tokens exceeded",
        ]

        for output in test_outputs:
            detection = detector.detect_limit_message(output)
            assert detection is not None
            assert detection.matched_text in output

    @pytest.mark.integration
    def test_case_insensitive_detection(self):
        """Test case-insensitive pattern detection."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        config = SystemConfiguration(
            detection_patterns=["USAGE LIMIT", "Rate Limit", "please WAIT"]
        )
        detector = PatternDetector(config)

        test_cases = [
            "usage limit exceeded",  # lowercase
            "USAGE LIMIT EXCEEDED",  # uppercase
            "Usage Limit Exceeded",  # mixed case
            "rate limit reached",
            "RATE LIMIT REACHED",
            "please wait 5 hours",
            "PLEASE WAIT 5 HOURS",
        ]

        for output in test_cases:
            detection = detector.detect_limit_message(output)
            assert detection is not None, f"Failed to detect: {output}"

    @pytest.mark.integration
    def test_multiline_pattern_detection(self):
        """Test detection across multiple lines of output."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        config = SystemConfiguration(detection_patterns=["usage.*limit", "wait.*hours"])
        detector = PatternDetector(config)

        multiline_output = """
        Error: Your usage limit has been
        exceeded. Please wait 5 hours
        before continuing with Claude Code.
        """

        detection = detector.detect_limit_message(multiline_output)
        assert detection is not None

    @pytest.mark.integration
    def test_false_positive_prevention(self):
        """Test that detector avoids false positives."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        config = SystemConfiguration(
            detection_patterns=["usage limit", "5 hours", "wait"]
        )
        detector = PatternDetector(config)

        # These should NOT trigger detection
        false_positives = [
            "The usage limit for this feature is 100 requests",  # Describing limit, not hitting it
            "I will wait 5 hours for the meeting",  # User talking about waiting
            "Usage limit configuration updated",  # System message about config
            "Please wait while loading...",  # Generic loading message
            "5 hours ago I started this task",  # Time reference
        ]

        for output in false_positives:
            detection = detector.detect_limit_message(output)
            # May detect but should have low confidence or be filtered out
            if detection:
                assert detection.confidence < 0.8 or not detection.is_limit_hit

    @pytest.mark.integration
    def test_detection_performance(self):
        """Test pattern detection performance requirements."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        # Large pattern set
        patterns = [f"pattern_{i}" for i in range(100)]
        config = SystemConfiguration(detection_patterns=patterns)
        detector = PatternDetector(config)

        # Large text input
        large_text = "x" * 10000 + "usage limit exceeded" + "y" * 10000

        # Should detect within performance requirements (< 100ms)
        start_time = time.time()
        detection = detector.detect_limit_message(large_text)
        detection_time = time.time() - start_time

        assert detection is not None
        assert (
            detection_time < 0.1
        ), f"Detection took {detection_time}s, should be < 0.1s"

    @pytest.mark.integration
    def test_streaming_detection(self):
        """Test real-time detection from streaming output."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        config = SystemConfiguration(detection_patterns=["usage limit"])
        detector = PatternDetector(config)

        # Simulate streaming chunks
        chunks = [
            "Starting Claude Code...\n",
            "Processing request...\n",
            "Error: Your usage",
            " limit has been exceeded.\n",
            "Please wait 5 hours.\n",
        ]

        detections = []
        for chunk in chunks:
            detection = detector.process_chunk(chunk)
            if detection:
                detections.append(detection)

        # Should detect when complete pattern is formed
        assert len(detections) > 0
        assert any("usage limit" in d.matched_text.lower() for d in detections)

    @pytest.mark.integration
    def test_pattern_priority_and_specificity(self):
        """Test pattern matching priority and specificity."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        # More specific patterns should take priority
        patterns = [
            "limit",  # Generic
            "usage limit",  # More specific
            "usage limit exceeded",  # Most specific
            "5-hour usage limit exceeded",  # Very specific
        ]

        config = SystemConfiguration(detection_patterns=patterns)
        detector = PatternDetector(config)

        test_text = "Error: 5-hour usage limit exceeded"

        detection = detector.detect_limit_message(test_text)
        assert detection is not None

        # Should match the most specific pattern
        assert "5-hour usage limit exceeded" in detection.matched_text.lower()

    @pytest.mark.integration
    def test_detection_with_noise(self):
        """Test detection in noisy output with lots of irrelevant text."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        config = SystemConfiguration(detection_patterns=["usage limit exceeded"])
        detector = PatternDetector(config)

        noisy_output = """
        [DEBUG] 2025-09-18 10:00:01 - Loading configuration
        [INFO] 2025-09-18 10:00:02 - Starting Claude Code session
        [DEBUG] 2025-09-18 10:00:03 - Processing user input
        [INFO] 2025-09-18 10:00:04 - Generating response
        [ERROR] 2025-09-18 10:00:05 - Usage limit exceeded - please wait 5 hours
        [DEBUG] 2025-09-18 10:00:06 - Cleaning up resources
        [INFO] 2025-09-18 10:00:07 - Session ended
        """

        detection = detector.detect_limit_message(noisy_output)
        assert detection is not None
        assert "usage limit exceeded" in detection.matched_text.lower()

    @pytest.mark.integration
    def test_detection_state_management(self):
        """Test detection state management across multiple messages."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        config = SystemConfiguration(detection_patterns=["usage limit"])
        detector = PatternDetector(config)

        # First detection
        detection1 = detector.detect_limit_message("Usage limit exceeded")
        assert detection1 is not None

        # Second detection of same pattern (should not duplicate)
        detection2 = detector.detect_limit_message("Usage limit exceeded again")
        assert detection2 is not None

        # Should track detection history
        history = detector.get_detection_history()
        assert len(history) >= 2

    @pytest.mark.integration
    def test_pattern_configuration_reload(self):
        """Test reloading detection patterns during runtime."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        # Initial patterns
        config = SystemConfiguration(detection_patterns=["old pattern"])
        detector = PatternDetector(config)

        # Should not detect new pattern initially
        detection = detector.detect_limit_message("new pattern detected")
        assert detection is None

        # Update patterns
        new_config = SystemConfiguration(
            detection_patterns=["old pattern", "new pattern"]
        )
        detector.update_patterns(new_config.detection_patterns)

        # Should now detect new pattern
        detection = detector.detect_limit_message("new pattern detected")
        assert detection is not None

    @pytest.mark.integration
    def test_unicode_and_encoding_handling(self):
        """Test detection with unicode characters and different encodings."""
        from src.models.system_configuration import SystemConfiguration
        from src.services.pattern_detector import PatternDetector

        config = SystemConfiguration(
            detection_patterns=["사용 제한", "使用限制", "límite de uso"]
        )
        detector = PatternDetector(config)

        unicode_tests = [
            "오류: 사용 제한에 도달했습니다",  # Korean
            "错误：使用限制已达到",  # Chinese
            "Error: límite de uso alcanzado",  # Spanish
        ]

        for test_text in unicode_tests:
            detection = detector.detect_limit_message(test_text)
            assert detection is not None
