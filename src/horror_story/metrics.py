from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator


@dataclass
class StageEntry:
    stage: str
    scene_id: str | None
    duration_s: float


@dataclass
class MetricsCollector:
    story_id: str
    run_id: str
    scene_id: str | None = None
    _stages: list[StageEntry] = field(default_factory=list)
    _start: float = field(default_factory=time.monotonic)

    @contextmanager
    def stage(self, name: str, scene_id: str | None = None) -> Generator[None, None, None]:
        t0 = time.monotonic()
        yield
        self._stages.append(
            StageEntry(
                stage=name,
                scene_id=scene_id,
                duration_s=max(round(time.monotonic() - t0, 3), 0.001),
            )
        )

    def write(self, out_path: Path) -> None:
        total_s = round(time.monotonic() - self._start, 3)
        payload = {
            "schema_version": "1.0",
            "story_id": self.story_id,
            "run_id": self.run_id,
            "scene_id": self.scene_id,
            "total_s": total_s,
            "stages": [
                {
                    "stage": e.stage,
                    "scene_id": e.scene_id,
                    "duration_s": e.duration_s,
                }
                for e in self._stages
            ],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2))
