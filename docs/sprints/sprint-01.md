# Sprint 01 — Foundation

**Duration:** 2026-05-24 (completed same day)
**Goal:** scaffold + parser + script generator + TTS mock + image mock + CI all green.

By the end of this sprint, a 3-scene mini-story fixture can be parsed into scene JSONs,
converted into bilingual script JSONs, and have valid (silent/placeholder) WAV and PNG
artifacts generated for every segment. **No video output in Sprint 01.** Video rendering
(motion, compositor, renderer) is Sprint 02.

**Status: COMPLETE** — all Sprint 01 issues closed on 2026-05-24.

---

## Sprint backlog

| Issue | Title | Owner | Estimate | Status |
|-------|-------|-------|----------|--------|
| #001 | Project scaffold and CLI skeleton | Claude Code | 0.5d | **Done** |
| #002 | Story parser: raw text → scene JSON | Claude Code | 0.5d | **Done** |
| #003 | Script generator: scene → bilingual script | Claude Code | 0.5d | **Done** |
| #004 | TTS adapter (mock-first) | Claude Code | 0.5d | **Done** |
| #005 | Image adapter: keyframe generation (mock-first) | Claude Code | 0.5d | **Done** |
| #012 | GitHub Actions CI | Claude Code | 0.25d | **Done** |

**Sprint total:** ~2.75 days of implementation

---

## Sprint 02 (completed on same day)

| Issue | Title | Status |
|-------|-------|--------|
| #006 | Typography overlay (mock-first, PNG) | **Done** |
| #007 | Motion adapter (mock-first) | **Done** |
| #008 | Ambient audio adapter (mock-first) | **Done** |
| #008b | Timeline planner (Stage 7.5) | **Done** |
| #009 | Scene compositor | **Done** |
| #010 | Final renderer | **Done** |
| #011 | End-to-end CLI | **Done** |

MVP shipped. See `docs/sprints/sprint-03-atmosphere.md` for what comes next.

---

## Daily cadence

Each session:
1. Pick the next unstarted issue from the backlog.
2. Read the spec references cited in the issue.
3. Write the failing test first.
4. Implement until tests pass.
5. Run `mypy --strict` and `pytest --cov`.
6. Commit with a message referencing the issue: `fix: scene parser slug (#002)`.
7. Mark the issue done.

---

## Definition of done (sprint)

- All Sprint 01 issues closed. ✓
- `pytest` passes with ≥ 80% coverage on `src/`. ✓ (94%)
- `mypy --strict src/` passes. ✓
- CI workflow runs green on `main`. ✓
- `python -m horror_story --help` works. ✓
- 3-scene mini-story fixture is fully parsed, scripted, and has WAV + PNG artifacts. ✓
- **No video output required.** Motion/compositor/renderer are Sprint 02 scope. ✓

---

## Risks (historical record)

| Risk | Likelihood | Outcome |
|------|-----------|---------|
| Schema changes during sprint | Medium | No schema changes needed |
| Mock WAV duration drift | Low | Tests assert duration within ±5% — passed |
| `mypy --strict` friction on first pass | Medium | Resolved; argparse/dataclasses worked cleanly |
