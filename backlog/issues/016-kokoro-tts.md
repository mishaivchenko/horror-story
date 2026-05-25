# Issue #016 — Local TTS adapter: Kokoro

**Status:** Done
**Sprint:** 03
**Labels:** adapter, atmosphere
**Estimate:** 1.0d
**Depends on:** #013, #014
**Blocks:** #017

---

## Goal

Replace silent mock WAV narration with real synthesized speech using Kokoro,
a lightweight offline TTS model (~82 MB ONNX, CPU-only, works on Apple Silicon).

Package: `kokoro-onnx` (PyPI). No GPU required.

---

## Scope

### New file: `src/horror_story/adapters/tts/kokoro.py`

Implement `KokoroTTSAdapter(TTSAdapter)` with:

```python
class KokoroTTSAdapter(TTSAdapter):
    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str,
        pacing_ms: int,
        seed: int,
        out_path: Path,
        *,
        story_id: str = "",
        scene_id: str = "",
        line_ref: str = "",
        line_type: str = "narration",
    ) -> Path: ...
```

Responsibilities:
- Lazy-load the Kokoro ONNX model on first call; cache in `~/.cache/horror_story/kokoro/`
- Map `voice_id` → Kokoro voice name via a small config dict:
  - `"narrator_en"` → `"af_heart"` (deep, atmospheric default)
  - Any unmapped `voice_id` falls back to `"af_heart"`
- Synthesize speech, write 44.1 kHz mono WAV to `out_path`
- Write sidecar JSON (same schema as MockTTSAdapter, adapter field = `"kokoro"`)
- Determinism: Kokoro is non-deterministic across runs; real provider exemption applies

### Register in `AdapterFactory`

```python
elif name == "kokoro":
    from horror_story.adapters.tts.kokoro import KokoroTTSAdapter
    return KokoroTTSAdapter()
```

Import is deferred (inside the branch) so `kokoro-onnx` is not required unless used.

### `pyproject.toml` optional dependency

```toml
[project.optional-dependencies]
real = ["kokoro-onnx>=0.4"]
```

---

## Tests

- Unit tests mock the Kokoro model entirely (no download in CI)
- One integration test gated: `pytest.mark.skipif(not _kokoro_available(), reason="kokoro-onnx not installed")`
- CI runs with mock only; Kokoro tests are local-only

---

## Acceptance criteria

1. `pip install -e ".[real]"` installs `kokoro-onnx`.
2. `AdapterFactory.get_tts("kokoro")` returns a `KokoroTTSAdapter` instance.
3. `KokoroTTSAdapter.synthesize(...)` writes a non-silent WAV when `kokoro-onnx` is available.
4. Sidecar JSON is valid against `spec/schemas/voice_line.schema.json`.
5. CI (mock-only) passes without `kokoro-onnx` installed.
6. `mypy --strict` passes.
