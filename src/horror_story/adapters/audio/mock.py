from __future__ import annotations

import json
import struct
import wave
from pathlib import Path

from horror_story.adapters.audio.base import AudioAdapter

_SAMPLE_RATE = 44100
_CHANNELS = 2
_SAMPLE_WIDTH = 2  # 16-bit


class MockAudioAdapter(AudioAdapter):
    """Deterministic silent stereo WAV audio adapter. No real synthesis; all-zero PCM."""

    def generate(
        self,
        mood: str,
        duration_s: float,
        seed: int,
        out_path: Path,
        *,
        story_id: str = "",
        scene_id: str = "",
    ) -> Path:
        if not mood:
            raise ValueError("mood must not be empty")
        if duration_s <= 0:
            raise ValueError("duration_s must be > 0")
        if seed < 0:
            raise ValueError("seed must be >= 0")

        n_frames = round(_SAMPLE_RATE * duration_s)
        n_samples = n_frames * _CHANNELS
        pcm_data = struct.pack(f"<{n_samples}h", *([0] * n_samples))

        tmp = out_path.with_suffix(".wav.tmp")
        with wave.open(str(tmp), "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(_SAMPLE_WIDTH)
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(pcm_data)
        tmp.replace(out_path)

        actual_duration_s = n_frames / _SAMPLE_RATE
        sidecar = {
            "schema_version": "1.0",
            "story_id": story_id or "unknown",
            "scene_id": scene_id or "unknown",
            "mood": mood,
            "duration_s": duration_s,
            "seed": seed,
            "adapter": "mock",
            "output_path": str(out_path),
            "actual_duration_s": actual_duration_s,
            "status": "generated",
            "error": None,
        }
        sidecar_path = out_path.with_suffix(".json")
        tmp_sidecar = sidecar_path.with_suffix(".json.tmp")
        tmp_sidecar.write_text(json.dumps(sidecar, indent=2))
        tmp_sidecar.replace(sidecar_path)

        return out_path
