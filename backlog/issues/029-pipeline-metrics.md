# Issue #029 — Pipeline: per-stage timing and metrics collection

**Status:** Closed
**Sprint:** backlog
**Priority:** P3
**Labels:** observability, performance
**Estimate:** 1d
**Depends on:** —
**Blocks:** —

---

## Problem

Pipeline runs are slow (single scene with real image generation can take minutes).
There is no visibility into where time is spent, how runs compare over time, or
which stages are the bottleneck.

---

## Goal

Collect and persist per-stage wall-clock metrics for every pipeline run so that:

- Bottlenecks are visible without instrumenting manually.
- Runs can be compared across seeds, adapter choices, and hardware.
- No code change is required to start collecting; metrics are emitted automatically.

---

## Proposed design

### Artifact: `output/<story_id>/<run_id>/metrics.json`

Written at the end of each full pipeline run (or per-scene run with `--scene`).

```json
{
  "schema_version": "1.0",
  "story_id": "pigeons-from-hell",
  "run_id": "run-2026-05-26T14:00:00",
  "scene_id": null,
  "total_s": 183.4,
  "stages": [
    {"stage": "parse",      "scene_id": null,       "duration_s": 0.12},
    {"stage": "script_gen", "scene_id": null,       "duration_s": 1.83},
    {"stage": "tts",        "scene_id": "scene-01", "duration_s": 12.4},
    {"stage": "image",      "scene_id": "scene-01", "duration_s": 97.6},
    {"stage": "typography", "scene_id": "scene-01", "duration_s": 0.08},
    {"stage": "compositor", "scene_id": "scene-01", "duration_s": 4.2},
    {"stage": "render",     "scene_id": "scene-01", "duration_s": 67.1}
  ]
}
```

### CLI addition

`python -m horror_story stats` — prints a table of the last N runs:

```
run-id                    total    parse  script   tts   image   render
run-2026-05-26T14:00:00   183s     0.1s   1.8s    12s    98s     67s
run-2026-05-25T11:30:00   201s     0.1s   2.1s    13s   112s     74s
```

### Scope

- Thin `StageTimer` context-manager in `horror_story/metrics.py` — wraps each stage call in CLI orchestration layer only; no changes to adapter interfaces.
- `metrics.json` schema in `spec/schemas/`.
- `horror_story stats` sub-command reads `output/*/metrics.json` and pretty-prints.
- No changes to existing adapter or stage code.

---

## Acceptance criteria

1. After a full run, `output/<story_id>/<run_id>/metrics.json` exists and validates.
2. Each stage present in the manifest has a positive `duration_s`.
3. `python -m horror_story stats` prints a readable summary table.
4. Existing tests unaffected.
5. `mypy --strict` passes.
