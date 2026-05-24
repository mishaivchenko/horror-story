from __future__ import annotations

import json
import hashlib
import textwrap
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFont

from horror_story.adapters.typography.base import TypographyAdapter

_MIN_WIDTH = 320
_MIN_HEIGHT = 240

# Zone fraction constraints — box must not exceed these fractions of the frame.
_ZONE_MAX_W_FRAC = 0.50   # max 50% of frame width per zone
_ZONE_MAX_H_FRAC = 0.30   # max 30% of frame height per zone

# Semi-transparent box background
_BOX_BG = (0, 0, 0, 160)
# Padding inside each box (pixels)
_BOX_PAD = 8


class _Zone(NamedTuple):
    """Axis-aligned bounding box for a text zone: (x0, y0, x1, y1)."""
    x0: int
    y0: int
    x1: int
    y1: int


def _pick_zones(
    scene_id: str,
    seed: int,
    has_dialogue: bool,
    width: int,
    height: int,
) -> list[_Zone]:
    """Return one or two non-overlapping safe-area zones, deterministically.

    Zone positions are derived from scene_id + seed so that the layout is
    stable across re-runs but varies across scenes.

    Primary zone (narration):  always bottom strip.
    Secondary zone (dialogue): left or right strip in the upper region,
                               only present when has_dialogue is True.
    """
    # Deterministic choice for secondary zone side. Do not use Python's
    # process-salted hash(); layout must be stable across separate runs.
    digest = hashlib.sha256(f"{scene_id}:{seed}".encode("utf-8")).digest()

    box_w = int(width * _ZONE_MAX_W_FRAC)
    box_h = int(height * _ZONE_MAX_H_FRAC)

    margin = max(8, int(min(width, height) * 0.03))

    # Primary zone: bottom-centred strip.
    prim_x0 = margin
    prim_y0 = height - margin - box_h
    prim_x1 = width - margin
    prim_y1 = height - margin
    primary = _Zone(prim_x0, prim_y0, prim_x1, prim_y1)

    if not has_dialogue:
        return [primary]

    # Secondary zone: left or right, upper half of frame.
    if digest[0] % 2 == 0:
        # Left side
        sec_x0 = margin
        sec_x1 = sec_x0 + box_w
    else:
        # Right side
        sec_x1 = width - margin
        sec_x0 = sec_x1 - box_w

    sec_y0 = margin
    sec_y1 = sec_y0 + box_h
    secondary = _Zone(sec_x0, sec_y0, sec_x1, sec_y1)

    return [primary, secondary]


def _render_text_box(
    draw: ImageDraw.ImageDraw,
    zone: _Zone,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    font_size: int,
    text_color: tuple[int, int, int, int],
) -> None:
    """Draw a semi-transparent box and clamp text inside it."""
    if not text:
        return

    box_w = zone.x1 - zone.x0
    box_h = zone.y1 - zone.y0

    # Draw background box
    draw.rectangle([zone.x0, zone.y0, zone.x1, zone.y1], fill=_BOX_BG)

    available_w = box_w - 2 * _BOX_PAD
    available_h = box_h - 2 * _BOX_PAD

    char_w = max(1, int(available_w / max(1, font_size * 0.6)))
    wrapped = textwrap.fill(text, width=char_w) if text else ""

    # Clamp to lines that fit vertically
    line_height = font_size + 4
    max_lines = max(1, available_h // line_height)
    lines = wrapped.splitlines()[:max_lines]
    clamped = "\n".join(lines)

    if not clamped:
        return

    shadow_off = max(1, font_size // 12)
    tx = zone.x0 + _BOX_PAD
    ty = zone.y0 + _BOX_PAD

    draw.text(
        (tx + shadow_off, ty + shadow_off),
        clamped,
        fill=(0, 0, 0, 200),
        font=font,
    )
    draw.text(
        (tx, ty),
        clamped,
        fill=text_color,
        font=font,
    )


def _render_overlay(
    text_en: str,
    text_secondary: str,
    dialogue_en: str,
    dialogue_secondary: str,
    scene_id: str,
    seed: int,
    width: int,
    height: int,
) -> Image.Image:
    """Render adaptive-zones RGBA overlay. Text never covers the full frame."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    has_dialogue = bool(dialogue_en.strip())
    zones = _pick_zones(scene_id, seed, has_dialogue, width, height)

    font_size = max(12, height // 20)
    font_size_sec = max(10, height // 28)
    font = ImageFont.load_default(size=font_size)
    font_sec = ImageFont.load_default(size=font_size_sec)

    # Primary zone: narration (EN + secondary combined)
    narration = text_en
    if text_secondary:
        narration = text_en + "\n" + text_secondary
    _render_text_box(draw, zones[0], narration, font, font_size, (255, 255, 255, 255))

    # Secondary zone: dialogue when present
    if has_dialogue and len(zones) == 2:
        dlg_text = dialogue_en
        if dialogue_secondary:
            dlg_text = dialogue_en + "\n" + dialogue_secondary
        _render_text_box(draw, zones[1], dlg_text, font_sec, font_size_sec, (220, 220, 180, 255))

    return img


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

        narration_en = " ".join(str(seg["text_en"]) for seg in segments)
        narration_sec = " ".join(str(seg["text_secondary"]) for seg in segments)

        dlg_en_parts: list[str] = []
        dlg_sec_parts: list[str] = []
        for dlg in dialogue_lines:
            char = str(dlg["character"])
            dlg_en_parts.append(f"{char}: {dlg['text_en']}")
            dlg_sec_parts.append(f"{char}: {dlg['text_secondary']}")

        dialogue_en = " ".join(dlg_en_parts)
        dialogue_secondary = " ".join(dlg_sec_parts)

        img = _render_overlay(
            narration_en,
            narration_sec,
            dialogue_en,
            dialogue_secondary,
            scene_id,
            seed,
            width,
            height,
        )

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
