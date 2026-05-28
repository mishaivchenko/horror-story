# Issue #039 — CLI: make TTS language selection explicit

**Status:** Closed
**Sprint:** 07
**Priority:** P1
**Labels:** cli, tts, bilingual, bug
**Estimate:** 1d
**Depends on:** #031, #034
**Blocks:** —

---

## Problem

`_run_scene()` currently infers the synthesis language from the manifest:

```python
tts_lang = secondary_lang if secondary_lang else primary_lang
tts_text = seg.text_secondary if seg.text_secondary else seg.text_en
```

That means any story with `secondary_language = "uk"` will synthesize Ukrainian text,
even when `pipeline.toml` still selects the English Kokoro adapter and English voices.

This couples subtitle availability to narration language and makes English runs with
Ukrainian subtitles impossible without editing config or code.

---

## Scope

### `src/horror_story/cli.py`

- Stop using the mere presence of `secondary_language` to choose TTS text/language.
- Introduce an explicit language mode, likely through #034 `--lang`.
- Keep omitted `--lang` behavior compatible with `pipeline.toml`.
- Ensure selected TTS adapter, voice IDs, text field, and `language` argument all agree.

### Tests

- With English config and `secondary_language = "uk"`, default run must synthesize
  English text through English voices unless `--lang uk` is requested.
- `--lang uk` must synthesize `text_secondary` through the Ukrainian adapter/voices.
- `--lang en` must synthesize `text_en` through the English adapter/voices.

---

## Acceptance Criteria

1. English and Ukrainian narration modes are explicit and deterministic.
2. Subtitle/secondary-text presence does not silently change the TTS language.
3. Adapter, voice ID, TTS text, and language code are internally consistent.
4. Existing CLI tests pass.
5. `mypy --strict src/` passes.

