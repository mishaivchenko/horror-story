"""Tests for Issue #008 — Mock audio adapter."""
from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from horror_story.adapters import AdapterFactory
from horror_story.adapters.audio.base import AudioAdapter
from horror_story.adapters.audio.mock import MockAudioAdapter
from horror_story.schemas import validate


# ---------------------------------------------------------------------------
# AudioAdapter ABC
# ---------------------------------------------------------------------------


def test_audio_adapter_is_abstract() -> None:
    with pytest.raises(TypeError):
        AudioAdapter()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# MockAudioAdapter — WAV properties
# ---------------------------------------------------------------------------


def test_mock_audio_writes_wav(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    out = tmp_path / "ambient.wav"
    result = adapter.generate(mood="dread", duration_s=3.0, seed=42, out_path=out)
    assert result == out
    assert out.exists()


def test_mock_audio_wav_format(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    out = tmp_path / "ambient.wav"
    adapter.generate(mood="tension", duration_s=2.0, seed=1, out_path=out)
    with wave.open(str(out)) as wf:
        assert wf.getnchannels() == 2       # stereo
        assert wf.getframerate() == 44100   # 44.1 kHz
        assert wf.getsampwidth() == 2       # 16-bit PCM


def test_mock_audio_duration_matches(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    duration_s = 5.0
    out = tmp_path / "ambient.wav"
    adapter.generate(mood="horror", duration_s=duration_s, seed=7, out_path=out)
    with wave.open(str(out)) as wf:
        actual_s = wf.getnframes() / wf.getframerate()
    assert abs(actual_s - duration_s) <= duration_s * 0.05


@pytest.mark.parametrize("duration_s", [1.0, 2.5, 10.0, 30.0])
def test_mock_audio_duration_various(tmp_path: Path, duration_s: float) -> None:
    adapter = MockAudioAdapter()
    out = tmp_path / f"ambient_{duration_s}.wav"
    adapter.generate(mood="dread", duration_s=duration_s, seed=0, out_path=out)
    with wave.open(str(out)) as wf:
        actual_s = wf.getnframes() / wf.getframerate()
    assert abs(actual_s - duration_s) <= duration_s * 0.05


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_mock_audio_deterministic_bytes(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    kwargs: dict[str, object] = dict(mood="unease", duration_s=4.0, seed=99)
    out1 = tmp_path / "run1.wav"
    out2 = tmp_path / "run2.wav"
    adapter.generate(**kwargs, out_path=out1)  # type: ignore[arg-type]
    adapter.generate(**kwargs, out_path=out2)  # type: ignore[arg-type]
    assert out1.read_bytes() == out2.read_bytes()


def test_mock_audio_different_seeds_still_valid(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    out1 = tmp_path / "seed1.wav"
    out2 = tmp_path / "seed2.wav"
    adapter.generate(mood="dread", duration_s=2.0, seed=1, out_path=out1)
    adapter.generate(mood="dread", duration_s=2.0, seed=2, out_path=out2)
    for out in (out1, out2):
        with wave.open(str(out)) as wf:
            actual_s = wf.getnframes() / wf.getframerate()
        assert abs(actual_s - 2.0) <= 0.1


# ---------------------------------------------------------------------------
# Sidecar JSON
# ---------------------------------------------------------------------------


def test_mock_audio_writes_sidecar(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    out = tmp_path / "ambient.wav"
    adapter.generate(mood="dread", duration_s=3.0, seed=5, out_path=out)
    sidecar = out.with_suffix(".json")
    assert sidecar.exists()


def test_mock_audio_sidecar_schema_valid(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    out = tmp_path / "ambient.wav"
    adapter.generate(
        mood="horror",
        duration_s=6.0,
        seed=10,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene-01",
    )
    data = json.loads(out.with_suffix(".json").read_text())
    validate(data, "ambient_artifact.schema.json")


def test_mock_audio_sidecar_fields(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    out = tmp_path / "ambient.wav"
    adapter.generate(
        mood="dread",
        duration_s=4.5,
        seed=3,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene-02",
    )
    data = json.loads(out.with_suffix(".json").read_text())
    assert data["schema_version"] == "1.0"
    assert data["story_id"] == "pigeons-from-hell"
    assert data["scene_id"] == "scene-02"
    assert data["mood"] == "dread"
    assert data["duration_s"] == 4.5
    assert data["seed"] == 3
    assert data["adapter"] == "mock"
    assert data["status"] == "generated"
    assert data["actual_duration_s"] is not None


def test_mock_audio_sidecar_minimal_fields(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    out = tmp_path / "ambient.wav"
    adapter.generate(mood="tension", duration_s=2.0, seed=0, out_path=out)
    data = json.loads(out.with_suffix(".json").read_text())
    validate(data, "ambient_artifact.schema.json")
    assert data["status"] == "generated"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_mock_audio_negative_seed_raises(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    with pytest.raises(ValueError, match="seed"):
        adapter.generate(mood="dread", duration_s=2.0, seed=-1, out_path=tmp_path / "bad.wav")


def test_mock_audio_nonpositive_duration_raises(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    with pytest.raises(ValueError, match="duration_s"):
        adapter.generate(mood="dread", duration_s=0.0, seed=0, out_path=tmp_path / "bad.wav")


def test_mock_audio_empty_mood_raises(tmp_path: Path) -> None:
    adapter = MockAudioAdapter()
    with pytest.raises(ValueError, match="mood"):
        adapter.generate(mood="", duration_s=2.0, seed=0, out_path=tmp_path / "bad.wav")


# ---------------------------------------------------------------------------
# AdapterFactory
# ---------------------------------------------------------------------------


def test_adapter_factory_get_audio_mock() -> None:
    adapter = AdapterFactory.get_audio("mock")
    assert isinstance(adapter, MockAudioAdapter)


def test_adapter_factory_get_audio_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown"):
        AdapterFactory.get_audio("freesound")
