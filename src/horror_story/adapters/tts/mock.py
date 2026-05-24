from __future__ import annotations

import json
import re
import struct
import wave
from pathlib import Path

from horror_story.adapters.tts.base import TTSAdapter

_SAMPLE_RATE = 44100
_CHANNELS = 1
_SAMPLE_WIDTH = 2  # 16-bit

_LANGUAGE_RE = re.compile(r"^[a-z]{2}$")


class MockTTSAdapter(TTSAdapter):
    """Deterministic silent-WAV TTS adapter. No real synthesis; uses all-zero PCM."""

    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str,
        pacing_ms: int,
        seed: int,
        out_path: Path,
        *,
        story_id: str = "",
        scene_id: str = "",
        line_ref: str = "",
        line_type: str = "narration",
    ) -> Path:
        if not text:
            raise ValueError("text must not be empty")
        if pacing_ms < 500:
            raise ValueError("pacing_ms must be >= 500 (schema minimum)")
        if seed < 0:
            raise ValueError("seed must be >= 0 (schema minimum)")
        if line_type not in ("narration", "dialogue"):
            raise ValueError(f"line_type must be 'narration' or 'dialogue', got: {line_type!r}")
        if not _LANGUAGE_RE.match(language):
            raise ValueError(f"language must be a 2-letter BCP-47 code, got: {language!r}")

        n_frames = round(_SAMPLE_RATE * pacing_ms / 1000)
        pcm_data = struct.pack(f"<{n_frames}h", *([0] * n_frames))

        tmp = out_path.with_suffix(".wav.tmp")
        with wave.open(str(tmp), "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(_SAMPLE_WIDTH)
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(pcm_data)
        tmp.replace(out_path)

        actual_duration_ms = round(n_frames / _SAMPLE_RATE * 1000)
        sidecar = {
            "schema_version": "1.0",
            "story_id": story_id or "unknown",
            "scene_id": scene_id or "unknown",
            "line_ref": line_ref or "unknown",
            "line_type": line_type,
            "text": text,
            "language": language,
            "voice_id": voice_id,
            "seed": seed,
            "pacing_ms": pacing_ms,
            "adapter": "mock",
            "output_path": str(out_path),
            "actual_duration_ms": actual_duration_ms,
            "status": "synthesized",
            "error": None,
        }
        sidecar_path = out_path.with_suffix(".json")
        tmp_sidecar = sidecar_path.with_suffix(".json.tmp")
        tmp_sidecar.write_text(json.dumps(sidecar, indent=2))
        tmp_sidecar.replace(sidecar_path)

        return out_path
