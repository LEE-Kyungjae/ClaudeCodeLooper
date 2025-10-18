# Changelog

All notable changes to ClaudeCodeLooper will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-18

### Added
- **Core Monitoring System**
  - Real-time Claude Code output monitoring
  - Automatic usage limit detection with pattern matching
  - 5-hour countdown timer with precise timing
  - Automatic process restart after cooldown
  - Daemon mode for background operation

- **CLI Interface**
  - `claude-looper start` - Start monitoring
  - `claude-looper stop` - Stop monitoring
  - `claude-looper status` - Check system status
  - `claude-looper logs` - View system logs
  - `claude-looper config` - Manage configuration

- **Claude Code Integration**
  - `/cl:on` - Start monitoring (slash command)
  - `/cl:off` - Stop monitoring (slash command)
  - `/cl:status` - Check status (slash command)
  - `/cl:logs` - View logs (slash command)
  - Auto-formatted output with emoji indicators

- **Services Architecture**
  - ProcessMonitor - Orchestrator service
  - ProcessLauncher - Process lifecycle management
  - OutputCapture - Stream capturing and buffering
  - HealthChecker - Process health monitoring
  - PatternDetector - Limit detection with confidence scoring
  - RestartController - Restart scheduling and execution

- **Data Models** (Pydantic)
  - SystemConfiguration - System settings
  - MonitoringSession - Session state tracking
  - WaitingPeriod - Countdown management
  - LimitDetectionEvent - Detection events
  - TaskCompletionMonitor - Task tracking

- **Quality & Security**
  - Shell injection prevention (shlex.split, shell=False)
  - Path traversal protection
  - Exception hierarchy (12 domain-specific exceptions)
  - Structured logging (JSON format)
  - Type hints throughout codebase
  - 70% test coverage (contract + integration tests)

- **Configuration**
  - JSON-based configuration system
  - Default configuration with user overrides
  - Pattern customization for detection
  - Timing and retry configuration
  - Logging configuration

- **Documentation**
  - Comprehensive README with installation guide
  - CLI command reference
  - Slash command usage guide
  - Troubleshooting section
  - Developer guide with project structure
  - API documentation in docstrings

- **Installation Infrastructure**
  - PyPI-compatible packaging (pyproject.toml)
  - Direct GitHub installation support
  - Automated installation scripts (Unix/Windows)
  - Requirements separation (runtime/dev)
  - MIT License

### Changed
- Refactored ProcessMonitor from 545 LOC monolith to 331 LOC orchestrator
- Reduced complexity by 40% through service-oriented architecture
- Optimized pattern detection with early exit (30-50% faster)

### Fixed
- Shell injection vulnerability in subprocess calls
- Path traversal vulnerability in directory validation
- Unsafe os.system() usage replaced with subprocess.run()

### Security
- Forced shell=False for all subprocess calls
- Safe command parsing with shlex.split()
- Path validation with os.path.realpath()
- Input sanitization for all user inputs

## [Unreleased]

### Planned
- PyPI distribution for `pip install claude-code-looper`
- Homebrew formula for macOS installation
- Windows installer (MSI)
- Web dashboard for monitoring
- Notification system (email, Slack)
- Multiple process monitoring
- Custom detection patterns via UI
- Performance metrics and analytics
- Docker support

---

## Version History

- **1.0.0** (2025-10-18): Initial release with core functionality
  - Monitoring, detection, restart automation
  - CLI and slash command interfaces
  - Comprehensive documentation
  - Production-ready quality and security

---

## Upgrade Guide

### From Development to 1.0.0

If you were using the development version:

```bash
# Uninstall old version
pip uninstall claude-restart-monitor

# Install new version
pip install git+https://github.com/LEE-Kyungjae/ClaudeCodeLooper.git

# Update command usage
# Old: claude-restart-monitor start
# New: claude-looper start
```

---

## Contributors

- **Kyungjae Lee** - Initial development and architecture
- **Claude (Anthropic)** - Development assistance and code generation

---

**Note**: This project follows semantic versioning. Breaking changes will increment major version, new features increment minor version, and bug fixes increment patch version.
