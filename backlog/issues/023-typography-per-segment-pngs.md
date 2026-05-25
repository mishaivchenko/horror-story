# Issue #023 — Typography: per-segment PNG sequence from timeline

**Status:** Done
**Sprint:** 04
**Priority:** P1
**Labels:** typography, pipeline
**Estimate:** 1.0d
**Depends on:** #022
**Blocks:** #024

---

## Goal

Update `TypographyAdapter` and the mock implementation to accept `timeline.json` as
input and output one RGBA PNG per narration segment plus a timing manifest, instead of
a single static PNG for the whole scene.

---

## Scope

### `src/horror_story/adapters/typography/base.py`

New signature:

```python
def render(
    self,
    script: dict[str, Any],
    timeline: dict[str, Any],
    scene_id: str,
    seed: int,
    out_dir: Path,        # video/ directory — PNGs written here
    out_timing: Path,     # video/typography_<scene_id>_timing.json
    width: int,
    height: int,
) -> Path:               # returns out_timing path
```

Old single-PNG output (`typography_<scene_id>.png`) is removed.

### `src/horror_story/adapters/typography/mock.py`

- For each narration segment in `timeline["audio_tracks"]` (track_type == "narration"):
  - Render a Pillow RGBA PNG with EN + UA text for that segment only
  - Write `video/typography_<scene_id>_seg-N.png`
- For dialogue segments: include in the PNG of the narration segment they follow
- Write `video/typography_<scene_id>_timing.json` with real `start_s`/`end_s` from timeline

### `src/horror_story/cli.py`

- Pass `timeline` to Typography stage
- Pass `out_timing` path to Compositor stage instead of single PNG path

### `spec/schemas/typography_timing.schema.json`

Implement the schema defined in #022.

---

## Tests

- Update `tests/test_typography.py`: all tests must use the new signature
- Add test: N segments → N PNGs + 1 timing manifest
- Add test: timing manifest validates against `typography_timing.schema.json`
- Add test: `start_s`/`end_s` in timing manifest match values from input timeline

---

## Acceptance criteria

1. Mock adapter outputs one PNG per narration segment.
2. Timing manifest validates against schema.
3. `start_s`/`end_s` values come from `timeline.json`, not from `pacing_ms`.
4. All tests pass.
5. `mypy --strict` passes.
