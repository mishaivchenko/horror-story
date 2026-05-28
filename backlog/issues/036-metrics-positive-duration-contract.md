# Issue #036 — Metrics: enforce positive stage durations

**Status:** Closed
**Sprint:** 07
**Priority:** P1
**Labels:** metrics, schema, bug
**Estimate:** 0.5d
**Depends on:** #029
**Blocks:** —

---

## Problem

`MetricsCollector.stage()` rounds elapsed wall time to three decimals before storing
it. Fast stages can therefore record `duration_s = 0.0`.

This violates the acceptance criteria in #029:

> Each stage present in the manifest has a positive `duration_s`.

The current schema also permits zero:

```json
"duration_s": {"type": "number", "minimum": 0}
```

So both the implementation and schema allow artifacts that do not satisfy the issue
contract.

---

## Scope

### `src/horror_story/metrics.py`

- Store a strictly positive stage duration.
- Prefer preserving real precision instead of rounding to zero.
- If rounding is retained for readability, clamp to a small positive value after
  measuring elapsed time.

### `spec/schemas/metrics.schema.json`

- Require `duration_s > 0` for stage entries.
- Keep `total_s >= 0` unless a stronger total-duration contract is added.

### `tests/test_metrics.py`

- Change duration assertions from `>= 0` to `> 0`.
- Add a regression test for an effectively no-op stage.
- Validate the written metrics JSON against the stricter schema.

---

## Acceptance Criteria

1. A no-op `with metrics.stage("parse"):` records `duration_s > 0`.
2. `metrics.schema.json` rejects stage entries with `duration_s = 0`.
3. Existing metrics tests pass.
4. `mypy --strict src/` passes.

