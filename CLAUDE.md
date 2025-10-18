# Claude Code Agent Context

## Project Overview
Claude Code Automated Restart System - A monitoring and automation tool that detects Claude Code usage limits and automatically handles restart cycles.

## Recent Development (Feature 001-5-5-5)

### Current Feature: Automated Restart System
**Status**: Planning Phase Complete
**Branch**: `001-5-5-5`

**Key Technologies**:
- Python 3.9+ (Windows process management)
- psutil (process monitoring)
- subprocess (process control and output capture)
- JSON (configuration and state persistence)
- regex (pattern matching for limit detection)

**Architecture**:
- CLI-based utility with daemon mode capability
- Real-time terminal output monitoring
- Precise 5-hour countdown timing
- State persistence across system restarts
- Configurable restart commands and detection patterns

**Recent Changes**:
1. Created comprehensive specification (specs/001-5-5-5/spec.md)
2. Completed technical research and design decisions (specs/001-5-5-5/research.md)
3. Defined data model with 6 core entities (specs/001-5-5-5/data-model.md)
4. Specified CLI interface and API contracts (specs/001-5-5-5/contracts/)
5. Developed quickstart guide with integration scenarios (specs/001-5-5-5/quickstart.md)

**Implementation Notes**:
- TDD approach mandatory - tests before implementation
- Focus on Windows compatibility with WSL support
- Graceful error handling and resilience required
- Comprehensive logging for debugging long-running operations

## Core Technical Decisions

### Process Monitoring Strategy
- Real-time stdout/stderr capture using subprocess.Popen
- Non-blocking I/O to prevent deadlocks
- Buffer management for high-volume output

### Timing Precision
- datetime-based scheduling with timezone awareness
- State persistence enables recovery from interruptions
- Countdown display for user feedback

### Configuration Management
- JSON-based configuration with validation
- Hierarchical settings with defaults
- Hot reload capability for updates

## Development Context

**Testing Requirements**:
- Contract tests for CLI interface
- Integration tests for process monitoring
- Timing accuracy validation
- Windows-specific functionality testing

**Key Files to Understand**:
- `specs/001-5-5-5/spec.md` - Complete feature requirements
- `specs/001-5-5-5/contracts/cli-interface.md` - CLI command structure
- `specs/001-5-5-5/data-model.md` - Core entities and relationships

**Next Phase**: Task generation (/tasks command) to create detailed implementation tasks

---
*Context updated: 2025-09-18 | Feature: 001-5-5-5 | Phase: Planning Complete*
