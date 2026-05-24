from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

from horror_story.adapters.motion.base import MotionAdapter

logger = logging.getLogger(__name__)


class FFmpegNotFoundError(RuntimeError):
    """Raised when FFmpeg is absent from $PATH."""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


class MockMotionAdapter(MotionAdapter):
    def animate(
        self,
        frame_path: Path,
        duration_s: float,
        fps: int,
        effect: str,
        seed: int,
        out_path: Path,
        *,
        story_id: str = "",
        scene_id: str = "",
    ) -> Path:
        if not ffmpeg_available():
            raise FFmpegNotFoundError("ffmpeg not found in $PATH")

        tmp = out_path.with_name(out_path.stem + ".tmp.mp4")
        cmd = [
            "ffmpeg",
            "-fflags", "+bitexact",
            "-loop", "1",
            "-t", str(duration_s),
            "-r", str(fps),
            "-i", str(frame_path),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-f", "mp4",
            "-y",
            str(tmp),
        ]
        logger.debug("FFmpeg command: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True)
        tmp.replace(out_path)

        width: int | None = None
        height: int | None = None
        try:
            from PIL import Image
            with Image.open(frame_path) as img:
                width, height = img.size
        except Exception:
            pass

        rel_frame = str(
            frame_path.relative_to(Path.cwd())
            if frame_path.is_absolute() and frame_path.is_relative_to(Path.cwd())
            else frame_path
        )
        sidecar: dict[str, object] = {
            "schema_version": "1.0",
            "story_id": story_id or "unknown",
            "scene_id": scene_id or "unknown",
            "source_keyframe": rel_frame,
            "duration_s": duration_s,
            "fps": fps,
            "effect": effect,
            "seed": seed,
            "adapter": "mock",
            "output_path": out_path.name,
            "status": "generated",
            "error": None,
        }
        if width is not None:
            sidecar["width"] = width
        if height is not None:
            sidecar["height"] = height

        sidecar_path = out_path.with_suffix(".json")
        tmp_sidecar = sidecar_path.with_suffix(".json.tmp")
        tmp_sidecar.write_text(json.dumps(sidecar, indent=2))
        tmp_sidecar.replace(sidecar_path)

        return out_path
