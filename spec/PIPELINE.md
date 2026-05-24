# Pipeline Specification

**Status:** Draft

Each stage is a pure function with no side effects beyond writing its output artifact(s).
Stages are run sequentially per scene; scenes may be processed in parallel (future).

---

## Stage 0: Manifest initialization

**Input:** `pipeline.toml`, `story.txt`
**Output:** `manifest.json` (written once, never mutated after Stage 1 completes)

Stage 0 and Stage 1 (parse) run as a single atomic operation from the CLI's perspective:
the CLI calls `initialize_run(toml_path, story_path, out_dir)` which:
1. Reads `pipeline.toml` and `story.txt`.
2. Parses the story into scenes (Stage 1 logic).
3. Writes all `scene_<id>.json` files.
4. Writes `manifest.json` with the `scenes` list fully populated.
5. Writes `artifact_index.json` with initial entries for all expected artifacts.

After this function returns, `manifest.json` is immutable for the rest of the run. No
subsequent stage reads `story.txt` or writes to `manifest.json`.

See `spec/schemas/manifest.schema.json`.

---

## Stage 1: Story parser

**Module:** `horror_story.pipeline.parse`
**Input:** `story.txt` (raw text, passed directly — not re-read from disk in the stage fn)
**Output:** `list[Scene]` (in-memory; caller writes to disk)

**Scene boundary rule (MVP):** split on lines containing only `---`. The fixture
`tests/fixtures/mini-story.txt` must use this marker. Automatic paragraph-break detection
is MVP+ scope.

Responsibilities:
- Split story text into scenes at `---` markers.
- Assign stable `scene_id`: kebab-slug of first 8 non-stopword words, max 48 chars.
- Extract `visual_description`: first 2 sentences stripped of `"Character: text"` dialogue.
- Classify `mood` from keyword matching (vocabulary defined in `config.py`).
- Return `list[Scene]` dataclasses; file I/O is the caller's responsibility.

See `spec/schemas/scene.schema.json`.

---

## Stage 2: Script generator

**Module:** `horror_story.pipeline.script`
**Input:** `scenes/scene_<id>.json`
**Output:** `scripts/script_<id>.json`

Responsibilities:
- Split scene text into narration segments (≤ 40 words each).
- Extract dialogue lines by `"[Character]: [text]"` pattern.
- Assign `segment_id` (sequential within scene).
- Generate `pacing_ms` per segment (100 ms per word, minimum 500 ms).
- Populate `text_uk` with mock translation (word order reversed + `[uk]` prefix).
- Assign `voice_id` to each dialogue line from manifest voice map.

See `spec/schemas/script.schema.json`.

---

## Stage 3a: Narration TTS

**Module:** `horror_story.adapters.tts.mock` (via `TTSAdapter`)
**Input:** `scripts/script_<id>.json` (narration segments)
**Output:** `audio/narration_<scene_id>_<seg_id>.wav` per segment

Each WAV: mono, 44.1 kHz, 16-bit PCM. Duration = `pacing_ms`.

---

## Stage 3b: Dialogue TTS

**Module:** `horror_story.adapters.tts.mock` (via `TTSAdapter`)
**Input:** `scripts/script_<id>.json` (dialogue lines)
**Output:** `audio/dialogue_<scene_id>_<line_id>.wav` per line

Same WAV spec as narration.

---

## Stage 4: Keyframe generation

**Module:** `horror_story.adapters.image.mock` (via `ImageAdapter`)
**Input:** `scenes/scene_<id>.json` (`.visual_description`, `.mood`)
**Output:** `frames/keyframe_<scene_id>.png`

PNG: 3840×2160 (or lower for dev mode). Mock: grey background, scene ID as white text.

---

## Stage 5: Motion / VFX

**Module:** `horror_story.adapters.motion.mock` (via `MotionAdapter`)
**Input:** `frames/keyframe_<scene_id>.png`, duration from script
**Output:** `frames/motion_<scene_id>.mp4`

MP4: H.264, no audio. fps = caller-supplied value from render config (default 24).
Duration = sum of `pacing_ms` for the scene. Mock: repeats the keyframe for the full duration.

---

## Stage 6: Ambient audio

**Module:** `horror_story.adapters.audio.mock` (via `AudioAdapter`)
**Input:** `scenes/scene_<id>.json` (`.mood`), duration from script
**Output:** `audio/ambient_<scene_id>.wav`

WAV: stereo, 44.1 kHz, 16-bit PCM. Duration = scene duration. Mock: silence.

---

## Stage 7: Typography overlay

**Module:** `horror_story.adapters.typography.mock` (via `TypographyAdapter`)
**Input:** `scripts/script_<id>.json` (all segments + dialogue, both languages)
**Output:** `video/typography_<scene_id>.png`

Transparent RGBA PNG with bilingual text overlaid (EN upper area, secondary language
below). No video output; no FFmpeg. Pillow only. The compositor composites this PNG
onto the motion video frames at Stage 8.

---

## Stage 8: Scene compositor

**Module:** `horror_story.pipeline.compositor`
**Input:** `frames/motion_<scene_id>.mp4`, all audio WAVs, `video/typography_<scene_id>.png`
**Output:** `video/scene_<scene_id>_composed.mp4`

FFmpeg pipeline:
1. Alpha-composite the typography PNG overlay onto the motion video (`overlay` filter).
2. Mix narration + dialogue + ambient into single stereo audio track (`amix`).
3. Mux video + audio into output MP4.

All timing is driven by `pacing_ms` from the script. Narration and ambient play
simultaneously; dialogue is interleaved with narration gaps.

---

## Stage 9: Final renderer

**Module:** `horror_story.pipeline.renderer`
**Input:** All `video/scene_<id>_composed.mp4` in scene order, manifest metadata
**Output:** `final_<story_id>_<seed>.mp4`

FFmpeg concat:
1. Generate 3-second title card (story title + author, black background).
2. Concatenate all scene videos in manifest order.
3. Append 2-second end card (black fade).
4. Encode to H.264 / AAC at target resolution.

---

## Stage ordering and dependencies

```
manifest  ──► parse  ──► script  ──► [tts-narration, tts-dialogue]
                                  ──► image  ──► motion
                                  ──► audio
                                  ──► typography
                 compositor (waits for: motion, tts-*, audio, typography)
                 renderer (waits for: all composited scenes)
```

Scene-level stages (parse through typography) are independent across scenes.
The compositor and renderer are serial.

---

## Regeneration contract

**`--scene <id>` (partial re-run):**
1. The run directory and `manifest.json` must already exist.
2. Only the stages for the named scene are re-executed.
3. New artifact files are written with a `_r<n>` suffix (e.g. `keyframe_abc_r1.png`).
4. `artifact_index.json` is updated to point to the new `_r<n>` files for that scene.
5. The final renderer is re-run to incorporate the updated scene.
6. All other scenes' artifacts are unchanged.

**`--regen` (full re-run, new version):**
1. A new run directory is created: `run_<story_id>_<seed>_r<n>`.
2. The full pipeline executes from scratch in the new directory.
3. The original run directory is untouched.

**`artifact_index.json`:**
- Written at Stage 0 with `"status": "pending"` for all expected artifacts.
- Each stage updates its entries to `"status": "complete", "path": "<relative_path>"`.
- The renderer reads `artifact_index.json` to locate composed scene artifacts.
- On `--scene` re-run, only affected entries are updated.

**Latest artifact selection:**
- The renderer always reads composed scene paths from `artifact_index.json["scenes"]`.
- If an entry has a `_r<n>` path, that is the authoritative artifact for that scene.

**Dependency invalidation:**
- Regenerating a scene marks its downstream entries in `artifact_index.json` as `"pending"`.
- The renderer will not run if any composed scene entry is `"pending"`.

## Error handling

- Each stage function raises `PipelineError(scene_id, stage, reason)` on failure.
- The CLI catches per-scene errors, logs them, and continues with remaining scenes.
- After all scenes, the CLI prints a summary of failed scenes and exits non-zero if any failed.
- A partially completed run can be resumed via `--scene <id>` for each failed scene.
