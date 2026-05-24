# Issue #017 — Pigeons from Hell: story file + real scene run

**Status:** Open
**Sprint:** 03
**Labels:** pipeline, atmosphere
**Estimate:** 0.5d
**Depends on:** #013, #014, #015, #016
**Blocks:** #018

---

## Goal

Run the full pipeline on the first real scene of *Pigeons from Hell* using Kokoro TTS,
producing a watchable MP4 with synthesized narration.

---

## Scope

### 1. Add story file

`stories/pigeons-from-hell/story.txt`

Full public-domain text of *Pigeons from Hell* (Robert E. Howard, 1938) with `---` scene
boundary markers inserted at natural dramatic breaks. Scene 1 must be ≤ 30 seconds of
narration (≈ 70–90 words).

### 2. Add pipeline config

`stories/pigeons-from-hell/pipeline.toml`

```toml
[story]
id = "pigeons-from-hell"
title = "Pigeons from Hell"
primary_language = "en"
secondary_language = "uk"
seed = 42

[render]
width = 1920
height = 1080
fps = 24
codec = "libx264"
audio_codec = "aac"

[adapters]
tts = "kokoro"
image = "mock"
motion = "mock"
audio = "mock"
typography = "mock"

[voices]
narrator_en = "narrator_en"
zanner = "character_en"
Branner = "character_en"
```

### 3. Run command

```bash
python -m horror_story run \
  --story stories/pigeons-from-hell/story.txt \
  --out output/sprint03 \
  --scene <scene-1-id> \
  --seed 42
```

Confirm `output/sprint03/.../final_pigeons-from-hell_42.mp4` is produced and playable.

---

## Acceptance criteria

1. Pipeline completes without error for Scene 1.
2. Final MP4 exists and is a valid video file.
3. Narration audio is synthesized speech (not silent).
4. Human can open and watch the MP4.

No automated test is added for this issue — it is a manual acceptance run.
Result is recorded in checkpoint-sprint03.md (#018).
