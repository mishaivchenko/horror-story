# Issue #025 — E2E: verify timed typography on real Kokoro scene

**Status:** Closed
**Sprint:** 04
**Priority:** P3 — final verification only
**Labels:** pipeline, acceptance
**Estimate:** 0.5d
**Depends on:** #021, #024
**Blocks:** —

---

## Goal

Manual acceptance run confirming that per-segment timed text overlays work correctly
with real Kokoro TTS audio on a single scene of Pigeons from Hell.

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

## Acceptance criteria

1. Text appears on screen in sync with narration audio (±0.5s tolerance).
2. Text fades in/out between segments — no hard cuts.
3. Right audio channel is clean (no stuttering — see #021).
4. Both EN and UA text visible per segment.
5. Human watches the scene and confirms it feels watchable.

No automated test — result recorded in sprint-04 checkpoint.
