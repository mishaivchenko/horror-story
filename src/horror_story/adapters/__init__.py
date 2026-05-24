from __future__ import annotations

from horror_story.adapters.audio.base import AudioAdapter
from horror_story.adapters.audio.mock import MockAudioAdapter
from horror_story.adapters.image.base import ImageAdapter
from horror_story.adapters.image.mock import MockImageAdapter
from horror_story.adapters.motion.base import MotionAdapter
from horror_story.adapters.motion.mock import MockMotionAdapter
from horror_story.adapters.tts.base import TTSAdapter
from horror_story.adapters.tts.mock import MockTTSAdapter
from horror_story.adapters.typography.base import TypographyAdapter
from horror_story.adapters.typography.mock import MockTypographyAdapter


class AdapterFactory:
    @staticmethod
    def get_tts(name: str) -> TTSAdapter:
        if name == "mock":
            return MockTTSAdapter()
        elif name == "kokoro":
            from horror_story.adapters.tts.kokoro import KokoroTTSAdapter
            return KokoroTTSAdapter()
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

    @staticmethod
    def get_motion(name: str) -> MotionAdapter:
        if name == "mock":
            return MockMotionAdapter()
        raise ValueError(f"unknown motion adapter: {name!r}")

    @staticmethod
    def get_audio(name: str) -> AudioAdapter:
        if name == "mock":
            return MockAudioAdapter()
        raise ValueError(f"unknown audio adapter: {name!r}")
