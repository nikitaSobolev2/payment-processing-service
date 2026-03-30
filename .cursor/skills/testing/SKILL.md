---
name: testing
description: Ensure tests exist for every major functional area, using the project's Python/pytest stack
---

# Testing Convention

## Framework

- Use **pytest** as the test runner.
- Use `unittest.mock` (or `pytest-mock`) for mocking external dependencies.
- Keep test dependencies in `pyproject.toml` under `[project.optional-dependencies] dev`.

## Test Structure

```
tests/
  conftest.py              # shared fixtures
  unit/
    test_keyword_match.py
    test_scraper.py
    test_extractor.py
    test_report.py
    test_circuit_breaker.py
  integration/
    test_handlers.py
    test_tasks.py
```

- Mirror source modules: one `test_<area>.py` per major functional area.
- Place unit tests under `tests/unit/`, integration tests under `tests/integration/`.

## Required Coverage Areas

Every pull request that adds or changes logic **must** include tests for the affected area.

| Area | Key modules | What to test |
|------|------------|--------------|
| Keyword matching | `src.services.parser.keyword_match` | OR/AND combos, edge cases, empty input |
| Scraping | `src.services.parser.scraper` | Pagination, dedup, keyword filtering, retry |
| AI extraction | `src.services.ai.client` | Prompt structure, response parsing, API error handling |
| Reports | `src.services.parser.report` | All 3 output formats (txt, md, message) |
| Task management | `src.worker.circuit_breaker` | State transitions, threshold, recovery |
| Bot handlers | `src.bot.handlers.*` | Mock Telegram updates, verify responses |
| Celery tasks | `src.worker.tasks.*` | Task with mocked services, idempotency |

## Mocking Rules

- **Always mock** HTTP calls (`httpx`) — never hit real HH.ru in tests.
- **Always mock** OpenAI client — never call the real API in tests.
- **Always mock** filesystem writes when testing report saving.
- Use `respx` for httpx mocking or `unittest.mock.patch`.

## Test Quality

- One logical assertion per test; name describes scenario and outcome:

```python
# Good
def test_matches_keyword_expr_or_operator_returns_true_on_partial_match():
    assert matches_keyword_expression("frontend developer", "frontend|backend")

# Bad
def test_keyword():
    ...
```

- Use `@pytest.fixture` for reusable setup.
- Use `@pytest.mark.parametrize` to cover multiple inputs concisely.
- Keep tests independent — no shared mutable state between tests.
