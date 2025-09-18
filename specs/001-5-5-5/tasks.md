# Tasks: Claude Code Automated Restart System

**Input**: Design documents from `/specs/001-5-5-5/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- Paths follow plan.md structure decision: Option 1 (Single project)

## Phase 3.1: Setup
- [ ] T001 Create project structure with src/, tests/, docs/ directories at repository root
- [ ] T002 Initialize Python project with pyproject.toml, requirements.txt for psutil, pytest, click dependencies
- [ ] T003 [P] Configure linting with flake8, black, isort in pyproject.toml
- [ ] T004 [P] Create .gitignore for Python project with __pycache__, *.pyc, .pytest_cache, logs/

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T005 [P] Contract test CLI start command in tests/contract/test_cli_start.py
- [ ] T006 [P] Contract test CLI stop command in tests/contract/test_cli_stop.py
- [ ] T007 [P] Contract test CLI status command in tests/contract/test_cli_status.py
- [ ] T008 [P] Contract test CLI config command in tests/contract/test_cli_config.py
- [ ] T009 [P] Contract test CLI logs command in tests/contract/test_cli_logs.py
- [ ] T010 [P] Integration test complete restart cycle in tests/integration/test_restart_cycle.py
- [ ] T011 [P] Integration test configuration validation in tests/integration/test_config_validation.py
- [ ] T012 [P] Integration test error recovery scenarios in tests/integration/test_error_recovery.py
- [ ] T013 [P] Integration test limit detection patterns in tests/integration/test_limit_detection.py
- [ ] T014 [P] Integration test process monitoring in tests/integration/test_process_monitoring.py

## Phase 3.3: Core Models (ONLY after tests are failing)
- [ ] T015 [P] MonitoringSession model in src/models/monitoring_session.py
- [ ] T016 [P] LimitDetectionEvent model in src/models/limit_detection_event.py
- [ ] T017 [P] RestartCommandConfiguration model in src/models/restart_command_config.py
- [ ] T018 [P] WaitingPeriod model in src/models/waiting_period.py
- [ ] T019 [P] TaskCompletionMonitor model in src/models/task_completion_monitor.py
- [ ] T020 [P] SystemConfiguration model in src/models/system_configuration.py

## Phase 3.4: Core Services
- [ ] T021 [P] ProcessMonitor service for Claude Code process management in src/services/process_monitor.py
- [ ] T022 [P] PatternDetector service for limit message detection in src/services/pattern_detector.py
- [ ] T023 [P] TimingManager service for 5-hour countdown in src/services/timing_manager.py
- [ ] T024 [P] StateManager service for persistence and recovery in src/services/state_manager.py
- [ ] T025 [P] ConfigManager service for configuration management in src/services/config_manager.py
- [ ] T026 RestartController service orchestrating restart cycle in src/services/restart_controller.py

## Phase 3.5: CLI Implementation
- [ ] T027 Main CLI entry point with click framework in src/cli/main.py
- [ ] T028 [P] CLI start command implementation in src/cli/commands/start.py
- [ ] T029 [P] CLI stop command implementation in src/cli/commands/stop.py
- [ ] T030 [P] CLI status command implementation in src/cli/commands/status.py
- [ ] T031 [P] CLI config command implementation in src/cli/commands/config.py
- [ ] T032 [P] CLI logs command implementation in src/cli/commands/logs.py

## Phase 3.6: Core Integration
- [ ] T033 Wire ProcessMonitor with PatternDetector for real-time monitoring in src/services/restart_controller.py
- [ ] T034 Connect TimingManager with RestartController for countdown handling in src/services/restart_controller.py
- [ ] T035 Integrate StateManager with all services for persistence in src/services/restart_controller.py
- [ ] T036 Connect ConfigManager with CLI commands for configuration in src/cli/main.py
- [ ] T037 Implement logging infrastructure with structured logging in src/lib/logging_config.py
- [ ] T038 Add error handling and graceful shutdown signals in src/lib/signal_handler.py

## Phase 3.7: Windows-Specific Features
- [ ] T039 [P] Windows process monitoring utilities in src/lib/windows_process.py
- [ ] T040 [P] Windows-specific signal handling in src/lib/windows_signals.py
- [ ] T041 [P] Windows service integration for daemon mode in src/lib/windows_service.py

## Phase 3.8: Polish
- [ ] T042 [P] Unit tests for ProcessMonitor in tests/unit/test_process_monitor.py
- [ ] T043 [P] Unit tests for PatternDetector in tests/unit/test_pattern_detector.py
- [ ] T044 [P] Unit tests for TimingManager in tests/unit/test_timing_manager.py
- [ ] T045 [P] Unit tests for StateManager in tests/unit/test_state_manager.py
- [ ] T046 [P] Unit tests for ConfigManager in tests/unit/test_config_manager.py
- [ ] T047 [P] Performance tests for real-time monitoring (<1s detection) in tests/performance/test_monitoring_performance.py
- [ ] T048 [P] Performance tests for timing accuracy (±1s over 5 hours) in tests/performance/test_timing_accuracy.py
- [ ] T049 [P] Create comprehensive README.md with installation and usage
- [ ] T050 [P] Package setup with setuptools for pip installation in setup.py
- [ ] T051 Validate quickstart scenarios work end-to-end
- [ ] T052 Code cleanup and remove duplication across services

## Dependencies
**Critical TDD Order**:
- Tests (T005-T014) MUST complete before implementation (T015-T041)
- Models (T015-T020) before Services (T021-T026)
- Services before CLI (T027-T032)
- Core before Integration (T033-T038)
- Integration before Windows features (T039-T041)
- Implementation before Polish (T042-T052)

**Specific Blockers**:
- T026 (RestartController) blocks T033-T035 (requires all services)
- T036 (CLI integration) blocks T051 (quickstart validation)
- T037 (logging) blocks all integration tasks
- T049-T050 (packaging) blocks final validation

## Parallel Execution Examples

### Phase 3.2 - All Contract Tests (Run Together)
```bash
# Launch T005-T009 together - all CLI contract tests:
Task: "Contract test CLI start command in tests/contract/test_cli_start.py"
Task: "Contract test CLI stop command in tests/contract/test_cli_stop.py"
Task: "Contract test CLI status command in tests/contract/test_cli_status.py"
Task: "Contract test CLI config command in tests/contract/test_cli_config.py"
Task: "Contract test CLI logs command in tests/contract/test_cli_logs.py"
```

### Phase 3.2 - All Integration Tests (Run Together)
```bash
# Launch T010-T014 together - all integration scenarios:
Task: "Integration test complete restart cycle in tests/integration/test_restart_cycle.py"
Task: "Integration test configuration validation in tests/integration/test_config_validation.py"
Task: "Integration test error recovery scenarios in tests/integration/test_error_recovery.py"
Task: "Integration test limit detection patterns in tests/integration/test_limit_detection.py"
Task: "Integration test process monitoring in tests/integration/test_process_monitoring.py"
```

### Phase 3.3 - All Models (Run Together)
```bash
# Launch T015-T020 together - all data models:
Task: "MonitoringSession model in src/models/monitoring_session.py"
Task: "LimitDetectionEvent model in src/models/limit_detection_event.py"
Task: "RestartCommandConfiguration model in src/models/restart_command_config.py"
Task: "WaitingPeriod model in src/models/waiting_period.py"
Task: "TaskCompletionMonitor model in src/models/task_completion_monitor.py"
Task: "SystemConfiguration model in src/models/system_configuration.py"
```

### Phase 3.4 - Independent Services (Run Together)
```bash
# Launch T021-T025 together - independent services:
Task: "ProcessMonitor service for Claude Code process management in src/services/process_monitor.py"
Task: "PatternDetector service for limit message detection in src/services/pattern_detector.py"
Task: "TimingManager service for 5-hour countdown in src/services/timing_manager.py"
Task: "StateManager service for persistence and recovery in src/services/state_manager.py"
Task: "ConfigManager service for configuration management in src/services/config_manager.py"
```

### Phase 3.5 - All CLI Commands (Run Together)
```bash
# Launch T028-T032 together - all CLI command implementations:
Task: "CLI start command implementation in src/cli/commands/start.py"
Task: "CLI stop command implementation in src/cli/commands/stop.py"
Task: "CLI status command implementation in src/cli/commands/status.py"
Task: "CLI config command implementation in src/cli/commands/config.py"
Task: "CLI logs command implementation in src/cli/commands/logs.py"
```

## Task Optimization Notes
**Context Integration**: "알아서 업무 최적으로 분배시켜줘" - Tasks optimally distributed for:
- **Maximum Parallelization**: 32 tasks marked [P] for concurrent execution
- **Clean Dependencies**: Clear blocking relationships prevent conflicts
- **TDD Enforcement**: All tests before implementation ensures quality
- **Windows Focus**: Dedicated Windows integration tasks for platform requirements
- **Performance Validation**: Specific timing and monitoring performance tests

## Validation Checklist
*GATE: Checked by main() before returning*

- [x] All CLI commands have corresponding contract tests (T005-T009)
- [x] All entities have model tasks (T015-T020)
- [x] All tests come before implementation (T005-T014 before T015+)
- [x] Parallel tasks truly independent (different files, no shared state)
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Integration scenarios from quickstart covered (T010-T014)
- [x] Windows-specific requirements addressed (T039-T041)
- [x] Performance requirements tested (T047-T048)

## Success Criteria
After completing all 52 tasks, the system will:
- ✅ Monitor Claude Code output in real-time
- ✅ Detect 5-hour usage limits accurately
- ✅ Execute precise countdown timers
- ✅ Restart Claude Code automatically with user commands
- ✅ Persist state across system restarts
- ✅ Provide comprehensive CLI interface
- ✅ Handle Windows-specific requirements
- ✅ Maintain performance under continuous operation