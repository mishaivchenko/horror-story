# Issue 008 — Typography overlay adapter (mock-first)

**Labels:** `adapter`, `sprint-02`
**Spec refs:** `spec/MVP.md` §F-08; `spec/MVP_PLUS.md` §F-08; `spec/PIPELINE.md` §Stage 7
**Estimate:** 0.5 day
**Depends on:** #003, #006

## Goal

Define the `TypographyAdapter` ABC and implement `MockTypographyAdapter` that renders
bilingual subtitle overlays onto video frames using Pillow, outputting an MP4.

## Acceptance criteria

- [ ] `TypographyAdapter` ABC in `horror_story/adapters/typography/base.py` with signature:
      `render(self, script_path: Path, duration_s: float, width: int, height: int, fps: int, seed: int, out_path: Path) -> Path`
- [ ] Output MP4: H.264, correct resolution and duration, no audio
- [ ] EN text rendered in upper third of frame; secondary language below in smaller font
- [ ] Both language tracks visible in at least one sampled frame (assert via Pillow frame
      inspection before FFmpeg encode, or FFmpeg thumbnail extraction)
- [ ] Same inputs + seed → same output bytes
- [ ] Adapter registered: `AdapterFactory.get_typography("mock") -> MockTypographyAdapter`
- [ ] `pytest tests/test_typography.py` passes with ≥ 85% coverage on `typography/`
- [ ] `mypy --strict` passes

## Tasks

1. Define `TypographyAdapter` ABC.
2. Implement `MockTypographyAdapter`: render one Pillow frame per segment (text burned in),
   write frames to a temp dir, encode to MP4 with FFmpeg.
3. Add `get_typography()` to `AdapterFactory`.
4. Write unit tests using a minimal 1-segment script fixture; skip if FFmpeg absent.

## Notes

- Default font: bundled system font fallback (`ImageFont.load_default()` is acceptable for mock).
- The real adapter will use proper font files and timed subtitle tracks — that's future work.
