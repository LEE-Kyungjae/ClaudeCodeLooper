# Claude Code Restart System Prompt Guide

## Goals
- Preserve project context (Feature 001-5-5-5) and constraints (Windows compatibility, TDD-first).
- Drive assistants toward verifiable increments: failing test-first, minimal scope, observable state.
- Capture status deltas for the operations log (`CLAUDE.md`).

## Core Prompt Structure
Use the following scaffold whenever requesting implementation work:

```
[Context]
- Feature: Claude Code automated restart monitor, branch 001-5-5-5.
- Current phase: Planning complete, implementation outstanding.
- Known blockers: pytest unavailable locally; contract/integration tests currently red by design.

[Objective]
Describe the single verifiable outcome for this iteration (e.g., "Implement CLI start command skeleton satisfying contract tests 1–3").

[Constraints]
- Follow spec + contracts in `specs/001-5-5-5/`.
- Add failing tests before code when extending coverage.
- Avoid altering existing behaviour outside target scope.

[Acceptance Checks]
- Tests to run (explicit pytest node list). If tooling missing, specify install command.
- State/log updates (e.g., update `CLAUDE.md`, persist config sample).

[Deliverables]
- Files expected to change.
- Notes for QA / manual verification.
```

Populate each bracketed section before issuing to an assistant. Include links to file paths when referencing artefacts.

## Reusable Prompt Snippets

### 1. Test Creation First
```
Write failing pytest cases under {path} capturing:
- Scenario A …
- Scenario B …
Ensure names follow test_contract_* or test_integration_* conventions.
```

### 2. Config / Spec Alignment
```
Cross-check implementation against spec FR-00X. Summarise deviations & propose code updates.
```

### 3. Regression Sweep
```
List commands to execute for smoke validation on Windows vs. macOS shells.
```

## Quality Checklist
Before accepting assistant output, verify:
- Prompt references exact files/lines where clarification needed.
- Each acceptance check is objectively verifiable.
- Exit criteria map to spec functional requirements.
- Risks/gaps called out for follow-up backlog entry.

## Escalation Template
If assistant encounters blockers (missing dependencies, permissions), reuse:
```
Blocker: <describe>
Impact: <tests/feature affected>
Proposed remedy: <command or manual step>
```

## Maintenance
- Update this guide when spec evolves or new tooling introduced.
- Version changes in `CLAUDE.md` under "Prompting" subsection.
- Review quarterly to ensure alignment with active workflow.
