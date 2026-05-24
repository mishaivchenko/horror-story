# Reconciliation Summary

**Date (pre-#001):** 2026-05-24 — Reconciler: Claude Code → READY FOR ISSUE #001
**Date (pre-#011):** 2026-05-24 — Final architectural hardening pass → READY FOR ISSUE #011
**Date (post-MVP):** 2026-05-24 — Commit 6bf3863 — Typography adaptive zones v1 → READY FOR SPRINT 03

---

## Post-MVP correction: Typography adaptive zones v1 (2026-05-24)

**Problem:** `MockTypographyAdapter` rendered the full concatenated script as raw
full-frame text (EN narration + secondary + all dialogue), covering the entire image.
The "image is the dominant visual" contract was violated. This was caught before Sprint 03.

**Fix (commit 6bf3863):**
- Replaced `_render_overlay` with a two-zone safe-area layout (`_pick_zones`).
- Primary zone: bottom strip for narration.
- Secondary zone: upper left or right for dialogue (when present).
- Zone side deterministic via `SHA-256(scene_id:seed)` — no Python `hash()`.
- Each zone: semi-transparent dark box, text clamped to fit, opaque pixels < 50% of frame.
- 6 new tests + 2 updated tests.
- Spec (`spec/PIPELINE.md` Stage 7, `spec/MVP_PLUS.md` F-08) updated to reflect new contract.
- Backlog issue #006 updated with adaptive zones v1 acceptance criteria.
- Checkpoint `docs/checkpoints/checkpoint-012.md` written.

---

## Changes made

### 1. Sprint 01 scope corrected

**Problem:** Sprint 01 goal promised a final MP4 ("valid placeholder final MP4 for the
first 3 scenes"). The DoD contradicted this with "no video yet" on the last line.

**Fix:** `docs/sprints/sprint-01.md` — sprint goal now explicitly states **no video
output**. Sprint 01 ends at WAV + PNG artifacts. Sprint 02 adds motion, compositor,
renderer. The DoD is now a single coherent statement.

---

### 2. MVP / MVP+ split introduced

**Problem:** A single `MVP_PLUS.md` was used for everything from "scaffold" to "full
Pigeons from Hell pipeline." No clear checkpoint for "pipeline works."

**Fix:** Created `spec/MVP.md` as the **first milestone**: 3-scene mini-story fixture,
all mock adapters, full artifact chain, CLI, CI. `spec/MVP_PLUS.md` is updated to be
explicitly post-MVP scope (begins after MVP ships). Issues #006–#011 now reference
`spec/MVP.md`.

---

### 3. Determinism model fixed

**Problem:** Constitution said "bit-identical artifacts" but `manifest.schema.json` had a
`created_at` field and the run directory used `run_<timestamp>`, both of which would
break bit-identity across runs.

**Fix:**
- Removed `created_at` from `manifest.schema.json`.
- Run directory is now `run_<story_id>_<seed>` (deterministic name, no timestamp).
- Constitution and TECHNICAL_PLAN now distinguish "deterministic content" (the
  guarantee) from "file metadata" (not part of the contract).
- Added explicit rule: SHA-256 of content artifacts must match across runs in mock mode.

---

### 4. Regeneration contract defined

**Problem:** `--regen` was mentioned in the constitution but never defined. `--scene`
behavior (what gets re-run, what file is written, what happens to the renderer) was
unspecified.

**Fix:** `spec/PIPELINE.md` now has a "Regeneration contract" section covering:
- `--scene <id>`: re-runs that scene's stages, writes `_r<n>` files, updates
  `artifact_index.json`, re-runs renderer.
- `--regen`: creates `run_<story_id>_<seed>_r<n>` directory; full clean re-run.
- `artifact_index.json`: the mutable "latest artifact" registry.
- Dependency invalidation: regenerating a scene marks downstream entries as `pending`.
- Renderer reads from `artifact_index.json`, not hardcoded paths.

---

### 5. Manifest immutability contradiction resolved

**Problem:** Stage 0 said "manifest is written once and never mutated." Stage 1 said
"write scene IDs into manifest.json." These were contradictory.

**Fix:** `spec/PIPELINE.md` — Stage 0 and Stage 1 are now defined as a single atomic
operation (`initialize_run()`). `manifest.json` is fully populated (including scene IDs)
before any other stage runs, then immutable. Stage 1 is a pure function returning
`list[Scene]`; the caller writes all files including `manifest.json`.

---

### 6. Missing artifact schemas added

**Problem:** Five artifact types had no schema: ambient, motion, typography,
composed-scene, artifact-index.

**Fix:** Added five minimal schemas:
- `spec/schemas/ambient_artifact.schema.json`
- `spec/schemas/motion_artifact.schema.json`
- `spec/schemas/typography_artifact.schema.json`
- `spec/schemas/composed_scene.schema.json`
- `spec/schemas/artifact_index.schema.json`

All kept minimal — only required fields for MVP.

---

### 7. Adapter interface signatures normalized

**Problem:** F-03 (TTS) had `synthesize(text, voice_id, language) -> Path` — missing
`seed` and `pacing_ms`. Issue #004 contradicted the spec by requiring both. All other
adapters had `seed` in their signatures. Inconsistent.

**Fix:** `spec/TECHNICAL_PLAN.md` now has a unified "Adapter interface contracts" section
with explicit Python signatures for all five adapters. Rules:
- `seed` is always the second-to-last argument.
- `out_path: Path` is always the last argument (caller-supplied destination).
- Mock writes to temp, then `Path.replace(out_path)`.

`spec/MVP_PLUS.md` F-03/F-04 updated to match. Issues #004 and #005 updated to match.

---

### 8. Scene boundary rule locked for MVP

**Problem:** F-01 said "configurable regex" which is underspecified for MVP and
incompatible with hand-written test fixtures.

**Fix:** `spec/MVP_PLUS.md` and `spec/PIPELINE.md` both now state: **MVP boundary rule
is `---` (a line containing only three dashes)**. Fixtures must use this. Paragraph-break
or word-count heuristics are explicit MVP+ scope.

Issue #002 acceptance criteria updated to match.

---

### 9. Pydantic and atomicwrites removed

**Problem:** `config.py` in the module tree referenced "Pydantic models." `atomicwrites`
was mentioned as a dependency. Neither was in the technology choices table.

**Fix:**
- `spec/TECHNICAL_PLAN.md` tech choices table now lists: argparse (stdlib), dataclasses
  (stdlib), `Path.replace()` (stdlib) for atomic writes.
- Module tree updated: `config.py` now says "dataclasses" not "Pydantic models."
- Issue #001 and #002 notes updated to make this explicit.

---

### 10. CI backlog issue corrected

**Problem:** Issue #012 said "Write `.github/workflows/ci.yml`" but those files already
exist on disk from the initial spec pass.

**Fix:** Issue #012 rewritten. Goal is now: "validate and wire" not "create". Tasks
describe confirming the existing files work after the scaffold lands, not rewriting them.
Label changed from `sprint-02` to `sprint-01` (CI must pass in Sprint 01).

---

## Files changed

| File | Change |
|------|--------|
| `docs/sprints/sprint-01.md` | Removed MP4 from sprint goal; fixed DoD |
| `spec/MVP.md` | **New.** 3-scene milestone definition |
| `spec/MVP_PLUS.md` | Added prerequisite note; fixed F-01 boundary rule; fixed F-03/F-04 signatures |
| `spec/TECHNICAL_PLAN.md` | Removed Pydantic/atomicwrites; added argparse/dataclasses; fixed run dir naming; fixed determinism strategy; normalized adapter interfaces; fixed test strategy |
| `spec/PIPELINE.md` | Resolved Stage 0+1 immutability; locked boundary rule; added Regeneration contract |
| `spec/constitution.md` | Fixed determinism clause; clarified artifact immutability + regen flags |
| `spec/README.md` | Added MVP.md; added schema table |
| `spec/schemas/manifest.schema.json` | Removed `created_at`; relaxed adapter enum |
| `spec/schemas/artifact_index.schema.json` | **New** |
| `spec/schemas/ambient_artifact.schema.json` | **New** |
| `spec/schemas/motion_artifact.schema.json` | **New** |
| `spec/schemas/typography_artifact.schema.json` | **New** |
| `spec/schemas/composed_scene.schema.json` | **New** |
| `backlog/issues/001-scaffold.md` | Locked argparse/dataclasses; removed click/Pydantic ambiguity |
| `backlog/issues/002-story-parser.md` | Fixed boundary rule; removed Pydantic; fixed function signature |
| `backlog/issues/003-script-gen.md` | Fixed field name (`text_secondary`); added voice_id fallback |
| `backlog/issues/004-tts-adapter.md` | Aligned signature with normalized contract |
| `backlog/issues/005-image-adapter.md` | Aligned signature; added `out_path` convention |
| `backlog/issues/006–011` | Updated spec refs to `spec/MVP.md` |
| `backlog/issues/012-ci.md` | Rewritten: validate/update not create; moved to sprint-01 |

---

## Remaining decisions (not blockers for #001)

These are documented for visibility but do not block Sprint 01:

1. **`validate-schemas` CLI stub**: Issue #001 must add this stub so CI (issue #012) can
   run `python -m horror_story validate-schemas` without erroring. The stub can exit 0
   and print "OK" — real validation is Issue #012's job.

2. **`AdapterFactory` location**: Introduced in issues #004 and #005 but not yet placed
   in the module tree. Implementer should put it in `horror_story/adapters/__init__.py`
   as specified in those issues. No spec change needed.

3. **`artifact_index.json` write path**: Stage 0+1 must create this file with all scenes
   at `"status": "pending"`. The schema exists; the implementation detail belongs in
   issue #002's manifest task.

---

## READY FOR ISSUE #001

---

# Pre-#011 Architectural Hardening Pass

**Date:** 2026-05-24
**Context:** Issues #001–#010 complete. CLI/e2e wiring (#011) is next.
**Purpose:** Lock architectural decisions discovered during Sprint 02 before CLI wiring begins.

---

## A. Typography contract hardened

**Contracts locked in `spec/PIPELINE.md` Stage 7:**
- Typography output for MVP is a transparent RGBA PNG overlay only.
- Typography stage owns text layout and visual framing only.
- Typography stage does NOT generate MP4.
- Typography stage does NOT invoke FFmpeg.
- Typography stage does NOT own subtitle timing.
- The compositor owns overlay application to video.

**Future note added:** Timed typography, animated subtitles, PNG sequences, and
ASS/SRT subtitle pipelines are explicitly Sprint 03+ scope, not MVP.

No remaining spec, backlog, or docs describe typography MP4 output or FFmpeg inside
the typography stage.

---

## B. Timeline contract hardened

**Architectural law added to `spec/PIPELINE.md` Stage 7.5:**

> "No compositor timing logic may exist outside timeline artifacts."

Explicit contracts locked:
- `timeline.json` is the sole temporal authority (start_s, end_s, source_path, track
  ordering, scene duration).
- The compositor MUST NOT infer timing, reconstruct source paths, calculate implicit
  durations, or invent track ordering.
- All future emotion/pacing systems MUST emit explicit `timeline.json` changes before
  composition runs.

---

## C. Artistic gap documented

**New file: `docs/product/ARTISTIC_GAP.md`**

Explicitly documents:
- MVP validates technical pipeline integrity only.
- MVP does NOT validate artistic quality.
- Passing tests do not imply atmospheric success.
- Mock outputs are intentionally emotionally empty.
- Cinematic horror atmosphere does not exist in the current implementation.
- `mood` metadata is structurally present but artistically inert.

Warning recorded:
> "The project can reach 100% technical correctness while still producing emotionally
> dead content."

---

## D. Post-MVP atmosphere phase specified

**New file: `docs/sprints/sprint-03-atmosphere.md`**

Sprint 03 goals documented:
- One real 30-second scene.
- One real provider (TTS or image generation, local-first preferred).
- One human artistic review loop.
- `mood` must drive at least one observable behavioral difference.
- Bilingual text or temporary secondary-language removal.
- Silence/pause logic (optional).

Hard constraints preserved:
- No batching, no orchestration systems, no fan-out subagents before one scene works.
- No distributed systems.
- Single Python process, existing `AdapterFactory`.

**`spec/MVP_PLUS.md`** updated with pointer to Sprint 03 atmosphere phase and the gate:
no real provider integration until one scene has been confirmed to carry horror atmosphere
by a human reviewer.

---

## E. Architectural discipline reinforced

**`spec/constitution.md`** updated with "Architectural discipline — always enforced" section:

- No provider integrations before #011/#012 complete.
- No architecture redesign inside implementation issues.
- No plugin framework.
- No distributed systems, message queues, or container orchestration (ever).
- No async orchestration expansion beyond existing spec requirements.
- No cinematic engine implementation before one real scene has been human-reviewed.
- Spec before implementation for any stage contract, artifact schema, or timing change.

Each constraint is documented with its rationale (identified failure mode).

---

## Files changed

| File | Change |
|------|--------|
| `spec/PIPELINE.md` | Added typography MVP contract + future-work note; added timeline architectural law |
| `spec/constitution.md` | Added "Architectural discipline — always enforced" section |
| `spec/MVP_PLUS.md` | Added Sprint 03 atmosphere phase pointer and provider integration gate |
| `docs/product/ARTISTIC_GAP.md` | **New.** Artistic gap acknowledgement document |
| `docs/sprints/sprint-03-atmosphere.md` | **New.** Sprint 03 atmosphere phase plan |
| `RECONCILIATION_SUMMARY.md` | This section appended |

---

## Remaining ambiguities

1. **Absolute paths in sidecars** — Known tech debt from checkpoint-008 item 6. Not
   addressed here (runtime behavior change). Must be resolved in or before #011.

2. **`_r<n>` regeneration logic** — Specified in `spec/PIPELINE.md` (Regeneration
   contract). CLI implementation is #011's responsibility. No spec gap.

3. **Seed XOR formula** — Specified in `spec/TECHNICAL_PLAN.md` but not yet
   implemented. Only affects real (non-mock) providers. Not a blocker for #011.

4. **`mood` behavioral wiring** — Currently inert. Deferred to Sprint 03 by design.
   Acknowledged in `docs/product/ARTISTIC_GAP.md`. Not a blocker for #011.

---

## READY FOR ISSUE #011
