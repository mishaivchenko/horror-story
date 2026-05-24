# Issue 009 — Scene compositor

**Labels:** `pipeline`, `sprint-02`
**Spec refs:** `spec/MVP.md` §F-09; `spec/PIPELINE.md` §Stage 8
**Estimate:** 1 day
**Depends on:** #006, #007, #008

## Goal

Implement `horror_story.pipeline.compositor` to combine the motion video, ambient audio,
narration/dialogue audio, and typography PNG overlay into a single scene MP4 using FFmpeg.

The compositor is the only stage responsible for FFmpeg. Upstream stages (including
typography) do not invoke FFmpeg.

## Inputs

| Artifact | Source stage | Format |
|----------|--------------|--------|
| `frames/motion_<scene_id>.mp4` | #007 MotionAdapter | H.264 MP4, no audio |
| `audio/narration_<scene_id>_<seg>.wav` | #004 TTSAdapter | mono WAV per segment |
| `audio/dialogue_<scene_id>_<line>.wav` | #004 TTSAdapter | mono WAV per line |
| `audio/ambient_<scene_id>.wav` | #008 AudioAdapter | stereo WAV |
| `video/typography_<scene_id>.png` | #006 TypographyAdapter | transparent RGBA PNG |

## Output

```
video/scene_<scene_id>_composed.mp4   ← H.264 + AAC scene video
```

## Acceptance criteria

- [x] `compositor.compose_scene(timeline_path, out_path) -> Path` exists
- [x] Output MP4 has a combined audio track (narration + dialogue mixed over ambient)
- [x] Typography PNG overlay is composited onto the motion video using FFmpeg `overlay`
      filter (RGBA alpha blending)
- [x] Duration matches `duration_s` from timeline via explicit `-t` flag
- [x] Integration test runs the full per-scene stack (stages 1–8) on a 1-scene fixture
      and asserts a valid MP4 is produced (skipped when FFmpeg absent)
- [x] `pytest tests/test_compositor.py` passes (11 passed, 1 skipped)
- [x] `mypy --strict` passes

## Status: COMPLETE

## Tasks

1. Implement `compose_scene()` in `horror_story/pipeline/compositor.py`.
2. Design the FFmpeg filtergraph:
   - `overlay` to alpha-composite the typography PNG onto the motion video
   - `amix` for audio mixing (narration + dialogue + ambient)
3. Add `tests/test_compositor.py` with integration test (requires FFmpeg; mark skip if absent).

## Notes

- The typography PNG is a static overlay for the full scene duration. Per-segment timing
  is future work.
- Audio timing: narration segments play sequentially; dialogue is interleaved at the
  `insert_after_segment` offsets; ambient plays for the full duration.
- Use `-shortest` or explicit `-t` to avoid duration drift.
- Log the exact FFmpeg command at DEBUG level.
