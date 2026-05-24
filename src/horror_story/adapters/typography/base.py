from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


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
