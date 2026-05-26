from __future__ import annotations

import importlib.util
import json
import re
import struct
import urllib.request
import wave
from pathlib import Path
from typing import Any

from horror_story.adapters.tts.base import TTSAdapter

_SAMPLE_RATE = 44100
_CHANNELS = 1
_SAMPLE_WIDTH = 2  # 16-bit PCM
_CACHE_DIR = Path.home() / ".cache" / "horror_story" / "kokoro"
_LANGUAGE_RE = re.compile(r"^[a-z]{2}$")

_MODEL_FILENAME = "kokoro-v1.0.onnx"
_VOICES_FILENAME = "voices-v1.0.bin"
_RELEASE_BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"

_VOICE_MAP: dict[str, str] = {
    "narrator_en": "am_adam",
    "character_en": "am_michael",
    "character_en_deep": "bm_george",
    "character_en_young": "am_puck",
    "character_en_f": "af_heart",
}
_DEFAULT_VOICE = "am_adam"

# Maps BCP-47 two-letter codes to the lang string kokoro-onnx expects.
_LANG_MAP: dict[str, str] = {
    "en": "en-us",
    "ja": "ja",
}


def _kokoro_available() -> bool:
    return importlib.util.find_spec("kokoro_onnx") is not None


class KokoroTTSAdapter(TTSAdapter):
    def __init__(self) -> None:
        self._kokoro: Any = None

    def _load_model(self) -> Any:
        import kokoro_onnx  # type: ignore[import-untyped]
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        model_path = _ensure_asset(_MODEL_FILENAME)
        voices_path = _ensure_asset(_VOICES_FILENAME)
        return kokoro_onnx.Kokoro(str(model_path), str(voices_path))

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
        if pacing_ms < 400:
            raise ValueError("pacing_ms must be >= 400 (schema minimum)")
        if seed < 0:
            raise ValueError("seed must be >= 0 (schema minimum)")
        if line_type not in ("narration", "dialogue"):
            raise ValueError(f"line_type must be 'narration' or 'dialogue', got: {line_type!r}")
        if not _LANGUAGE_RE.match(language):
            raise ValueError(f"language must be a 2-letter BCP-47 code, got: {language!r}")
        if language not in _LANG_MAP:
            supported = ", ".join(sorted(_LANG_MAP))
            raise ValueError(
                f"language {language!r} is not supported by KokoroTTSAdapter; "
                f"supported: {supported}"
            )

        if self._kokoro is None:
            self._kokoro = self._load_model()

        kokoro_voice = _VOICE_MAP.get(voice_id, _DEFAULT_VOICE)
        kokoro_lang = _LANG_MAP[language]
        samples, sample_rate = self._kokoro.create(text=text, voice=kokoro_voice, lang=kokoro_lang)

        pcm_data = _to_pcm(samples, sample_rate, _SAMPLE_RATE)
        n_frames = len(pcm_data) // _SAMPLE_WIDTH

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
            "adapter": "kokoro",
            "output_path": out_path.name,
            "actual_duration_ms": actual_duration_ms,
            "status": "synthesized",
            "error": None,
        }
        sidecar_path = out_path.with_suffix(".json")
        tmp_sidecar = sidecar_path.with_suffix(".json.tmp")
        tmp_sidecar.write_text(json.dumps(sidecar, indent=2))
        tmp_sidecar.replace(sidecar_path)

        return out_path


def _ensure_asset(filename: str) -> Path:
    """Return absolute path to a cached model asset, downloading if absent."""
    dest = _CACHE_DIR / filename
    if not dest.exists():
        url = f"{_RELEASE_BASE}/{filename}"
        tmp = dest.with_suffix(".tmp")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(dest)
    return dest


def _to_pcm(samples: Any, src_rate: int, dst_rate: int) -> bytes:
    """Convert float samples to 16-bit PCM, resampling if needed."""
    floats = list(samples)

    if src_rate != dst_rate:
        floats = _resample(floats, src_rate, dst_rate)

    n = len(floats)
    packed = bytearray(n * _SAMPLE_WIDTH)
    for i, s in enumerate(floats):
        val = max(-1.0, min(1.0, s))
        pcm_val = int(val * 32767)
        struct.pack_into("<h", packed, i * 2, pcm_val)
    return bytes(packed)


def _resample(samples: list[float], src_rate: int, dst_rate: int) -> list[float]:
    """Linear resampling from src_rate to dst_rate."""
    if src_rate == dst_rate:
        return samples
    n_in = len(samples)
    n_out = round(n_in * dst_rate / src_rate)
    if n_out == 0:
        return []
    out: list[float] = []
    for i in range(n_out):
        pos = i * (n_in - 1) / (n_out - 1) if n_out > 1 else 0.0
        lo = int(pos)
        hi = min(lo + 1, n_in - 1)
        frac = pos - lo
        out.append(samples[lo] * (1.0 - frac) + samples[hi] * frac)
    return out
