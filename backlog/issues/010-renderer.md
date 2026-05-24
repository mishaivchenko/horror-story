# Issue 010 — Final renderer

**Labels:** `pipeline`, `sprint-02`
**Spec refs:** `spec/MVP.md` §F-10; `spec/PIPELINE.md` §Stage 9; `spec/schemas/render_job.schema.json`
**Estimate:** 0.5 day
**Depends on:** #009

## Goal

Implement `horror_story.pipeline.renderer` to concatenate all scene MP4s, add title and
end cards, and produce the final `final_<story_id>_<seed>.mp4`.

## Status: COMPLETE

## Acceptance criteria

- [x] `renderer.render_final(manifest, scene_paths) -> Path` exists
- [x] Output MP4: H.264 video, AAC audio, correct resolution from manifest
- [x] Title card: 3 seconds, story title + author, white text on black
- [x] End card: 2 seconds, black fade
- [x] `render_job.json` written and validates against `spec/schemas/render_job.schema.json`
- [x] SHA-256 of output written to `render_job.json`
- [x] Determinism test: two runs with same seed and mock adapters produce identical SHA-256
- [x] `pytest tests/test_renderer.py` passes (requires FFmpeg; skip if absent)
- [x] `mypy --strict` passes

## Tasks

1. Implement `render_final()` in `horror_story/pipeline/renderer.py`.
2. Generate title card as a PNG (Pillow), convert to 3s video (FFmpeg).
3. Use FFmpeg concat demuxer with a generated `concat.txt` list.
4. Compute and record SHA-256 of the output.
5. Write determinism test as part of the integration test suite.
