"""Tests for Issue #010 — Final renderer (Stage 9)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from horror_story.pipeline.renderer import (
    FFmpegNotFoundError,
    ffmpeg_available,
    render_final,
)
from horror_story.schemas import validate

requires_ffmpeg = pytest.mark.skipif(
    not ffmpeg_available(), reason="FFmpeg not installed"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manifest(
    tmp_path: Path,
    *,
    story_id: str = "test-story",
    seed: int = 42,
    scene_ids: list[str] | None = None,
    width: int = 320,
    height: int = 240,
    fps: int = 24,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "story_id": story_id,
        "title": "Test Story",
        "author": "Test Author",
        "seed": seed,
        "languages": {"primary": "en", "secondary": "uk"},
        "render": {
            "width": width,
            "height": height,
            "fps": fps,
            "codec": "libx264",
            "audio_codec": "aac",
        },
        "voices": {"narrator": "narrator-v1"},
        "adapters": {
            "tts": "mock",
            "image": "mock",
            "motion": "mock",
            "audio": "mock",
            "typography": "mock",
        },
        "scenes": scene_ids or ["scene-01"],
    }


def _write_dummy_mp4(path: Path, duration_s: float = 2.0, fps: int = 24) -> Path:
    """Write a minimal black MP4 via FFmpeg (only called in @requires_ffmpeg tests)."""
    import shutil
    import subprocess
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg, "ffmpeg required"
    tmp = path.with_name(path.stem + ".tmp.mp4")
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"color=black:size=320x240:rate={fps}:duration={duration_s}",
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={duration_s}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-t", str(duration_s),
        "-fflags", "+bitexact",
        str(tmp),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    tmp.replace(path)
    return path


# ---------------------------------------------------------------------------
# Unit tests — FFmpeg-free
# ---------------------------------------------------------------------------


def test_ffmpeg_not_found_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: False
    )
    manifest = _make_manifest(tmp_path)
    out = tmp_path / "final.mp4"
    with pytest.raises(FFmpegNotFoundError):
        render_final(manifest, [], out)


def test_render_final_writes_render_job_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """render_final must write a render_job.json sidecar."""
    captured: dict[str, Any] = {}

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        captured["calls"] = captured.get("calls", 0) + 1
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    scene_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    scene_mp4.touch()

    manifest = _make_manifest(tmp_path, scene_ids=["scene-01"])
    out = tmp_path / "final_test-story_42.mp4"
    render_final(manifest, [scene_mp4], out)

    rj_path = out.with_name("render_job.json")
    assert rj_path.exists(), "render_job.json must be written"


def test_render_job_validates_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    scene_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    scene_mp4.touch()

    manifest = _make_manifest(tmp_path, scene_ids=["scene-01"])
    out = tmp_path / "final_test-story_42.mp4"
    render_final(manifest, [scene_mp4], out)

    rj = json.loads(out.with_name("render_job.json").read_text())
    validate(rj, "render_job.schema.json")


def test_render_job_status_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    scene_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    scene_mp4.touch()

    manifest = _make_manifest(tmp_path, scene_ids=["scene-01"])
    out = tmp_path / "final_test-story_42.mp4"
    render_final(manifest, [scene_mp4], out)

    rj = json.loads(out.with_name("render_job.json").read_text())
    assert rj["status"] == "complete"


def test_render_job_sha256_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).write_bytes(b"\x00" * 16)

    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    scene_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    scene_mp4.touch()

    manifest = _make_manifest(tmp_path, scene_ids=["scene-01"])
    out = tmp_path / "final_test-story_42.mp4"
    render_final(manifest, [scene_mp4], out)

    rj = json.loads(out.with_name("render_job.json").read_text())
    assert rj["sha256"] is not None
    assert len(rj["sha256"]) == 64
    assert all(c in "0123456789abcdef" for c in rj["sha256"])


def test_render_job_scene_ids_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    scene_ids = ["scene-01", "scene-02"]
    mp4s = []
    for sid in scene_ids:
        p = tmp_path / f"scene_{sid}_composed.mp4"
        p.touch()
        mp4s.append(p)

    manifest = _make_manifest(tmp_path, scene_ids=scene_ids)
    out = tmp_path / "final_test-story_42.mp4"
    render_final(manifest, mp4s, out)

    rj = json.loads(out.with_name("render_job.json").read_text())
    assert rj["scene_ids"] == scene_ids


def test_render_final_returns_output_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    scene_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    scene_mp4.touch()

    manifest = _make_manifest(tmp_path, scene_ids=["scene-01"])
    out = tmp_path / "final_test-story_42.mp4"
    result = render_final(manifest, [scene_mp4], out)
    assert result == out


def test_render_job_output_path_is_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """render_job.json output_path must be run-relative, not an absolute path."""

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    run_dir = tmp_path / "run_test-story_42"
    run_dir.mkdir()
    scene_mp4 = run_dir / "scene_scene-01_composed.mp4"
    scene_mp4.touch()

    manifest = _make_manifest(tmp_path, scene_ids=["scene-01"])
    out = run_dir / "final_test-story_42.mp4"
    render_final(manifest, [scene_mp4], out)

    rj = json.loads(out.with_name("render_job.json").read_text())
    assert not Path(rj["output_path"]).is_absolute(), (
        f"render_job output_path must be relative, got: {rj['output_path']!r}"
    )


def test_scene_paths_count_mismatch_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """render_final raises ValueError when scene_paths count differs from manifest scenes."""
    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    manifest = _make_manifest(tmp_path, scene_ids=["scene-01", "scene-02"])
    one_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    one_mp4.touch()
    with pytest.raises(ValueError, match="scene_paths length"):
        render_final(manifest, [one_mp4], tmp_path / "final.mp4")


def test_ffmpeg_command_uses_concat_demuxer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The final FFmpeg call must use -f concat as adjacent arguments."""
    captured: dict[str, Any] = {}

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        captured.setdefault("cmds", []).append(list(cmd))
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    scene_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    scene_mp4.touch()

    manifest = _make_manifest(tmp_path, scene_ids=["scene-01"])
    out = tmp_path / "final_test-story_42.mp4"
    render_final(manifest, [scene_mp4], out)

    # Only the final concat call should contain -f concat as adjacent flags
    found = any(
        "-f" in cmd and cmd[cmd.index("-f") + 1] == "concat"
        for cmd in captured["cmds"]
        if "-f" in cmd
    )
    assert found, "Final FFmpeg call must include -f concat as adjacent arguments"


def test_ffmpeg_command_includes_libx264_aac(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        captured.setdefault("cmds", []).append(list(cmd))
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr(
        "horror_story.pipeline.renderer.ffmpeg_available", lambda: True
    )
    monkeypatch.setattr("subprocess.run", fake_run)

    scene_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    scene_mp4.touch()

    manifest = _make_manifest(tmp_path, scene_ids=["scene-01"])
    out = tmp_path / "final_test-story_42.mp4"
    render_final(manifest, [scene_mp4], out)

    all_args = " ".join(str(a) for cmd in captured["cmds"] for a in cmd)
    assert "libx264" in all_args
    assert "aac" in all_args


# ---------------------------------------------------------------------------
# Integration tests — require FFmpeg
# ---------------------------------------------------------------------------


def _ffprobe_streams(path: Path) -> list[dict[str, Any]]:
    import subprocess as _sp
    result = _sp.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return list(json.loads(result.stdout).get("streams", []))


@requires_ffmpeg
def test_integration_render_final_produces_mp4(tmp_path: Path) -> None:
    """render_final produces a real MP4 from two scene clips with correct codec/resolution."""
    scene_ids = ["scene-01", "scene-02"]
    scene_paths: list[Path] = []
    for sid in scene_ids:
        p = tmp_path / f"scene_{sid}_composed.mp4"
        _write_dummy_mp4(p, duration_s=1.0)
        scene_paths.append(p)

    manifest = _make_manifest(tmp_path, scene_ids=scene_ids, width=320, height=240)
    out = tmp_path / "final_test-story_42.mp4"
    result = render_final(manifest, scene_paths, out)

    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0

    header = out.read_bytes()[:12]
    assert header[4:8] in (b"ftyp", b"mdat", b"moov"), (
        f"Expected MP4 box header, got {header!r}"
    )

    streams = _ffprobe_streams(out)
    video = next((s for s in streams if s["codec_type"] == "video"), None)
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)

    assert video is not None, "Output MP4 must have a video stream"
    assert video["codec_name"] == "h264", f"Expected h264, got {video['codec_name']}"
    assert video["width"] == 320, f"Expected width=320, got {video['width']}"
    assert video["height"] == 240, f"Expected height=240, got {video['height']}"

    assert audio is not None, "Output MP4 must have an audio stream"
    assert audio["codec_name"] == "aac", f"Expected aac, got {audio['codec_name']}"


@requires_ffmpeg
def test_integration_render_job_sha256_matches_file(tmp_path: Path) -> None:
    """SHA-256 in render_job.json must match the actual output file."""
    scene_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    _write_dummy_mp4(scene_mp4, duration_s=1.0)

    manifest = _make_manifest(tmp_path, scene_ids=["scene-01"])
    out = tmp_path / "final_test-story_42.mp4"
    render_final(manifest, [scene_mp4], out)

    rj = json.loads(out.with_name("render_job.json").read_text())
    actual_sha = hashlib.sha256(out.read_bytes()).hexdigest()
    assert rj["sha256"] == actual_sha


@requires_ffmpeg
def test_integration_determinism(tmp_path: Path) -> None:
    """Two render_final calls with identical inputs produce identical SHA-256."""
    scene_mp4 = tmp_path / "scene_scene-01_composed.mp4"
    _write_dummy_mp4(scene_mp4, duration_s=1.0)

    manifest = _make_manifest(tmp_path, seed=42, scene_ids=["scene-01"])

    out1 = tmp_path / "run1" / "final.mp4"
    out1.parent.mkdir()
    render_final(manifest, [scene_mp4], out1)
    rj1 = json.loads(out1.with_name("render_job.json").read_text())

    out2 = tmp_path / "run2" / "final.mp4"
    out2.parent.mkdir()
    render_final(manifest, [scene_mp4], out2)
    rj2 = json.loads(out2.with_name("render_job.json").read_text())

    assert rj1["sha256"] == rj2["sha256"], (
        "Identical inputs must produce identical SHA-256 (determinism failure)"
    )
