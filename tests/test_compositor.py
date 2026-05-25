"""Tests for Issue #009 — Scene compositor (Stage 8)."""
from __future__ import annotations

import json
import struct
import wave
from pathlib import Path
from typing import Any

import pytest

from horror_story.pipeline.compositor import (
    FFmpegNotFoundError,
    compose_scene,
    ffmpeg_available,
)
from horror_story.schemas import validate

requires_ffmpeg = pytest.mark.skipif(
    not ffmpeg_available(), reason="FFmpeg not installed"
)


# ---------------------------------------------------------------------------
# Helpers — build realistic input artifacts
# ---------------------------------------------------------------------------

def _write_silent_wav(path: Path, duration_s: float, channels: int = 1) -> Path:
    sample_rate = 44100
    n_frames = round(sample_rate * duration_s)
    n_samples = n_frames * channels
    pcm = struct.pack(f"<{n_samples}h", *([0] * n_samples))
    tmp = path.with_suffix(".wav.tmp")
    with wave.open(str(tmp), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    tmp.replace(path)
    return path


def _write_dummy_png(path: Path, width: int = 64, height: int = 64) -> Path:
    """Write a minimal RGBA PNG (all-transparent)."""
    try:
        from PIL import Image
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        img.save(str(path), format="PNG")
    except ImportError:
        # Fallback: write a 1x1 transparent PNG via raw bytes
        import zlib, base64
        # 1x1 transparent PNG
        raw = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        path.write_bytes(raw)
    return path


def _write_dummy_mp4(path: Path, duration_s: float, fps: int = 24) -> Path:
    """Write a minimal MP4 using FFmpeg (only called in @requires_ffmpeg tests)."""
    import shutil, subprocess
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg, "ffmpeg required for this helper"
    tmp = path.with_name(path.stem + ".tmp.mp4")
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi",
        "-i", f"color=black:size=320x240:rate={fps}:duration={duration_s}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-t", str(duration_s),
        str(tmp),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    tmp.replace(path)
    return path


def _make_timeline(
    tmp_path: Path,
    *,
    scene_id: str = "scene-01",
    story_id: str = "test-story",
    duration_s: float = 3.0,
    fps: int = 24,
    motion_path: str,
    typography_path: str,
    audio_tracks: list[dict[str, Any]],
) -> Path:
    tl: dict[str, Any] = {
        "schema_version": "1.0",
        "story_id": story_id,
        "scene_id": scene_id,
        "duration_s": duration_s,
        "fps": fps,
        "video_tracks": [
            {
                "track_id": "video-motion",
                "source_path": motion_path,
                "start_s": 0.0,
                "end_s": duration_s,
            }
        ],
        "audio_tracks": audio_tracks,
        "overlay_tracks": [
            {
                "track_id": "overlay-typography",
                "source_path": typography_path,
                "start_s": 0.0,
                "end_s": duration_s,
            }
        ],
    }
    p = tmp_path / f"timeline_{scene_id}.json"
    p.write_text(json.dumps(tl, indent=2))
    return p


# ---------------------------------------------------------------------------
# Unit tests — FFmpeg-free
# ---------------------------------------------------------------------------


def test_ffmpeg_available_returns_bool() -> None:
    result = ffmpeg_available()
    assert isinstance(result, bool)


def test_ffmpeg_not_found_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: False)

    # We need a valid timeline file path (content doesn't matter — raises before reading)
    tl = tmp_path / "timeline.json"
    tl.write_text("{}")
    out = tmp_path / "out.mp4"

    with pytest.raises(FFmpegNotFoundError):
        compose_scene(tl, out)


def test_missing_artifact_raises_file_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """compose_scene raises FileNotFoundError for missing referenced files."""
    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)

    tl = _make_timeline(
        tmp_path,
        motion_path="/nonexistent/motion.mp4",
        typography_path="/nonexistent/overlay.png",
        audio_tracks=[
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": "/nonexistent/ambient.wav",
                "start_s": 0.0,
                "end_s": 3.0,
                "line_ref": "ambient",
            }
        ],
    )
    out = tmp_path / "out.mp4"

    with pytest.raises(FileNotFoundError):
        compose_scene(tl, out)


def test_compose_scene_reads_timeline_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """compose_scene must read story_id, scene_id, duration_s from the timeline."""
    captured: dict[str, Any] = {}

    original_run = __import__("subprocess").run

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        captured["cmd"] = list(cmd)
        # Fake: create the tmp output file so replace() works
        for i, part in enumerate(cmd):
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()
        return original_run.__class__  # not called; return dummy

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    # Create real WAV and PNG files so _resolve doesn't raise
    wav = tmp_path / "ambient.wav"
    _write_silent_wav(wav, 3.0, channels=2)
    png = tmp_path / "overlay.png"
    _write_dummy_png(png)
    mp4 = tmp_path / "motion.mp4"
    mp4.touch()  # just needs to exist for _resolve

    tl = _make_timeline(
        tmp_path,
        scene_id="my-scene",
        story_id="my-story",
        duration_s=3.0,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(wav),
                "start_s": 0.0,
                "end_s": 3.0,
                "line_ref": "ambient",
            }
        ],
    )
    out = tmp_path / "scene.mp4"

    compose_scene(tl, out)
    assert "-t" in captured["cmd"]
    t_idx = captured["cmd"].index("-t")
    assert float(captured["cmd"][t_idx + 1]) == pytest.approx(3.0)


def test_compose_scene_ffmpeg_command_includes_overlay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FFmpeg command must include an overlay filter for the typography PNG."""
    captured: dict[str, Any] = {}

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        captured["cmd"] = list(cmd)
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    wav = tmp_path / "ambient.wav"
    _write_silent_wav(wav, 2.0, channels=2)
    png = tmp_path / "overlay.png"
    _write_dummy_png(png)
    mp4 = tmp_path / "motion.mp4"
    mp4.touch()

    tl = _make_timeline(
        tmp_path,
        duration_s=2.0,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(wav),
                "start_s": 0.0,
                "end_s": 2.0,
                "line_ref": "ambient",
            }
        ],
    )
    out = tmp_path / "scene.mp4"
    compose_scene(tl, out)

    cmd_str = " ".join(str(c) for c in captured["cmd"])
    assert "overlay" in cmd_str, "FFmpeg command must include 'overlay' filter"


def test_compose_scene_ffmpeg_command_includes_amix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FFmpeg command must include amix for audio mixing."""
    captured: dict[str, Any] = {}

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        captured["cmd"] = list(cmd)
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    narr = tmp_path / "narration.wav"
    _write_silent_wav(narr, 1.5)
    amb = tmp_path / "ambient.wav"
    _write_silent_wav(amb, 2.0, channels=2)
    png = tmp_path / "overlay.png"
    _write_dummy_png(png)
    mp4 = tmp_path / "motion.mp4"
    mp4.touch()

    tl = _make_timeline(
        tmp_path,
        duration_s=2.0,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-seg-0",
                "track_type": "narration",
                "source_path": str(narr),
                "start_s": 0.0,
                "end_s": 1.5,
                "line_ref": "seg-0",
            },
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(amb),
                "start_s": 0.0,
                "end_s": 2.0,
                "line_ref": "ambient",
            },
        ],
    )
    out = tmp_path / "scene.mp4"
    compose_scene(tl, out)

    cmd_str = " ".join(str(c) for c in captured["cmd"])
    assert "amix" in cmd_str, "FFmpeg command must include 'amix' filter"


def test_compose_scene_ffmpeg_command_includes_adelay_for_delayed_track(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Narration starting after t=0 must produce an adelay offset in the filtergraph."""
    captured: dict[str, Any] = {}

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        captured["cmd"] = list(cmd)
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    dlg = tmp_path / "dialogue.wav"
    _write_silent_wav(dlg, 1.0)
    amb = tmp_path / "ambient.wav"
    _write_silent_wav(amb, 3.0, channels=2)
    png = tmp_path / "overlay.png"
    _write_dummy_png(png)
    mp4 = tmp_path / "motion.mp4"
    mp4.touch()

    tl = _make_timeline(
        tmp_path,
        duration_s=3.0,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-dlg-0",
                "track_type": "dialogue",
                "source_path": str(dlg),
                "start_s": 2.0,  # delayed by 2 s
                "end_s": 3.0,
                "line_ref": "dlg-0",
            },
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(amb),
                "start_s": 0.0,
                "end_s": 3.0,
                "line_ref": "ambient",
            },
        ],
    )
    out = tmp_path / "scene.mp4"
    compose_scene(tl, out)

    cmd_str = " ".join(str(c) for c in captured["cmd"])
    # 2.0 s delay → 2000 ms
    assert "adelay=2000" in cmd_str, (
        f"Expected adelay=2000 for 2-second offset in filter graph, got:\n{cmd_str}"
    )


def test_sidecar_written_after_compose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """compose_scene must write a sidecar JSON alongside the output MP4."""

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    wav = tmp_path / "ambient.wav"
    _write_silent_wav(wav, 2.0, channels=2)
    png = tmp_path / "overlay.png"
    _write_dummy_png(png)
    mp4 = tmp_path / "motion.mp4"
    mp4.touch()

    tl = _make_timeline(
        tmp_path,
        scene_id="s-test",
        story_id="test-story",
        duration_s=2.0,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(wav),
                "start_s": 0.0,
                "end_s": 2.0,
                "line_ref": "ambient",
            }
        ],
    )
    out = tmp_path / "scene_s-test_composed.mp4"
    compose_scene(tl, out)

    sidecar_path = out.with_suffix(".json")
    assert sidecar_path.exists(), "Sidecar JSON must be written alongside the MP4"
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["scene_id"] == "s-test"
    assert sidecar["story_id"] == "test-story"
    assert sidecar["status"] == "composed"


def test_sidecar_schema_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The written sidecar must validate against composed_scene.schema.json."""

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    wav = tmp_path / "ambient.wav"
    _write_silent_wav(wav, 1.0, channels=2)
    png = tmp_path / "overlay.png"
    _write_dummy_png(png)
    mp4 = tmp_path / "motion.mp4"
    mp4.touch()

    tl = _make_timeline(
        tmp_path,
        scene_id="sv",
        duration_s=1.0,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(wav),
                "start_s": 0.0,
                "end_s": 1.0,
                "line_ref": "ambient",
            }
        ],
    )
    out = tmp_path / "scene_sv_composed.mp4"
    compose_scene(tl, out)

    sidecar = json.loads(out.with_suffix(".json").read_text())
    validate(sidecar, "composed_scene.schema.json")


def test_sidecar_narration_and_dialogue_wavs_populated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """narration_wavs and dialogue_wavs in sidecar must list the correct WAV paths."""

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    narr = tmp_path / "narration.wav"
    _write_silent_wav(narr, 1.5)
    dlg = tmp_path / "dialogue.wav"
    _write_silent_wav(dlg, 0.8)
    amb = tmp_path / "ambient.wav"
    _write_silent_wav(amb, 2.5, channels=2)
    png = tmp_path / "overlay.png"
    _write_dummy_png(png)
    mp4 = tmp_path / "motion.mp4"
    mp4.touch()

    tl = _make_timeline(
        tmp_path,
        duration_s=2.5,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-seg-0",
                "track_type": "narration",
                "source_path": str(narr),
                "start_s": 0.0,
                "end_s": 1.5,
                "line_ref": "seg-0",
            },
            {
                "track_id": "audio-dlg-0",
                "track_type": "dialogue",
                "source_path": str(dlg),
                "start_s": 1.5,
                "end_s": 2.3,
                "line_ref": "dlg-0",
            },
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(amb),
                "start_s": 0.0,
                "end_s": 2.5,
                "line_ref": "ambient",
            },
        ],
    )
    out = tmp_path / "scene_composed.mp4"
    compose_scene(tl, out)

    sidecar = json.loads(out.with_suffix(".json").read_text())
    assert len(sidecar["inputs"]["narration_wavs"]) == 1
    assert len(sidecar["inputs"]["dialogue_wavs"]) == 1


def test_sidecar_paths_are_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sidecar input paths and output_path must be run-relative, not absolute."""

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    wav = run_dir / "ambient.wav"
    _write_silent_wav(wav, 1.0, channels=2)
    png = run_dir / "overlay.png"
    _write_dummy_png(png)
    mp4 = run_dir / "motion.mp4"
    mp4.touch()

    tl = _make_timeline(
        run_dir,
        scene_id="rel-test",
        duration_s=1.0,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(wav),
                "start_s": 0.0,
                "end_s": 1.0,
                "line_ref": "ambient",
            }
        ],
    )
    out = run_dir / "scene_rel-test_composed.mp4"
    compose_scene(tl, out)

    sidecar = json.loads(out.with_suffix(".json").read_text())
    assert not Path(sidecar["output_path"]).is_absolute(), (
        f"sidecar output_path must be relative, got: {sidecar['output_path']!r}"
    )
    for key in ("motion", "ambient", "typography"):
        p = sidecar["inputs"][key]
        assert not Path(p).is_absolute(), (
            f"sidecar inputs.{key} must be relative, got: {p!r}"
        )
    for p in sidecar["inputs"].get("narration_wavs", []):
        assert not Path(p).is_absolute(), f"narration_wav must be relative, got: {p!r}"
    for p in sidecar["inputs"].get("dialogue_wavs", []):
        assert not Path(p).is_absolute(), f"dialogue_wav must be relative, got: {p!r}"


def test_compose_scene_ffmpeg_command_includes_stereo_upmix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FFmpeg filter graph must upmix each audio input to stereo before amix."""
    captured: dict[str, Any] = {}

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        captured["cmd"] = list(cmd)
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    narr = tmp_path / "narration.wav"
    _write_silent_wav(narr, 1.5)  # mono (1 channel)
    amb = tmp_path / "ambient.wav"
    _write_silent_wav(amb, 2.0, channels=2)
    png = tmp_path / "overlay.png"
    _write_dummy_png(png)
    mp4 = tmp_path / "motion.mp4"
    mp4.touch()

    tl = _make_timeline(
        tmp_path,
        duration_s=2.0,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-seg-0",
                "track_type": "narration",
                "source_path": str(narr),
                "start_s": 0.0,
                "end_s": 1.5,
                "line_ref": "seg-0",
            },
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(amb),
                "start_s": 0.0,
                "end_s": 2.0,
                "line_ref": "ambient",
            },
        ],
    )
    out = tmp_path / "scene.mp4"
    compose_scene(tl, out)

    cmd_str = " ".join(str(c) for c in captured["cmd"])
    assert "aformat=channel_layouts=stereo" in cmd_str, (
        "FFmpeg filter graph must include aformat=channel_layouts=stereo for mono→stereo upmix"
    )
    assert "-ac" in captured["cmd"] and "2" in captured["cmd"], (
        "FFmpeg command must include -ac 2 to enforce stereo AAC output"
    )


def test_compose_scene_returns_output_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        for part in cmd:
            if isinstance(part, str) and part.endswith(".tmp.mp4"):
                Path(part).touch()

    monkeypatch.setattr("horror_story.pipeline.compositor.ffmpeg_available", lambda: True)
    monkeypatch.setattr("subprocess.run", fake_run)

    wav = tmp_path / "a.wav"
    _write_silent_wav(wav, 1.0, channels=2)
    png = tmp_path / "o.png"
    _write_dummy_png(png)
    mp4 = tmp_path / "m.mp4"
    mp4.touch()

    tl = _make_timeline(
        tmp_path,
        duration_s=1.0,
        motion_path=str(mp4),
        typography_path=str(png),
        audio_tracks=[
            {
                "track_id": "audio-ambient",
                "track_type": "ambient",
                "source_path": str(wav),
                "start_s": 0.0,
                "end_s": 1.0,
                "line_ref": "ambient",
            }
        ],
    )
    out = tmp_path / "result.mp4"
    result = compose_scene(tl, out)
    assert result == out


# ---------------------------------------------------------------------------
# Integration test — full per-scene stack (stages 1–8), requires FFmpeg
# ---------------------------------------------------------------------------


@requires_ffmpeg
def test_integration_full_scene_pipeline(tmp_path: Path) -> None:
    """Run the full per-scene stack (stages 1–8) on a 1-scene fixture.

    Stages run:
      parse → script → TTS (mock) → image (mock) → motion (mock, FFmpeg)
      → audio (mock) → typography (mock) → timeline → compositor (FFmpeg)

    Asserts a valid MP4 file is produced.
    """
    import shutil
    from horror_story.adapters import AdapterFactory
    from horror_story.pipeline.parse import parse_story
    from horror_story.pipeline.script import generate_script
    from horror_story.pipeline.timeline import plan_timeline
    from horror_story.manifest import Manifest

    story_text = (
        "The shadows deepened as dread crept through the silent hall. "
        "Something ancient stirred behind the locked door."
    )
    story_id = "test-integration"
    fps = 24

    manifest = Manifest(
        schema_version="1.0",
        story_id=story_id,
        title="Test",
        seed=42,
        languages={"primary": "en", "secondary": "uk"},
        render={"width": 320, "height": 240, "fps": fps, "output_format": "mp4"},
        voices={"narrator": "narrator", "Branner": "branner-voice"},
        adapters={"tts": "mock", "image": "mock", "motion": "mock", "audio": "mock", "typography": "mock"},
        scenes=[],
    )

    # Stage 1: parse
    scenes = parse_story(story_text, story_id)
    assert scenes
    scene = scenes[0]
    scene_id = scene.scene_id

    # Stage 2: script
    script = generate_script(scene, manifest)
    script_path = tmp_path / f"script_{scene_id}.json"
    script_path.write_text(json.dumps(script.to_dict(), indent=2))

    # Stage 3: TTS
    tts = AdapterFactory.get_tts("mock")
    tts_sidecars: list[Path] = []

    narr_wavs: list[str] = []
    for seg in script.segments:
        wav = tmp_path / f"narration_{scene_id}_{seg.segment_id}.wav"
        tts.synthesize(
            text=seg.text_en,
            voice_id=seg.voice_id,
            language="en",
            pacing_ms=seg.pacing_ms,
            seed=manifest.seed,
            out_path=wav,
            story_id=story_id,
            scene_id=scene_id,
            line_ref=seg.segment_id,
            line_type="narration",
        )
        tts_sidecars.append(wav.with_suffix(".json"))
        narr_wavs.append(str(wav))

    dlg_wavs: list[str] = []
    for dlg in script.dialogue_lines:
        wav = tmp_path / f"dialogue_{scene_id}_{dlg.line_id}.wav"
        tts.synthesize(
            text=dlg.text_en,
            voice_id=dlg.voice_id,
            language="en",
            pacing_ms=dlg.pacing_ms,
            seed=manifest.seed,
            out_path=wav,
            story_id=story_id,
            scene_id=scene_id,
            line_ref=dlg.line_id,
            line_type="dialogue",
        )
        tts_sidecars.append(wav.with_suffix(".json"))
        dlg_wavs.append(str(wav))

    # Stage 4: keyframe
    image = AdapterFactory.get_image("mock")
    keyframe = tmp_path / f"keyframe_{scene_id}.png"
    image.generate(
        prompt=scene.visual_description,
        width=320,
        height=240,
        seed=manifest.seed,
        out_path=keyframe,
        story_id=story_id,
        scene_id=scene_id,
    )

    # Stage 5: motion
    motion_adapter = AdapterFactory.get_motion("mock")
    total_ms = sum(s.pacing_ms for s in script.segments) + sum(d.pacing_ms for d in script.dialogue_lines)
    duration_s = total_ms / 1000.0
    motion_mp4 = tmp_path / f"motion_{scene_id}.mp4"
    motion_adapter.animate(
        frame_path=keyframe,
        duration_s=duration_s,
        fps=fps,
        effect="none",
        seed=manifest.seed,
        out_path=motion_mp4,
        story_id=story_id,
        scene_id=scene_id,
    )
    motion_sidecar = motion_mp4.with_suffix(".json")

    # Stage 6: ambient audio
    audio = AdapterFactory.get_audio("mock")
    ambient_wav = tmp_path / f"ambient_{scene_id}.wav"
    audio.generate(
        mood=scene.mood,
        duration_s=duration_s,
        seed=manifest.seed,
        out_path=ambient_wav,
        story_id=story_id,
        scene_id=scene_id,
    )
    ambient_sidecar = ambient_wav.with_suffix(".json")

    # Stage 7: typography
    typography = AdapterFactory.get_typography("mock")
    typo_png = tmp_path / f"typography_{scene_id}.png"
    typography.render(
        script_path=script_path,
        duration_s=duration_s,
        width=320,
        height=240,
        fps=fps,
        seed=manifest.seed,
        out_path=typo_png,
    )
    typography_sidecar = typo_png.with_suffix(".json")

    # Stage 7.5: timeline
    timeline_path = tmp_path / f"timeline_{scene_id}.json"
    plan_timeline(
        script_path=script_path,
        motion_sidecar_path=motion_sidecar,
        ambient_sidecar_path=ambient_sidecar,
        typography_sidecar_path=typography_sidecar,
        voice_line_sidecar_paths=tts_sidecars,
        out_path=timeline_path,
    )

    # Stage 8: compositor
    composed_mp4 = tmp_path / f"scene_{scene_id}_composed.mp4"
    result = compose_scene(timeline_path, composed_mp4)

    # Assertions
    assert result == composed_mp4
    assert composed_mp4.exists(), "Composed MP4 must exist"
    assert composed_mp4.stat().st_size > 0, "Composed MP4 must not be empty"

    # Validate sidecar
    sidecar = json.loads(composed_mp4.with_suffix(".json").read_text())
    assert sidecar["status"] == "composed"
    validate(sidecar, "composed_scene.schema.json")

    # Verify it's a real MP4 (starts with ftyp box)
    header = composed_mp4.read_bytes()[:12]
    assert header[4:8] in (b"ftyp", b"mdat", b"moov"), (
        f"Expected MP4 box header, got {header!r}"
    )
