# Contributing

1. Create a virtual environment with Python 3.10 or newer.
2. Install development tools with `uv sync` (or `pip install -e '.[dev]'`).
3. Run `pytest`, `ruff check .`, and `mypy` before opening a pull request.
4. Add a fixture and regression test for every new validation rule.

Keep the core package dependency-free and preserve the payload-safe output
contract. Changes to rule behavior should link to the relevant CloudEvents
specification section and update `RESEARCH.md` or the README when user-facing.
