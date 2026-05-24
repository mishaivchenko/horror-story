"""Tests for Issue #007 — Mock Motion adapter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from horror_story.adapters import AdapterFactory
from horror_story.adapters.motion.base import MotionAdapter
from horror_story.adapters.motion.mock import (
    FFmpegNotFoundError,
    MockMotionAdapter,
    ffmpeg_available,
    ffprobe_available,
)
from horror_story.schemas import validate

FIXTURE_PNG = Path(__file__).parent / "fixtures" / "keyframe_64x64.png"

requires_ffmpeg = pytest.mark.skipif(
    not ffmpeg_available(), reason="FFmpeg not installed"
)
requires_ffprobe = pytest.mark.skipif(
    not ffprobe_available(), reason="ffprobe not installed"
)


# ---------------------------------------------------------------------------
# MotionAdapter ABC
# ---------------------------------------------------------------------------


def test_motion_adapter_is_abstract() -> None:
    with pytest.raises(TypeError):
        MotionAdapter()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# ffmpeg_available helper
# ---------------------------------------------------------------------------


def test_ffmpeg_available_returns_bool() -> None:
    result = ffmpeg_available()
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# FFmpegNotFoundError raised when FFmpeg absent
# ---------------------------------------------------------------------------


def test_ffmpeg_not_found_error_when_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("horror_story.adapters.motion.mock.ffmpeg_available", lambda: False)
    adapter = MockMotionAdapter()
    with pytest.raises(FFmpegNotFoundError):
        adapter.animate(
            frame_path=FIXTURE_PNG,
            duration_s=2.0,
            fps=24,
            effect="none",
            seed=1,
            out_path=tmp_path / "out.mp4",
        )


# ---------------------------------------------------------------------------
# MockMotionAdapter — video properties (requires ffmpeg)
# ---------------------------------------------------------------------------


@requires_ffmpeg
def test_mock_motion_writes_mp4(tmp_path: Path) -> None:
    adapter = MockMotionAdapter()
    out = tmp_path / "motion.mp4"
    result = adapter.animate(
        frame_path=FIXTURE_PNG,
        duration_s=1.0,
        fps=24,
        effect="none",
        seed=42,
        out_path=out,
    )
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0


@requires_ffmpeg
@requires_ffprobe
def test_mock_motion_duration_within_one_frame(tmp_path: Path) -> None:
    fps = 24
    duration_s = 2.0
    out = tmp_path / "motion.mp4"
    MockMotionAdapter().animate(
        frame_path=FIXTURE_PNG,
        duration_s=duration_s,
        fps=fps,
        effect="none",
        seed=0,
        out_path=out,
    )
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=nb_frames,r_frame_rate,codec_name",
         "-of", "json", str(out)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    assert stream["codec_name"] == "h264"
    nb_frames = int(stream["nb_frames"])
    expected = duration_s * fps
    assert abs(nb_frames - expected) <= 1


@requires_ffmpeg
@requires_ffprobe
def test_mock_motion_video_dimensions_match_source(tmp_path: Path) -> None:
    out = tmp_path / "motion.mp4"
    MockMotionAdapter().animate(
        frame_path=FIXTURE_PNG,
        duration_s=1.0,
        fps=24,
        effect="none",
        seed=0,
        out_path=out,
    )
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "json", str(out)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    assert stream["width"] == 64
    assert stream["height"] == 64


@requires_ffmpeg
@requires_ffprobe
def test_mock_motion_no_audio_stream(tmp_path: Path) -> None:
    out = tmp_path / "motion.mp4"
    MockMotionAdapter().animate(
        frame_path=FIXTURE_PNG,
        duration_s=1.0,
        fps=24,
        effect="none",
        seed=0,
        out_path=out,
    )
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type",
         "-of", "json", str(out)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data["streams"] == []


@requires_ffmpeg
def test_mock_motion_deterministic_bytes(tmp_path: Path) -> None:
    # Byte-for-byte identity holds within the same FFmpeg/libx264 build.
    # Cross-machine reproducibility is not guaranteed by this test.
    kwargs: dict[str, object] = dict(
        frame_path=FIXTURE_PNG,
        duration_s=1.0,
        fps=24,
        effect="none",
        seed=7,
        story_id="pigeons-from-hell",
        scene_id="scene_001",
    )
    out1 = tmp_path / "m1.mp4"
    out2 = tmp_path / "m2.mp4"
    MockMotionAdapter().animate(**kwargs, out_path=out1)  # type: ignore[arg-type]
    MockMotionAdapter().animate(**kwargs, out_path=out2)  # type: ignore[arg-type]
    assert out1.read_bytes() == out2.read_bytes()


# ---------------------------------------------------------------------------
# Sidecar JSON
# ---------------------------------------------------------------------------


@requires_ffmpeg
def test_mock_motion_sidecar_exists(tmp_path: Path) -> None:
    out = tmp_path / "motion.mp4"
    MockMotionAdapter().animate(
        frame_path=FIXTURE_PNG,
        duration_s=1.0,
        fps=24,
        effect="parallax",
        seed=1,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene_001",
    )
    assert out.with_suffix(".json").exists()


@requires_ffmpeg
def test_mock_motion_sidecar_validates_schema(tmp_path: Path) -> None:
    out = tmp_path / "motion.mp4"
    MockMotionAdapter().animate(
        frame_path=FIXTURE_PNG,
        duration_s=2.5,
        fps=24,
        effect="zoom",
        seed=99,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene_002",
    )
    sidecar = json.loads(out.with_suffix(".json").read_text())
    validate(sidecar, "motion_artifact.schema.json")


@requires_ffmpeg
def test_mock_motion_sidecar_fields(tmp_path: Path) -> None:
    out = tmp_path / "motion.mp4"
    MockMotionAdapter().animate(
        frame_path=FIXTURE_PNG,
        duration_s=3.0,
        fps=30,
        effect="none",
        seed=42,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene_003",
    )
    sidecar = json.loads(out.with_suffix(".json").read_text())
    assert sidecar["schema_version"] == "1.0"
    assert sidecar["story_id"] == "pigeons-from-hell"
    assert sidecar["scene_id"] == "scene_003"
    assert sidecar["duration_s"] == 3.0
    assert sidecar["fps"] == 30
    assert sidecar["effect"] == "none"
    assert sidecar["seed"] == 42
    assert sidecar["adapter"] == "mock"
    assert sidecar["status"] == "generated"
    assert sidecar["width"] == 64
    assert sidecar["height"] == 64


@requires_ffmpeg
def test_mock_motion_sidecar_paths_are_cwd_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    frame = tmp_path / "frame.png"
    import shutil as _shutil
    _shutil.copy(FIXTURE_PNG, frame)
    out = tmp_path / "motion.mp4"
    MockMotionAdapter().animate(
        frame_path=frame,
        duration_s=1.0,
        fps=24,
        effect="none",
        seed=0,
        out_path=out,
    )
    sidecar = json.loads(out.with_suffix(".json").read_text())
    assert not Path(sidecar["source_keyframe"]).is_absolute(), "source_keyframe must be relative"
    assert not Path(sidecar["output_path"]).is_absolute(), "output_path must be relative"


@requires_ffmpeg
def test_mock_motion_sidecar_effect_recorded_as_passed(tmp_path: Path) -> None:
    out = tmp_path / "motion.mp4"
    MockMotionAdapter().animate(
        frame_path=FIXTURE_PNG,
        duration_s=1.0,
        fps=24,
        effect="custom_spooky",
        seed=0,
        out_path=out,
    )
    sidecar = json.loads(out.with_suffix(".json").read_text())
    assert sidecar["effect"] == "custom_spooky"


# ---------------------------------------------------------------------------
# AdapterFactory
# ---------------------------------------------------------------------------


def test_adapter_factory_get_motion_mock() -> None:
    adapter = AdapterFactory.get_motion("mock")
    assert isinstance(adapter, MockMotionAdapter)


def test_adapter_factory_get_motion_unknown() -> None:
    with pytest.raises(ValueError, match="unknown motion adapter"):
        AdapterFactory.get_motion("real-runway")


# ---------------------------------------------------------------------------
# Module imports cleanly without ffmpeg
# ---------------------------------------------------------------------------


def test_module_imports_without_ffmpeg() -> None:
    # If we got here, the module imported fine regardless of ffmpeg presence.
    from horror_story.adapters.motion import mock  # noqa: F401
    assert hasattr(mock, "ffmpeg_available")
    assert hasattr(mock, "ffprobe_available")
    assert hasattr(mock, "FFmpegNotFoundError")
    assert hasattr(mock, "MockMotionAdapter")
