# Issue #020 — --scene flag fails when full run used --regen

**Status:** Done
**Sprint:** 03
**Labels:** cli, bug
**Estimate:** 0.5d
**Depends on:** #011
**Blocks:** —

---

## Problem

`--scene` requires an existing run directory named `run_<story_id>_<seed>` (no suffix).
But when a full run is created with `--regen`, it gets a versioned suffix:
`run_<story_id>_<seed>_r1`, `_r2`, etc.

Result: `--scene` always fails with:

```
[error] no existing run at output/pigeons-test/run_pigeons-from-hell_42. Run without --scene first.
```

even though a valid run exists at `output/pigeons-test/run_pigeons-from-hell_42_r1`.

---

## Reproduction

```bash
# First full run — creates run_pigeons-from-hell_42
python -m horror_story run --story ... --out output/pigeons-test --seed 42

# Second full run with --regen — creates run_pigeons-from-hell_42_r1
python -m horror_story run --story ... --out output/pigeons-test --seed 42 --regen

# --scene now fails because it looks for run_pigeons-from-hell_42 (no longer the latest)
python -m horror_story run --story ... --out output/pigeons-test --seed 42 \
  --scene griswell-awoke-suddenly-every-nerve-tingling-pre
# → [error] no existing run at output/pigeons-test/run_pigeons-from-hell_42
```

---

## Root cause

`src/horror_story/cli.py:434`:

```python
base_run_dir = out_dir / base_run_id  # always run_<id>_<seed>, no suffix
```

`--scene` checks `base_run_dir.exists()` — but `--regen` on a full run writes to
`run_<id>_<seed>_r1`, leaving `run_<id>_<seed>` as the old (possibly stale) directory.

---

## Fix

When `--scene` is passed, resolve `base_run_dir` to the **latest versioned run** if the
bare directory does not exist:

```python
def _resolve_run_dir(out_dir: Path, base_run_id: str) -> Path | None:
    bare = out_dir / base_run_id
    if bare.exists():
        return bare
    # find highest _r<n> sibling
    candidates = sorted(out_dir.glob(f"{base_run_id}_r*"))
    return candidates[-1] if candidates else None
```

Use this in the `--scene` branch instead of `base_run_dir` directly.

---

## Acceptance criteria

1. `--scene` resolves to the latest `_r<n>` directory when the bare directory is absent.
2. If neither bare nor versioned directory exists, the existing error message is shown.
3. Existing `--scene` tests pass; add a test covering the `_r1` resolution case.
4. `mypy --strict` passes.
