"""Tests for SystemConfiguration utilities."""

from __future__ import annotations

import json
from pathlib import Path

from src.models.system_configuration import SystemConfiguration


def test_create_default_configuration(tmp_path):
    config = SystemConfiguration.create_default()
    assert config.log_level.value == "INFO"
    assert config.monitoring["allow_process_simulation"] is True

    # Save and reload via to_file/from_file
    config_path = Path(tmp_path) / "config.json"
    config.to_file(str(config_path))

    loaded = SystemConfiguration.from_file(str(config_path))
    assert loaded.log_level == config.log_level
    assert loaded.monitoring["allow_process_simulation"] is True


def test_from_file_merges_defaults(tmp_path):
    custom = {
        "log_level": "DEBUG",
        "monitoring": {"check_interval": 2.0},
        "detection_patterns": ["custom pattern"],
    }
    config_path = Path(tmp_path) / "custom.json"
    config_path.write_text(json.dumps(custom))

    merged = SystemConfiguration.from_file(str(config_path))
    assert merged.log_level.value == "DEBUG"
    assert merged.monitoring["task_timeout"] == 300  # default retained
    assert "custom pattern" in merged.detection_patterns
