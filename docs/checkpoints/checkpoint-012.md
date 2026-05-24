# Checkpoint: After Adaptive Zones v1 — Typography Layout Correction

**Date:** 2026-05-24
**Commit:** 6bf3863
**Branch:** main
**Preceding state:** All 12 MVP issues complete (checkpoint-008 + #008b + #009–#012)

---

## Context

Before Issue #012 (CI), a visual correction was applied to the typography overlay:
text was covering the entire frame. This checkpoint documents that correction and the
current complete-MVP state of the project.

---

## Quality Metrics

| Metric | Result |
|---|---|
| pytest | 240 passed, 5 warnings, 0 failed |
| Skipped tests | FFmpeg-dependent tests skip gracefully when FFmpeg absent |
| Coverage | ~94% (unchanged from checkpoint-008 baseline) |
| mypy --strict | Success: no issues found in 30 source files |
| Schema validation | 12 schemas loaded, all well-formed |

---

## Typography Adaptive Zones v1

### Problem
`MockTypographyAdapter._render_overlay` rendered the entire concatenated script as
full-frame text (EN + secondary + all dialogue), covering the whole image. The
"image as dominant visual" contract was violated.

### Solution
Replaced full-frame text rendering with a two-zone safe-area layout:

| Zone | Position | Content | Condition |
|------|----------|---------|-----------|
| Primary | Bottom strip, full width minus margins, max 30% height | Narration EN + secondary | Always |
| Secondary | Upper left or right, max 50% width, max 30% height | Dialogue character + text | Only when `dialogue_lines` non-empty |

Zone layout properties:
- Zone side (left vs right) from `SHA-256(scene_id + ":" + seed)[0] % 2` — stable across runs, not Python's salted `hash()`
- Background: semi-transparent dark box (`rgba(0,0,0,160)`)
- Text clamped to box; overflow truncated, never drawn outside
- Opaque pixels stay below 50% of total frame area (verified by test)
- No zone overlap, all zones within frame bounds

### New tests (6 added)
- `test_text_boxes_not_full_frame_coverage` — opaque < 50% of frame
- `test_two_zone_layout_when_dialogue_present` — both halves have pixels
- `test_layout_deterministic_pixels` — byte-identical PNG for same inputs
- `test_no_zone_overlap` — direct test of `_pick_zones()`
- `test_single_zone_no_dialogue` — one zone without dialogue
- `test_zones_respect_frame_bounds` — all zones inside frame

### Modified tests (2)
`test_mock_typography_text_visible` and `test_mock_typography_secondary_text_visible`
relaxed from region-specific assertions to whole-image assertions (layout no longer
guarantees text in the upper third).

---

## Complete Pipeline State

| # | Stage | Module | Status |
|---|---|---|---|
| #001 | Scaffold | `config.py`, `manifest.py`, `cli.py`, `schemas.py` | Complete |
| #002 | Story parser | `pipeline/parse.py`, `models.Scene` | Complete |
| #003 | Script generator | `pipeline/script.py` | Complete |
| #004 | TTS adapter (mock) | `adapters/tts/` | Complete |
| #005 | Image adapter (mock) | `adapters/image/` | Complete |
| #006 | Typography overlay (mock, adaptive zones v1) | `adapters/typography/` | Complete |
| #007 | Motion adapter (mock) | `adapters/motion/` | Complete |
| #008 | Ambient audio adapter (mock) | `adapters/audio/` | Complete |
| #008b | Timeline planner | `pipeline/timeline.py` | Complete |
| #009 | Scene compositor | `pipeline/compositor.py` | Complete |
| #010 | Final renderer | `pipeline/renderer.py` | Complete |
| #011 | End-to-end CLI | `cli.py` | Complete |
| #012 | CI | `.github/workflows/` | Complete |

---

## End-to-End Verification

```bash
python -m horror_story run --story tests/fixtures/mini-story.txt --out output/e2e_test --seed 42
# → output/e2e_test/run_mini-story_42/final_mini-story_42.mp4
```

The pipeline runs without errors on the 3-scene `mini-story.txt` fixture. Typography
overlays show two-zone layout (dialogue in upper box, narration in bottom bar).

---

## Known Limitations (deferred to Sprint 03)

These are intentional mock-first limitations, not bugs:

| Item | State |
|------|-------|
| Images | Grey PNG with scene ID label |
| Audio | Silent WAV (narration, dialogue, ambient) |
| Typography font | Pillow default — no horror aesthetic |
| Bilingual text | Word-reversed placeholder (`[uk]` prefix) |
| Mood field | Populated but behaviorally inert |
| Motion | Static frame loop |

See `docs/product/ARTISTIC_GAP.md` for the full artistic gap analysis.

---

## Next: Sprint 03 — Atmosphere Phase

Prerequisites met. Sprint 03 begins when the human maintainer is ready to:
1. Select one mock adapter to replace with a real provider (TTS or image gen recommended).
2. Select one scene from *Pigeons from Hell* as the first real test.
3. Run a human review and record the verdict in a new checkpoint.

See `docs/sprints/sprint-03-atmosphere.md`.
