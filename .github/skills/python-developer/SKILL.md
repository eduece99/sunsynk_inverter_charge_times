---
name: python-developer
description: "Use when developing, debugging, or testing Python code; setting up its environment; writing pytest coverage; or checking Python dependencies."
---

# Python development

Use this workflow for Python code changes and environment setup. The bundled [environment.yml](./environment.yml) defines the project's Conda environment named `venv` and its Conda and pip dependencies.

## Environment

1. Use the project's `venv` environment for all Python commands. Do not install packages into the system interpreter.
2. With Conda/Mamba installed, create the environment from the repository root:

   ```bash
   mamba env create -f .github/skills/python-developer/environment.yml
   conda activate venv
   ```

   `mamba` is preferred for dependency solving; `conda activate` activates the environment. If `venv` already exists, update it with `mamba env update -n venv -f .github/skills/python-developer/environment.yml` rather than creating another environment.
3. Check that commands use the environment's interpreter (`which python`, `python --version`) before installing packages, running tests, or scripts. Install additional Python dependencies into `venv`, and add them to the appropriate Conda or pip section of `environment.yml` so a fresh setup remains reproducible.
4. Run Python tooling from the repository root unless its project documentation specifies a different working directory.

## Tests with pytest

1. Before editing, inspect the Python modules and existing tests. Build a checklist of every class, function, and method that the change will add or affect.
2. Write or update pytest tests for each new or affected class, function, and method. Cover normal behavior, important boundary cases, and error paths. Prefer testing public behavior; exercise private helpers directly when needed to provide meaningful coverage.
3. Check whether existing classes, functions, or methods lack tests. Do not silently leave a known gap: add tests when in scope, or tell the user what is untested and suggest concrete test cases by symbol and behavior.
4. Run the focused test file(s) first, then run the full repository suite:

   ```bash
   pytest -q path/to/relevant_test.py
   pytest -q
   ```

   Replace the example path with actual test paths; if the project uses a documented command/configuration, follow it. A missing test suite or pytest exit indicating no tests is not a passing result. Report commands run and any tests that could not be run.
5. Never call live services or perform destructive/real-world actions as a test. Mock external APIs and isolate filesystem or network effects.

## Dependencies and validation

- Keep `environment.yml` in sync with runtime, development, and test dependencies. Prefer Conda packages where available; use its `pip:` subsection for packages not supplied through Conda or where the project specifically requires pip.
- Respect project-specific Python version constraints and established formatting, lint, type-check, and test conventions. Run the narrowest relevant checks and then any required full checks.
- Do not claim coverage for a class or callable unless tests actually exercise it. Summarize missing coverage, validation results, and any follow-up test suggestions to the user.
