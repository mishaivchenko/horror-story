# Issue 006 — Motion adapter: keyframe → silent video (mock-first)

**Labels:** `adapter`, `sprint-02`
**Spec refs:** `spec/MVP.md` §F-06; `spec/MVP_PLUS.md` §F-06; `spec/PIPELINE.md` §Stage 5
**Estimate:** 0.5 day
**Depends on:** #005

## Goal

Define the `MotionAdapter` ABC and implement `MockMotionAdapter` that converts a PNG
keyframe into a looping silent MP4 video of the correct duration.

## Acceptance criteria

- [ ] `MotionAdapter` ABC in `horror_story/adapters/motion/base.py` with signature:
      `animate(self, frame_path: Path, duration_s: float, fps: int, effect: str, seed: int, out_path: Path) -> Path`
- [ ] `MockMotionAdapter` produces a valid MP4: H.264, `fps` frames per second, no audio
- [ ] Video duration matches `duration_s` ± 1 frame
- [ ] Same inputs → same output bytes (deterministic; FFmpeg invoked with fixed args)
- [ ] Adapter registered: `AdapterFactory.get_motion("mock") -> MockMotionAdapter`
- [ ] `pytest tests/test_motion.py` passes with ≥ 85% coverage on `motion/`
- [ ] `mypy --strict` passes

## Tasks

1. Define `MotionAdapter` ABC.
2. Implement `MockMotionAdapter` using FFmpeg subprocess (`ffmpeg -loop 1 -t <dur> -i <png>`).
3. Write a `FFmpegNotFoundError` that is raised if FFmpeg is missing at import time.
4. Write unit tests using a tiny 64×64 test PNG fixture; skip if FFmpeg not found
   (`pytest.mark.skipif`).

## Notes

- Use `subprocess.run` with explicit FFmpeg args. No shell=True.
- Log the exact FFmpeg command at DEBUG level so it is visible in CI.
