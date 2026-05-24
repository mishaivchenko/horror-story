# Spec Kit

This directory is the **source of truth** for the Horror Story pipeline.
All implementation decisions must trace back to a document here.

## Documents

| File | Purpose |
|------|---------|
| `constitution.md` | Hard constraints, working agreements, immutable principles |
| `MVP.md` | **Start here.** 3-scene mock vertical slice — Sprint 01 + 02 target |
| `MVP_PLUS.md` | Full *Pigeons from Hell* pipeline — begins after MVP ships |
| `TECHNICAL_PLAN.md` | Architecture, module breakdown, technology choices |
| `PIPELINE.md` | Stage-by-stage data flow, regeneration contract |
| `schemas/` | JSON Schema definitions for every artifact type |

## Schemas

| File | Artifact |
|------|---------|
| `manifest.schema.json` | Pipeline manifest (written once at Stage 0+1) |
| `scene.schema.json` | Per-scene JSON |
| `script.schema.json` | Per-scene bilingual script |
| `keyframe.schema.json` | Image generation sidecar |
| `voice_line.schema.json` | TTS audio sidecar |
| `ambient_artifact.schema.json` | Ambient audio sidecar |
| `motion_artifact.schema.json` | Motion/VFX video sidecar |
| `typography_artifact.schema.json` | Typography overlay sidecar |
| `composed_scene.schema.json` | Composed scene MP4 sidecar |
| `render_job.schema.json` | Final render job record |
| `artifact_index.schema.json` | Mutable latest-artifact registry for a run |

## Conventions

- Specs are written in Markdown.
- Every spec section that drives implementation has a **Status** field:
  `Draft | Review | Accepted | Superseded`.
- When a spec is superseded, leave it in place and add a `Superseded-by:` link.
- Acceptance criteria in `MVP_PLUS.md` are the definition of done for each issue.
- Schema files are the contract between pipeline stages. A stage that reads an artifact
  must validate it against the schema before processing.

## How to update specs

1. Open a PR that changes the spec file.
2. Tag it `spec-change`.
3. Get at least one review (human or Codex) before merging.
4. After merging, file or update GitHub Issues if implementation work is implied.
