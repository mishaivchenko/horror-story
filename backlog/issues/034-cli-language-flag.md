# #034 — CLI `--lang` flag for language selection

**Status:** Open
**Sprint:** 07

## Problem

Language (TTS adapter + voice IDs) is currently hardcoded in `pipeline.toml`.
Switching between EN and UK requires editing the TOML file manually.

## Proposed solution

Add `--lang` CLI flag to `horror-story run`. Accepted values: `en`, `uk` (extensible).

### Mapping

| `--lang` | TTS adapter | narrator voice | character voices |
|----------|-------------|----------------|-----------------|
| `en`     | `kokoro`    | `narrator_en`  | `character_en`  |
| `uk`     | `piper`     | `narrator_uk`  | `character_uk`  |

When `--lang` is passed:
- Override `config.adapters.tts` with the mapped adapter name
- Override all voice IDs in `manifest.voices` using the mapped voice prefix
- Override `tts_lang` used for synthesis

When `--lang` is omitted: use whatever is in `pipeline.toml` (current behavior, no regression).

## Acceptance

- `--lang en` produces EN kokoro TTS, EN subtitles
- `--lang uk` produces Piper UK TTS, UK-only subtitles
- `--lang` omitted → behavior unchanged from current `pipeline.toml` values
- Unit test: `_resolve_lang_overrides(lang="uk", config, manifest)` returns correct overrides
