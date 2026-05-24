# MVP Specification — 3-Scene Mock Vertical Slice

**Status:** Draft
**Scope:** Sprint 01 + Sprint 02 combined deliverable
**Story fixture:** `tests/fixtures/mini-story.txt` (hand-written, ≤ 300 words, 3 scenes)

---

## Goal

Prove the full pipeline compiles and runs end-to-end on a 3-scene mini-story using only
mock adapters, with every stage producing valid artifacts. This is the definition of
"pipeline works" before scaling to the full *Pigeons from Hell* story.

---

## MVP is NOT

- The full *Pigeons from Hell* story (that is MVP+, see `spec/MVP_PLUS.md`)
- Production-quality media output
- A real user-facing tool

---

## Scope

### Sprint 01 deliverables (no video)

| Feature | Description |
|---------|-------------|
| F-01 | Story parser: mini-story → scene JSONs |
| F-02 | Script generator: scene → bilingual script JSON |
| F-03 | Narration TTS mock: script → silent WAV per segment |
| F-04 | Dialogue TTS mock: script → silent WAV per dialogue line |
| F-05 | Image mock: scene → grey PNG keyframe |
| CI | GitHub Actions: pytest + mypy + schema validation |

### Sprint 02 deliverables (video path)

| Feature | Description |
|---------|-------------|
| F-06 | Motion mock: PNG → looping silent MP4 |
| F-07 | Ambient audio mock: mood → silent stereo WAV |
| F-08 | Typography mock: script → transparent PNG overlay |
| F-09 | Scene compositor: combine all artifacts → scene MP4 |
| F-10 | Final renderer: concatenate scenes → final MP4 |
| F-11 | CLI: `run`, `--scene`, `--dry-run`, `--validate`, `--seed` |

---

## MVP acceptance criteria

- [ ] `python -m horror_story run --story tests/fixtures/mini-story.txt --out /tmp/out`
      exits 0 and produces `final_mini-story_42.mp4`
- [ ] All intermediate artifacts exist and validate against their schemas
- [ ] Same command run twice with `--seed 42` produces the same file content for all
      non-metadata artifacts (see determinism contract in `spec/TECHNICAL_PLAN.md`)
- [ ] `--dry-run` prints the plan and produces no files
- [ ] `--validate` catches a deliberately broken fixture JSON
- [ ] `pytest` passes with ≥ 80% coverage; `mypy --strict` passes

---

## MVP+ (post-MVP, see `spec/MVP_PLUS.md`)

After MVP is shipped:
1. Run the full *Pigeons from Hell* text through the pipeline (≥ 10 scenes)
2. Replace mock adapters one at a time with real providers
3. Bilingual secondary language becomes real (LLM translation, not word-reversal)
