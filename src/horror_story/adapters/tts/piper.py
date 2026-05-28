from __future__ import annotations

import importlib.util
import json
import wave
from pathlib import Path
from typing import Any

from horror_story.adapters.tts.base import TTSAdapter

_SAMPLE_RATE = 22050
_CHANNELS = 1
_SAMPLE_WIDTH = 2

_CACHE_DIR = Path.home() / ".cache" / "horror_story" / "piper"
_ESPEAK_DATA = Path(__file__).parent.parent.parent.parent.parent / ".venv" / "lib"

_MODEL_URL_BASE = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main"
)
_LANG_MODELS: dict[str, tuple[str, str]] = {
    "uk": (
        "uk/uk_UA/ukrainian_tts/medium/uk_UA-ukrainian_tts-medium.onnx",
        "uk/uk_UA/ukrainian_tts/medium/uk_UA-ukrainian_tts-medium.onnx.json",
    ),
}

# voice_id → (language, speaker_id)
_VOICE_MAP: dict[str, tuple[str, int | None]] = {
    "narrator_uk": ("uk", None),
    "character_uk": ("uk", None),
    "character_uk_f": ("uk", None),
}
_DEFAULT_LANG = "uk"


def _normalize_text_type(text: str, phoneme_map: set[str]) -> str:
    """Prepare text for text-type Piper models (character-level phoneme maps).

    Collapses whitespace variants to plain space, lowercases, then drops any
    character not present in the model's phoneme_id_map.
    """
    import re as _re
    text = _re.sub(r"[\r\n\t\xa0​]+", " ", text)
    text = text.lower()
    text = "".join(c for c in text if c in phoneme_map)
    return text.strip()


def _piper_available() -> bool:
    return importlib.util.find_spec("piper") is not None


def _espeak_data_dir() -> Path:
    """Find piper's bundled espeak-ng-data directory."""
    try:
        import piper as _piper_pkg
        bundled = Path(_piper_pkg.__file__).parent / "espeak-ng-data"
        if bundled.is_dir():
            return bundled
    except ImportError:
        pass
    return Path("/opt/homebrew/share/espeak-ng-data")


class PiperTTSAdapter(TTSAdapter):
    def __init__(self) -> None:
        self._voices: dict[str, Any] = {}

    def _load_voice(self, lang: str) -> Any:
        if lang in self._voices:
            return self._voices[lang]
        if not _piper_available():
            raise RuntimeError("piper-tts is not installed; run: pip install piper-tts")
        model_path = _ensure_model(lang)
        from piper.voice import PiperVoice
        voice = PiperVoice.load(str(model_path), espeak_data_dir=str(_espeak_data_dir()))
        self._voices[lang] = voice
        return voice

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
            raise ValueError("pacing_ms must be >= 400")
        if seed < 0:
            raise ValueError("seed must be >= 0")
        if line_type not in ("narration", "dialogue"):
            raise ValueError(f"line_type must be 'narration' or 'dialogue', got: {line_type!r}")

        lang, _ = _VOICE_MAP.get(voice_id, (_DEFAULT_LANG, None))
        voice = self._load_voice(lang)

        from piper.config import PhonemeType
        if voice.config.phoneme_type == PhonemeType.TEXT:
            text = _normalize_text_type(text, set(voice.config.phoneme_id_map.keys()))

        tmp = out_path.with_suffix(".wav.tmp")
        with wave.open(str(tmp), "wb") as wf:
            voice.synthesize_wav(text, wf)
        tmp.replace(out_path)

        with wave.open(str(out_path), "rb") as wf:
            n_frames = wf.getnframes()
            actual_rate = wf.getframerate()
        actual_duration_ms = round(n_frames / actual_rate * 1000)

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
            "adapter": "piper",
            "output_path": out_path.name,
            "actual_duration_ms": actual_duration_ms,
            "status": "synthesized",
            "error": None,
        }
        sidecar_path = out_path.with_suffix(".json")
        tmp_sc = sidecar_path.with_suffix(".json.tmp")
        tmp_sc.write_text(json.dumps(sidecar, indent=2))
        tmp_sc.replace(sidecar_path)

        return out_path


def _ensure_model(lang: str) -> Path:
    if lang not in _LANG_MODELS:
        supported = ", ".join(_LANG_MODELS)
        raise ValueError(f"Piper: unsupported language {lang!r}; supported: {supported}")
    model_rel, _ = _LANG_MODELS[lang]
    model_name = Path(model_rel).name
    dest = _CACHE_DIR / model_name
    if not dest.exists():
        import urllib.request
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        url = f"{_MODEL_URL_BASE}/{model_rel}"
        tmp = dest.with_suffix(".onnx.tmp")
        urllib.request.urlretrieve(url, tmp)
        tmp.replace(dest)
        # config JSON
        json_rel = _LANG_MODELS[lang][1]
        json_name = Path(json_rel).name
        json_dest = _CACHE_DIR / json_name
        if not json_dest.exists():
            json_url = f"{_MODEL_URL_BASE}/{json_rel}"
            json_tmp = json_dest.with_suffix(".json.tmp")
            urllib.request.urlretrieve(json_url, json_tmp)
            json_tmp.replace(json_dest)
    return dest
