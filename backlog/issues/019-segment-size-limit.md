# Issue #019 — Increase narration segment size limit

**Status:** Open
**Sprint:** 03
**Labels:** script, tts, performance
**Estimate:** 0.5d
**Depends on:** #016
**Blocks:** —

---

## Problem

`_split_narration()` in `src/horror_story/pipeline/script.py` slices scene text into
chunks of ≤ 40 words (`_MAX_SEGMENT_WORDS = 40`). This limit was set when TTS was a
silent mock and segmentation granularity had no cost.

With Kokoro each segment is a separate ONNX inference call. A 894-word scene produces
23 segments — 23 round-trips through the model, 23 WAV files, 23 timeline tracks, and
audible micro-pauses at every boundary. This inflates runtime and degrades output
quality.

---

## Goal

Raise the segment limit so that each segment maps to a natural prose unit (paragraph or
sentence group) rather than an arbitrary word count, reducing inference calls per scene
by ~5–8×.

---

## Scope

### `src/horror_story/pipeline/script.py`

Replace word-count slicing with paragraph-aware splitting:

1. Split scene text on blank lines (`\n\n`) to get paragraphs.
2. Merge consecutive short paragraphs until the accumulated word count reaches
   `_MAX_SEGMENT_WORDS` (new default: **200**).
3. Never split a paragraph mid-sentence; if a single paragraph exceeds the limit,
   split it at sentence boundaries (`. `, `? `, `! `).

`_MAX_SEGMENT_WORDS = 200` is a module-level constant — easy to tune later.

No changes to the `Segment` dataclass, schema, or any downstream stage.

---

## Expected impact

| Scene (words) | Before (40-word cap) | After (200-word cap) |
|---|---|---|
| griswell-awoke… (709 w) | 18 segments | ~4 segments |
| griswell-never… (894 w) | 23 segments | ~5 segments |
| made-turn… (797 w) | 20 segments | ~4 segments |

Full 18-scene run: ~300 segments → ~60 segments. Kokoro runtime roughly 5× faster.

---

## Tests

- Update `tests/test_script.py`: existing tests that assert exact segment counts must be
  revised to match the new segmentation.
- Add a test: single paragraph of 250 words is split at a sentence boundary, not mid-word.
- Add a test: two short paragraphs (30 + 40 words) are merged into one segment.
- `mypy --strict` must pass.

---

## Acceptance criteria

1. `_MAX_SEGMENT_WORDS = 200` (or configured via constant).
2. Segments respect paragraph boundaries; no mid-sentence splits.
3. A 894-word scene produces ≤ 6 segments.
4. All existing tests pass after count adjustments.
5. `mypy --strict` passes.
