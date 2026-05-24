---
name: run-horror-story
description: Run, start, build, test, or screenshot the horror-story pipeline CLI. Use when asked to run the app, verify a command works, check CLI output, or confirm a pipeline change behaves correctly.
---

# run-horror-story

Python CLI and library pipeline. No GUI. The driver is
`.claude/skills/run-horror-story/smoke.sh` — a shell script that exercises every
live CLI surface and exits non-zero on failure.

All commands below were run and verified in this session.

## Prerequisites

Python ≥ 3.11 virtualenv at `.venv/`. If missing:

```bash
python3 -m venv .venv
pip install -e ".[dev]"
```

## Run (agent path)

```bash
bash .claude/skills/run-horror-story/smoke.sh
```

Runs four checks in order; prints `=== ALL PASSED ===` on success.

To exercise individual commands directly:

```bash
source .venv/bin/activate

# version
python -m horror_story --version
# → horror-story 0.1.0

# validate all spec JSON schemas
python -m horror_story validate-schemas
# → [validate-schemas] loaded 11 schemas — all well-formed.

# dry-run the pipeline (no artifacts written)
python -m horror_story run --story tests/fixtures/mini-story.txt --out /tmp/hs-out --seed 42 --dry-run
# → [run] story=... dry-run mode: no artifacts written.

# validate a run directory (stub, any path accepted)
python -m horror_story validate --run-dir /tmp/hs-out
# → [validate] run_dir=/tmp/hs-out
```

## Run tests

```bash
source .venv/bin/activate
python -m pytest -q
# → 167 passed, 10 skipped (FFmpeg-dependent), 2 warnings
```

With coverage:

```bash
python -m pytest --cov=horror_story -q
```

Type-check:

```bash
mypy --strict src/
```

## Gotchas

- `run` and `validate` subcommands are **stubs** as of sprint 02 — they print
  their arguments and return 0. Real pipeline execution arrives in later issues.
- The 10 skipped tests require `ffmpeg` on `PATH`; they are intentionally skipped
  when it is absent and do not indicate a broken install.
- `python -m horror_story` requires the venv to be active (or `pip install -e .`
  to have been run in the environment calling it). There is no global entry point.
