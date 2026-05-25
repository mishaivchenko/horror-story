# Issue #021 — Compositor: broken right channel in final audio

**Status:** Done
**Sprint:** 03
**Labels:** compositor, bug, audio
**Estimate:** 0.5d
**Depends on:** #009
**Blocks:** —

---

## Problem

Final MP4 has distorted/stuttering audio on the right channel. Left channel plays
correctly. Observed in `output/pigeons-test/run_pigeons-from-hell_42_r1/final_pigeons-from-hell_42.mp4`.

Root cause hypothesis: Kokoro writes mono WAV (1 channel). The `amix` filter in the
compositor mixes multiple mono inputs into a mono output. When FFmpeg encodes this as
stereo AAC it may produce phase artifacts or duplicate a single channel incorrectly.

---

## Investigation

1. Print the exact FFmpeg command the compositor builds (already logged to stdout as
   `[compositor]`). Capture it and run manually to reproduce.
2. Inspect the `amix` output: add `-filter_complex` debug dump or pipe to a WAV first.
3. Check whether the issue is in per-scene composed MP4s (look in `video/`) or only
   in the final concatenated file from the renderer.

---

## Fix candidates

- Explicitly upmix mono to stereo before `amix`:
  `[Ni]aformat=channel_layouts=stereo[aNi]` for each input.
- Or force mono output from `amix` and let the AAC encoder handle stereo expansion:
  add `pan=stereo|c0=c0|c1=c0` after `amix`.
- Or add `-ac 2` to the ffmpeg output flags consistently.

The fix must be verified by inspecting the output with `ffprobe` and listening to both
channels.

---

## Acceptance criteria

1. Final MP4 left and right channels are identical (mono content, stereo container).
2. No distortion or stuttering on either channel.
3. `ffprobe` reports `stereo`, `aac`, `44100 Hz`.
4. Existing compositor tests pass.
5. `mypy --strict` passes.
