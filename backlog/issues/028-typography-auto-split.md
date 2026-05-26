# Issue #028 — Typography: auto-split long narration segments into timed sub-segments

**Status:** Closed
**Sprint:** 06
**Priority:** P1
**Labels:** typography, bug
**Estimate:** 1.5d
**Depends on:** #023, #024, #025
**Blocks:** —

---

## Problem

`MockTypographyAdapter` renders one PNG per narration segment. The zone height is
capped at `_ZONE_MAX_H_FRAC = 0.30` of the frame (324px at 1080p). At `font_size =
height // 20 = 54px` that is `max_lines = 5`. A typical narration segment (e.g.
the Griswell opening scene) contains 78 words → ~11 lines → the bottom 6 lines are
silently truncated by `lines[:max_lines]`. The narration audio plays the full text
but only ~51% appears on screen.

---

## Goal

Split each narration segment whose wrapped line count exceeds `max_lines` into N
consecutive sub-segments. Each sub-segment gets:

- Its own PNG (a chunk of the text that fits within `max_lines`).
- A `start_s` / `end_s` proportional to its word count relative to the full segment.
- A unique `seg_id`: `seg-0a`, `seg-0b`, `seg-0c`, … (suffix `a`/`b`/`c` appended to
  the original `seg_id`). Single-chunk segments keep the original `seg_id` unchanged.

The compositor and FFmpeg overlay chain already support multiple timing entries per
scene — no changes needed outside `MockTypographyAdapter`.

---

## Scope

### `src/horror_story/adapters/typography/mock.py`

Extract a helper:

```python
def _split_text_into_chunks(
    text: str,
    max_lines: int,
    char_w: int,
) -> list[str]:
    """Split text into chunks where each chunk wraps to at most max_lines lines."""
```

Logic:
1. Word-tokenise the text.
2. Greedily accumulate words until `textwrap.fill(chunk, width=char_w)` wraps to
   more than `max_lines` lines, then start a new chunk.
3. Return list of chunk strings (at least one, even if text is empty).

In `render()`, after computing `max_lines` and `char_w` for the primary zone, call
`_split_text_into_chunks(text_en, max_lines, char_w)`. If there is only one chunk,
emit one timing entry as before. If N > 1:

- Distribute `[start_s, end_s]` across chunks proportionally by word count.
- Suffix the `seg_id`: `seg-0a`, `seg-0b`, …
- Emit one PNG and one timing entry per chunk.

`char_w` and `max_lines` must be computed **before** the per-track loop and reused
consistently so all splits use identical geometry.

### No schema changes

`typography_timing.schema.json` already accepts any number of segments and any
`seg_id` string — no update needed.

---

## Tests

### `tests/test_typography.py`

Add to the existing test file:

**`test_long_segment_splits_into_multiple_pngs`**: render a segment with text long
enough to exceed `max_lines` at 320×240. Assert that the timing manifest contains
more than one entry for that segment. Assert that each PNG file exists. Assert that
`start_s` of entry[1] equals `end_s` of entry[0].

**`test_split_covers_full_duration`**: `entries[0].start_s == original_start_s` and
`entries[-1].end_s == original_end_s`.

**`test_short_segment_not_split`**: text that fits in `max_lines` → exactly one
timing entry, `seg_id` unchanged (no `a` suffix).

**`test_split_text_into_chunks_unit`**: unit test for the helper directly —
pass known text + max_lines=3 + char_w, assert every chunk wraps to ≤ 3 lines,
assert joined chunks contain all original words.

---

## Acceptance criteria

1. Narration segment with 78 words at 1920×1080 produces ≥ 3 timing entries.
2. Each PNG shows only text that fits within the zone (no truncation).
3. Timing entries for split sub-segments are contiguous: `entries[i].end_s ==
   entries[i+1].start_s`.
4. Total duration preserved: `entries[-1].end_s == original_end_s`.
5. Short segments (≤ max_lines) produce exactly one entry, `seg_id` unchanged.
6. All existing typography tests pass.
7. `mypy --strict` passes.

---

## Notes

- The `_ZONE_MAX_H_FRAC = 0.30` constant stays — the fix works within it.
- `char_w` estimation (`available_w / (font_size * 0.6)`) is an approximation for
  the default bitmap font; it is good enough for splitting and already used
  for rendering.
- This issue applies only to `MockTypographyAdapter`. When a real typography adapter
  is introduced later, it will own its own split/layout logic.
