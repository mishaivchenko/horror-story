# Checkpoint 002 — After Issue #002 (Story Parser)

Date: 2026-05-24

## Quality Baseline

| Check | Result |
|---|---|
| pytest | 47 passed, 0 failed |
| coverage | 95% (264 statements, 12 missed) |
| mypy --strict | Success: no issues found in 16 source files |
| validate-schemas | 11 schemas loaded — all well-formed |

Uncovered lines: `__main__.py:1-3` (entry point), `adapters/base.py:1-54` (abstract base classes, not instantiated), `pipeline/parse.py:16,22` (unreachable branches in mood/slug edge paths), `models.py:47` (one branch in `to_dict`).

## Implemented Pipeline Stages

| Stage | Module | Status |
|---|---|---|
| Stage 0: Config load | `config.py` | Complete |
| Stage 1: Story parse + run init | `pipeline/parse.py`, `manifest.py` | Complete |
| Schema validation | `schemas.py` | Complete |
| CLI scaffold | `cli.py` | Stub (run/validate commands print placeholders) |
| Adapter ABCs | `adapters/base.py` | Abstract interfaces defined, no mock implementations yet |

## Repository / Module Structure

```
src/horror_story/
  __init__.py          — package init, version string
  __main__.py          — python -m horror_story entry point
  cli.py               — argparse CLI: run, validate, validate-schemas
  config.py            — PipelineConfig / StoryConfig / RenderConfig / AdapterConfig (TOML loader)
  manifest.py          — Manifest, ArtifactIndex, SceneEntry dataclasses + initialize_run()
  models.py            — Scene dataclass, slugify(), classify_mood(), _extract_visual_description()
  schemas.py           — load_all_schemas(), validate() (jsonschema wrapper)
  pipeline/
    __init__.py
    parse.py           — parse_story(): splits text on '---', returns list[Scene]
  adapters/
    __init__.py
    base.py            — TTSAdapter, ImageAdapter, MotionAdapter, AudioAdapter, TypographyAdapter ABCs
    tts/__init__.py    — stub namespace
    image/__init__.py  — stub namespace
    motion/__init__.py — stub namespace
    audio/__init__.py  — stub namespace
    typography/__init__.py — stub namespace

tests/
  test_scaffold.py     — package version, help, CLI smoke tests (4 tests)
  test_cli.py          — parser + main() dispatch (8 tests)
  test_config.py       — TOML config loading (1 test)
  test_manifest.py     — Manifest + ArtifactIndex round-trips, atomic writes (4 tests)
  test_parse.py        — parse_story(), slugify(), classify_mood(), initialize_run() (30 tests)
  test_schemas.py      — schema loading + fixture validation (3 tests)
```

## Implemented Schemas

All 11 schemas in `spec/schemas/` are present and well-formed:

- `manifest.schema.json`
- `scene.schema.json`
- `script.schema.json`
- `voice_line.schema.json`
- `keyframe.schema.json`
- `ambient_artifact.schema.json`
- `motion_artifact.schema.json`
- `typography_artifact.schema.json`
- `composed_scene.schema.json`
- `artifact_index.schema.json`
- `render_job.schema.json`

## Implemented CLI Commands

| Command | Status |
|---|---|
| `--version` | Returns `horror-story 0.1.0` |
| `--help` | Full help with subcommands |
| `run --story --out --seed --scene --dry-run --regen` | Args parsed; prints stub output; no pipeline execution yet |
| `validate --run-dir` | Args parsed; prints stub output |
| `validate-schemas` | Fully functional — loads and validates all 11 spec schemas |

## Deterministic Guarantees

- `parse_story()` is a pure function: same text + story_id → identical Scene list
- `initialize_run()` produces identical output for identical inputs (seed flows through but mock adapters not yet wired)
- `slugify()` is deterministic and stable (same text → same slug, always ≤48 chars)
- `classify_mood()` is deterministic (keyword scoring, no randomness)
- Atomic writes via `.tmp` → `replace()` for all JSON artifact files
- Run directory name encodes `story_id` and `seed`: `run_{story_id}_{seed}`

## Explicitly NOT Implemented Yet

- Mock adapter implementations (TTS, image, motion, audio, typography) — Issue #004–#008
- Script generation stage — Issue #003
- Actual pipeline execution wired through `run` command — after adapters
- `--scene` per-scene regeneration logic
- `--regen` versioned run directory logic
- Compositor, renderer stages — Issues #009–#010
- Full `validate` command with artifact inspection
- GitHub Issues created (backlog drafts exist in `backlog/issues/`)

## MVP Scope Status

Sprint 01 target: Issues #001–#005 + #012.

- #001 Scaffold: **Complete**
- #002 Story Parser: **Complete**
- #003 Script Generation: Not started
- #004 TTS Adapter (mock): Not started
- #005 Image Adapter (mock): Not started
- #012 CI: Workflows written, no GitHub repo yet to activate them
