from abc import ABC, abstractmethod
from pathlib import Path

from horror_story.adapters.image.base import ImageAdapter
from horror_story.adapters.tts.base import TTSAdapter
from horror_story.adapters.typography.base import TypographyAdapter


class MotionAdapter(ABC):
    @abstractmethod
    def animate(
        self,
        frame_path: Path,
        duration_s: float,
        fps: int,
        effect: str,
        seed: int,
        out_path: Path,
    ) -> Path: ...


class AudioAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        mood: str,
        duration_s: float,
        seed: int,
        out_path: Path,
    ) -> Path: ...


__all__ = [
    "TTSAdapter",
    "ImageAdapter",
    "MotionAdapter",
    "AudioAdapter",
    "TypographyAdapter",
]
