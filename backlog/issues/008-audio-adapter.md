# Issue 008 — Ambient audio adapter (mock-first)

**Status:** Done

**Labels:** `adapter`, `sprint-02`
**Spec refs:** `spec/MVP.md` §F-07; `spec/MVP_PLUS.md` §F-07; `spec/PIPELINE.md` §Stage 6
**Estimate:** 0.25 day
**Depends on:** #002

### Goal
Define the `AudioAdapter` ABC and implement `MockAudioAdapter` that writes a deterministic
silent stereo WAV of the specified duration.

### Acceptance criteria
- [ ] `AudioAdapter` ABC in `horror_story/adapters/audio/base.py` with signature:
      `generate(self, mood: str, duration_s: float, seed: int, out_path: Path) -> Path`
- [ ] `MockAudioAdapter` produces a valid WAV: stereo, 44.1 kHz, 16-bit PCM
- [ ] Duration matches `duration_s` ± 5%
- [ ] Same inputs + seed → same bytes
- [ ] Adapter registered: `AdapterFactory.get_audio("mock") -> MockAudioAdapter`
- [ ] `pytest tests/test_audio.py` passes with ≥ 85% coverage on `audio/`
- [ ] `mypy --strict` passes

### Output artifact
```
audio/ambient_<scene_id>.wav   ← silent stereo WAV
```

### Tasks
1. Define `AudioAdapter` ABC in `horror_story/adapters/audio/base.py`.
2. Implement `MockAudioAdapter` using stdlib `wave`.
3. Add `get_audio()` to `AdapterFactory`.
4. Write unit tests: WAV properties, duration, determinism.

### Notes
- Stereo = 2 channels; interleaved samples.
- Same pattern as `MockTTSAdapter` — just stereo and duration-driven rather than text-driven.
- Use `wave` stdlib only. No third-party audio libraries.
