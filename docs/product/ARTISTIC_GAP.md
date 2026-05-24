# Artistic Gap — Horror Story Pipeline

**Status:** Acknowledged
**Date:** 2026-05-24

---

## What the MVP validates

The MVP (Sprint 01 + Sprint 02) validates **technical pipeline integrity only**:

- Every stage runs without error.
- Every artifact validates against its JSON schema.
- The full chain from `story.txt` to `final_<story_id>_<seed>.mp4` executes.
- Determinism holds: same seed → same bytes in mock mode.

## What the MVP does NOT validate

**The MVP does not validate artistic quality.**

Passing all tests does not imply atmospheric success. A green CI run does not mean the
output is a horror video. It means the pipeline is structurally correct.

---

## Current artistic state

| Concern | Current state |
|---------|---------------|
| Keyframe images | Grey PNG with scene ID text. Intentionally empty. |
| Narration audio | Silent WAV files. Zero emotional content. |
| Ambient audio | Silent stereo WAV files. No atmosphere. |
| Motion / VFX | Single static frame repeated. No movement. |
| Typography | Adaptive zones v1: text in constrained boxes, not full-frame. Still system font, no horror aesthetic. |
| Bilingual text | Word-reversed placeholder with `[uk]` prefix. Meaningless. |
| Pacing | Flat 100 ms/word. No pauses, no dramatic timing. |
| Mood field | Structurally present (`night_insects`, `wind`, etc.) but **artistically inert**. |

Mock outputs are intentionally emotionally empty. This is correct mock-first behavior.
The danger is treating technical correctness as artistic readiness.

---

## The critical warning

> **The project can reach 100% technical correctness while still producing emotionally
> dead content.**

A 100% passing test suite, a fully wired CLI, and a valid final MP4 can coexist with
output that no human would recognize as a horror video. The `mood` field carries
vocabulary (`fear`, `dread`, `silence`) but nothing in the pipeline uses mood to alter
timing, visuals, or audio texture. The structure exists; the soul does not.

---

## Mood metadata: structurally present, artistically inert

`scene.schema.json` defines a `mood` field. It is populated by the parser via keyword
matching and flows through to script, timeline, and composition. However:

- No stage uses `mood` to alter pacing.
- No stage uses `mood` to alter ambient texture.
- No stage uses `mood` to alter visual treatment.
- No stage uses `mood` to alter typography style.

`mood` is a data field with no behavioral consequence in the current implementation.
This is intentional for MVP. It becomes a liability if left unaddressed through Sprint 03.

---

## When artistic validation begins

Artistic validation begins when **one real 30-second scene** is produced with at least
one real provider (real TTS, real image generation, or real ambient audio) and reviewed
by a human.

Until that happens, all artistic claims about the pipeline are speculative.

See `docs/sprints/sprint-03-atmosphere.md` for the planned atmosphere phase.
