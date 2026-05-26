# Issue 003 — Script generator: scene → bilingual script

**Status:** Done

**Labels:** `pipeline`, `sprint-01`
**Spec refs:** `spec/PIPELINE.md` §Stage 2, `spec/schemas/script.schema.json`
**Estimate:** 0.5 day
**Depends on:** #002

## Goal

Implement `horror_story.pipeline.script` to convert a scene JSON into a bilingual script
JSON (EN + secondary language mock).

## Acceptance criteria

- [ ] `horror_story.pipeline.script.generate_script(scene: Scene, manifest: Manifest) -> Script`
      exists and is type-annotated
- [ ] Narration is split into segments of ≤ 40 words; each has `segment_id` = `seg-0`, `seg-1`, …
- [ ] Dialogue lines extracted by `"Word: text"` pattern (capitalized word, colon, space, text)
- [ ] Every segment has `text_secondary` (mock: reversed word order, prefixed `[uk] `).
      Field name is `text_secondary` — not `text_uk` — matching the schema.
- [ ] Every segment has `pacing_ms` = `max(500, word_count * 100)`
- [ ] `total_duration_ms` equals exact sum of all segment and dialogue `pacing_ms` values
- [ ] `voice_id` on each segment is `manifest.voices["narrator"]`
- [ ] `voice_id` on each dialogue line looks up `manifest.voices[character.lower()]`;
      falls back to `manifest.voices["narrator"]` if character not in voices map
- [ ] Output validates against `spec/schemas/script.schema.json`
- [ ] `pytest tests/test_script.py` passes with ≥ 85% coverage on `script.py`
- [ ] `mypy --strict` passes

## Tasks

1. Define `Script`, `Segment`, `DialogueLine` dataclasses in `horror_story/models.py`.
2. Implement `generate_script()` in `horror_story/pipeline/script.py`.
3. Implement `mock_translate(text: str) -> str` helper (reverse word order + `[uk] ` prefix).
4. Write unit tests: segmentation, `≤ 40` word boundary, dialogue extraction, pacing math,
   `text_secondary` presence, schema validation.
5. Add `tests/fixtures/scene_001.json` (hand-crafted 1-scene fixture with 1 dialogue line).

## Notes

- Mock translation is a placeholder for a real LLM call post-MVP.
- `insert_after_segment`: find the segment whose span in the original text ends immediately
  before the `"Character: text"` line. Set to `null` if the dialogue precedes all segments.
