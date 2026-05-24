from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


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
