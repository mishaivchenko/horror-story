# Sprint 06 — Bilingual Text, Ambient Atmosphere, and Multi-Scene Validation

**Status:** Planned
**Prerequisite:** Sprint 05 complete — real AI keyframe via FLUX.1-schnell, per-stage
metrics, image style suffix all working.

---

## Goal

At the end of Sprint 06, a human can run the full pipeline on the first three scenes of
*Pigeons from Hell* and watch a video that reads correctly in both English and Ukrainian,
carries audible environmental atmosphere (night insects, wind, or silence depending on
scene mood), and displays all narration text on screen without truncation. The result is
still not a finished horror film — animation is still a zoom and TTS is still Kokoro —
but it crosses the threshold from technically correct to atmospherically legible.

---

## Sprint 06 is NOT

- A full 19-scene render. Three scenes is the validation target.
- Real Ukrainian TTS. The secondary-language audio channel remains English (Kokoro) for
  this sprint; only the on-screen typography uses real Ukrainian text.
- Any new animation beyond the existing zoom effect.
- A `--tts-adapter` CLI flag or any new adapter overrides beyond `--image-adapter`.
- LLM-based translation. The existing `pijons_from_hell.txt` parallel translation is the
  sole source; no API calls.
- Ambient audio assets committed to the repo. Asset files live outside the repo at a
  path configured in `pipeline.toml` (gitignored); only the adapter code is committed.

---

## Issues

| # | Title | Priority | Estimate | Depends on |
|---|-------|----------|----------|------------|
| #028 | Typography: auto-split long narration segments into timed sub-segments | P1 | 1.5d | — |
| #031 | Script: parallel-text Ukrainian translation from `pijons_from_hell.txt` | P1 | 1.5d | — |
| #032 | Ambient audio: mood-mapped looped WAV adapter | P2 | 1.5d | — |
| #033 | Validation: full 3-scene run end-to-end checkpoint | P2 | 0.5d | #028, #031, #032 |

Total estimated effort: ~5 days.

---

## Acceptance criteria

1. All narration text appears on screen without truncation for the Griswell opening scene
   (78-word segment produces ≥ 3 timed sub-segment PNGs).
2. Typography overlays show real Ukrainian Cyrillic text, not `[uk]`-prefixed reversed
   English.
3. Composed scene MP4s contain a non-silent ambient audio track that matches the scene's
   mood (when asset files are present at configured path).
4. A full pipeline run over 3+ scenes completes without error using `tts = "kokoro"`,
   `image = "mock"`, `audio = "loop"` (with assets on disk).
5. `python -m horror_story run --validate` reports zero validation errors on the Sprint
   06 output directory.
6. `checkpoint-sprint06.md` documents a human observation: "secondary language text is
   legible" and "ambient audio is audible."
7. `pytest` passes (all tests, 1 skipped smoke test). `mypy --strict src/` passes.

---

## Issue notes

### #028 — Typography: auto-split long narration segments

Already fully specified in `backlog/issues/028-typography-auto-split.md`. Fix is entirely
inside `MockTypographyAdapter.render()` — no schema, no CLI, no adapter interface
changes. The bug causes narration segments of 78+ words (the Griswell opening) to silently
drop roughly half their text from the screen.

---

### #031 — Script: parallel-text Ukrainian translation

**Problem.** Every rendered frame shows reversed English prefixed with `[uk]`.

**Approach.** `stories/pigeons-from-hell/pijons_from_hell.txt` already exists. A new
`horror_story/pipeline/translate.py` module provides `ParallelTextTranslator`:

- Constructor: `__init__(self, text: str)` — loads the full secondary-language text.
- `translate_segment(scene_index: int, segment_index: int, fallback: str) -> str` —
  returns the corresponding Ukrainian paragraph chunk or `fallback` if alignment fails.
- Alignment strategy: split secondary text into scenes by the same section-number heading
  pattern (`^\d+\.`), then split each scene into chunks using the same `_split_narration`
  logic as the English pipeline. Return chunk at `segment_index`; fall back on
  out-of-range.

In `generate_script()`: accept optional `ParallelTextTranslator` (defaults to `None`);
use it instead of `mock_translate` when present. No change to data models or schemas —
`text_secondary` already exists.

In `cli.py`: when `pijons_from_hell.txt` (resolved by convention: `<story_stem>_uk.txt`
or explicit `secondary_text_path` in config) exists, construct the translator and pass it
to `generate_script`. Missing file → `mock_translate`, no error.

**Acceptance criteria:**
1. With `pijons_from_hell.txt` present, `text_secondary` contains Cyrillic characters
   and does not start with `[uk]`.
2. Missing secondary file falls back to `mock_translate` without error.
3. `pytest` and `mypy --strict` pass.

---

### #032 — Ambient audio: mood-mapped looped WAV adapter

**Problem.** Every scene's ambient track is silence.

**Approach.** New `LoopAudioAdapter` in `src/horror_story/adapters/audio/loop.py`:

- Constructor: `__init__(self, assets_dir: Path)` — scans for `<mood>.wav` at
  construction time.
- `generate(mood, duration_s, ...)`: loop-extend or trim the matching WAV to exactly
  `duration_s` using Python's `wave` module (no FFmpeg). Write output WAV + sidecar.
  Unknown mood → log warning, delegate to `MockAudioAdapter` (silence).
- Loop extension: repeat source frames cyclically until `round(sample_rate * duration_s)`
  frames; write exactly that many.

Asset files (one `.wav` per mood: `dread`, `tension`, `night_insects`, `wind`,
`silence`) live at the path configured in `pipeline.toml` under a new `[audio]` section:

```toml
[audio]
assets_dir = "/path/to/ambient-assets"
```

The path is gitignored; only adapter code is committed. When `assets_dir` is absent or
the directory does not exist, the adapter falls back to silence.

New `AudioConfig` dataclass in `config.py` with `assets_dir: str = ""`.
Register `"loop"` in `AdapterFactory.get_audio()`.

**Acceptance criteria:**
1. `audio = "loop"` with valid `assets_dir` produces non-silent WAV output matching
   `duration_s` ± 5%.
2. Unknown mood falls back to silence without exception.
3. Missing `assets_dir` silently falls back to mock.
4. `pytest` and `mypy --strict` pass.

---

### #033 — Validation: full 3-scene run end-to-end checkpoint

No new code. Run the pipeline on 3 scenes with `tts = "kokoro"`, `image = "mock"`,
`audio = "loop"`, capture `metrics.json`, watch the resulting MP4s, record observations
in `docs/checkpoints/checkpoint-sprint06.md`.

---

## Known gaps going into Sprint 07

1. **Real ambient synthesis** — `LoopAudioAdapter` uses pre-recorded loops that repeat
   and lack variation. A generative ambient model would be the next atmosphere upgrade.
2. **Ukrainian TTS** — secondary language audio is still English (Kokoro). Typography is
   now real Ukrainian; the narrated voice is not.
3. **Translation alignment drift** — position-based mapping may drift in scenes where the
   Ukrainian translation added or dropped a paragraph. Sentence-level alignment would
   improve fidelity.
4. **Animation beyond zoom** — still a single static frame with a Ken Burns effect.
5. **Full 19-scene render** — validated only on 3 scenes in Sprint 06.
