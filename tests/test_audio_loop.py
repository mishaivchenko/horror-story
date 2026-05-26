"""Tests for LoopAudioAdapter — Issue #032."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from horror_story.adapters import AdapterFactory
from horror_story.adapters.audio.loop import LoopAudioAdapter


def _make_wav(path: Path, duration_s: float = 1.0, sample_rate: int = 44100) -> None:
    n_frames = round(sample_rate * duration_s)
    n_channels = 2
    sample_width = 2
    pcm = struct.pack(f"<{n_frames * n_channels}h", *([100] * (n_frames * n_channels)))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def test_loop_extends_short_source(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _make_wav(assets_dir / "dread.wav", duration_s=1.0)

    out = tmp_path / "out.wav"
    adapter = LoopAudioAdapter(assets_dir)
    adapter.generate("dread", 3.5, 0, out)

    duration = _wav_duration(out)
    assert 3.4 <= duration <= 3.6


def test_loop_trims_long_source(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _make_wav(assets_dir / "dread.wav", duration_s=10.0)

    out = tmp_path / "out.wav"
    adapter = LoopAudioAdapter(assets_dir)
    adapter.generate("dread", 2.0, 0, out)

    duration = _wav_duration(out)
    assert abs(duration - 2.0) <= 0.1


def test_loop_unknown_mood_falls_back_to_silence(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _make_wav(assets_dir / "dread.wav", duration_s=1.0)

    out = tmp_path / "out.wav"
    adapter = LoopAudioAdapter(assets_dir)
    adapter.generate("wind", 2.0, 0, out)

    assert out.exists()
    with wave.open(str(out), "rb") as wf:
        assert wf.getnframes() > 0


def test_loop_missing_assets_dir_falls_back(tmp_path: Path) -> None:
    nonexistent = tmp_path / "no_such_dir"
    out = tmp_path / "out.wav"
    adapter = LoopAudioAdapter(nonexistent)
    adapter.generate("dread", 1.0, 0, out)

    assert out.exists()
    with wave.open(str(out), "rb") as wf:
        assert wf.getnframes() > 0


def test_loop_empty_assets_dir_falls_back(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    out = tmp_path / "out.wav"
    adapter = LoopAudioAdapter(assets_dir)
    adapter.generate("dread", 1.0, 0, out)

    assert out.exists()
    with wave.open(str(out), "rb") as wf:
        assert wf.getnframes() > 0


def test_loop_sidecar_written(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _make_wav(assets_dir / "dread.wav", duration_s=2.0)

    out = tmp_path / "out.wav"
    adapter = LoopAudioAdapter(assets_dir)
    adapter.generate("dread", 1.5, 42, out, story_id="test-story", scene_id="scene-01")

    sidecar = out.with_suffix(".json")
    assert sidecar.exists()

    import json
    data = json.loads(sidecar.read_text())
    assert data["adapter"] == "loop"
    assert data["status"] == "generated"


@pytest.mark.parametrize("source_duration,target_duration", [
    (0.5, 2.0),
    (1.0, 5.3),
    (2.0, 0.7),
])
def test_loop_duration_within_tolerance(
    tmp_path: Path, source_duration: float, target_duration: float
) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _make_wav(assets_dir / "dread.wav", duration_s=source_duration)

    out = tmp_path / "out.wav"
    adapter = LoopAudioAdapter(assets_dir)
    adapter.generate("dread", target_duration, 0, out)

    duration = _wav_duration(out)
    assert abs(duration - target_duration) <= target_duration * 0.05


def test_adapter_factory_get_audio_loop(tmp_path: Path) -> None:
    adapter = AdapterFactory.get_audio("loop", assets_dir="")
    assert isinstance(adapter, LoopAudioAdapter)


def test_adapter_factory_get_audio_unknown_still_raises() -> None:
    with pytest.raises(ValueError):
        AdapterFactory.get_audio("bogus")
