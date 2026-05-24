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

### Status: COMPLETE (adaptive zones v1 shipped post-MVP)

### Acceptance criteria
- [x] `TypographyAdapter` ABC in `horror_story/adapters/typography/base.py` with signature:
      `render(self, script_path: Path, duration_s: float, width: int, height: int, fps: int, seed: int, out_path: Path) -> Path`
- [x] Output is a **transparent RGBA PNG** (not MP4); `out_path` ends in `.png`
- [x] Narration text in bottom safe-area box; dialogue (when present) in upper left/right box
- [x] Both language tracks visible within constrained semi-transparent boxes
- [x] Opaque pixels < 50% of frame — image remains dominant visual element
- [x] Zone layout deterministic from `scene_id + seed` (SHA-256, not `hash()`)
- [x] No zone overlap; all zones within frame bounds
- [x] Same inputs + seed → same output bytes (deterministic)
- [x] `typography_<scene_id>.json` sidecar written at `out_path.with_suffix('.json')` and
      validates against `spec/schemas/typography_artifact.schema.json`
- [x] Adapter registered: `AdapterFactory.get_typography("mock") -> MockTypographyAdapter`
- [x] `pytest tests/test_typography.py` passes (28 tests)
- [x] `mypy --strict` passes

### Adaptive zones v1 contract (added after MVP)

Layout uses up to two zones:
- **Primary** (narration): bottom strip, full width minus margins, 30% frame height max.
- **Secondary** (dialogue): upper left or right, 50% frame width max, 30% frame height max.
  Only rendered when `dialogue_lines` is non-empty.

Zone side (left vs right) is derived from `SHA-256(scene_id + ":" + seed)[0] % 2`.
Text is clamped (truncated) rather than overflowing. Background box: `rgba(0,0,0,160)`.

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
