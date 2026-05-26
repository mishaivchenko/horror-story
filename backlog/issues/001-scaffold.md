# Issue 001 — Project scaffold and CLI skeleton

**Status:** Done

**Labels:** `setup`, `sprint-01`
**Spec refs:** `spec/TECHNICAL_PLAN.md`, `spec/constitution.md`
**Estimate:** 0.5 day

## Goal

Create the Python package layout, `pyproject.toml`, CLI entry point skeleton, schema
validation helper, and a passing empty test suite. After this issue, `pytest` and
`mypy --strict` run clean and `python -m horror_story --help` prints usage.

## Acceptance criteria

- [ ] `src/horror_story/__main__.py` exists; `python -m horror_story --help` prints usage
- [ ] `src/horror_story/cli.py` defines `run`, `validate`, `dry-run` subcommands (stubs ok)
- [ ] `src/horror_story/schemas.py` loads and caches all schemas from `spec/schemas/`
- [ ] `pytest` runs (0 tests or all pass, no errors)
- [ ] `mypy --strict src/` passes
- [ ] `pyproject.toml` defines all dev dependencies (pytest, mypy, jsonschema, Pillow)
- [ ] `.gitignore` excludes `output/`, `__pycache__/`, `.mypy_cache/`, `dist/`, `.venv/`

## Tasks

1. Write `pyproject.toml` with `[project]`, `[project.optional-dependencies]`, and
   `[tool.mypy]` sections.
2. Create `src/horror_story/` package with `__init__.py`, `__main__.py`, `cli.py`,
   `schemas.py`.
3. Create `tests/__init__.py` and `tests/test_scaffold.py` that imports `horror_story`
   and asserts the package version is set.
4. Write `.gitignore`.
5. Verify `python -m horror_story --help`, `pytest`, `mypy` all pass.

## Notes

- Do not implement any pipeline logic yet.
- CLI uses `argparse` (stdlib). This is decided — no click, no typer. See `spec/TECHNICAL_PLAN.md`.
- Config models use `dataclasses` (stdlib). No Pydantic.
- No `atomicwrites` package. Use `Path.write_bytes` + `Path.replace()` for atomic writes.
