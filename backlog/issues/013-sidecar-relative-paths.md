# Issue #013 — Sidecar paths: absolute → relative

**Status:** Done
**Sprint:** 03
**Labels:** tech-debt, adapter
**Estimate:** 0.25d
**Blocks:** #016

---

## Problem

All mock adapters write `output_path` into the sidecar JSON as an absolute filesystem path
(`str(out_path)`). This breaks reproducibility when output directories change and violates
the portability requirement: a sidecar should describe artifacts relative to its own location,
not to the machine that generated it.

Example of current broken sidecar:
```json
{ "output_path": "/Users/alice/dev/horror-story/output/run_42/narration_scene-01_seg-01.wav" }
```

Expected:
```json
{ "output_path": "narration_scene-01_seg-01.wav" }
```

---

## Scope

Replace `str(out_path)` with `out_path.name` in the sidecar JSON construction of all five
mock adapters:

- `src/horror_story/adapters/tts/mock.py`
- `src/horror_story/adapters/image/mock.py`
- `src/horror_story/adapters/motion/mock.py`
- `src/horror_story/adapters/audio/mock.py`
- `src/horror_story/adapters/typography/mock.py`

Verify that JSON schemas do not require an absolute path — if any schema has a `format: uri`
or similar constraint on `output_path`, remove it.

---

## Acceptance criteria

1. All five sidecar files contain only the filename (no directory component) in `output_path`.
2. All existing tests pass (update snapshot assertions that compared absolute paths).
3. `mypy --strict` passes.
4. `pytest --cov=horror_story` ≥ 80% on modified files.
