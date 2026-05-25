# Issue #022 — Spec: move Typography after Timeline, define new contract

**Status:** Done
**Sprint:** 04
**Priority:** P0 — blocks #023, #024, #025
**Labels:** spec, architecture
**Estimate:** 0.5d
**Depends on:** —
**Blocks:** #023, #024, #025

---

## Goal

Update the spec to reflect a new stage order: Typography moves after Timeline.
Typography now reads `timeline.json` (real TTS timecodes) and outputs a per-segment
PNG sequence + timing manifest instead of a single static PNG.

---

## Changes required

### `spec/PIPELINE.md`

New stage order:
```
Stage 1:  Parse
Stage 2:  Script generator
Stage 3a: Narration TTS
Stage 3b: Dialogue TTS
Stage 4:  Keyframe
Stage 5:  Motion
Stage 6:  Ambient audio
Stage 7:  Timeline planner   ← was 7.5, now runs before Typography
Stage 8:  Typography overlay ← was 7, now reads timeline.json
Stage 9:  Compositor
Stage 10: Renderer
```

### New Typography contract

**Input:** `scripts/script_<id>.json` + `video/timeline_<id>.json`

**Output:**
- `video/typography_<scene_id>_seg-N.png` — RGBA PNG per segment (same Pillow rendering)
- `video/typography_<scene_id>_timing.json` — timing manifest:

```json
{
  "schema_version": "1.0",
  "scene_id": "...",
  "segments": [
    {
      "seg_id": "seg-0",
      "start_s": 0.0,
      "end_s": 3.2,
      "png": "typography_<scene_id>_seg-0.png",
      "text_en": "...",
      "text_uk": "..."
    }
  ]
}
```

### New Compositor contract

**Input:** now includes `video/typography_<scene_id>_timing.json` instead of
a single `typography_<scene_id>.png`.

Compositor builds FFmpeg overlay chain with per-segment `enable='between(t,start,end)'`
+ fade-in/fade-out filters.

### `spec/schemas/`

Add `typography_timing.schema.json`.

---

## Acceptance criteria

1. `spec/PIPELINE.md` reflects new stage order and new Typography I/O contract.
2. `spec/schemas/typography_timing.schema.json` exists and is valid JSON Schema.
3. No implementation changes in this issue — spec only.
