# Reconciliation Summary

**Date:** 2026-05-24
**Reviewer:** Codex (architecture/spec review → NOT READY)
**Reconciler:** Claude Code
**Result:** READY FOR ISSUE #001

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
