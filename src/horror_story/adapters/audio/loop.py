from __future__ import annotations

import json
import wave
from pathlib import Path

from horror_story.adapters.audio.base import AudioAdapter
from horror_story.adapters.audio.mock import MockAudioAdapter

_SAMPLE_RATE = 44100
_CHANNELS = 2
_SAMPLE_WIDTH = 2  # 16-bit


class LoopAudioAdapter(AudioAdapter):
    """Mood-mapped looped WAV ambient audio adapter.

    Reads a pre-recorded WAV file for the scene's mood from assets_dir,
    loops or trims it to duration_s, and writes the output WAV + sidecar.
    Falls back to silence (MockAudioAdapter) when the mood asset is absent.
    """

    def __init__(self, assets_dir: Path) -> None:
        self._assets_dir = assets_dir
        self._available: dict[str, Path] = {}
        if assets_dir.is_dir():
            for f in assets_dir.glob("*.wav"):
                self._available[f.stem] = f

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

        wav_src = self._available.get(mood)
        if wav_src is None:
            print(f"[warning] loop audio: no asset for mood '{mood}', falling back to silence")
            return MockAudioAdapter().generate(
                mood, duration_s, seed, out_path,
                story_id=story_id, scene_id=scene_id,
            )

        return self._loop_wav(wav_src, duration_s, mood, seed, out_path, story_id, scene_id)

    def _loop_wav(
        self,
        src: Path,
        duration_s: float,
        mood: str,
        seed: int,
        out_path: Path,
        story_id: str,
        scene_id: str,
    ) -> Path:
        with wave.open(str(src), "rb") as wf:
            src_rate = wf.getframerate()
            src_channels = wf.getnchannels()
            src_width = wf.getsampwidth()
            src_frame_count = wf.getnframes()
            src_frames = wf.readframes(src_frame_count)

        # Resample to standard params if needed (simple: just use source params)
        frame_size = src_channels * src_width
        target_frame_count = round(src_rate * duration_s)

        if src_frame_count == 0 or frame_size == 0:
            return MockAudioAdapter().generate(
                mood, duration_s, seed, out_path,
                story_id=story_id, scene_id=scene_id,
            )

        # Build looped output by repeating source frames cyclically
        output = bytearray()
        written = 0
        while written < target_frame_count:
            take = min(src_frame_count, target_frame_count - written)
            output.extend(src_frames[:take * frame_size])
            written += take

        tmp = out_path.with_suffix(".wav.tmp")
        with wave.open(str(tmp), "wb") as wf:
            wf.setnchannels(src_channels)
            wf.setsampwidth(src_width)
            wf.setframerate(src_rate)
            wf.writeframes(bytes(output))
        tmp.replace(out_path)

        actual_duration_s = target_frame_count / src_rate
        sidecar = {
            "schema_version": "1.0",
            "story_id": story_id or "unknown",
            "scene_id": scene_id or "unknown",
            "mood": mood,
            "duration_s": duration_s,
            "seed": seed,
            "adapter": "loop",
            "output_path": out_path.name,
            "actual_duration_s": actual_duration_s,
            "status": "generated",
            "error": None,
        }
        sidecar_path = out_path.with_suffix(".json")
        tmp_sidecar = sidecar_path.with_suffix(".json.tmp")
        tmp_sidecar.write_text(json.dumps(sidecar, indent=2))
        tmp_sidecar.replace(sidecar_path)

        return out_path
