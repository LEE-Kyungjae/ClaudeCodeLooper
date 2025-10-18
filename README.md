# ClaudeCodeLooper

<div align="center">

**Automated monitoring and restart system for Claude Code usage limits**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](#-cli-reference)

</div>

---

## 🎯 Overview

ClaudeCodeLooper automatically detects Claude Code's 5-hour usage limits, manages the cooldown period, and restarts your session seamlessly. Work for extended periods without interruption or manual intervention.

**Perfect for:**
- Long coding sessions
- CI/CD pipelines
- Automated workflows
- Production environments

---

## ✨ Features

- **🔍 Automatic Detection**: Real-time monitoring of Claude Code output for usage limit patterns
- **⏰ Precise Timing**: Accurate 5-hour countdown tracking with automatic restart
- **🔄 Background Operation**: Daemon mode for uninterrupted workflow
- **💬 Claude Code Integration**: Convenient slash commands (`/cl:on`, `/cl:off`, `/cl:status`, `/cl:logs`)
- **🛡️ Resilient**: Graceful shutdown and state persistence across system restarts
- **📊 Comprehensive Logging**: Structured JSON logging for complete event tracking
- **🔒 Secure**: Shell injection prevention, path traversal protection, input sanitization

---

## 📋 Requirements

- **Python**: 3.11 or higher
- **OS**: Windows, macOS, Linux (WSL supported)
- **Claude Code**: Must be installed and accessible

---

## 🚀 Installation

### Method 1: Direct from GitHub (Fastest ⚡)

```bash
# One-line installation
pip install git+https://github.com/LEE-Kyungjae/ClaudeCodeLooper.git

# Verify installation
claude-looper --version
```

### Method 2: Automated Installation Scripts

```bash
# Clone repository
git clone https://github.com/LEE-Kyungjae/ClaudeCodeLooper.git
cd ClaudeCodeLooper

# Run installer (macOS/Linux)
./install.sh

# Run installer (Windows)
install.bat
```

### Method 3: Development Installation

```bash
# Clone repository
git clone https://github.com/LEE-Kyungjae/ClaudeCodeLooper.git
cd ClaudeCodeLooper

# Install in development mode
pip install -e ".[dev]"

# Or standard installation
pip install -e .
```

---

## 🎯 Quick Start

### Basic Usage

```bash
# Start monitoring (daemon mode)
claude-looper start --claude-cmd "claude" --work-dir "$PWD" --daemon

# Check status
claude-looper status

# View logs
claude-looper logs --tail 50

# Stop monitoring
claude-looper stop --all
```

### Using Slash Commands in Claude Code

If you're using Claude Code, it's even simpler:

```
/cl:on        # Start monitoring
/cl:status    # Check status
/cl:logs      # View logs
/cl:off       # Stop monitoring
```

> 💡 **Tip**: Slash commands automatically format output with emoji indicators for better readability!

---

## 📖 Usage Scenarios

### Scenario 1: Extended Coding Session

```bash
# Start work in the morning
/cl:on

# [Work normally throughout the day]
# [System automatically detects when 5-hour limit is reached]
# [System waits for 5-hour cooldown period]
# [Claude Code automatically restarts]

# Finish work in the evening
/cl:off
```

### Scenario 2: CI/CD Pipeline Integration

```bash
# Use in automated workflow
claude-looper start \
  --claude-cmd "claude --no-interactive" \
  --work-dir "/path/to/project" \
  --daemon

# Run pipeline tasks
# ...

# Clean up after completion
claude-looper stop --all
```

### Scenario 3: Multi-Project Monitoring

```bash
# Monitor Project A
cd /path/to/project-a
claude-looper start --claude-cmd "claude" --daemon

# Monitor Project B
cd /path/to/project-b
claude-looper start --claude-cmd "claude" --daemon

# Check all session statuses
claude-looper status --verbose
```

---

## ⚙️ Configuration

### Configuration File Locations

- **Default Config**: `config/default.json`
- **User Config**: `.claude-restart-config.json` (create in project root)

### Configuration Example

Create `.claude-restart-config.json` to customize settings:

```json
{
  "detection": {
    "patterns": [
      "usage limit exceeded",
      "wait (\\d+) hours?"
    ],
    "confidence_threshold": 0.7
  },
  "timing": {
    "wait_hours": 5,
    "check_interval_seconds": 60
  },
  "restart": {
    "max_retries": 3,
    "retry_delay_seconds": 10
  },
  "logging": {
    "level": "INFO",
    "file": "logs/claude-restart-monitor.log"
  }
}
```

---

## 🔧 CLI Command Reference

### `start` - Start monitoring

```bash
claude-looper start [OPTIONS]

Options:
  --claude-cmd TEXT       Claude Code command to run [default: claude]
  --work-dir TEXT         Working directory [default: current directory]
  --daemon                Run in background daemon mode
  --config TEXT           Path to config file
  --session-id TEXT       Session ID (optional; auto-generated)
```

**Examples:**
```bash
# Start with defaults
claude-looper start

# Run as a daemon
claude-looper start --daemon

# Start with a custom config
claude-looper start --config /path/to/config.json --daemon
```

### `stop` - Stop monitoring

```bash
claude-looper stop [OPTIONS]

Options:
  --session-id TEXT       Stop a specific session
  --all                   Stop all sessions
  --force                 Force shutdown
```

**Examples:**
```bash
# Gracefully stop every session
claude-looper stop --all

# Stop a particular session
claude-looper stop --session-id sess_abc123

# Force termination
claude-looper stop --all --force
```

### `status` - Check current status

```bash
claude-looper status [OPTIONS]

Options:
  --verbose               Show detailed information
  --format [text|json]    Output format
  --session-id TEXT       Status of a specific session
```

**Examples:**
```bash
# Basic status
claude-looper status

# Detailed output
claude-looper status --verbose

# JSON output
claude-looper status --format json
```

### `logs` - View logs

```bash
claude-looper logs [OPTIONS]

Options:
  --tail INTEGER          Show the last N lines [default: 50]
  --follow                Stream logs in real time
  --filter TEXT           Filter logs (detection, error, warning)
  --session-id TEXT       Logs for a specific session
```

**Examples:**
```bash
# Last 50 lines
claude-looper logs

# Last 100 lines
claude-looper logs --tail 100

# Live stream
claude-looper logs --follow

# Only errors
claude-looper logs --filter error

# Detection events only
claude-looper logs --filter detection
```

### `config` - Manage configuration

```bash
claude-looper config [OPTIONS]

Options:
  --show                  Display the current configuration
  --set KEY VALUE         Change a configuration value
  --reset                 Reset to defaults
```

**Examples:**
```bash
# View configuration
claude-looper config --show

# Change wait time
claude-looper config --set timing.wait_hours 6

# Reset to defaults
claude-looper config --reset
```

### `queue` - Manage post-restart tasks

```bash
claude-looper queue [COMMAND]

Commands:
  add <text>        Add a task that runs after the next restart
  list              Show queued tasks in execution order
  remove <nums...>  Remove tasks by their list numbers
  clear             Clear the queue (use --confirm to skip prompt)
```

**Examples:**
```bash
# Add a follow-up task
claude-looper queue add "코드 점검"

# Inspect the queue
claude-looper queue list

# Remove tasks 1 and 3
claude-looper queue remove 1 3
```

---

## 🐛 Troubleshooting

### Monitoring won't start

```bash
# 1. Inspect logs
claude-looper logs --filter error

# 2. Check permissions
ls -la logs/

# 3. Confirm Python version
python --version  # Requires 3.11+

# 4. Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Automatic restart isn't working

```bash
# 1. Check detection patterns
claude-looper logs --filter detection

# 2. Verify configuration
claude-looper config --show

# 3. Inspect detailed status
claude-looper status --verbose
```

### Claude Code command not found

```bash
# 1. Confirm Claude Code is installed
which claude

# 2. Check PATH
echo $PATH

# 3. Use an absolute path
claude-looper start --claude-cmd "/full/path/to/claude"
```

### Log file is too large

```bash
# Clean up the log file
rm logs/claude-restart-monitor.log

# Or reduce the log level
claude-looper config --set logging.level WARNING
```

---

## 👨‍💻 Developer Guide

### Set up the development environment

```bash
# Clone repository
git clone https://github.com/LEE-Kyungjae/ClaudeCodeLooper.git
cd ClaudeCodeLooper

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint and type-check
black src/ tests/
flake8 src/ tests/
mypy src/
```

### Project structure

```
ClaudeCodeLooper/
├── src/
│   ├── cli/                 # CLI interface
│   │   ├── main.py
│   │   └── commands/        # Command implementations
│   ├── models/              # Data models (Pydantic)
│   ├── services/            # Core services
│   │   ├── process_monitor.py      # Process monitoring orchestrator
│   │   ├── process_launcher.py     # Process launch management
│   │   ├── output_capture.py       # Output capture
│   │   ├── health_checker.py       # Health monitoring
│   │   ├── pattern_detector.py     # Pattern detection
│   │   └── restart_controller.py   # Restart control
│   ├── utils/               # Utilities
│   │   └── logging.py       # Structured logging
│   └── exceptions.py        # Exception hierarchy
├── tests/
│   ├── contract/            # Contract tests
│   ├── integration/         # Integration tests
│   └── unit/                # Unit tests
├── config/
│   └── default.json         # Default configuration
├── .claude/
│   └── commands/            # Claude Code slash commands
└── docs/                    # Additional documentation
```

### Writing tests

```python
# tests/unit/services/test_example.py
import pytest
from src.services.process_monitor import ProcessMonitor

def test_monitor_initialization():
    monitor = ProcessMonitor(config)
    assert monitor is not None

@pytest.mark.asyncio
async def test_async_operation():
    # Async test example
    pass
```

### Adding a new feature

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Write tests**: Start with TDD when possible
3. **Implement**: Make the tests pass
4. **Run quality checks**: Execute `black`, `flake8`, and `mypy`
5. **Commit**: Use clear, descriptive messages
6. **Open a Pull Request**: Target the main branch

---

## 📄 License

MIT License - free to use, modify, and distribute.

---

## 🤝 Contributing

Bug reports, feature suggestions, and pull requests are always welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/LEE-Kyungjae/ClaudeCodeLooper/issues)
- **Documentation**: [Wiki](https://github.com/LEE-Kyungjae/ClaudeCodeLooper/wiki)
- **Email**: your-email@example.com

---

## 🙏 Acknowledgments

We built this project to make working with Claude Code easier.
Feedback and contributions are appreciated!

---

**Made with ❤️ for Claude Code users**
