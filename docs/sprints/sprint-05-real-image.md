# Sprint 05 — Real Image Generation

**Status:** Active (started 2026-05-26)
**Prerequisite:** Sprint 04 complete — per-segment typography, timed overlays, full-run MP4.

---

## Goal

Replace the mock grey keyframe with a real AI-generated image via FLUX.1-schnell (mflux).
First sprint where the pipeline produces a visually atmospheric scene.

---

## Sprint 05 is NOT

- Multi-scene parallel generation.
- Real ambient audio or music.
- Real Ukrainian translation.
- Animation beyond the existing zoom effect.

---

## Issues

| # | Title | Status |
|---|-------|--------|
| #026 | MfluxImageAdapter: real keyframe via FLUX.1-schnell | **Closed** |
| #027 | CLI: `--image-adapter` flag to override adapter at runtime | **Closed** |

---

## Acceptance criteria

1. `python -m horror_story run ... --image-adapter mflux-schnell` completes one scene end-to-end.
2. The resulting MP4 contains a real AI-generated keyframe (not a grey rectangle).
3. `--image-adapter` absent → falls back to `pipeline.toml` value unchanged.
4. `pytest` passes (296+ tests, 1 skipped smoke test).
5. `mypy --strict src/` passes.

---

## Known gaps going into Sprint 06

1. **No real ambient audio** — mock silence; no environmental sound or music.
2. **Typography secondary language** — placeholder reversed-English, not real Ukrainian.
3. ~~**HuggingFace auth required** — FLUX.1-schnell is a gated model; first run downloads ~8 GB.~~ **Resolved** — model downloaded, auth confirmed working.
