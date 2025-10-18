# Claude Restart System Implementation Roadmap

## Current State Snapshot
- Planning artefacts complete; no production-ready code validated.
- Contract & integration test suites define required behaviour but currently unsatisfied.
- Tooling gap: pytest/dev dependencies not installed in workspace.
- Key inconsistencies: missing task monitor API, restart sequencing gaps, PatternDetector event schema mismatch.

## Guiding Principles
1. **Spec Alignment First** – Map each change to FR-001…FR-012.
2. **Test-Driven Flow** – Write/enable failing tests, then implement.
3. **Incremental Delivery** – Ship thin vertical slices that conclude with green contracts.
4. **Windows Compatibility** – Validate subprocess & path handling for Windows/WSL.

## Phase 0 – Environment Bring-Up
- Install dev dependencies: `pip install -r requirements.txt`.
- Verify pytest discoverability (`pytest --collect-only`).
- Document environment steps in `CLAUDE.md`.

## Phase 1 – Foundation Repairs
1. **Pattern Detector**
   - Add `is_limit_hit` flag and session-safe construction.
   - Ensure low-confidence matches flagged properly.
2. **Process Monitor Test Hooks**
   - Implement `inject_output`, `simulate_process_death` used by tests.
   - Provide lightweight fake process mode when command is `echo`.
3. **Restart Controller Contract Surface**
   - Expose `waiting_period` property returning primary active period.
   - Provide `task_monitor` proxy for current session.

_Exit Criteria_: `tests/integration/test_limit_detection.py` passes.

## Phase 2 – CLI Contract Compliance
1. Adjust CLI commands to support Click testing without side effects (dependency injection, dry-run modes).
2. Add guard rails for missing executables with informative messages.
3. Update `start` command to integrate fake process when `--test-mode` flag present.

_Exit Criteria_: `tests/contract/test_cli_*.py` green.

## Phase 3 – Restart Cycle Engine
1. Implement waiting period scheduling via `TimingManager` using accelerated clock for tests.
2. Wire `TaskCompletionMonitor` to honour in-progress tasks before restarts.
3. Ensure state persistence serialises sessions/waiting periods to disk.

_Exit Criteria_: `tests/integration/test_restart_cycle.py` green.

## Phase 4 – Observability & Logging
- Flesh out logging to file/console per configuration.
- Surface diagnostics via `cli info` and `cli logs` commands.
- Document log rotation behaviour.

## Phase 5 – Hardening
- Windows-specific process control validation.
- Negative tests for malformed configs.
- Performance benchmarks (monitoring overhead < target thresholds).

## Work Tracking & Governance
- Record phase start/finish + blockers in `CLAUDE.md` under a “Progress Log”.
- Create Git branches per phase (e.g., `feature/001-5-5-5-phase1`).
- Mandate code review checklist: spec alignment, tests, Windows parity, logging.

## Risk Register
- **External dependency availability** – Mitigate by caching packages locally.
- **Long-running daemon stability** – Add soak tests post-Phase 3.
- **Spec drift** – Schedule fortnightly spec review with stakeholders.

## Definition of Done (Project)
- All contract/integration tests pass in CI.
- User quickstart validated end-to-end on Windows + macOS.
- Documentation updated (`spec.md`, quickstart, CLI help).
- Version tagged `v1.0.0` with release notes summarising capabilities & known limitations.
