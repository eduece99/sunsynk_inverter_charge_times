# Copilot agent instructions

## Project at a glance

This is a small Python CLI that schedules battery charging on a SunSynk inverter using inverter status, Octopus Agile/Go tariff data, and (for Go) an Open-Meteo forecast. Its central implementation and CLI entry point are `inverter_set.py`; it authenticates to remote services and can change live inverter settings. The tracked project is four files: `README.md`, `inverter_set.py`, `LICENSE`, and `token1.txt`. Python is the only application language; the source uses Python 3.10+ union type syntax. There is no declared or tested Python version, dependency lock, packaging metadata, or framework beyond Typer and pandas.

## Setup and validation

- There is no build system, bootstrap script, requirements file, linter configuration, or CI workflow in the tracked repository. Do not invent a build step or report a CI check that does not exist.
- The README lists the runtime dependencies: `pandas`, `requests`, `typer`, `pycryptodome`, and `typing_extensions`. There are no pinned versions. Before running the CLI or importing the module in a fresh environment, create and activate an isolated Python 3.10+ virtual environment and install those dependencies with `python -m pip install pandas requests typer pycryptodome typing_extensions`. No dependency installation sequence has been validated here.
- Test discovery was checked with `pytest -q` at the repository root: **no tests ran** and pytest exited with status 5. No test files or test configuration are tracked. Do not treat that as a passing test suite or add tests to an unrelated external directory; when changing behavior, add focused tests and their required test dependencies as part of the change.
- No lint or build command is configured. Run only checks supported by changes/dependencies and report clearly when a check is unavailable or unverified. `git diff --check` is an appropriate whitespace check for a proposed patch.
- The README's usage examples invoke live API operations. `--help` is the safe CLI smoke check after dependencies are installed; actual scheduling commands authenticate with SunSynk and post changed settings to an inverter. Never run a live command, use a real account/token, or make a live API call as validation. A valid account and inverter are required for manual operation; test changes with mocks or offline fixtures instead.
- The README's dependency install command is documentation, not a lockfile. Use placeholders for credentials and avoid placing secrets in command history, logs, tests, or patches.

## Code map and behavior

- `README.md`: usage, dependencies, operating modes, safety notes, and project overview. Check it when changing documented behavior.
- `inverter_set.py`: `SunsynkInverter` owns authentication, token loading, API access, schedule payload construction, charge-rate/duration estimates, and common scheduling calculations. `SunsynkInverterAgile` implements Agile price-window selection; `SunsynkInverterOctopusGo` uses export pricing and an Open-Meteo daylight forecast. `main()` selects a strategy and `typer.run(main)` exposes the CLI.
- `LICENSE`: GPL-3.0.
- `token1.txt`: tracked credential-like data. Treat it as a secret: do not open, print, use, quote, or include it in logs or patches. Do not add or expose credentials or tokens.

There are no tracked `CONTRIBUTING.md`, tests, CI workflows, dependency manifests, or lint/build configuration. The local workspace may contain additional untracked files or projects; they are not part of the cloud agent checkout and must not be assumed available or authoritative. Make changes against tracked files unless the task explicitly establishes otherwise. Be especially careful with authentication, time zones, price-window boundaries, and payload fields: mistakes can cause real charging behavior changes.

## Working approach

Start with these instructions and the relevant section of `README.md`; trust this guide unless information is incomplete or demonstrably out of date. Search the repository only when needed to resolve such a gap. Keep changes focused, preserve the existing simple module/class structure, and update the README when CLI behavior, dependencies, or safe operating instructions change. Never run commands that write inverter settings as a test.
