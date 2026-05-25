# Issue #024 — Compositor: per-segment timed text overlays with fade

**Status:** Open
**Sprint:** 04
**Priority:** P2
**Labels:** compositor, typography, animation
**Estimate:** 1.0d
**Depends on:** #023
**Blocks:** #025

---

## Goal

Update the compositor to use `typography_timing.json` instead of a single static PNG,
building an FFmpeg overlay chain where each segment's text fades in and out at the
correct timecode.

---

## Scope

### `src/horror_story/pipeline/compositor.py`

Replace single `[overlay_path]` with a chain of per-segment overlays:

```python
# For each segment in timing manifest:
# [base][seg_N_png]overlay=enable='between(t,start,end)':
#   fade-in 0.15s at start, fade-out 0.15s before end
```

FFmpeg filter graph structure:
```
[0:v]              ← motion video
[1:v]              ← seg-0 PNG, enabled between(t, 0.0, 3.2) with fade
[2:v]              ← seg-1 PNG, enabled between(t, 3.2, 6.1) with fade
...
[N:v]              ← seg-N PNG
chain: [0][1]overlay→tmp0; [tmp0][2]overlay→tmp1; ... → [video_out]
```

Fade expression using FFmpeg `alpha` channel:
```
alpha=if(lt(t-start, 0.15), (t-start)/0.15, if(gt(t, end-0.15), (end-t)/0.15, 1))
```

### `src/horror_story/pipeline/compositor.py` — `compose_scene()`

- Accept `timing_path: Path` instead of `overlay_path: Path`
- Load `typography_timing.json`
- Build overlay chain from segments list

---

## Tests

- Add test: compositor with 3-segment timing manifest builds correct FFmpeg command
- Verify `enable=` expressions are correct for each segment
- Existing compositor tests updated to use timing manifest fixture

---

## Acceptance criteria

1. Each text segment appears and disappears at the correct time in the composed MP4.
2. Fade-in and fade-out are 0.15s each.
3. No text visible before first segment or after last segment.
4. Existing audio mixing behavior unchanged.
5. `mypy --strict` passes.
