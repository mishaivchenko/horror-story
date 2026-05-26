# Issue #027 — CLI: --image-adapter flag to override adapter at runtime

**Status:** Closed
**Sprint:** 05
**Priority:** P2
**Labels:** cli, adapter
**Estimate:** 0.5d
**Depends on:** #026
**Blocks:** —

---

## Goal

Add a `--image-adapter` flag to the `run` subcommand so the image adapter can
be switched from the command line without editing `pipeline.toml`.

```bash
python -m horror_story run \
  --story stories/pigeons-from-hell/pigeons_from_hell_EN.txt \
  --out output/sprint05 \
  --seed 42 \
  --image-adapter mflux-schnell
```

---

## Scope

### `src/horror_story/cli.py`

Add argument to `run` subparser:

```python
run_p.add_argument(
    "--image-adapter",
    metavar="NAME",
    default=None,
    help="Override the image adapter from pipeline.toml (e.g. mock, mflux-schnell).",
)
```

In `_cmd_run`, apply override before passing `config.adapters` to `_run_scene`:

```python
if args.image_adapter is not None:
    import dataclasses
    config = dataclasses.replace(
        config,
        adapters=dataclasses.replace(config.adapters, image=args.image_adapter),
    )
```

No other changes — `_run_scene` already reads `adapters.image` from config.

---

## Tests

Add to `tests/test_cli.py`:

- `test_image_adapter_flag_overrides_config`: pass `--image-adapter mock` via
  `main([...])` with a monkeypatched `AdapterFactory`; assert
  `mock_factory.get_image` was called with `"mock"` not the toml value.
- `test_image_adapter_flag_absent_uses_toml`: no `--image-adapter` flag;
  assert `get_image` called with the adapter name from `pipeline.toml`.

---

## Acceptance criteria

1. `--image-adapter mflux-schnell` overrides `pipeline.toml` value for that run only.
2. Omitting the flag falls back to `pipeline.toml` unchanged.
3. Unknown adapter name surfaces as `ValueError` from `AdapterFactory` (no
   special validation needed in CLI — fail fast at first scene).
4. `--help` lists the flag with description.
5. `mypy --strict` passes.
6. All existing CLI tests pass.
