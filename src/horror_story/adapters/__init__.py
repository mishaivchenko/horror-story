from __future__ import annotations

from horror_story.adapters.image.base import ImageAdapter
from horror_story.adapters.image.mock import MockImageAdapter
from horror_story.adapters.tts.base import TTSAdapter
from horror_story.adapters.tts.mock import MockTTSAdapter
from horror_story.adapters.typography.base import TypographyAdapter
from horror_story.adapters.typography.mock import MockTypographyAdapter


class AdapterFactory:
    @staticmethod
    def get_tts(name: str) -> TTSAdapter:
        if name == "mock":
            return MockTTSAdapter()
        raise ValueError(f"unknown TTS adapter: {name!r}")

    @staticmethod
    def get_image(name: str) -> ImageAdapter:
        if name == "mock":
            return MockImageAdapter()
        raise ValueError(f"unknown image adapter: {name!r}")

    @staticmethod
    def get_typography(name: str) -> TypographyAdapter:
        if name == "mock":
            return MockTypographyAdapter()
        raise ValueError(f"unknown typography adapter: {name!r}")
