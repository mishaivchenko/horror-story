from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from horror_story.adapters.typography.base import TypographyAdapter

_MIN_WIDTH = 320
_MIN_HEIGHT = 240


class MockTypographyAdapter(TypographyAdapter):
    """Deterministic transparent-PNG typography adapter. No video rendering; uses Pillow."""

    def render(
        self,
        script_path: Path,
        duration_s: float,
        width: int,
        height: int,
        fps: int,
        seed: int,
        out_path: Path,
    ) -> Path:
        if width < _MIN_WIDTH:
            raise ValueError(f"width must be >= {_MIN_WIDTH}, got {width}")
        if height < _MIN_HEIGHT:
            raise ValueError(f"height must be >= {_MIN_HEIGHT}, got {height}")
        if duration_s < 0:
            raise ValueError(f"duration_s must be >= 0, got {duration_s}")
        if fps < 1:
            raise ValueError(f"fps must be >= 1, got {fps}")
        if seed < 0:
            raise ValueError("seed must be >= 0")
        if not script_path.exists():
            raise FileNotFoundError(f"script not found: {script_path}")

        script = json.loads(script_path.read_text())

        story_id: str = script.get("story_id", "unknown")
        scene_id: str = script.get("scene_id", "unknown")

        segments = script.get("segments", [])
        dialogue_lines = script.get("dialogue_lines", [])

        parts_en = [str(seg["text_en"]) for seg in segments]
        parts_secondary = [str(seg["text_secondary"]) for seg in segments]

        for dlg in dialogue_lines:
            char = str(dlg["character"])
            parts_en.append(f"{char}: {dlg['text_en']}")
            parts_secondary.append(f"{char}: {dlg['text_secondary']}")

        text_en = " ".join(parts_en)
        text_secondary = " ".join(parts_secondary)

        img = _render_overlay(text_en, text_secondary, width, height)

        tmp = out_path.with_suffix(".png.tmp")
        img.save(str(tmp), format="PNG")
        tmp.replace(out_path)

        def _rel(p: Path) -> str:
            try:
                return str(p.relative_to(Path.cwd()))
            except ValueError:
                return str(p)

        sidecar = {
            "schema_version": "1.0",
            "story_id": story_id,
            "scene_id": scene_id,
            "source_script": _rel(script_path),
            "duration_s": duration_s,
            "width": width,
            "height": height,
            "fps": fps,
            "seed": seed,
            "adapter": "mock",
            "output_path": _rel(out_path),
            "status": "generated",
            "error": None,
        }
        sidecar_path = out_path.with_suffix(".json")
        tmp_sidecar = sidecar_path.with_suffix(".json.tmp")
        tmp_sidecar.write_text(json.dumps(sidecar, indent=2))
        tmp_sidecar.replace(sidecar_path)

        return out_path


def _render_overlay(
    text_en: str,
    text_secondary: str,
    width: int,
    height: int,
) -> Image.Image:
    """Render a transparent RGBA frame with EN text in upper third, secondary below."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size_en = max(12, height // 20)
    font_size_secondary = max(10, height // 28)

    font_en = ImageFont.load_default(size=font_size_en)
    font_secondary = ImageFont.load_default(size=font_size_secondary)

    margin_x = max(10, int(width * 0.05))
    available_width = width - 2 * margin_x

    chars_en = max(10, int(available_width / (font_size_en * 0.6)))
    chars_secondary = max(10, int(available_width / (font_size_secondary * 0.6)))

    wrapped_en = textwrap.fill(text_en, width=chars_en) if text_en else ""
    wrapped_secondary = (
        textwrap.fill(text_secondary, width=chars_secondary) if text_secondary else ""
    )

    top_en = max(10, int(height * 0.05))
    shadow_offset_en = max(1, font_size_en // 12)

    if wrapped_en:
        draw.text(
            (margin_x + shadow_offset_en, top_en + shadow_offset_en),
            wrapped_en,
            fill=(0, 0, 0, 200),
            font=font_en,
        )
        draw.text(
            (margin_x, top_en),
            wrapped_en,
            fill=(255, 255, 255, 255),
            font=font_en,
        )

    if wrapped_secondary:
        en_lines = wrapped_en.count("\n") + 1 if wrapped_en else 0
        en_block_height = en_lines * (font_size_en + 4)
        gap = max(8, height // 30)
        top_secondary = top_en + en_block_height + gap
        shadow_offset_sec = max(1, font_size_secondary // 12)

        draw.text(
            (margin_x + shadow_offset_sec, top_secondary + shadow_offset_sec),
            wrapped_secondary,
            fill=(0, 0, 0, 200),
            font=font_secondary,
        )
        draw.text(
            (margin_x, top_secondary),
            wrapped_secondary,
            fill=(220, 220, 180, 255),
            font=font_secondary,
        )

    return img
