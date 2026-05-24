# Issue 006 — Typography overlay adapter (mock-first)

**Labels:** `adapter`, `sprint-02`
**Spec refs:** `spec/MVP.md` §F-08; `spec/MVP_PLUS.md` §F-08; `spec/PIPELINE.md` §Stage 7
**Estimate:** 0.5 day
**Depends on:** #003

### Goal
Define the `TypographyAdapter` ABC and implement `MockTypographyAdapter` that renders
bilingual subtitle overlays as a **transparent PNG** using Pillow.

Typography is NOT responsible for video generation. It produces a single composite-ready
transparent overlay image. FFmpeg / video composition is the compositor's responsibility
(issue #009).

### Acceptance criteria
- [ ] `TypographyAdapter` ABC in `horror_story/adapters/typography/base.py` with signature:
      `render(self, script_path: Path, duration_s: float, width: int, height: int, fps: int, seed: int, out_path: Path) -> Path`
- [ ] Output is a **transparent RGBA PNG** (not MP4); `out_path` ends in `.png`
- [ ] EN text rendered in upper area of the transparent canvas
- [ ] Secondary language text rendered below EN text in smaller font
- [ ] Both language tracks visible when composited onto any background (RGBA mode)
- [ ] Same inputs + seed → same output bytes (deterministic)
- [ ] `typography_<scene_id>.json` sidecar written at `out_path.with_suffix('.json')` and
      validates against `spec/schemas/typography_artifact.schema.json`
- [ ] Adapter registered: `AdapterFactory.get_typography("mock") -> MockTypographyAdapter`
- [ ] `pytest tests/test_typography.py` passes with ≥ 85% coverage on `typography/`
- [ ] `mypy --strict` passes

### Output artifact
```
video/typography_<scene_id>.png   ← transparent RGBA PNG overlay
video/typography_<scene_id>.json  ← sidecar (typography_artifact schema)
```

### Tasks
1. Define `TypographyAdapter` ABC in `horror_story/adapters/typography/base.py`.
2. Implement `MockTypographyAdapter` using Pillow: render EN + secondary text onto a
   transparent `RGBA` canvas; save as PNG.
3. Add `get_typography()` to `AdapterFactory`.
4. Write unit tests: PNG mode is `RGBA`, both language texts visible via pixel sampling,
   byte-level determinism, sidecar schema validation.

### Notes
- Default font: `ImageFont.load_default()` is acceptable for mock.
- No FFmpeg dependency in this stage. PNG output only.
- The compositor (issue #009) is responsible for using `overlay` to composite this PNG
  onto the motion video frames.
- The real adapter will produce per-segment timed PNG frames — that is future work.
