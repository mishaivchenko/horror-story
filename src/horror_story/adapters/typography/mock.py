from __future__ import annotations

import json
import hashlib
import textwrap
from pathlib import Path
from typing import Any, NamedTuple

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
    """Deterministic per-segment RGBA PNG typography adapter. No video rendering; uses Pillow."""

    def render(
        self,
        script: dict[str, Any],
        timeline: dict[str, Any],
        scene_id: str,
        seed: int,
        out_dir: Path,
        out_timing: Path,
        width: int,
        height: int,
    ) -> Path:
        if width < _MIN_WIDTH:
            raise ValueError(f"width must be >= {_MIN_WIDTH}, got {width}")
        if height < _MIN_HEIGHT:
            raise ValueError(f"height must be >= {_MIN_HEIGHT}, got {height}")
        if seed < 0:
            raise ValueError("seed must be >= 0")

        segments: list[dict[str, Any]] = script.get("segments", [])
        dialogue_lines: list[dict[str, Any]] = script.get("dialogue_lines", [])

        # Build a lookup of segment data by segment_id
        seg_by_id: dict[str, dict[str, Any]] = {
            str(s["segment_id"]): s for s in segments
        }

        # Build a lookup of dialogue lines by insert_after_segment
        dlg_by_after: dict[str, list[dict[str, Any]]] = {}
        for dlg in dialogue_lines:
            after = str(dlg.get("insert_after_segment", ""))
            dlg_by_after.setdefault(after, []).append(dlg)

        # Collect narration tracks from the timeline
        narration_tracks = [
            tr for tr in timeline.get("audio_tracks", [])
            if tr.get("track_type") == "narration"
        ]

        timing_segments: list[dict[str, Any]] = []

        for i, track in enumerate(narration_tracks):
            line_ref = str(track["line_ref"])
            start_s: float = float(track["start_s"])
            end_s: float = float(track["end_s"])

            seg_data = seg_by_id.get(line_ref, {})
            text_en = str(seg_data.get("text_en", ""))
            text_secondary = str(seg_data.get("text_secondary", ""))

            # Collect dialogue that follows this narration segment
            following_dlg = dlg_by_after.get(line_ref, [])
            dlg_en_parts: list[str] = []
            dlg_sec_parts: list[str] = []
            for dlg in following_dlg:
                dlg_en_parts.append(str(dlg.get("text_en", "")))
                dlg_sec_parts.append(str(dlg.get("text_secondary", "")))
            dialogue_en = " ".join(dlg_en_parts)
            dialogue_secondary = " ".join(dlg_sec_parts)

            img = _render_overlay(
                text_en,
                text_secondary,
                dialogue_en,
                dialogue_secondary,
                scene_id,
                seed,
                width,
                height,
            )

            # Derive PNG stem from out_timing so versioned reruns (_r1, _r2, …)
            # produce versioned PNGs and never overwrite the originals.
            # out_timing stem: "typography_<scene_id>[_rN]_timing" → strip "_timing"
            png_stem = out_timing.stem[: -len("_timing")]
            png_filename = f"{png_stem}_seg-{i}.png"
            png_path = out_dir / png_filename
            tmp_png = png_path.with_suffix(".png.tmp")
            img.save(str(tmp_png), format="PNG")
            tmp_png.replace(png_path)

            timing_segments.append({
                "seg_id": line_ref,
                "start_s": start_s,
                "end_s": end_s,
                "png": png_path.name,
                "text_en": text_en,
                "text_uk": text_secondary,
            })

        timing_manifest: dict[str, Any] = {
            "schema_version": "1.0",
            "scene_id": scene_id,
            "segments": timing_segments,
        }

        tmp_timing = out_timing.with_suffix(".json.tmp")
        tmp_timing.write_text(json.dumps(timing_manifest, indent=2))
        tmp_timing.replace(out_timing)

        return out_timing
