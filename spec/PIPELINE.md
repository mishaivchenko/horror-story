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

Transparent RGBA PNG with bilingual text rendered in constrained safe-area boxes.
No video output; no FFmpeg. Pillow only. The compositor composites this PNG onto the
motion video frames at Stage 8.

**Adaptive zones v1 layout (current mock contract):**
- Two possible zones: primary (narration) and secondary (dialogue, optional).
- **Primary zone:** bottom strip, full width minus margins, max 30% frame height.
  Contains narration EN text + secondary language text.
- **Secondary zone:** upper left or right strip, max 50% frame width, max 30% frame height.
  Present only when `dialogue_lines` is non-empty. Contains dialogue character + text.
- Zone side (left vs right) derived from `SHA-256(scene_id + ":" + seed)[0] % 2`.
- Each zone is a semi-transparent dark box (`rgba(0,0,0,160)`) with padding.
- Text is clamped to fit the box; overflow is truncated, never drawn outside the box.
- Opaque pixels must stay below 50% of total frame area.
- Zones must not overlap and must remain within frame bounds.
- Layout is fully deterministic from `scene_id`, `seed`, `width`, `height`, and script content.

**Typography stage scope — MVP contract:**
- Typography owns: text layout, font selection, canvas sizing, zone positioning.
- Typography does NOT: generate MP4, invoke FFmpeg, own subtitle timing, emit video of any kind.
- Output is always a single transparent RGBA PNG per scene.
- The compositor (Stage 8) is solely responsible for applying this overlay to video.

**Future work (Sprint 03+ only — NOT MVP):**
Per-segment timed typography, animated subtitles, per-frame PNG sequences, and
ASS/SRT subtitle pipelines are out of scope until at least Sprint 03. No spec, issue, or
implementation should describe typography producing MP4 or invoking FFmpeg.

---

## Stage 7.5: Timeline planner

**Module:** `horror_story.pipeline.timeline`
**Input:** `scripts/script_<id>.json`, motion sidecar, ambient sidecar, typography sidecar,
           all voice-line sidecars for the scene (`audio/narration_<scene_id>_<seg>.json`,
           `audio/dialogue_<scene_id>_<line>.json`)
**Output:** `video/timeline_<scene_id>.json`

Pure function — no FFmpeg, no media generation. Reads sidecar metadata only.

Timing rules:
- Narration segments play sequentially in script order, starting at 0.0 s.
- Dialogue lines are inserted immediately after the segment named by
  `insert_after_segment`. If that field is `null` or references a missing
  segment, the line is appended after all other tracks (fallback).
- Multiple dialogue lines sharing the same `insert_after_segment` are ordered
  by `line_id` (deterministic).
- Ambient audio: `start_s = 0.0`, `end_s = scene_duration_s`.
- Motion video: `start_s = 0.0`, `end_s = scene_duration_s`.
- Typography overlay: `start_s = 0.0`, `end_s = scene_duration_s`.
- `scene_duration_s = max(motion_duration_s, audio_timeline_end_s, ambient_duration_s)`.

**Timeline architectural law:**
`timeline.json` is the sole temporal authority for composition. The compositor MUST NOT:
- infer timing from media file durations
- reconstruct source paths from naming conventions
- calculate implicit scene durations
- invent track ordering

All timing, ordering, and source path information flows through `timeline.json`. Any
future system that modifies emotion, pacing, or scene rhythm MUST emit explicit changes
to `timeline.json` artifacts before the compositor runs. No compositor timing logic may
exist outside timeline artifacts.

See `spec/schemas/timeline.schema.json`.

---

## Stage 8: Scene compositor

**Module:** `horror_story.pipeline.compositor`
**Input:** `video/timeline_<scene_id>.json` + all referenced media artifacts
**Output:** `video/scene_<scene_id>_composed.mp4`

FFmpeg pipeline driven by the Stage 7.5 timeline artifact:
1. Alpha-composite the typography PNG overlay onto the motion video (`overlay` filter).
2. Mix narration + dialogue + ambient into single stereo audio track (`amix`),
   using the absolute `start_s` offsets from the timeline.
3. Mux video + audio into output MP4.

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
                 timeline-planner (waits for: script, tts-* sidecars, motion, audio, typography sidecars)
                 compositor (waits for: timeline, all media artifacts)
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
