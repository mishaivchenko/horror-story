from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from horror_story.adapters.image.base import ImageAdapter

_MIN_WIDTH = 320
_MIN_HEIGHT = 240


class MockImageAdapter(ImageAdapter):
    """Deterministic grey-PNG image adapter. No real generation; uses Pillow."""

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int,
        out_path: Path,
        *,
        story_id: str = "",
        scene_id: str = "",
    ) -> Path:
        # story_id and scene_id carry sidecar metadata only; they do not affect
        # pixel output and are not part of the ImageAdapter ABC contract.
        if not prompt:
            raise ValueError("prompt must not be empty")
        if width < _MIN_WIDTH:
            raise ValueError(f"width must be >= {_MIN_WIDTH}, got {width}")
        if height < _MIN_HEIGHT:
            raise ValueError(f"height must be >= {_MIN_HEIGHT}, got {height}")
        if seed < 0:
            raise ValueError("seed must be >= 0")

        grey = seed % 128 + 64
        img = Image.new("RGB", (width, height), color=(grey, grey, grey))

        label = scene_id if scene_id else prompt[:40]
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), label, fill=(255, 255, 255))

        tmp = out_path.with_suffix(".png.tmp")
        img.save(str(tmp), format="PNG")
        tmp.replace(out_path)

        sidecar = {
            "schema_version": "1.0",
            "story_id": story_id or "unknown",
            "scene_id": scene_id or "unknown",
            "prompt": prompt,
            "width": width,
            "height": height,
            "seed": seed,
            "adapter": "mock",
            "output_path": str(out_path.relative_to(Path.cwd()) if out_path.is_absolute() and out_path.is_relative_to(Path.cwd()) else out_path),
            "status": "generated",
            "error": None,
        }
        sidecar_path = out_path.with_suffix(".json")
        tmp_sidecar = sidecar_path.with_suffix(".json.tmp")
        tmp_sidecar.write_text(json.dumps(sidecar, indent=2))
        tmp_sidecar.replace(sidecar_path)

        return out_path
