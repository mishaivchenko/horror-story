# Sprint 01 — Foundation

**Duration:** 2026-05-24 → 2026-05-30 (one week)
**Goal:** scaffold + parser + script generator + TTS mock + image mock + CI all green.

By the end of this sprint, a 3-scene mini-story fixture can be parsed into scene JSONs,
converted into bilingual script JSONs, and have valid (silent/placeholder) WAV and PNG
artifacts generated for every segment. **No video output in Sprint 01.** Video rendering
(motion, compositor, renderer) is Sprint 02.

---

## Sprint backlog

| Issue | Title | Owner | Estimate | Status |
|-------|-------|-------|----------|--------|
| #001 | Project scaffold and CLI skeleton | Claude Code | 0.5d | To Do |
| #002 | Story parser: raw text → scene JSON | Claude Code | 0.5d | To Do |
| #003 | Script generator: scene → bilingual script | Claude Code | 0.5d | To Do |
| #004 | TTS adapter (mock-first) | Claude Code | 0.5d | To Do |
| #005 | Image adapter: keyframe generation (mock-first) | Claude Code | 0.5d | To Do |
| #012 | GitHub Actions CI | Claude Code | 0.25d | To Do |

**Sprint total:** ~2.75 days of implementation

---

## Sprint 02 preview

| Issue | Title | Estimate |
|-------|-------|----------|
| #006 | Typography overlay (mock-first, PNG) | 0.5d |
| #007 | Motion adapter (mock-first) | 0.5d |
| #008 | Ambient audio adapter (mock-first) | 0.25d |
| #009 | Scene compositor | 1d |
| #010 | Final renderer | 0.5d |
| #011 | End-to-end CLI | 0.5d |

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

- All Sprint 01 issues closed.
- `pytest` passes with ≥ 80% coverage on `src/`.
- `mypy --strict src/` passes.
- CI workflow runs green on `main`.
- `python -m horror_story --help` works.
- 3-scene mini-story fixture is fully parsed, scripted, and has WAV + PNG artifacts.
- **No video output required.** Motion/compositor/renderer are Sprint 02 scope.

---

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Schema changes during sprint | Medium | Spec PR required before any implementation change |
| Mock WAV duration drift | Low | Tests assert duration within ±5% |
| `mypy --strict` friction on first pass | Medium | Stub types early in #001; iterate |
