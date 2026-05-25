from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class TypographyAdapter(ABC):
    @abstractmethod
    def render(
        self,
        script: dict[str, Any],
        timeline: dict[str, Any],
        scene_id: str,
        seed: int,
        out_dir: Path,        # video/ directory — PNGs written here
        out_timing: Path,     # video/typography_<scene_id>_timing.json
        width: int,
        height: int,
    ) -> Path: ...            # returns out_timing path
