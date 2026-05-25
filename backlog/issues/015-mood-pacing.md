# Issue #015 — Mood → pacing wiring

**Status:** Done
**Sprint:** 03
**Labels:** pipeline, atmosphere
**Estimate:** 0.5d
**Depends on:** (none — can run in parallel with #013/#014)
**Blocks:** #017

---

## Problem

`pipeline/script.py::_pacing_ms(word_count)` computes segment duration from word count only.
The `mood` field on `Scene` is populated but never influences pacing, making it artistically
inert. This was explicitly flagged in `docs/product/ARTISTIC_GAP.md`.

Additionally, `Script` does not carry a `mood` field, so downstream stages must re-load the
scene JSON to retrieve it.

---

## Scope

### 1. Extend `_pacing_ms` with mood multipliers

```python
_MOOD_PACING: dict[str, float] = {
    "tension":  0.80,
    "violence": 0.80,
    "silence":  1.25,
    "mystery":  1.25,
}

def _pacing_ms(word_count: int, mood: str = "neutral") -> int:
    base = max(500, word_count * 100)
    return round(base * _MOOD_PACING.get(mood, 1.0))
```

### 2. Add `mood: str` to `Script` dataclass (`models.py`)

Propagate `Scene.mood` into `Script` when `generate_script()` builds the object.

### 3. Update `spec/schemas/script.schema.json`

Add `"mood"` to the required fields, same enum as `scene.schema.json`.

---

## Acceptance criteria

1. A `tension` scene produces segments with `pacing_ms` ≈ 80% of the word-count baseline.
2. A `silence` scene produces segments with `pacing_ms` ≈ 125% of the baseline.
3. A `neutral` scene is unchanged.
4. `Script` dataclass has a `mood` field; its value matches the source `Scene.mood`.
5. `script.schema.json` validates scripts with the `mood` field.
6. All existing tests pass.
7. `mypy --strict` passes.
