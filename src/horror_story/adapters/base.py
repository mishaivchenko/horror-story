from abc import ABC, abstractmethod
from pathlib import Path


class TTSAdapter(ABC):
    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str,
        pacing_ms: int,
        seed: int,
        out_path: Path,
    ) -> Path: ...


class ImageAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int,
        out_path: Path,
    ) -> Path: ...


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


class TypographyAdapter(ABC):
    @abstractmethod
    def render(
        self,
        script_path: Path,
        duration_s: float,
        width: int,
        height: int,
        fps: int,
        seed: int,
        out_path: Path,
    ) -> Path: ...
