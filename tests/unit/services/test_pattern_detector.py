"""Unit tests for PatternDetector service."""
import pytest
import re
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.services.pattern_detector import PatternDetector, DetectionResult
from src.models.system_configuration import SystemConfiguration


class TestPatternDetectorInitialization:
    """Test PatternDetector initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        config = SystemConfiguration()
        detector = PatternDetector(config)

        assert detector.config == config
        assert isinstance(detector.detection_patterns, list)
        assert len(detector.compiled_patterns) >= 0
        assert detector.line_number == 0
        assert detector.detection_count == 0

    def test_patterns_are_compiled(self):
        """Test that patterns are compiled on initialization."""
        config = SystemConfiguration()
        config.detection_patterns = [r"test.*pattern", r"another\s+pattern"]

        detector = PatternDetector(config)

        assert len(detector.compiled_patterns) == 2
        for pattern in detector.compiled_patterns:
            assert isinstance(pattern, re.Pattern)


class TestPatternMatching:
    """Test pattern matching functionality."""

    def test_simple_pattern_match(self):
        """Test detection of simple pattern."""
        config = SystemConfiguration()
        config.detection_patterns = [r"usage limit exceeded"]

        detector = PatternDetector(config)
        event = detector.detect_limit_message("Error: usage limit exceeded - please wait")

        assert event is not None
        assert event.matched_text is not None
        assert "usage limit exceeded" in event.matched_text.lower()

    def test_no_match_returns_none(self):
        """Test that non-matching text returns None."""
        config = SystemConfiguration()
        config.detection_patterns = [r"usage limit exceeded"]

        detector = PatternDetector(config)
        event = detector.detect_limit_message("Normal operation message")

        assert event is None

    def test_case_insensitive_matching(self):
        """Test case-insensitive pattern matching."""
        config = SystemConfiguration()
        config.detection_patterns = [r"limit exceeded"]
        # Assume case_sensitive is False by default

        detector = PatternDetector(config)
        detector.case_sensitive = False
        detector._compile_patterns()

        event = detector.detect_limit_message("LIMIT EXCEEDED warning")
        assert event is not None


class TestSystemMessageFiltering:
    """Test system message filtering."""

    def test_system_message_is_skipped(self):
        """Test that system/debug messages are skipped."""
        config = SystemConfiguration()
        config.detection_patterns = [r".*"]  # Match everything

        detector = PatternDetector(config)
        event = detector.detect_limit_message("[DEBUG] System initialization")

        assert event is None

    def test_normal_message_is_processed(self):
        """Test that normal messages are processed."""
        config = SystemConfiguration()
        config.detection_patterns = [r"limit"]

        detector = PatternDetector(config)
        event = detector.detect_limit_message("User limit reached")

        assert event is not None


class TestConfidenceCalculation:
    """Test confidence score calculation."""

    def test_confidence_increases_with_keywords(self):
        """Test confidence increases with limit-related keywords."""
        config = SystemConfiguration()
        detector = PatternDetector(config)

        # Message with many keywords should have higher confidence
        confidence_high = detector._calculate_confidence(
            r"limit.*exceeded",
            "limit exceeded",
            "usage limit exceeded - wait 5 hours",
            0
        )

        confidence_low = detector._calculate_confidence(
            r"test",
            "test",
            "simple test message",
            0
        )

        assert confidence_high > confidence_low

    def test_confidence_bounded_to_one(self):
        """Test confidence score is capped at 1.0."""
        config = SystemConfiguration()
        detector = PatternDetector(config)

        confidence = detector._calculate_confidence(
            r"very.*long.*specific.*pattern",
            "very long specific pattern with limit exceeded wait hours quota",
            "very long specific pattern with limit exceeded wait hours quota rate",
            0
        )

        assert confidence <= 1.0


class TestPatternManagement:
    """Test pattern addition and removal."""

    def test_add_valid_pattern(self):
        """Test adding a valid regex pattern."""
        config = SystemConfiguration()
        detector = PatternDetector(config)

        initial_count = len(detector.detection_patterns)
        success = detector.add_pattern(r"new.*pattern")

        assert success is True
        assert len(detector.detection_patterns) == initial_count + 1
        assert r"new.*pattern" in detector.detection_patterns

    def test_add_invalid_pattern(self):
        """Test adding an invalid regex pattern fails."""
        config = SystemConfiguration()
        detector = PatternDetector(config)

        success = detector.add_pattern(r"invalid[pattern")  # Unclosed bracket

        assert success is False

    def test_remove_existing_pattern(self):
        """Test removing an existing pattern."""
        config = SystemConfiguration()
        config.detection_patterns = [r"test", r"pattern"]
        detector = PatternDetector(config)

        success = detector.remove_pattern(r"test")

        assert success is True
        assert r"test" not in detector.detection_patterns
        assert len(detector.detection_patterns) == 1

    def test_remove_nonexistent_pattern(self):
        """Test removing non-existent pattern returns False."""
        config = SystemConfiguration()
        detector = PatternDetector(config)

        success = detector.remove_pattern(r"nonexistent")

        assert success is False


class TestPerformanceOptimization:
    """Test performance optimization features."""

    def test_early_exit_on_high_confidence(self):
        """Test early exit when high confidence match found."""
        config = SystemConfiguration()
        config.detection_patterns = [
            r"usage limit exceeded wait \d+ hours",  # Very specific
            r"limit",  # Generic
        ]

        detector = PatternDetector(config)
        result = detector._check_line_for_patterns(
            "usage limit exceeded wait 5 hours",
            1
        )

        # Should match the first pattern with high confidence
        assert result.matched is True
        assert result.confidence > 0.8

    def test_empty_line_returns_immediately(self):
        """Test empty lines return immediately without processing."""
        config = SystemConfiguration()
        detector = PatternDetector(config)

        result = detector._check_line_for_patterns("", 1)

        assert result.matched is False


class TestDetectionStatistics:
    """Test detection statistics tracking."""

    def test_statistics_track_detections(self):
        """Test statistics correctly track detection count."""
        config = SystemConfiguration()
        config.detection_patterns = [r"limit"]
        detector = PatternDetector(config)

        detector.detect_limit_message("limit reached")
        detector.detect_limit_message("limit exceeded")

        stats = detector.get_statistics()

        assert stats["total_detections"] == 2
        assert stats["lines_processed"] > 0

    def test_statistics_include_processing_time(self):
        """Test statistics include average processing time."""
        config = SystemConfiguration()
        detector = PatternDetector(config)

        detector.detect_limit_message("test message")

        stats = detector.get_statistics()

        assert "average_processing_time_ms" in stats
        assert isinstance(stats["average_processing_time_ms"], float)
