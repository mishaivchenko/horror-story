# Issue #038 — Typography: split secondary text so overlays do not truncate

**Status:** Open
**Sprint:** 07
**Priority:** P1
**Labels:** typography, bilingual, bug
**Estimate:** 1d
**Depends on:** #028, #031
**Blocks:** —

---

## Problem

#028 splits long narration based on `text_en`, but the renderer now prefers
`text_secondary` when it exists. The first split chunk is rendered with the full
secondary-language text while later chunks render no secondary text.

Practical result:

- English chunk sizing can say a segment fits.
- The actual Ukrainian/secondary text rendered in the box can still overflow.
- `_render_text_box()` silently clamps overflowing lines, so subtitles are truncated.
- Timing entries after the first chunk can lose secondary text entirely.

This keeps the original typography bug alive for real bilingual runs.

---

## Scope

### `src/horror_story/adapters/typography/mock.py`

- Split the displayed text, not only `text_en`.
- If `text_secondary` exists, use it as the primary displayed narration text for
  split decisions.
- Preserve timing proportionality based on the displayed chunks.
- Ensure every split timing entry carries the matching displayed text.

Possible conservative approach:

```python
display_text = text_secondary if text_secondary else text_en
chunks = _split_text_into_chunks(display_text, max_lines, char_w)
```

Then render `chunk` as the primary narration text and keep `text_en` in metadata only
if needed by schema or debugging.

### Tests

- Add a long `text_secondary` regression where `text_en` is short.
- Assert the adapter emits multiple timing entries.
- Assert no timing entry contains text that wraps beyond `max_lines`.
- Assert no secondary text is dropped across split entries.

---

## Acceptance Criteria

1. Long secondary-language narration is split into multiple PNG/timing entries.
2. Each rendered narration chunk fits within the primary typography zone.
3. Secondary text is not silently dropped after the first chunk.
4. Existing typography tests pass.
5. `mypy --strict src/` passes.

