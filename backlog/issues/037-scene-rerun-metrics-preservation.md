# Issue #037 — Metrics: preserve full-run metrics during `--scene` reruns

**Status:** Closed
**Sprint:** 07
**Priority:** P1
**Labels:** metrics, cli, regen, bug
**Estimate:** 1d
**Depends on:** #029
**Blocks:** —

---

## Problem

`python -m horror_story run --scene ...` writes scene-rerun metrics to:

```text
<run_dir>/metrics.json
```

This overwrites the original full-run metrics artifact. The final render during the
scene rerun is also not wrapped in a metrics stage, so the replacement metrics file
does not capture all work performed by that command.

This loses historical performance data and makes `horror-story stats` misleading.

---

## Scope

### `src/horror_story/cli.py`

- Do not overwrite the original full-run `metrics.json` during `--scene` reruns.
- Write revision-scoped metrics, for example:
  - `metrics_<scene_id>_r<n>.json`, or
  - `metrics/scene_<scene_id>_r<n>.json`
- Wrap the scene-rerun final render call in a `render` metrics stage.
- Update validation globs to include the chosen revision metrics path.

### `horror-story stats`

- Decide whether stats should show full-run metrics only or include scene-rerun
  metrics separately.
- Make that behavior explicit in tests and output labels.

### Tests

- Add a CLI test that creates an existing `metrics.json`, runs `--scene`, and asserts
  the original metrics file is preserved.
- Assert a new scene-rerun metrics artifact exists and includes a `render` stage.

---

## Acceptance Criteria

1. `--scene` reruns never overwrite the full-run `metrics.json`.
2. Scene-rerun metrics include script, tts, image, motion, audio, timeline,
   typography, compositor, and render timing where those stages run.
3. `validate --run-dir` validates both full-run and scene-rerun metrics artifacts.
4. `horror-story stats` behavior for scene-rerun metrics is documented by tests.
5. `pytest` and `mypy --strict src/` pass.

