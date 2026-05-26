# Issue 002 — Story parser: raw text → scene JSON

**Status:** Done

**Labels:** `pipeline`, `sprint-01`
**Spec refs:** `spec/PIPELINE.md` §Stage 1, `spec/schemas/scene.schema.json`
**Estimate:** 0.5 day
**Depends on:** #001

## Goal

Implement `horror_story.pipeline.parse` so that a plain-text story file is converted
into `manifest.json` + one `scene_<id>.json` per scene, all validating against schemas.

## Acceptance criteria

- [ ] `horror_story.pipeline.parse.parse_story(text, config) -> list[Scene]` exists and
      is type-annotated (returns only scenes; manifest construction is the caller's job)
- [ ] **Scene boundary rule (MVP):** splits on lines containing only `---`. No other
      heuristic. Fixtures must use `---` markers.
- [ ] Each `Scene` dataclass has: `scene_id`, `index`, `text`, `visual_description`,
      `mood`, `word_count`, `story_id`
- [ ] Each scene serialized to JSON validates against `spec/schemas/scene.schema.json`
- [ ] `scene_id` is a stable kebab-slug (same text → same ID across runs), max 48 chars
- [ ] `mood` is assigned from keyword vocabulary (at least 5 moods recognized)
- [ ] `tests/fixtures/mini-story.txt` (3 scenes, explicit `---` markers) parses correctly
- [ ] `pytest tests/test_parse.py` passes with ≥ 85% coverage on `parse.py`
- [ ] `mypy --strict` passes

## Tasks

1. Define `Scene` dataclass (stdlib `dataclasses`) in `horror_story/models.py`.
2. Implement `parse_story(text: str, story_id: str) -> list[Scene]` in
   `horror_story/pipeline/parse.py`.
3. Implement `slugify(text: str, max_chars: int = 48) -> str` helper.
4. Implement mood classifier (keyword dict lookup, returns `"neutral"` as fallback).
5. Add `tests/fixtures/mini-story.txt` with exactly 3 scenes separated by `---`.
6. Write unit tests: scene count, slug stability, mood assignment, schema validation.

## Notes

- `parse_story()` is a pure function — no file I/O.
- Manifest construction (combining config + scene list) happens in `manifest.py`, not here.
- No Pydantic. Use `dataclasses.dataclass` + `@dataclasses.asdict` for JSON serialization.
