# Issue 007 — Motion adapter: keyframe → silent video (mock-first)

**Status:** Done

**Labels:** `adapter`, `sprint-02`
**Spec refs:** `spec/MVP.md` §F-06; `spec/MVP_PLUS.md` §F-06; `spec/PIPELINE.md` §Stage 5
**Estimate:** 0.5 day
**Depends on:** #005

### Goal
Define the `MotionAdapter` ABC and implement `MockMotionAdapter` that converts a PNG
keyframe into a looping silent MP4 video of the correct duration.

### Acceptance criteria
- [ ] `MotionAdapter` ABC in `horror_story/adapters/motion/base.py` with signature:
      `animate(self, frame_path: Path, duration_s: float, fps: int, effect: str, seed: int, out_path: Path) -> Path`
- [ ] `MotionAdapter` removed from `horror_story/adapters/base.py` and its `__all__`;
      `base.py` re-exports from `adapters/motion/base.py` if downstream code requires it
- [ ] `MockMotionAdapter` produces a valid MP4: H.264, `fps` frames per second, no audio,
      dimensions identical to the source keyframe PNG (`width × height`)
- [ ] Video duration matches `duration_s` ± 1 frame; `fps` is the caller-supplied value
- [ ] Same inputs + seed → same output bytes (FFmpeg invoked with `-fflags +bitexact` and
      fixed ordered args; no timestamp metadata embedded)
- [ ] `motion_<scene_id>.json` sidecar written at `out_path.with_suffix('.json')` and
      validates against `spec/schemas/motion_artifact.schema.json`; sidecar includes
      required `effect`, `source_keyframe`, and `output_path` (relative to cwd), and
      optional `width`/`height` matching the source keyframe dimensions
- [ ] `ffmpeg_available() -> bool` helper exposed in `horror_story/adapters/motion/mock.py`
      (or a shared `horror_story.adapters.motion` namespace); used by test `skipif` guards
- [ ] `animate()` raises `FFmpegNotFoundError` at call time if FFmpeg is absent from `$PATH`;
      the module imports cleanly even when FFmpeg is absent
- [ ] Adapter registered: `AdapterFactory.get_motion("mock") -> MockMotionAdapter`
- [ ] `pytest tests/test_motion.py` passes with ≥ 85% coverage on `motion/`
- [ ] `mypy --strict` passes

### Output artifacts
```
frames/motion_<scene_id>.mp4    ← silent H.264 video (repeated keyframe)
frames/motion_<scene_id>.json   ← sidecar (motion_artifact schema)
```

### Tasks
1. Define `MotionAdapter` ABC in `horror_story/adapters/motion/base.py`.
2. Remove `MotionAdapter` from `horror_story/adapters/base.py` and update `__all__`.
3. Implement `MockMotionAdapter` in `horror_story/adapters/motion/mock.py`:
   - `ffmpeg_available() -> bool` checks `shutil.which("ffmpeg") is not None`
   - `FFmpegNotFoundError(RuntimeError)` raised inside `animate()` when FFmpeg absent
   - FFmpeg invocation: `ffmpeg -fflags +bitexact -loop 1 -t <dur> -r <fps> -i <png>
     -c:v libx264 -pix_fmt yuv420p -y <tmp_out>`
   - Mock ignores `effect`; sidecar records it as passed
4. Add `get_motion()` to `AdapterFactory`.
5. Write unit tests using a 64×64 test PNG fixture; all tests that invoke FFmpeg use
   `pytest.mark.skipif(not ffmpeg_available(), reason="FFmpeg not installed")`.

### Notes
- `subprocess.run` with explicit list args. No `shell=True`.
- Log the exact FFmpeg command at DEBUG level.
- Write to temp path, then `Path.replace(out_path)`.
- `fps` and `duration_s` are always caller-supplied; the pipeline passes values from
  the render config (default 24 fps) and the scene's `total_duration_ms`.
