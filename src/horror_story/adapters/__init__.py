from __future__ import annotations

from horror_story.adapters.tts.base import TTSAdapter
from horror_story.adapters.tts.mock import MockTTSAdapter


class AdapterFactory:
    @staticmethod
    def get_tts(name: str) -> TTSAdapter:
        if name == "mock":
            return MockTTSAdapter()
        raise ValueError(f"unknown TTS adapter: {name!r}")
