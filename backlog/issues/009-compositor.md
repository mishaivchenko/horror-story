# Issue 009 — Scene compositor

**Labels:** `pipeline`, `sprint-02`
**Spec refs:** `spec/MVP.md` §F-09; `spec/PIPELINE.md` §Stage 8
**Estimate:** 1 day
**Depends on:** #006, #007, #008

## Goal

Implement `horror_story.pipeline.compositor` to combine the motion video, ambient audio,
narration/dialogue audio, and typography overlay into a single scene MP4 using FFmpeg.

## Acceptance criteria

- [ ] `compositor.compose_scene(scene_id, artifacts, manifest) -> Path` exists
- [ ] Output MP4 has a combined audio track (narration + dialogue mixed over ambient)
- [ ] Typography is overlaid on the motion video
- [ ] Duration matches `total_duration_ms` from script ± 1 frame
- [ ] Integration test runs the full per-scene stack (stages 1–8) on a 1-scene fixture
      and asserts a valid MP4 is produced
- [ ] `pytest tests/test_compositor.py` passes
- [ ] `mypy --strict` passes

## Tasks

1. Implement `compose_scene()` in `horror_story/pipeline/compositor.py`.
2. Design the FFmpeg filtergraph:
   - `amix` for audio mixing (narration + dialogue + ambient)
   - `overlay` for typography video
3. Add `tests/test_compositor.py` with integration test (requires FFmpeg; mark skip if absent).
4. Document the FFmpeg invocation in a comment for future adapter authors.

## Notes

- Audio timing: narration segments play sequentially; dialogue is interleaved at the
  `insert_after_segment` offsets; ambient plays for the full duration.
- Use `-shortest` or explicit `-t` to avoid duration drift.
