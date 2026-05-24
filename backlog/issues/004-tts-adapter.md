# Issue 004 — TTS adapter: narration + dialogue (mock-first)

**Labels:** `adapter`, `sprint-01`
**Spec refs:** `spec/MVP_PLUS.md` §F-03, §F-04; `spec/PIPELINE.md` §Stage 3a/3b; `spec/schemas/voice_line.schema.json`
**Estimate:** 0.5 day
**Depends on:** #003

## Goal

Define the `TTSAdapter` ABC and implement `MockTTSAdapter` that writes deterministic
silent WAV files of the correct duration.

## Acceptance criteria

- [ ] `TTSAdapter` ABC in `horror_story/adapters/tts/base.py` with signature:
      `synthesize(self, text: str, voice_id: str, language: str, pacing_ms: int, seed: int, out_path: Path) -> Path`
- [ ] `MockTTSAdapter.synthesize(...)` writes a valid WAV to `out_path`: mono, 44.1 kHz,
      16-bit PCM, duration = `pacing_ms` ± 5%
- [ ] WAV duration check: `wave.open(str(path)).getnframes() / 44100 ≈ pacing_ms / 1000`
- [ ] Same arguments + seed → identical file bytes (deterministic)
- [ ] `voice_line.json` sidecar written at `out_path.with_suffix('.json')` and validates
      against `spec/schemas/voice_line.schema.json`
- [ ] Adapter registered in factory: `AdapterFactory.get_tts("mock") -> MockTTSAdapter`
- [ ] `pytest tests/test_tts.py` passes with ≥ 85% coverage on `tts/`
- [ ] `mypy --strict` passes

## Tasks

1. Define `TTSAdapter` ABC in `horror_story/adapters/tts/base.py`.
2. Implement `MockTTSAdapter` in `horror_story/adapters/tts/mock.py`.
3. Define `AdapterFactory` in `horror_story/adapters/__init__.py` with `get_tts()`.
4. Write unit tests: WAV properties, duration accuracy, byte-level determinism, sidecar schema.

## Notes

- Mock produces all-zero PCM samples. Duration is the only contract.
- Use stdlib `wave` only. No third-party audio libraries.
- `out_path` is caller-supplied. Write to a temp path, then `Path.replace(out_path)`.
