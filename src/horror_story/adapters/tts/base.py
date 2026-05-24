from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSAdapter(ABC):
    # Core synthesis contract (spec #004): the six positional arguments.
    # The keyword-only args (story_id … line_type) carry sidecar metadata only;
    # they do not affect audio output and must not be required by real adapters.
    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str,
        pacing_ms: int,
        seed: int,
        out_path: Path,
        *,
        story_id: str = "",
        scene_id: str = "",
        line_ref: str = "",
        line_type: str = "narration",
    ) -> Path: ...
