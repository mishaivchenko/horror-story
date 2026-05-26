# Sprint 05 Checkpoint

**Date:** 2026-05-26
**Branch:** main (working changes uncommitted)
**Issues closed:** #026, #027

---

## What was implemented

### #026 — MfluxImageAdapter

- `src/horror_story/adapters/image/mflux.py` — real FLUX.1-schnell adapter via mflux
  Python API. Lazy import with `ImportError` hint. Atomic PNG + sidecar write.
  Sidecar validated against `keyframe.schema.json`.
- `src/horror_story/adapters/__init__.py` — `"mflux-schnell"` registered in
  `AdapterFactory.get_image()` with lazy import.
- `pyproject.toml` — `mflux = ["mflux>=0.4"]` optional dep; `mflux` pytest marker.
- `tests/test_image_mflux.py` — 5 tests: missing-import, factory, mocked success path
  (PNG+sidecar, seed forwarding, deterministic sidecar), smoke (skipped by default).

**API fix applied during review:** original agent used old mflux API (`Flux1.from_alias`,
`Config`, `image.image.save`). Fixed to current 0.17.x API:
`Flux1(model_config=ModelConfig.schnell(), quantize=4)`, `image.save(path)`.

### #027 — CLI `--image-adapter` flag

- `src/horror_story/cli.py` — `--image-adapter NAME` arg on `run` subparser. Override
  applied via `dataclasses.replace` before any stage runs.
- `tests/test_cli.py` — 3 new tests. Override test fixed to use a distinct sentinel
  adapter in the toml fixture (`"mflux-schnell"`) so the assertion is meaningful.

---

## Test results

```
301 passed, 1 skipped (mflux smoke), 5 warnings
mypy --strict src/: Success, no issues found in 32 source files
```

---

## HuggingFace setup (required for real generation)

FLUX.1-schnell is a gated model. Before first use:

1. Accept license: https://huggingface.co/black-forest-labs/FLUX.1-schnell
2. Create a Read token: https://huggingface.co/settings/tokens
3. `hf auth login --token hf_xxx`

Then:

```bash
python -m horror_story run \
  --story stories/pigeons-from-hell/pigeons_from_hell_EN.txt \
  --out output/sprint05 \
  --seed 42 \
  --image-adapter mflux-schnell
```

First run downloads ~8 GB; subsequent runs use the cached model.

---

## Known gaps going into Sprint 06

1. No real ambient audio — mock silence.
2. Ukrainian text is placeholder (reversed English).
3. Single narration segment per scene.
