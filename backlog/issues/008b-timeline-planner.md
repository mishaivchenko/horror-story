# Issue 008b — Timeline Synchronization Contract

**Labels:** `pipeline`, `sprint-02`
**Spec refs:** `spec/PIPELINE.md` §Stage 7.5; `spec/schemas/timeline.schema.json`
**Estimate:** 0.5 day
**Depends on:** #004, #006, #007, #008
**Blocks:** #009

## Goal

Define and implement the deterministic timing model the compositor will use.
No FFmpeg. No media generation. Pure JSON planning stage only.

## Inputs

| Artifact | Source stage |
|----------|--------------|
| `scripts/script_<id>.json` | #003 Script generator |
| `frames/motion_<scene_id>.json` | #007 MotionAdapter sidecar |
| `audio/ambient_<scene_id>.json` | #008 AudioAdapter sidecar |
| `video/typography_<scene_id>.json` | #006 TypographyAdapter sidecar |

## Output

```
video/timeline_<scene_id>.json   ← Scene Timeline artifact
```

## Timing rules

- Narration segments play sequentially in script order, starting at 0.0 s.
- Dialogue lines are inserted immediately after the segment named by
  `insert_after_segment`. If `null` or invalid segment id, appended at end
  ordered by `line_id`.
- Ambient: `start_s = 0.0`, `end_s = scene_duration_s`.
- Motion: `start_s = 0.0`, `end_s = scene_duration_s`.
- Typography overlay: `start_s = 0.0`, `end_s = scene_duration_s`.
- `scene_duration_s = max(motion_duration_s, audio_timeline_end_s, ambient_duration_s)`.

## Acceptance criteria

- [x] `timeline.schema.json` added to `spec/schemas/`
- [x] `horror_story.pipeline.timeline.plan_timeline()` implemented
- [x] 18 tests in `tests/test_timeline.py` passing
- [x] `mypy --strict` clean
- [x] `spec/PIPELINE.md` updated with Stage 7.5
- [x] No FFmpeg calls in timeline planner

## Status: COMPLETE
