"""Stage 8: Scene compositor.

Combines the motion video, ambient audio, narration/dialogue WAVs, and
typography PNG overlay into a single H.264/AAC scene MP4 using FFmpeg.

FFmpeg is the *only* component in this stage. All timing is driven by
the timeline artifact written by Stage 7.5.

Audio mixing strategy
---------------------
Every audio track is delayed to its absolute ``start_s`` offset via the
``adelay`` filter, then all tracks are combined with ``amix``.  The
ambient track spans the full duration; narration and dialogue tracks are
silent elsewhere.

Video compositing
-----------------
The typography PNG (RGBA) is composited onto the motion video with the
``overlay`` filter using alpha blending (``format=auto``).

Duration
--------
The compositor passes ``-t <duration_s>`` to honour the scene duration
from the timeline.  This avoids ``-shortest`` drift when the ambient WAV
is slightly longer than the audio sequence end.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FFmpegNotFoundError(RuntimeError):
    """Raised when FFmpeg is absent from $PATH."""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def compose_scene(
    timeline_path: Path,
    out_path: Path,
) -> Path:
    """Compose a scene MP4 from the timeline artifact.

    Parameters
    ----------
    timeline_path:
        Path to ``video/timeline_<scene_id>.json`` (Stage 7.5 output).
    out_path:
        Destination for ``video/scene_<scene_id>_composed.mp4``.

    Returns
    -------
    Path
        ``out_path`` after a successful FFmpeg run.

    Raises
    ------
    FFmpegNotFoundError
        If FFmpeg is absent from ``$PATH``.
    subprocess.CalledProcessError
        If FFmpeg exits non-zero.
    FileNotFoundError
        If any artifact referenced in the timeline is missing.
    """
    if not ffmpeg_available():
        raise FFmpegNotFoundError("ffmpeg not found in $PATH")

    timeline: dict[str, Any] = json.loads(timeline_path.read_text())

    scene_id: str = timeline["scene_id"]
    story_id: str = timeline["story_id"]
    duration_s: float = float(timeline["duration_s"])

    video_tracks: list[dict[str, Any]] = timeline["video_tracks"]
    audio_tracks: list[dict[str, Any]] = timeline["audio_tracks"]
    overlay_tracks: list[dict[str, Any]] = timeline["overlay_tracks"]

    # Resolve paths relative to the timeline file's directory when needed.
    timeline_dir = timeline_path.parent

    def _resolve(p: str) -> Path:
        resolved = Path(p)
        if not resolved.is_absolute():
            resolved = (timeline_dir / resolved).resolve()
        if not resolved.exists():
            # try relative to CWD as a second fallback
            cwd_rel = Path.cwd() / p
            if cwd_rel.exists():
                return cwd_rel
            raise FileNotFoundError(
                f"Artifact not found for scene '{scene_id}': {p!r}"
            )
        return resolved

    motion_path = _resolve(video_tracks[0]["source_path"])
    overlay_path = _resolve(overlay_tracks[0]["source_path"])

    narration_wavs: list[str] = []
    dialogue_wavs: list[str] = []
    for track in audio_tracks:
        if track["track_type"] in ("narration", "dialogue"):
            if track["track_type"] == "narration":
                narration_wavs.append(str(_resolve(track["source_path"])))
            else:
                dialogue_wavs.append(str(_resolve(track["source_path"])))

    # Build FFmpeg command ------------------------------------------------
    # Input ordering:
    #   0: motion video (no audio)
    #   1: overlay PNG
    #   2..N: audio tracks (narration, dialogue, ambient — each with delay)
    cmd: list[str] = ["ffmpeg", "-y"]

    # Video inputs
    cmd += ["-i", str(motion_path)]
    cmd += ["-i", str(overlay_path)]

    # Audio inputs with their start offsets
    audio_input_indices: list[tuple[int, float]] = []
    base_input_idx = 2
    for track in audio_tracks:
        wav_path = _resolve(track["source_path"])
        cmd += ["-i", str(wav_path)]
        audio_input_indices.append((base_input_idx, float(track["start_s"])))
        base_input_idx += 1

    n_audio = len(audio_input_indices)

    # Filter graph ----------------------------------------------------------
    # Step 1: adelay each audio input to its absolute start offset (ms).
    # Step 2: amix all delayed streams.
    # Step 3: overlay the typography PNG (RGBA) onto the motion video.

    filter_parts: list[str] = []

    stereo_labels: list[str] = []
    for i, (input_idx, start_s) in enumerate(audio_input_indices):
        delay_ms = int(round(start_s * 1000))
        del_label = f"[adel{i}]"
        ster_label = f"[aster{i}]"
        # adelay: all_channels=1 handles both mono and stereo inputs uniformly
        filter_parts.append(
            f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}:all=1{del_label}"
        )
        # upmix each (possibly mono) delayed stream to stereo before mixing
        filter_parts.append(
            f"{del_label}aformat=channel_layouts=stereo{ster_label}"
        )
        stereo_labels.append(ster_label)

    # amix: normalise=0 to avoid volume reduction, dropout_transition=0 for clean cutoff
    stereo_concat = "".join(stereo_labels)
    filter_parts.append(
        f"{stereo_concat}amix=inputs={n_audio}:normalize=0:dropout_transition=0[amixed]"
    )

    # overlay: alpha-composite typography PNG onto motion video
    filter_parts.append(
        "[0:v][1:v]overlay=format=auto[vout]"
    )

    filter_graph = "; ".join(filter_parts)

    cmd += ["-filter_complex", filter_graph]
    cmd += ["-map", "[vout]"]
    cmd += ["-map", "[amixed]"]

    # Encoding parameters
    cmd += ["-t", str(duration_s)]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-ac", "2"]
    cmd += ["-movflags", "+faststart"]
    cmd += ["-fflags", "+bitexact"]

    tmp = out_path.with_name(out_path.stem + ".tmp.mp4")
    cmd.append(str(tmp))

    logger.debug("FFmpeg command: %s", " ".join(cmd))

    subprocess.run(cmd, check=True, capture_output=True)
    tmp.replace(out_path)

    # Write sidecar ---------------------------------------------------------
    # Paths are stored relative to the run root (parent of video/).
    run_root = out_path.parent.parent

    def _rel_to_run(p: Path) -> str:
        try:
            return str(p.relative_to(run_root))
        except ValueError:
            return p.name

    ambient_path = _resolve(
        next(t["source_path"] for t in audio_tracks if t["track_type"] == "ambient")
    )
    sidecar: dict[str, Any] = {
        "schema_version": "1.0",
        "story_id": story_id,
        "scene_id": scene_id,
        "inputs": {
            "motion": _rel_to_run(motion_path),
            "ambient": _rel_to_run(ambient_path),
            "typography": _rel_to_run(overlay_path),
            "narration_wavs": [_rel_to_run(Path(p)) for p in narration_wavs],
            "dialogue_wavs": [_rel_to_run(Path(p)) for p in dialogue_wavs],
        },
        "duration_ms": int(round(duration_s * 1000)),
        "output_path": _rel_to_run(out_path),
        "status": "composed",
        "error": None,
    }
    sidecar_path = out_path.with_suffix(".json")
    tmp_sidecar = sidecar_path.with_suffix(".json.tmp")
    tmp_sidecar.write_text(json.dumps(sidecar, indent=2))
    tmp_sidecar.replace(sidecar_path)

    return out_path
