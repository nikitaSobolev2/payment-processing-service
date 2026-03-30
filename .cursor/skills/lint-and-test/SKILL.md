---
name: lint-and-test
description: Ruff and pytest errors must always be fixed before completing work
---

# Lint and Test — Zero Tolerance

**Ruff and pytest errors MUST always be fixed.** Do not leave them unresolved.

## Before Finishing

1. Run `ruff check src tests` — fix all reported issues.
2. Run `pytest tests/unit -v` (or the relevant test scope) — fix all failures.

## Commands

- **Ruff**: `.venv\Scripts\python.exe -m ruff check src tests`
- **Pytest**: `.venv\Scripts\python.exe -m pytest tests/unit -v`

On Windows, use `.venv\Scripts\python.exe` per the venv rule.

## Behavior

- If you introduce new code: run ruff and pytest after edits; fix any new errors.
- If you touch existing code: ensure you don't break tests; fix any regressions.
- Pre-existing errors in untouched files: fix them when working in that area, or call them out explicitly if out of scope.

## Fix, Don't Skip

- Do not add `# noqa` or `# type: ignore` to silence ruff without a documented justification.
- Do not skip failing tests with `@pytest.mark.skip` to "fix later."
- Prefer fixing the root cause over suppressing the symptom.
