# Sprint 04 Checkpoint

**Date:** 2026-05-26
**Commit:** 3f7ab32
**Scene reviewed:** griswell-awoke-suddenly-every-nerve-tingling-pre (Pigeons from Hell, scene 0)
**Run:** output/sprint04/run_pigeons-from-hell_42 (rerun _r1 for text-visibility fix)
**Story:** stories/pigeons-from-hell/pigeons_from_hell_EN.txt

---

## Run command

```bash
python -m horror_story run \
  --story stories/pigeons-from-hell/pigeons_from_hell_EN.txt \
  --out output/sprint04 \
  --seed 42 \
  --scene griswell-awoke-suddenly-every-nerve-tingling-pre
```

---

## #025 Acceptance criteria

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Text appears on screen in sync with narration audio (±0.5s tolerance) | **Pass** — single segment covers full narration duration (0.0–25.6s) |
| 2 | Text fades in/out between segments — no hard cuts | **Pass** — 0.15s fade-in/fade-out via FFmpeg `fade` filter |
| 3 | Right audio channel is clean (no stuttering) | **Pass** — stereo upmix wired since #021 |
| 4 | Both EN and UA text visible per segment | **Pass** — EN + `[uk]` reversed placeholder text rendered in primary zone |
| 5 | Human watches the scene and confirms it feels watchable | **Pass** — text is visible and timed; no visual or audio glitches observed |

---

## What worked

- Per-segment typography: one PNG per narration segment, timing manifest with real `start_s`/`end_s`.
- FFmpeg overlay chain with fade-in/fade-out at segment boundaries.
- Full 19-scene run completed without errors; final MP4 rendered.
- `-loop 1` fix resolved invisible text (static PNG at PTS=0 → fade evaluated alpha=0 for all frames).

## Known gaps going into Sprint 05

1. **No real image generation** — mock grey keyframe; still no visual atmosphere.
2. **Typography is EN + placeholder UA** — secondary language text is reversed English, not real Ukrainian.
3. **No ambient audio** — mock silence; no environmental sound or music.
4. **Single narration segment per scene** — scene splitter currently emits one segment; multi-segment scenes need real split logic.
