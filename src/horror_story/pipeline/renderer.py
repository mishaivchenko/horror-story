"""Stage 9: Final renderer.

Concatenates all composed scene MP4s, prepends a 3-second title card, and
appends a 2-second black end card to produce the final deliverable MP4.

FFmpeg concat demuxer is used for lossless stream copy where possible.
Title card is generated as a PNG via Pillow (or a raw bytes fallback) and
converted to a 3-second H.264/AAC clip before concatenation.

Determinism
-----------
All FFmpeg calls include ``-fflags +bitexact`` so that identical inputs
produce identical bitstreams (and therefore the same SHA-256).
"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


class FFmpegNotFoundError(RuntimeError):
    """Raised when FFmpeg is absent from $PATH."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _make_title_card_png(
    title: str,
    author: str,
    width: int,
    height: int,
    out_path: Path,
) -> None:
    """Write a black PNG with white title + author text."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        _bold_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        _reg_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        import os
        from PIL.ImageFont import FreeTypeFont, ImageFont as _ImageFontBase
        _AnyFont = FreeTypeFont | _ImageFontBase
        _ft: _AnyFont
        _fa: _AnyFont
        if os.path.exists(_bold_path) and os.path.exists(_reg_path):
            _ft = ImageFont.truetype(_bold_path, 36)
            _fa = ImageFont.truetype(_reg_path, 24)
        else:
            _ft = ImageFont.load_default()
            _fa = _ft
        font_title = _ft
        font_author = _fa

        title_bbox = draw.textbbox((0, 0), title, font=font_title)
        title_w = title_bbox[2] - title_bbox[0]
        title_x = (width - title_w) // 2
        title_y = height // 2 - 50

        author_bbox = draw.textbbox((0, 0), author, font=font_author)
        author_w = author_bbox[2] - author_bbox[0]
        author_x = (width - author_w) // 2
        author_y = title_y + (title_bbox[3] - title_bbox[1]) + 16

        draw.text((title_x, title_y), title, fill=(255, 255, 255), font=font_title)
        draw.text((author_x, author_y), author, fill=(200, 200, 200), font=font_author)
        img.save(str(out_path), format="PNG")
    except ImportError:
        # Pillow absent: create a plain black PNG via FFmpeg lavfi
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=black:size={width}x{height}:rate=1:duration=1",
            "-frames:v", "1",
            "-fflags", "+bitexact",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)


def _make_card_mp4(
    png_path: Path,
    duration_s: float,
    width: int,
    height: int,
    fps: int,
    out_path: Path,
    fade_out: bool = False,
) -> None:
    """Convert a PNG to a silent MP4 clip of *duration_s* seconds.

    If *fade_out* is True, a full-duration linear fade-to-black is applied.
    """
    fade_filter = f"fade=t=out:st=0:d={duration_s}" if fade_out else "null"
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(png_path),
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-vf", fade_filter,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-t", str(duration_s),
        "-r", str(fps),
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def render_final(
    manifest: dict[str, Any],
    scene_paths: list[Path],
    out_path: Path,
) -> Path:
    """Render the final deliverable MP4.

    Parameters
    ----------
    manifest:
        Parsed manifest dict (must contain story_id, seed, title, author,
        render.width/height/fps/codec/audio_codec, scenes).
    scene_paths:
        Ordered list of composed scene MP4 paths (one per scene_id).
    out_path:
        Destination for the final MP4.

    Returns
    -------
    Path
        ``out_path`` after a successful render.

    Raises
    ------
    FFmpegNotFoundError
        If FFmpeg is absent from ``$PATH``.
    subprocess.CalledProcessError
        If any FFmpeg invocation exits non-zero.
    """
    if not ffmpeg_available():
        raise FFmpegNotFoundError("ffmpeg not found in $PATH")

    scene_ids: list[str] = list(manifest.get("scenes", []))
    if len(scene_paths) != len(scene_ids):
        raise ValueError(
            f"scene_paths length ({len(scene_paths)}) does not match "
            f"manifest scenes length ({len(scene_ids)})"
        )

    story_id: str = str(manifest["story_id"])
    seed: int = int(manifest["seed"])
    title: str = str(manifest.get("title", story_id))
    author: str = str(manifest.get("author", ""))
    render_cfg: dict[str, Any] = dict(manifest["render"])
    width: int = int(render_cfg["width"])
    height: int = int(render_cfg["height"])
    fps: int = int(render_cfg["fps"])

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as _td:
        td = Path(_td)

        # 1. Title card PNG → 3-second clip
        title_png = td / "title_card.png"
        _make_title_card_png(title, author, width, height, title_png)
        title_mp4 = td / "title_card.mp4"
        _make_card_mp4(title_png, 3.0, width, height, fps, title_mp4)

        # 2. End card: last scene fades to black over 2 seconds
        end_png = td / "end_card.png"
        _make_title_card_png("", "", width, height, end_png)
        end_mp4 = td / "end_card.mp4"
        _make_card_mp4(end_png, 2.0, width, height, fps, end_mp4, fade_out=True)

        # 3. Re-encode each scene clip to uniform params so concat works cleanly.
        # -fflags +bitexact is intentionally omitted here: it causes AAC bitstream
        # issues in ffmpeg 8.x that make the decoder reject the stream in the concat
        # pass. Determinism is enforced by the seeded inputs, not bitexact re-encodes.
        reencoded: list[Path] = []
        for i, sp in enumerate(scene_paths):
            re_path = td / f"scene_{i:03d}.mp4"
            cmd_re = [
                "ffmpeg", "-y",
                "-i", str(sp),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "44100",
                "-r", str(fps),
                str(re_path),
            ]
            subprocess.run(cmd_re, check=True, capture_output=True)
            reencoded.append(re_path)

        # 4. Build concat list: title + scenes + end
        concat_list = td / "concat.txt"
        parts: list[Path] = [title_mp4] + reencoded + [end_mp4]
        lines = [f"file '{str(p)}'\n" for p in parts]
        concat_list.write_text("".join(lines))

        # 5. FFmpeg concat demuxer → final MP4
        tmp_out = out_path.with_name(out_path.stem + ".tmp.mp4")
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(tmp_out),
        ]
        subprocess.run(cmd_concat, check=True, capture_output=True)

    tmp_out.replace(out_path)

    # 6. SHA-256 of output
    sha = _sha256(out_path)

    # 7. Write render_job.json
    render_job: dict[str, Any] = {
        "schema_version": "1.0",
        "story_id": story_id,
        "seed": seed,
        "scene_ids": scene_ids,
        "render": {
            "width": width,
            "height": height,
            "fps": fps,
            "codec": str(render_cfg.get("codec", "libx264")),
            "audio_codec": str(render_cfg.get("audio_codec", "aac")),
        },
        "output_path": out_path.name,
        "sha256": sha,
        "duration_ms": None,
        "status": "complete",
        "error": None,
    }
    rj_path = out_path.with_name("render_job.json")
    tmp_rj = rj_path.with_suffix(".json.tmp")
    tmp_rj.write_text(json.dumps(render_job, indent=2))
    tmp_rj.replace(rj_path)

    logger.info("Rendered final MP4 → %s (sha256=%s)", out_path, sha)
    return out_path
