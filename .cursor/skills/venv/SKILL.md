---
name: venv
description: Use project .venv for all Python commands
---

# Virtual Environment

Always use the project's `.venv` when running Python commands in this workspace.

- **pytest**: `.venv\Scripts\python.exe -m pytest ...`
- **pip**: `.venv\Scripts\pip.exe ...`
- **Other Python scripts**: `.venv\Scripts\python.exe ...`

On Windows, the Python executable is at `.venv\Scripts\python.exe`.
