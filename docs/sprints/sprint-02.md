# Sprint 02 — Full Pipeline (Video + CLI)

**Duration:** 2026-05-24 (completed same day as Sprint 01)
**Goal:** motion adapter, ambient audio, typography, compositor, renderer, timeline planner,
end-to-end CLI, and CI hardening all complete. Full pipeline produces a real MP4.

**Status: COMPLETE** — all Sprint 02 issues closed on 2026-05-24.

---

## Sprint backlog

| Issue | Title | Owner | Estimate | Status |
|-------|-------|-------|----------|--------|
| #006 | Typography overlay (mock-first, PNG) | Claude Code | 0.5d | **Done** |
| #007 | Motion adapter (mock-first) | Claude Code | 0.5d | **Done** |
| #008 | Ambient audio adapter (mock-first) | Claude Code | 0.25d | **Done** |
| #008b | Timeline planner (Stage 7.5) | Claude Code | — | **Done** |
| #009 | Scene compositor | Claude Code | 1d | **Done** |
| #010 | Final renderer | Claude Code | 0.5d | **Done** |
| #011 | End-to-end CLI | Claude Code | 0.5d | **Done** |

---

## Definition of done

- Full pipeline runs: `python -m horror_story run --story <txt> --out <dir>` → `final_<id>_<seed>.mp4`. ✓
- 240 tests passing (FFmpeg-dependent tests skip gracefully when FFmpeg absent). ✓
- `mypy --strict src/` passes across 30 source files. ✓
- 12 JSON schemas loaded and validated. ✓
- Typography adaptive zones v1: text in constrained semi-transparent boxes, not full-frame. ✓
- Per-scene `--scene` re-run, `--dry-run`, `--validate`, `--seed`, `--width`/`--height` flags all wired. ✓

---

## Notable technical decisions

- **Stage 7.5 (timeline planner)** extracted as its own module (`pipeline/timeline.py`). The
  timeline JSON is the sole temporal authority for the compositor; no stage computes timing
  independently.
- **Typography adaptive zones v1**: mock layout positions narration in a bottom strip and
  dialogue (when present) in an upper left/right box, determined by SHA-256 of `scene_id + seed`.
  Text is clamped to fit; opaque pixels stay below 50% of frame area.
- **Compositor** uses `adelay + amix` for audio mixing and `overlay=format=auto` for RGBA
  alpha-compositing of the typography PNG onto the motion video.
- **Renderer** uses FFmpeg concat demuxer with a Pillow-generated title card PNG; output
  SHA-256 written to `render_job.json` for determinism verification.

---

## Known limitations (addressed in Sprint 03)

See `docs/product/ARTISTIC_GAP.md` for the full list. Key items:

| Item | State |
|------|-------|
| Keyframe images | Grey PNG with scene ID label (mock) |
| Audio | Silent WAV files (mock) |
| Typography | System font, boxes visible but not stylized |
| Bilingual text | Word-reversed placeholder (`[uk]` prefix) |
| Mood field | Populated but behaviorally inert |

These are intentional for mock-first MVP. Sprint 03 replaces at least one mock with a
real provider and validates artistic output with a human reviewer.
