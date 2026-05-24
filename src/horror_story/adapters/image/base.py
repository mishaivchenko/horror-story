from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


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
