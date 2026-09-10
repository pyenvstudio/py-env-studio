# Py Env Studio - Repository Agent Instructions

Primary instruction source for this repository:

- .github/agent-context/instructions/master-coding-agent-instructions.md

Treat that document as the authoritative agent behavior for all coding tasks in this repository.

## Required Behavior

- Prioritize correctness, security, reliability, and maintainability.
- Reuse existing architecture and services before creating new ones.
- Avoid duplicate implementations of environment, package, config, logging, process, or template logic.
- Keep GUI concerns in the UI layer and business logic in core/service modules.
- Keep long-running operations off the GUI thread.
- Use cross-platform path/process handling and pathlib-based APIs.
- Use safe subprocess argument arrays, not shell-string concatenation.
- Validate untrusted input (paths, template vars, package names, process args).
- Fail clearly with user-friendly messages and actionable logs.
- Add deterministic tests for success, failure, and edge cases.
- Preserve backward compatibility and avoid unrelated refactors.
- Keep feature tracking current: for every added or fixed feature, append a dated entry to .github/agent-context/feature-ledger.md.

## Engineering Principles

- SOLID where it provides practical value.
- DRY by reusing existing code.
- KISS with the simplest correct design.
- YAGNI by implementing only requested scope.

## Implementation Workflow

1. Inspect existing implementation and dependencies.
2. Identify reusable components and integration points.
3. Design the smallest safe incremental change.
4. Implement with clear module responsibilities.
5. Add or update tests.
6. Run relevant tests.
7. Report results honestly with limitations.

## Response Contract

After changes, provide:

- Summary
- Added/Modified/Removed files
- Architecture notes
- Test commands executed and outcomes
- Compatibility notes
- Real limitations and next step when useful

## Priority Order

1. Correctness
2. Security
3. Reliability
4. Backward compatibility
5. Maintainability
6. Simplicity
7. Performance
8. Future extensibility
