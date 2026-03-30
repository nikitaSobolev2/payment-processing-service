---
name: quality-checks
description: Ruff and pytest errors should ALWAYS be fixed — never leave lint or test failures
---

# Quality Checks

**Ruff and pytest errors should ALWAYS be fixed.** Never leave lint or test failures in the codebase. Fix them before completing any task.

## When to Run

- After making code changes
- Before considering a task complete
- When introducing new code or modifying existing logic

## Commands

- **Ruff**: `.venv\Scripts\python.exe -m ruff check src tests`
- **Pytest**: `.venv\Scripts\python.exe -m pytest tests/unit -v` (or scope to affected tests)

## Workflow

1. Make your edits
2. Run `ruff check` — fix any reported issues
3. Run `pytest` — fix any failing tests
4. Only then consider the task done

## Do Not

- Leave ruff errors "for later" or mark them as acceptable
- Skip fixing failing tests
- Commit or complete work with known lint/test failures
