"""Tests for Issue #016 — Kokoro TTS adapter."""
from __future__ import annotations

import json
import wave
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from horror_story.adapters import AdapterFactory
from horror_story.adapters.tts.base import TTSAdapter
from horror_story.adapters.tts.kokoro import KokoroTTSAdapter, _kokoro_available
from horror_story.schemas import validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_model(n_samples: int = 44100, sample_rate: int = 44100) -> MagicMock:
    m = MagicMock()
    m.create.return_value = ([0.0] * n_samples, sample_rate)
    return m


def _adapter(model: MagicMock) -> KokoroTTSAdapter:
    a = KokoroTTSAdapter()
    a._kokoro = model
    return a


# ---------------------------------------------------------------------------
# Class contract
# ---------------------------------------------------------------------------


def test_kokoro_tts_adapter_is_tts_adapter() -> None:
    assert issubclass(KokoroTTSAdapter, TTSAdapter)


def test_adapter_factory_get_tts_kokoro() -> None:
    adapter = AdapterFactory.get_tts("kokoro")
    assert isinstance(adapter, KokoroTTSAdapter)


# ---------------------------------------------------------------------------
# WAV output
# ---------------------------------------------------------------------------


def test_kokoro_tts_writes_wav(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    out = tmp_path / "line.wav"
    result = adapter.synthesize(
        text="The dark corridor stretched endlessly.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=2000,
        seed=42,
        out_path=out,
    )
    assert result == out
    assert out.exists()


def test_kokoro_tts_wav_format(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model(n_samples=44100, sample_rate=44100))
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="Horror lurked.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=1000,
        seed=1,
        out_path=out,
    )
    with wave.open(str(out)) as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 44100
        assert wf.getsampwidth() == 2


def test_kokoro_tts_resampling_writes_correct_rate(tmp_path: Path) -> None:
    """When kokoro returns 24000 Hz, adapter resamples to 44100 Hz."""
    n_samples = 24000  # 1 second at 24 kHz
    adapter = _adapter(_mock_model(n_samples=n_samples, sample_rate=24000))
    out = tmp_path / "resampled.wav"
    adapter.synthesize(
        text="Test resampling.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=1000,
        seed=0,
        out_path=out,
    )
    with wave.open(str(out)) as wf:
        assert wf.getframerate() == 44100
        actual_ms = round(wf.getnframes() / wf.getframerate() * 1000)
        assert abs(actual_ms - 1000) <= 50


# ---------------------------------------------------------------------------
# Voice mapping
# ---------------------------------------------------------------------------


def test_kokoro_voice_map_narrator_en(tmp_path: Path) -> None:
    model = _mock_model()
    adapter = _adapter(model)
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="The house loomed.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=1000,
        seed=0,
        out_path=out,
    )
    model.create.assert_called_once()
    _, kwargs = model.create.call_args
    assert kwargs["voice"] == "af_heart"


def test_kokoro_voice_map_unknown_fallback(tmp_path: Path) -> None:
    model = _mock_model()
    adapter = _adapter(model)
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="The darkness rose.",
        voice_id="unknown_voice_xyz",
        language="en",
        pacing_ms=1000,
        seed=0,
        out_path=out,
    )
    _, kwargs = model.create.call_args
    assert kwargs["voice"] == "af_heart"


# ---------------------------------------------------------------------------
# Sidecar JSON
# ---------------------------------------------------------------------------


def test_kokoro_tts_writes_sidecar(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="The shadows moved.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=800,
        seed=5,
        out_path=out,
    )
    assert out.with_suffix(".json").exists()


def test_kokoro_tts_sidecar_schema_valid(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="Fear gripped him as the door creaked open.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=2000,
        seed=10,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene-01",
        line_ref="seg-0",
        line_type="narration",
    )
    data = json.loads(out.with_suffix(".json").read_text())
    validate(data, "voice_line.schema.json")


def test_kokoro_tts_sidecar_adapter_field(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="Something stirred.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=1000,
        seed=0,
        out_path=out,
    )
    data = json.loads(out.with_suffix(".json").read_text())
    assert data["adapter"] == "kokoro"


def test_kokoro_tts_sidecar_fields(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    out = tmp_path / "dlg.wav"
    adapter.synthesize(
        text="Get out of this house!",
        voice_id="narrator_en",
        language="en",
        pacing_ms=1200,
        seed=3,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene-02",
        line_ref="dlg-0",
        line_type="dialogue",
    )
    data = json.loads(out.with_suffix(".json").read_text())
    assert data["schema_version"] == "1.0"
    assert data["story_id"] == "pigeons-from-hell"
    assert data["scene_id"] == "scene-02"
    assert data["line_ref"] == "dlg-0"
    assert data["line_type"] == "dialogue"
    assert data["text"] == "Get out of this house!"
    assert data["voice_id"] == "narrator_en"
    assert data["language"] == "en"
    assert data["seed"] == 3
    assert data["pacing_ms"] == 1200
    assert data["status"] == "synthesized"
    assert data["adapter"] == "kokoro"
    assert data["actual_duration_ms"] is not None


# ---------------------------------------------------------------------------
# Lazy loading
# ---------------------------------------------------------------------------


def test_kokoro_tts_lazy_load(tmp_path: Path) -> None:
    """Model is loaded only on first synthesize call."""
    loaded: list[int] = []

    class _FakeAdapter(KokoroTTSAdapter):
        def _load_model(self) -> MagicMock:
            loaded.append(1)
            return _mock_model()

    adapter = _FakeAdapter()
    assert len(loaded) == 0
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="Darkness.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=500,
        seed=0,
        out_path=out,
    )
    assert len(loaded) == 1
    out2 = tmp_path / "line2.wav"
    adapter.synthesize(
        text="Silence.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=500,
        seed=0,
        out_path=out2,
    )
    assert len(loaded) == 1  # not loaded again


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_kokoro_tts_empty_text_raises(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    with pytest.raises(ValueError, match="text"):
        adapter.synthesize("", "narrator_en", "en", 1000, 0, tmp_path / "out.wav")


def test_kokoro_tts_invalid_pacing_raises(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    with pytest.raises(ValueError, match="pacing_ms"):
        adapter.synthesize("Some text.", "narrator_en", "en", 399, 0, tmp_path / "out.wav")


def test_kokoro_tts_negative_seed_raises(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    with pytest.raises(ValueError, match="seed"):
        adapter.synthesize("Some text.", "narrator_en", "en", 1000, -1, tmp_path / "out.wav")


def test_kokoro_tts_bad_line_type_raises(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    with pytest.raises(ValueError, match="line_type"):
        adapter.synthesize(
            "Some text.", "narrator_en", "en", 1000, 0,
            tmp_path / "out.wav", line_type="bad",
        )


def test_kokoro_tts_bad_language_raises(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    with pytest.raises(ValueError, match="language"):
        adapter.synthesize("Some text.", "narrator_en", "english", 1000, 0, tmp_path / "out.wav")


def test_kokoro_tts_unsupported_language_raises(tmp_path: Path) -> None:
    adapter = _adapter(_mock_model())
    with pytest.raises(ValueError, match="language"):
        adapter.synthesize("Some text.", "narrator_en", "de", 1000, 0, tmp_path / "out.wav")


def test_kokoro_tts_lang_passed_to_model(tmp_path: Path) -> None:
    model = _mock_model()
    adapter = _adapter(model)
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="The darkness rose.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=1000,
        seed=0,
        out_path=out,
    )
    _, kwargs = model.create.call_args
    assert kwargs["lang"] == "en-us"


def test_kokoro_tts_wav_duration_matches_actual_not_pacing(tmp_path: Path) -> None:
    """WAV reflects actual synth length; actual_duration_ms in sidecar matches WAV."""
    # mock returns 2 seconds of audio at 44100 Hz
    n_samples = 44100 * 2
    adapter = _adapter(_mock_model(n_samples=n_samples, sample_rate=44100))
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="Something ancient stirred in the dark.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=1000,  # pacing says 1 s, but synth returns 2 s
        seed=0,
        out_path=out,
    )
    with wave.open(str(out)) as wf:
        actual_ms = round(wf.getnframes() / wf.getframerate() * 1000)
    assert abs(actual_ms - 2000) <= 50
    data = json.loads(out.with_suffix(".json").read_text())
    assert abs(data["actual_duration_ms"] - 2000) <= 50


# ---------------------------------------------------------------------------
# Integration (requires kokoro-onnx installed)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _kokoro_available(), reason="kokoro-onnx not installed")
def test_kokoro_tts_integration_non_silent(tmp_path: Path) -> None:
    adapter = KokoroTTSAdapter()
    out = tmp_path / "line.wav"
    result = adapter.synthesize(
        text="The horror lurked in the shadows.",
        voice_id="narrator_en",
        language="en",
        pacing_ms=2000,
        seed=42,
        out_path=out,
    )
    assert result == out
    assert out.exists()
    with wave.open(str(out)) as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 44100
        assert wf.getsampwidth() == 2
    data = json.loads(out.with_suffix(".json").read_text())
    validate(data, "voice_line.schema.json")
    assert data["adapter"] == "kokoro"
    assert out.stat().st_size > 100
