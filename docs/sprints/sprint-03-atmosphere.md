# Sprint 03 — Atmosphere Phase

**Status:** Planned (begins after MVP ships)
**Prerequisite:** Issue #011 (CLI wiring) and #012 (CI) complete; MVP acceptance criteria
all passing.

---

## Goal

Produce one real, watchable 30-second horror scene that demonstrates cinematic atmosphere.
This sprint is the first artistic validation loop. Technical correctness is a precondition,
not the goal.

---

## Sprint 03 is NOT

- Scaling to many stories.
- Adding batching or parallel scene processing.
- Adding orchestration systems or distributed execution.
- Adding fan-out subagents.
- Adding real providers for all adapters simultaneously.

**Do not expand scope to the full pipeline until one scene emotionally works.**

---

## Sprint 03 deliverables

### Required (all must land before Sprint 03 is done)

| Item | Description |
|------|-------------|
| One real provider | Replace exactly one mock with a real provider. TTS or image generation is recommended as highest emotional impact. Start with local/offline options (e.g. Coqui TTS, local Stable Diffusion) before cloud APIs. |
| One real scene | Run the full pipeline on a single hand-selected scene from *Pigeons from Hell*. The scene should be ≤ 30 seconds of narration. |
| First human review | A human watches the produced video and gives feedback. This feedback is recorded in `docs/checkpoints/checkpoint-sprint03.md`. |
| Mood → behavior wiring | At minimum, `mood` must influence one observable output: ambient silence vs. ambient texture, or pacing variation between `fear` and `calm` moods. |

### Optional (nice-to-have, not blockers)

| Item | Description |
|------|-------------|
| Bilingual text | Replace mock Ukrainian with real translation (LLM or API). Only add this if it does not block the real scene goal. Removing secondary language temporarily is acceptable. |
| Silence / pause logic | Dramatic pauses at scene breaks, before dialogue lines, or at high-fear moments. |

---

## What success looks like

A human watches the 30-second output and says: "I can feel the horror atmosphere" or
"this is heading somewhere interesting." Not "the pipeline works."

Technical pass/fail is not the Sprint 03 acceptance criterion. Emotional resonance is.

---

## Architectural constraints (unchanged from constitution)

- Still no distributed systems.
- Still no message queues or container orchestration.
- Still no plugin framework.
- Still no async orchestration expansion.
- Still no microservices.
- Still a single Python process driven by the existing CLI.

Real providers plug in through the existing `AdapterFactory` — no new abstractions.

---

## Known gaps to address before Sprint 03

See `docs/product/ARTISTIC_GAP.md` for the full list. The minimum to close before
Sprint 03 work begins:

1. `mood` must drive at least one behavioral difference.
2. Absolute paths in sidecar files replaced with relative paths (known tech debt from
   checkpoint-008).
3. CLI `--scene` partial re-run wired and tested (from #011).

---

## Risks

| Risk | Mitigation |
|------|------------|
| Real provider produces unusable output | Fallback to mock; record what "unusable" means; do not block Sprint 03 on provider quality |
| Bilingual text blocks the scene | Temporarily remove secondary language for Sprint 03; re-add in Sprint 04 |
| Scope creep into full pipeline | Hard limit: one scene, one provider, one human review. If a second scene works, Sprint 03 is done early. |
