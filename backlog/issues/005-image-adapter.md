# Issue 005 — Image adapter: keyframe generation (mock-first)

**Labels:** `adapter`, `sprint-01`
**Spec refs:** `spec/MVP_PLUS.md` §F-05; `spec/PIPELINE.md` §Stage 4; `spec/schemas/keyframe.schema.json`
**Estimate:** 0.5 day
**Depends on:** #002

## Goal

Define the `ImageAdapter` ABC and implement `MockImageAdapter` that writes a deterministic
grey PNG with the scene ID as a text label.

## Acceptance criteria

- [ ] `ImageAdapter` ABC in `horror_story/adapters/image/base.py` with signature:
      `generate(self, prompt: str, width: int, height: int, seed: int, out_path: Path) -> Path`
- [ ] `MockImageAdapter.generate(...)` writes a valid PNG of exactly `width × height` pixels
- [ ] PNG contains scene_id label as readable white text on grey background (Pillow)
- [ ] Background grey value is derived from `seed % 128 + 64` (reproducible per-scene tint)
- [ ] Same arguments + seed → identical file bytes
- [ ] `keyframe.json` sidecar written at `out_path.with_suffix('.json')` and validates
      against `spec/schemas/keyframe.schema.json`
- [ ] Adapter registered: `AdapterFactory.get_image("mock") -> MockImageAdapter`
- [ ] `pytest tests/test_image.py` passes with ≥ 85% coverage on `image/`
- [ ] `mypy --strict` passes

## Tasks

1. Define `ImageAdapter` ABC in `horror_story/adapters/image/base.py`.
2. Implement `MockImageAdapter` in `horror_story/adapters/image/mock.py` using Pillow.
3. Add `get_image()` to `AdapterFactory`.
4. Write unit tests: PNG size check, pixel sampling, byte determinism, sidecar schema.

## Notes

- Pillow is a declared dependency from issue #001.
- Use `out_path` convention: write to temp, then `Path.replace(out_path)`.
