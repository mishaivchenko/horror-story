from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class AudioAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        mood: str,
        duration_s: float,
        seed: int,
        out_path: Path,
    ) -> Path: ...
