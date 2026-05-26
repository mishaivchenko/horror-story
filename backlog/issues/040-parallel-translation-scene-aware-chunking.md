# Issue #040 — Translation: use scene-aware aligned secondary text chunks

**Status:** Open
**Sprint:** 07
**Priority:** P2
**Labels:** translation, bilingual, alignment
**Estimate:** 1.5d
**Depends on:** #031, #035
**Blocks:** —

---

## Problem

`ParallelTextTranslator` distributes secondary-language paragraphs across scenes
proportionally by English word count. This is fragile for real text and can drift
from the source scene boundaries.

When a scene receives fewer secondary paragraphs than English narration segments,
`prepare_scene()` pads the remaining segment chunks with empty strings. The script
generator then falls back to `mock_translate()`, mixing real Ukrainian text and mock
reversed-English text in the same scene.

Existing #035 aligns the story files with `---` scene separators. The translator should
use that stronger contract instead of continuing to rely only on proportional guesses.

---

## Scope

### `src/horror_story/pipeline/translate.py`

- Parse secondary-language text with the same `---` scene separator convention as
  English story text when separators are present.
- Map secondary scene N to English scene N directly.
- Within a scene, distribute secondary paragraphs into segment chunks without falling
  back to mock translation merely because there are fewer paragraphs than segments.
- Keep proportional distribution only as an explicit fallback for unaligned secondary
  files.

### `src/horror_story/pipeline/script.py`

- If a real translator is present, avoid mixing mock-translated fallback text into
  otherwise real secondary-language output unless the entire scene has no translation.

### Tests

- Add aligned EN/UK fixture text with matching `---` separators.
- Assert scene N receives only text from UK scene N.
- Assert multiple English segments in one scene do not produce `[uk]` mock fallbacks
  when real secondary scene text exists.
- Keep a fallback test for unaligned files if proportional mode remains supported.

---

## Acceptance Criteria

1. Aligned secondary story files use exact scene-to-scene mapping.
2. Real secondary text is never mixed with `[uk]` mock fallback inside the same
   translated scene.
3. Proportional mode, if retained, is clearly tested as fallback behavior.
4. Script generation tests pass.
5. `mypy --strict src/` passes.

