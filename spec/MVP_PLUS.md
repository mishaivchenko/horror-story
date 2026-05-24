# MVP+ Specification — Pigeons from Hell

**Status:** Draft
**Prerequisite:** MVP (3-scene vertical slice) must be complete first. See `spec/MVP.md`.
**Story:** *Pigeons from Hell* by Robert E. Howard (1938, public domain)
**Target languages:** English (primary) + Ukrainian (secondary)

---

## Goal

Run the validated MVP pipeline on the full *Pigeons from Hell* story (≥ 10 scenes) using
mock adapters, then begin replacing mocks with real providers one at a time.

---

## MVP+ is NOT

- A production-quality video (mock adapters produce placeholder media in the first pass)
- A fully automated hands-off process (some manual review expected)
- A deployable service
- Sprint 01 or Sprint 02 scope — this begins after the MVP is shipped

---

## Feature list

### F-01: Story ingestion
- The pipeline accepts a plain-text story file as input.
- **Scene boundary rule (MVP):** a line containing only `---` (three dashes) marks a
  scene break. The parser splits on this marker. Fixtures must use this marker explicitly.
  Automatic boundary detection by word count is MVP+ scope only.
- Each scene is assigned a stable `scene_id` (kebab-slug of first 8 words, max 48 chars).
- Output: `manifest.json` (written once, then immutable) + one `scene_<id>.json` per scene.
  Scene IDs are populated in `manifest.json` by the parse stage — this is the only write
  to `manifest.json` after initial creation. No further mutation occurs.
- **Acceptance:** Parser produces exactly the scenes delimited by `---` in the input.
  Every scene JSON validates against `spec/schemas/scene.schema.json`.
  Manifest validates against `spec/schemas/manifest.schema.json`.

### F-02: Bilingual script generation
- For each scene, generate a narration script and dialogue lines in EN and UK.
- In mock mode: narration is the original scene text; dialogue is extracted by
  `"[Character]:" → dialogue_line` pattern; Ukrainian is a reversed-word placeholder.
- Script carries speaker labels, emotion hints, and pacing markers.
- Output: `script_<scene_id>.json` per scene.
- **Acceptance:** Every script JSON validates against `spec/schemas/script.schema.json`.
  Mock Ukrainian text is present for every narration segment and dialogue line.

### F-03: Narration TTS
- Converts narration segments to audio files (WAV, 44.1 kHz, mono).
- Mock adapter: generates a silent WAV of exactly `pacing_ms` duration.
- Interface: `TTSAdapter.synthesize(text, voice_id, language, pacing_ms, seed, out_path) -> Path`
- Output: `narration_<scene_id>_<segment_id>.wav`
- **Acceptance:** All WAV files are valid, duration matches `pacing_ms` ± 5%.
  Mock adapter is unit-tested in isolation. Same inputs + seed → same bytes.

### F-04: Dialogue TTS
- Same interface and mock behavior as F-03; uses per-character voice IDs.
- Character voice map is defined in `manifest.json`.
- **Acceptance:** Each dialogue line produces a separate WAV named
  `dialogue_<scene_id>_<line_id>.wav`. Mock produces silent audio of `pacing_ms` duration.

### F-05: Keyframe illustration
- Generates one still image per scene (PNG, target 3840×2160, mock: solid color + text).
- Image prompt is derived from the scene `visual_description` field in the scene JSON.
- Mock adapter: produces a grey PNG with scene ID overlaid in white text.
- Interface: `ImageAdapter.generate(prompt, width, height, seed, out_path) -> Path`
- Output: `keyframe_<scene_id>.png`
- **Acceptance:** All PNGs exist, are valid, correct resolution. Mock is unit-tested.

### F-06: Motion / VFX
- Applies subtle animation to the keyframe (parallax, slow zoom, light flicker).
- Mock adapter: outputs the input PNG as a silent MP4 (single repeated frame) of
  `duration_s` seconds at the caller-supplied `fps`.
- Interface: `MotionAdapter.animate(frame_path, duration_s, fps, effect, seed, out_path) -> Path`
- Output: `motion_<scene_id>.mp4`
- **Acceptance:** Valid MP4, correct duration, mock is unit-tested.

### F-07: Ambient audio
- Generates an ambient sound loop for the scene (WAV, stereo, 44.1 kHz).
- Mock adapter: generates a silent stereo WAV of the specified duration.
- Ambient type is derived from scene `mood` field (`night_insects`, `wind`, `silence`, etc.)
- Interface: `AudioAdapter.generate(mood, duration_s, seed, out_path) -> Path`
- Output: `ambient_<scene_id>.wav`
- **Acceptance:** Valid WAV, stereo, correct duration. Mock is unit-tested.

### F-08: Typography overlay
- Renders bilingual subtitle/overlay text as a transparent RGBA PNG.
- EN text in upper area; secondary language below in smaller typeface.
- Mock adapter: renders text onto a transparent canvas using Pillow. No FFmpeg.
- Output: `typography_<scene_id>.png` (transparent RGBA PNG overlay)
- The compositor (F-09) is responsible for compositing this PNG onto video frames.
- **Acceptance:** PNG is RGBA, text is legible, both languages present. Mock is unit-tested.

### F-09: Scene compositor
- Combines motion video, ambient audio, narration audio, dialogue audio, and the
  typography transparent PNG overlay into a single scene video (MP4).
- Uses FFmpeg for all mixing and compositing. All timings driven by script `pacing` field.
- FFmpeg overlay filter alpha-composites the typography PNG onto the motion video.
- Output: `scene_<scene_id>_composed.mp4`
- **Acceptance:** Valid MP4 with audio track. Duration matches sum of dialogue + narration.

### F-10: Final renderer
- Concatenates all scene videos in order, adds title card and end card.
- Output: `final_<story_id>_<seed>.mp4` at 3840×2160, H.264, AAC.
- **Acceptance:** Valid MP4, correct resolution. Identical seed → identical SHA-256 when
  using only mock adapters.

### F-11: CLI
- Single entry point: `python -m horror_story run --story <path> --out <dir> [--scene <id>]`
- `--scene` re-runs only the specified scene and re-renders from that point.
- `--dry-run` prints the pipeline plan without executing.
- `--validate` runs schema validation on all artifacts in the output dir.
- **Acceptance:** All flags work. `--dry-run` produces no files. `--validate` catches
  a deliberately broken fixture.

---

## Non-functional requirements

- **Speed (mock mode):** Full pipeline for *Pigeons from Hell* (~20 scenes) completes in
  under 60 seconds on a MacBook Pro M2.
- **Reproducibility:** `--seed 42` always produces the same artifacts with mock adapters.
- **Observability:** Each stage logs `[STAGE] scene_id → output_path` to stdout.
- **Error isolation:** A failure in one scene does not abort other scenes; failed scenes
  are reported at the end.

---

## Out of scope for MVP+

- Real media adapters
- GPU acceleration
- Progress bar / TUI
- Web preview
- Any scene > 2 minutes of audio
