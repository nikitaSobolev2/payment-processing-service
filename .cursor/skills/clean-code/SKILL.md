---
name: clean-code
description: Uncle Bob Clean Code principles — naming, functions, structure, and readability
---

# Clean Code (Uncle Bob)

## Naming

- Use intention-revealing names. A name should answer why it exists, what it does, and how it is used.
- Avoid abbreviations, single-letter variables, and encodings (e.g., Hungarian notation).
- Class names: nouns or noun phrases (`OrderProcessor`, not `ManageOrders`).
- Method names: verbs or verb phrases (`calculateTotal`, not `total`).
- Use consistent vocabulary — pick one word per concept and stick to it across the codebase.

## Functions

- **Small**: Functions should be short (ideally under 20 lines).
- **Do one thing**: A function should perform a single responsibility and do it well.
- **One level of abstraction**: Don't mix high-level logic with low-level details.
- **Few arguments**: Prefer 0-2 arguments. Three or more is a sign to introduce a parameter object.
- **No side effects**: A function named `checkPassword` should not also initialize a session.
- **Command-Query Separation**: Functions either do something (command) or return something (query), not both.

## Comments

- Don't comment bad code — rewrite it.
- Acceptable comments: legal headers, intent clarification, TODOs, Javadoc on public APIs.
- Avoid redundant comments that repeat what the code already says.

## Formatting & Structure

- Keep files short and focused on a single concept.
- Related code should be vertically close (functions that call each other, variable and its usage).
- Respect consistent indentation and team conventions.

## Error Handling

- Prefer exceptions over error codes.
- Don't return or pass `null` — use `Optional`, empty collections, or Null Object pattern.
- Write `try` blocks first, keep them narrow, and handle exceptions at the right abstraction level.

## Classes & Objects

- **Single Responsibility Principle**: A class should have one, and only one, reason to change.
- Keep classes small — measure by responsibilities, not lines.
- High cohesion: methods and fields of a class should belong together.
- Depend on abstractions, not concretions (Dependency Inversion).

## Tests

- Tests should be **F.I.R.S.T.**: Fast, Independent, Repeatable, Self-validating, Timely.
- One assertion concept per test.
- Test names should describe the scenario and expected outcome.
- Test code deserves the same quality standards as production code.
