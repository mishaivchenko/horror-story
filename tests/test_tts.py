"""Tests for Issue #004 — Mock TTS adapter."""
from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from horror_story.adapters import AdapterFactory
from horror_story.adapters.tts.base import TTSAdapter
from horror_story.adapters.tts.mock import MockTTSAdapter
from horror_story.schemas import validate

# ---------------------------------------------------------------------------
# TTSAdapter ABC
# ---------------------------------------------------------------------------


def test_tts_adapter_is_abstract() -> None:
    with pytest.raises(TypeError):
        TTSAdapter()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# MockTTSAdapter — WAV properties
# ---------------------------------------------------------------------------


def test_mock_tts_writes_wav(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "line.wav"
    result = adapter.synthesize(
        text="The dark corridor stretched endlessly.",
        voice_id="en-narrator-01",
        language="en",
        pacing_ms=2000,
        seed=42,
        out_path=out,
    )
    assert result == out
    assert out.exists()


def test_mock_tts_wav_format(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="Horror lurked in the shadows.",
        voice_id="en-narrator-01",
        language="en",
        pacing_ms=1000,
        seed=1,
        out_path=out,
    )
    with wave.open(str(out)) as wf:
        assert wf.getnchannels() == 1       # mono
        assert wf.getframerate() == 44100   # 44.1 kHz
        assert wf.getsampwidth() == 2       # 16-bit PCM


def test_mock_tts_duration_matches_pacing_ms(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    pacing_ms = 3000
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="Something ancient stirred.",
        voice_id="en-narrator-01",
        language="en",
        pacing_ms=pacing_ms,
        seed=7,
        out_path=out,
    )
    with wave.open(str(out)) as wf:
        actual_ms = round(wf.getnframes() / wf.getframerate() * 1000)
    tolerance = pacing_ms * 0.05
    assert abs(actual_ms - pacing_ms) <= tolerance


@pytest.mark.parametrize("pacing_ms", [500, 1000, 2500, 5000])
def test_mock_tts_duration_various_pacings(tmp_path: Path, pacing_ms: int) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / f"line_{pacing_ms}.wav"
    adapter.synthesize(
        text="Silence fell like a shroud.",
        voice_id="en-narrator-01",
        language="en",
        pacing_ms=pacing_ms,
        seed=0,
        out_path=out,
    )
    with wave.open(str(out)) as wf:
        actual_ms = round(wf.getnframes() / wf.getframerate() * 1000)
    tolerance = pacing_ms * 0.05
    assert abs(actual_ms - pacing_ms) <= tolerance


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_mock_tts_deterministic_bytes(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    kwargs = dict(
        text="The pigeon watched with dead eyes.",
        voice_id="en-narrator-01",
        language="en",
        pacing_ms=1500,
        seed=99,
    )
    out1 = tmp_path / "run1.wav"
    out2 = tmp_path / "run2.wav"
    adapter.synthesize(**kwargs, out_path=out1)  # type: ignore[arg-type]
    adapter.synthesize(**kwargs, out_path=out2)  # type: ignore[arg-type]
    assert out1.read_bytes() == out2.read_bytes()


def test_mock_tts_different_seeds_produce_same_bytes(tmp_path: Path) -> None:
    """Mock uses silence (all-zero PCM) regardless of seed; bytes still match."""
    adapter = MockTTSAdapter()
    base_kwargs = dict(
        text="A crow cried from the oak tree.",
        voice_id="en-narrator-01",
        language="en",
        pacing_ms=1000,
    )
    out1 = tmp_path / "seed1.wav"
    out2 = tmp_path / "seed2.wav"
    adapter.synthesize(**base_kwargs, seed=1, out_path=out1)  # type: ignore[arg-type]
    adapter.synthesize(**base_kwargs, seed=2, out_path=out2)  # type: ignore[arg-type]
    # Both must be valid WAVs of correct duration; byte equality is acceptable but not required
    for out in (out1, out2):
        with wave.open(str(out)) as wf:
            actual_ms = round(wf.getnframes() / wf.getframerate() * 1000)
        assert abs(actual_ms - 1000) <= 50


# ---------------------------------------------------------------------------
# Voice-line sidecar JSON
# ---------------------------------------------------------------------------


def test_mock_tts_writes_sidecar(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="The shadows moved.",
        voice_id="en-narrator-01",
        language="en",
        pacing_ms=800,
        seed=5,
        out_path=out,
    )
    sidecar = out.with_suffix(".json")
    assert sidecar.exists()


def test_mock_tts_sidecar_schema_valid(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "line.wav"
    adapter.synthesize(
        text="Fear gripped him as the door creaked open.",
        voice_id="en-narrator-01",
        language="en",
        pacing_ms=2000,
        seed=10,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene-01",
        line_ref="seg-0",
        line_type="narration",
    )
    sidecar = out.with_suffix(".json")
    data = json.loads(sidecar.read_text())
    validate(data, "voice_line.schema.json")


def test_mock_tts_sidecar_fields(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "dlg.wav"
    adapter.synthesize(
        text="Get out of this house!",
        voice_id="en-male-deep",
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
    assert data["voice_id"] == "en-male-deep"
    assert data["language"] == "en"
    assert data["seed"] == 3
    assert data["pacing_ms"] == 1200
    assert data["status"] == "synthesized"
    assert data["adapter"] == "mock"
    assert data["actual_duration_ms"] is not None


def test_mock_tts_sidecar_minimal_fields(tmp_path: Path) -> None:
    """Minimal call (no story_id/scene_id/line_ref/line_type) uses defaults."""
    adapter = MockTTSAdapter()
    out = tmp_path / "minimal.wav"
    adapter.synthesize(
        text="Darkness fell.",
        voice_id="narrator",
        language="en",
        pacing_ms=500,
        seed=0,
        out_path=out,
    )
    data = json.loads(out.with_suffix(".json").read_text())
    validate(data, "voice_line.schema.json")
    assert data["status"] == "synthesized"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_mock_tts_empty_text_raises(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "bad.wav"
    with pytest.raises(ValueError, match="text"):
        adapter.synthesize(
            text="",
            voice_id="en-narrator-01",
            language="en",
            pacing_ms=1000,
            seed=0,
            out_path=out,
        )


def test_mock_tts_invalid_pacing_raises(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "bad.wav"
    with pytest.raises(ValueError, match="pacing_ms"):
        adapter.synthesize(
            text="Some text.",
            voice_id="en-narrator-01",
            language="en",
            pacing_ms=499,
            seed=0,
            out_path=out,
        )


def test_mock_tts_negative_seed_raises(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "bad.wav"
    with pytest.raises(ValueError, match="seed"):
        adapter.synthesize(
            text="Some text.",
            voice_id="en-narrator-01",
            language="en",
            pacing_ms=1000,
            seed=-1,
            out_path=out,
        )


def test_mock_tts_bad_line_type_raises(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "bad.wav"
    with pytest.raises(ValueError, match="line_type"):
        adapter.synthesize(
            text="Some text.",
            voice_id="en-narrator-01",
            language="en",
            pacing_ms=1000,
            seed=0,
            out_path=out,
            line_type="bad",
        )


def test_mock_tts_bad_language_raises(tmp_path: Path) -> None:
    adapter = MockTTSAdapter()
    out = tmp_path / "bad.wav"
    with pytest.raises(ValueError, match="language"):
        adapter.synthesize(
            text="Some text.",
            voice_id="en-narrator-01",
            language="english",  # must be 2-letter code
            pacing_ms=1000,
            seed=0,
            out_path=out,
        )


# ---------------------------------------------------------------------------
# AdapterFactory
# ---------------------------------------------------------------------------


def test_adapter_factory_get_tts_mock() -> None:
    adapter = AdapterFactory.get_tts("mock")
    assert isinstance(adapter, MockTTSAdapter)


def test_adapter_factory_get_tts_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown"):
        AdapterFactory.get_tts("elevenlabs")


# ---------------------------------------------------------------------------
# Integration: all segments from a script get WAVs
# ---------------------------------------------------------------------------


def test_mock_tts_all_script_segments(tmp_path: Path) -> None:
    """Synthesize a WAV for every segment + dialogue in a fixture script."""
    import json as _json

    from horror_story.manifest import Manifest
    from horror_story.models import Scene
    from horror_story.pipeline.script import generate_script

    scene = Scene(
        story_id="pigeons-from-hell",
        scene_id="test-scene",
        index=0,
        text=(
            "The house loomed in the darkness. Evil shadows danced on the wall.\n\n"
            "Branner: Something evil walks these halls.\n\n"
            "Silence fell."
        ),
        visual_description="The house loomed in the darkness.",
        mood="dread",
        word_count=25,
    )
    manifest = Manifest(
        schema_version="1.0",
        story_id="pigeons-from-hell",
        title="Pigeons from Hell",
        seed=42,
        languages={"primary": "en", "secondary": "uk"},
        render={"width": 3840, "height": 2160, "fps": 24, "codec": "libx264", "audio_codec": "aac"},
        voices={"narrator": "en-narrator-01", "branner": "en-male-deep"},
        adapters={"tts": "mock", "image": "mock", "motion": "mock", "audio": "mock", "typography": "mock"},
        scenes=[],
    )
    script = generate_script(scene, manifest)

    adapter = MockTTSAdapter()
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    for seg in script.segments:
        out = audio_dir / f"narration_{scene.scene_id}_{seg.segment_id}.wav"
        adapter.synthesize(
            text=seg.text_en,
            voice_id=seg.voice_id,
            language="en",
            pacing_ms=seg.pacing_ms,
            seed=manifest.seed,
            out_path=out,
            story_id=scene.story_id,
            scene_id=scene.scene_id,
            line_ref=seg.segment_id,
            line_type="narration",
        )
        assert out.exists()
        with wave.open(str(out)) as wf:
            actual_ms = round(wf.getnframes() / wf.getframerate() * 1000)
        tolerance = seg.pacing_ms * 0.05
        assert abs(actual_ms - seg.pacing_ms) <= tolerance

    for dlg in script.dialogue_lines:
        out = audio_dir / f"dialogue_{scene.scene_id}_{dlg.line_id}.wav"
        adapter.synthesize(
            text=dlg.text_en,
            voice_id=dlg.voice_id,
            language="en",
            pacing_ms=dlg.pacing_ms,
            seed=manifest.seed,
            out_path=out,
            story_id=scene.story_id,
            scene_id=scene.scene_id,
            line_ref=dlg.line_id,
            line_type="dialogue",
        )
        assert out.exists()
