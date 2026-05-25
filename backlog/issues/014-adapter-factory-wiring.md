# Issue #014 — Wire AdapterFactory in CLI

**Status:** Done
**Sprint:** 03
**Labels:** pipeline, cli
**Estimate:** 0.5d
**Depends on:** #013
**Blocks:** #016

---

## Problem

`cli.py::_run_scene()` directly instantiates mock adapters regardless of what
`pipeline.toml` specifies:

```python
from horror_story.adapters.tts.mock import MockTTSAdapter
tts = MockTTSAdapter()
```

The `AdapterFactory` and the `[adapters]` section in `pipeline.toml` are ignored.
This means switching to a real provider (e.g. Kokoro TTS) requires editing `cli.py`
rather than just changing config.

---

## Scope

Replace all five direct mock instantiations in `_run_scene()` with `AdapterFactory` calls:

```python
from horror_story.adapters import AdapterFactory
tts   = AdapterFactory.get_tts(config.adapters.tts)
image = AdapterFactory.get_image(config.adapters.image)
motion = AdapterFactory.get_motion(config.adapters.motion)
audio  = AdapterFactory.get_audio(config.adapters.audio)
typo   = AdapterFactory.get_typography(config.adapters.typography)
```

The existing `PipelineConfig` is already parsed from `pipeline.toml` in `cli.py` — use it.

The default `pipeline.toml` (in `tests/fixtures/`) keeps all adapters as `"mock"`.
No behavioral change for existing tests.

---

## Acceptance criteria

1. All five adapters in `_run_scene()` are obtained via `AdapterFactory`.
2. Setting `tts = "kokoro"` in `pipeline.toml` causes `AdapterFactory.get_tts("kokoro")`
   to be called (verified by test — mock the factory, assert call args).
3. All existing CLI integration tests pass unchanged.
4. `mypy --strict` passes.
