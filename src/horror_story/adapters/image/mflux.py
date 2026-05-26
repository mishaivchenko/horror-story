from __future__ import annotations

import json
from pathlib import Path

from PIL import Image as PilImage

from horror_story.adapters.image.base import ImageAdapter
from horror_story.schemas import validate

_MIN_WIDTH = 320
_MIN_HEIGHT = 240

# FLUX.1-schnell produces static noise above this long-edge size at 4 steps.
_FLUX_MAX_LONG_EDGE = 1360


def _flux_dims(width: int, height: int) -> tuple[int, int]:
    """Scale down to fit within _FLUX_MAX_LONG_EDGE, keeping aspect ratio, aligned to 16."""
    long = max(width, height)
    if long <= _FLUX_MAX_LONG_EDGE:
        return width, height
    scale = _FLUX_MAX_LONG_EDGE / long
    fw = max(16, round(width * scale / 16) * 16)
    fh = max(16, round(height * scale / 16) * 16)
    return fw, fh


class MfluxImageAdapter(ImageAdapter):
    """Real image adapter using mflux (FLUX.1-schnell). Requires: pip install 'horror-story[mflux]'."""

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
        try:
            from mflux.models.flux.variants.txt2img.flux import Flux1  # type: ignore[import-untyped]
            from mflux.models.common.config import ModelConfig  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "mflux is not installed. Run: pip install 'horror-story[mflux]'"
            )

        if not prompt:
            raise ValueError("prompt must not be empty")
        if width < _MIN_WIDTH:
            raise ValueError(f"width must be >= {_MIN_WIDTH}, got {width}")
        if height < _MIN_HEIGHT:
            raise ValueError(f"height must be >= {_MIN_HEIGHT}, got {height}")
        if seed < 0:
            raise ValueError("seed must be >= 0")

        flux_w, flux_h = _flux_dims(width, height)

        flux = Flux1(
            model_config=ModelConfig.schnell(),
            quantize=4,
        )
        image = flux.generate_image(
            seed=seed,
            prompt=prompt,
            num_inference_steps=4,
            height=flux_h,
            width=flux_w,
        )

        tmp = out_path.with_name(out_path.stem + ".tmp.png")
        if tmp.exists():
            tmp.unlink()
        image.save(str(tmp), overwrite=True)

        # Upscale to target dimensions if FLUX generated at a smaller size.
        if (flux_w, flux_h) != (width, height):
            with PilImage.open(tmp) as pil_img:
                upscaled = pil_img.resize((width, height), PilImage.Resampling.LANCZOS)
            upscaled.save(str(tmp), format="PNG")

        tmp.replace(out_path)

        sidecar: dict[str, object] = {
            "schema_version": "1.0",
            "story_id": story_id or "unknown",
            "scene_id": scene_id or "unknown",
            "prompt": prompt,
            "width": width,
            "height": height,
            "seed": seed,
            "adapter": "mflux-schnell",
            "output_path": out_path.name,
            "status": "generated",
            "error": None,
        }
        validate(sidecar, "keyframe.schema.json")

        sidecar_path = out_path.with_suffix(".json")
        tmp_sidecar = sidecar_path.with_suffix(".json.tmp")
        tmp_sidecar.write_text(json.dumps(sidecar, indent=2))
        tmp_sidecar.replace(sidecar_path)

        return out_path
