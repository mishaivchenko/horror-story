# Checkpoint: After Issue #008 — Mock Ambient Audio Adapter

**Date:** 2026-05-24
**Commit:** 51eab3a
**Branch:** main
**Preceding issues:** #001 scaffold, #002 story parser, #003 script generator, #004 mock TTS, #005 mock image, #006 typography PNG overlay, #007 mock motion, #008 mock ambient audio

---

## Quality Metrics

| Metric | Result |
|---|---|
| pytest | 167 passed, 10 skipped, 0 failed |
| Skipped tests | 10 — all in `test_motion.py`, all require FFmpeg (see §FFmpeg Status) |
| Coverage | 94% overall |
| mypy --strict | Success: no issues found in 27 source files |
| Schema validation | 11 schemas loaded, all well-formed |

### Coverage gaps

| File | Coverage | Reason |
|---|---|---|
| `adapters/base.py` | 0% | Re-export module only; no executable lines |
| `adapters/motion/mock.py` | 40% | FFmpeg-dependent paths skipped in CI (no FFmpeg on this machine) |
| `pipeline/parse.py` | 90% | Two edge-case branches (separator-only input, empty result) |
| `models.py` | 99% | Mood tie-break path requires equal keyword counts |
| `__main__.py` | 0% | Entry-point shim; tested via integration, not unit tests |

`motion/mock.py` at 40% is expected and acceptable: the untested lines are the FFmpeg subprocess invocation paths that are gated by `@pytest.mark.skipif(not ffmpeg_available(), ...)`.

---

## Implemented Pipeline Stages

| # | Stage | Module | Status |
|---|---|---|---|
| #001 | Scaffold | `config.py`, `manifest.py`, `cli.py`, `schemas.py` | Complete |
| #002 | Story parser | `pipeline/parse.py`, `models.Scene` | Complete |
| #003 | Script generator | `pipeline/script.py`, `models.Script/Segment/DialogueLine` | Complete |
| #004 | TTS adapter (mock) | `adapters/tts/base.py`, `adapters/tts/mock.py` | Complete |
| #005 | Image adapter (mock) | `adapters/image/base.py`, `adapters/image/mock.py` | Complete |
| #006 | Typography overlay (mock) | `adapters/typography/base.py`, `adapters/typography/mock.py` | Complete |
| #007 | Motion adapter (mock) | `adapters/motion/base.py`, `adapters/motion/mock.py` | Complete |
| #008 | Ambient audio adapter (mock) | `adapters/audio/base.py`, `adapters/audio/mock.py` | Complete |

### Not yet implemented

#009 scene compositor, #010 final renderer, #011 CLI wiring/e2e, #012 CI hardening.

---

## Artifact Flow

```
Story text (.txt)
    │
    ▼ pipeline/parse.py
scenes/scene_<id>.json            [scene.schema.json]
    │
    ├─▼ pipeline/script.py
    │  scripts/script_<id>.json   [script.schema.json]
    │      │
    │      └─▼ adapters/tts/mock.py (per segment + dialogue line)
    │         audio/narration_<scene_id>_<seg_id>.wav
    │         audio/narration_<scene_id>_<seg_id>.json  [voice_line.schema.json]
    │         audio/dialogue_<scene_id>_<line_id>.wav
    │         audio/dialogue_<scene_id>_<line_id>.json  [voice_line.schema.json]
    │
    ├─▼ adapters/image/mock.py
    │  frames/keyframe_<scene_id>.png
    │  frames/keyframe_<scene_id>.json  [keyframe.schema.json]
    │
    ├─▼ adapters/motion/mock.py  (requires FFmpeg)
    │  frames/motion_<scene_id>.mp4
    │  frames/motion_<scene_id>.json  [motion_artifact.schema.json]
    │
    ├─▼ adapters/audio/mock.py
    │  audio/ambient_<scene_id>.wav
    │  audio/ambient_<scene_id>.json  [ambient_artifact.schema.json]
    │
    └─▼ adapters/typography/mock.py
       video/typography_<scene_id>.png   ← transparent RGBA overlay
       video/typography_<scene_id>.json  [typography_artifact.schema.json]

NOT YET GENERATED:
    video/scene_<scene_id>_composed.mp4  ← #009 compositor
    video/final_<story_id>.mp4           ← #010 renderer
```

---

## Implemented Adapters

### TTSAdapter
- **ABC:** `adapters/tts/base.py` — `synthesize(text, voice_id, language, pacing_ms, seed, out_path) -> Path`
- **Mock:** `adapters/tts/mock.py` — `MockTTSAdapter`
- **Artifacts:** mono WAV (44.1 kHz, 16-bit, silent) + voice_line sidecar JSON
- **Determinism:** same arguments → identical bytes (all-zero PCM; duration is exactly `round(44100 * pacing_ms / 1000)` frames)
- **Runtime deps:** stdlib `wave`, `struct` only
- **Limitations:** mono (not stereo); mock translation is reversed word order, not real Ukrainian

### ImageAdapter
- **ABC:** `adapters/image/base.py` — `generate(prompt, width, height, seed, out_path) -> Path`
- **Mock:** `adapters/image/mock.py` — `MockImageAdapter`
- **Artifacts:** RGB PNG (grey fill, scene label) + keyframe sidecar JSON
- **Determinism:** grey value = `seed % 128 + 64`; same seed → same pixel data
- **Runtime deps:** Pillow (dev dependency)
- **Limitations:** single flat grey colour; no scene content; label is first 30 chars of scene_id or prompt

### TypographyAdapter
- **ABC:** `adapters/typography/base.py` — `render(script_path, duration_s, width, height, fps, seed, out_path) -> Path`
- **Mock:** `adapters/typography/mock.py` — `MockTypographyAdapter`
- **Artifacts:** RGBA PNG (transparent canvas, bilingual text) + typography sidecar JSON
- **Determinism:** text content is deterministic; font size scaling is deterministic given width/height; no randomness
- **Runtime deps:** Pillow (dev dependency); no FFmpeg
- **Limitations:** static single-frame overlay (no per-segment timing); uses `ImageFont.load_default()` — no custom fonts; EN text in upper third, secondary below

### MotionAdapter
- **ABC:** `adapters/motion/base.py` — `animate(frame_path, duration_s, fps, effect, seed, out_path) -> Path`
- **Mock:** `adapters/motion/mock.py` — `MockMotionAdapter`
- **Artifacts:** H.264 MP4 (single repeated frame, no audio) + motion sidecar JSON
- **Determinism:** FFmpeg invoked with fixed, ordered args (no `-metadata` timestamps); same inputs → same bytes on the same FFmpeg version
- **Runtime deps:** FFmpeg binary on `PATH` at call time; Pillow for dimension extraction from source PNG
- **Limitations:** determinism is FFmpeg-version-sensitive (different FFmpeg versions may differ in output bytes); raises `FFmpegNotFoundError` if `ffmpeg` is absent; effect parameter is recorded in sidecar but not applied (single repeated frame only)

### AudioAdapter
- **ABC:** `adapters/audio/base.py` — `generate(mood, duration_s, seed, out_path) -> Path`
- **Mock:** `adapters/audio/mock.py` — `MockAudioAdapter`
- **Artifacts:** stereo WAV (44.1 kHz, 16-bit, 2-channel, silent) + ambient sidecar JSON
- **Determinism:** same arguments → identical bytes (all-zero interleaved stereo PCM; `n_frames = round(44100 * duration_s)`)
- **Runtime deps:** stdlib `wave`, `struct` only
- **Limitations:** mood parameter is validated (non-empty) but not used to vary output; all moods produce silence

---

## Artifact Graph

### Currently generated

| Artifact | Schema | Generator | Format |
|---|---|---|---|
| `scene_<id>.json` | `scene.schema.json` | `pipeline/parse.py` | JSON |
| `script_<id>.json` | `script.schema.json` | `pipeline/script.py` | JSON |
| `narration_<scene_id>_<seg_id>.wav` + `.json` | `voice_line.schema.json` | `adapters/tts/mock.py` | WAV + JSON |
| `dialogue_<scene_id>_<line_id>.wav` + `.json` | `voice_line.schema.json` | `adapters/tts/mock.py` | WAV + JSON |
| `keyframe_<scene_id>.png` + `.json` | `keyframe.schema.json` | `adapters/image/mock.py` | PNG + JSON |
| `motion_<scene_id>.mp4` + `.json` | `motion_artifact.schema.json` | `adapters/motion/mock.py` | MP4 + JSON |
| `ambient_<scene_id>.wav` + `.json` | `ambient_artifact.schema.json` | `adapters/audio/mock.py` | WAV + JSON |
| `typography_<scene_id>.png` + `.json` | `typography_artifact.schema.json` | `adapters/typography/mock.py` | PNG + JSON |

### Not yet generated

| Artifact | Schema | Blocked on |
|---|---|---|
| `scene_<scene_id>_composed.mp4` | `composed_scene.schema.json` | #009 compositor |
| `final_<story_id>.mp4` | `render_job.schema.json` | #010 renderer |
| `artifact_index.json` | `artifact_index.schema.json` | #009 / #011 |

---

## FFmpeg Status

**Where required:** `MockMotionAdapter.animate()` only. No other implemented stage invokes FFmpeg.

**Missing FFmpeg handling:** `ffmpeg_available()` checks `shutil.which("ffmpeg")` at call time. `MockMotionAdapter` raises `FFmpegNotFoundError` (a `RuntimeError` subclass) if called without FFmpeg. All 10 `test_motion.py` tests are decorated with `@pytest.mark.skipif(not ffmpeg_available(), reason="FFmpeg not found")` or `@pytest.mark.skipif(not ffprobe_available(), ...)`. Tests skip cleanly; they do not fail.

**Determinism / limitations for MP4 outputs:** FFmpeg is invoked with a fixed, ordered argument list and no `-metadata` flags. For a given FFmpeg binary version and source PNG, output bytes are identical across runs. However, output bytes are **not** guaranteed identical across different FFmpeg versions — the H.264 encoder may differ. This is acceptable for the mock: functional identity (duration, dimensions, no audio) is guaranteed; byte identity is best-effort.

**Tests skipped without FFmpeg (10 total):**

| Test | Skip condition |
|---|---|
| `test_mock_motion_writes_mp4` | FFmpeg not found |
| `test_mock_motion_duration_within_one_frame` | FFmpeg not found |
| `test_mock_motion_video_dimensions_match_source` | FFmpeg not found |
| `test_mock_motion_no_audio_stream` | ffprobe not found |
| `test_mock_motion_deterministic_bytes` | FFmpeg not found |
| `test_mock_motion_sidecar_exists` | FFmpeg not found |
| `test_mock_motion_sidecar_validates_schema` | FFmpeg not found |
| `test_mock_motion_sidecar_fields` | FFmpeg not found |
| `test_mock_motion_sidecar_paths_are_cwd_relative` | FFmpeg not found |
| `test_mock_motion_sidecar_effect_recorded_as_passed` | FFmpeg not found |

---

## Architecture Validation

| Constraint | Verdict | Evidence |
|---|---|---|
| Local-first | PASS | Zero network calls; no HTTP clients; `dependencies = []` in `pyproject.toml` |
| Deterministic | PASS | All mock adapters produce identical bytes given same inputs; no wall-clock timestamps; no unseeded random |
| Mock-first | PASS | Every adapter is a mock; all five ABCs have `MockX` implementations; no real provider code |
| No provider integrations | PASS | No API keys, no `requests`/`httpx`/`boto3`; no `.env` files |
| No distributed complexity | PASS | Single process; no queues, no async, no background workers, no sockets |
| No plugin framework | PASS | `AdapterFactory` is five `if name == "mock": return MockX()` static methods — no registry, no dynamic loading |
| Issue boundaries preserved | PASS | Each issue touched only its target module(s); no cross-stage imports introduced; `adapters/base.py` is a re-export shim only |
| One module per stage | PASS | `parse.py`, `script.py` are independent; no imports between pipeline stages |
| Pure function stages | PASS | `parse_story()` and `generate_script()` are `(config, input) -> output`; no side effects on module state |
| No global mutable state | PASS | No module-level mutable variables; all state flows through explicit function arguments |

---

## Technical Debt (Top 10)

1. **FFmpeg version lock for motion determinism.** `MockMotionAdapter` byte-determinism is FFmpeg-version-sensitive. If CI runs a different FFmpeg version than a developer's local machine, deterministic-bytes tests would diverge. The `test_mock_motion_deterministic_bytes` test checks same-run consistency, not cross-machine identity — this is acceptable now but becomes a risk when the compositor integration test compares composed output across environments.

2. **Motion skip coverage gap.** 10 motion tests are permanently skipped in environments without FFmpeg (including this development machine). The compositor (#009) will also depend on FFmpeg. If CI does not provide FFmpeg, the compositor will have the same coverage gap. CI hardening (#012) must install FFmpeg explicitly.

3. **Typography is a static single-frame overlay.** `MockTypographyAdapter` renders one PNG for the entire scene. Per-segment subtitle timing (different text appearing at different timestamps) is deferred to future work but not flagged in the spec as "future work" — it's described ambiguously. The compositor must not assume the typography PNG changes over time.

4. **`actual_duration_s` in ambient sidecar is rounded.** `MockAudioAdapter` stores `actual_duration_s = n_frames / 44100` where `n_frames = round(44100 * duration_s)`. For certain durations (e.g. 1.001 s) this can differ from the requested `duration_s` at the sub-millisecond level. The composed scene validator must use the `actual_duration_s` field, not the requested `duration_s`, when summing audio track lengths.

5. **Audio track timing for the compositor is unspecified at artifact level.** The script's `total_duration_ms` drives overall scene duration, but narration segments and dialogue lines each have their own `pacing_ms`. The compositor must implement sequential narration + interleaved dialogue logic from scratch — no artifact encodes the absolute start time of any audio clip. This is the most complex piece of undocumented logic entering #009.

6. **Artifact paths in sidecars are absolute at write time.** `MockAudioAdapter`, `MockMotionAdapter`, `MockImageAdapter`, and `MockTypographyAdapter` all store `str(out_path)` (an absolute path) in `output_path`. The `artifact_index.schema.json` schema describes `output_path` as "relative path." This is a latent contract mismatch that must be resolved before the artifact index is populated in #009/#011.

7. **`adapters/base.py` is a 0%-covered re-export shim.** It exists for backward compatibility and to satisfy the `__all__` contract. If any code imports `AudioAdapter` from `adapters.base` vs `adapters.audio.base`, they get the same object — but the indirection adds confusion. This file should be consolidated or eliminated once all downstream imports are updated.

8. **Mock translation placeholder is permanent.** `mock_translate()` reverses word order and prepends `[uk]`. Every sidecar JSON and script JSON will contain this placeholder text. Typography overlay will render garbage Ukrainian text. This is correct for the mock stage but creates a silent acceptance risk if a real translation adapter is never gated behind a spec acceptance criterion.

9. **No `output/fixtures/` for CI schema validation.** The CI workflow validates artifacts in `output/fixtures/`. This directory does not exist. The CI validate step passes vacuously. At minimum one fixture per schema (especially `composed_scene.schema.json` and `ambient_artifact.schema.json`) should be added before #012.

10. **`effect` parameter is recorded but not applied in `MockMotionAdapter`.** The sidecar records whatever `effect` string was passed (e.g. `"zoom"`, `"parallax"`), but the output MP4 is always a static repeated frame. A real adapter consumer checking `sidecar["effect"]` will believe the effect was applied. This is acceptable for the mock but should be documented explicitly in the adapter or via a `adapter_note` sidecar field.

---

## Remaining MVP Path

| Issue | Stage | Key dependency | Estimate |
|---|---|---|---|
| #009 | Scene compositor | FFmpeg; all stage #004–#008 adapters; audio timing logic | 1d |
| #010 | Final renderer | #009 composed MP4s per scene; FFmpeg concat | 0.5d |
| #011 | CLI wiring / e2e | All stages; `run` and `validate` de-stubbed | 0.5d |
| #012 | CI hardening | GitHub Actions; FFmpeg in CI; `output/fixtures/` | 0.5d |

The compositor (#009) is the highest-complexity remaining issue. It owns the only non-trivial algorithmic problem: computing absolute start times for all audio clips from per-segment `pacing_ms` offsets and the `insert_after_segment` dialogue interleaving field.

---

## Pre-#009 Checklist

- [x] All eight mock adapters implemented and tested
- [x] All adapter ABCs have the spec-exact signatures
- [x] `AdapterFactory` registers all five adapter types
- [x] `adapters/base.py` re-exports (no duplicate ABC definitions)
- [x] mypy --strict passes on all 27 source files
- [x] 167 tests pass; 10 skip cleanly (FFmpeg); 0 fail
- [x] All 11 schemas well-formed
- [ ] Audio timing logic for compositor documented in spec (gap — see debt item 5)
- [ ] `output/fixtures/` populated for CI (gap — see debt item 9)
- [ ] Absolute vs relative `output_path` contract resolved (gap — see debt item 6)

---

## Recommendation

**READY for #009.**

The mock adapter layer is complete and consistent. All inputs the compositor will consume (motion MP4, ambient WAV, narration WAVs, dialogue WAVs, typography PNG) are producible from a single scene fixture. The three open gaps above are pre-conditions for full CI validation (#012), not blockers for starting the compositor implementation.

The compositor author should read debt items 5 (audio timing), 3 (static typography), and 6 (absolute paths) before writing the first line of `pipeline/compositor.py`.
