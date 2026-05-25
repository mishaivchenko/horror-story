# Issue #026 — MfluxImageAdapter: real keyframe generation via FLUX.1-schnell

**Status:** Open
**Sprint:** 05
**Priority:** P1
**Labels:** image, adapter, ml
**Estimate:** 1.0d
**Depends on:** #005
**Blocks:** —

---

## Goal

Implement `MfluxImageAdapter` — a real image generation adapter backed by
`mflux` (MLX-native FLUX on Apple Silicon).  Default model: `FLUX.1-schnell`
at quantize=4 (~8 GB VRAM, ~15 s/frame on M3 Max).  Registered as
`"mflux-schnell"` in `AdapterFactory`.

---

## Scope

### `pyproject.toml`

Add optional dependency group:

```toml
[project.optional-dependencies]
mflux = ["mflux>=0.4"]
```

Do **not** add `mflux` to the main `dependencies` list — it should never be
required for the mock-only pipeline.

### `src/horror_story/adapters/image/mflux.py`

```python
class MfluxImageAdapter(ImageAdapter):
    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int,
        out_path: Path,
        *,
        story_id: str = "",
        scene_id: str = "",
    ) -> Path:
```

Implementation notes:
- Import `mflux` lazily inside the method body; raise `ImportError` with a
  helpful message if missing (`pip install 'horror-story[mflux]'`).
- Use `mflux` Python API (not CLI subprocess).
- Model name: `"black-forest-labs/FLUX.1-schnell"`, quantize=4.
- Steps: 4 (schnell default).
- Pass `seed` directly — same seed → identical output.
- Save the returned image to `out_path` (atomic write via `.png.tmp`).
- Write sidecar JSON at `out_path.with_suffix(".json")` with fields:
  `schema_version`, `story_id`, `scene_id`, `prompt`, `width`, `height`,
  `seed`, `adapter` (`"mflux-schnell"`), `output_path`, `status`, `error`.
- Sidecar must validate against `spec/schemas/keyframe.schema.json`.

### `src/horror_story/adapters/__init__.py`

Register in `AdapterFactory.get_image()`:

```python
if name == "mflux-schnell":
    from horror_story.adapters.image.mflux import MfluxImageAdapter
    return MfluxImageAdapter()
```

Lazy import so the rest of the pipeline never imports `mflux` unless the
adapter is explicitly requested.

---

## Tests

### `tests/test_image_mflux.py`

- `test_mflux_adapter_missing_import`: monkeypatch `builtins.__import__` to
  simulate missing `mflux`; assert `ImportError` with helpful message.
- `test_adapter_factory_mflux_schnell`: `AdapterFactory.get_image("mflux-schnell")`
  returns `MfluxImageAdapter` instance (import-only, no generation).
- `test_mflux_generate_smoke` (`@pytest.mark.mflux`): real generation — skip
  unless `HORROR_STORY_TEST_MFLUX=1` env var is set. Asserts PNG exists,
  correct dimensions, sidecar validates against schema.

Add `mflux` marker to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = ["mflux: requires mflux installed and HORROR_STORY_TEST_MFLUX=1"]
```

---

## Acceptance criteria

1. `AdapterFactory.get_image("mflux-schnell")` returns a `MfluxImageAdapter`.
2. Missing `mflux` package raises `ImportError` with install instructions.
3. Same `seed` → identical PNG bytes across runs.
4. Sidecar validates against `keyframe.schema.json`.
5. `mypy --strict` passes.
6. `pytest` (without `mflux` marker) passes — no `mflux` import at module level.
