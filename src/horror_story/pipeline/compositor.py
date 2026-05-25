"""Stage 8: Scene compositor.

Combines the motion video, ambient audio, narration/dialogue WAVs, and
per-segment typography PNG overlays into a single H.264/AAC scene MP4
using FFmpeg.

FFmpeg is the *only* component in this stage. All timing is driven by
the timeline artifact written by Stage 7.5 (for audio) and the typography
timing manifest written by Stage 7 (for per-segment text overlays).

Audio mixing strategy
---------------------
Every audio track is delayed to its absolute ``start_s`` offset via the
``adelay`` filter, then all tracks are combined with ``amix``.  The
ambient track spans the full duration; narration and dialogue tracks are
silent elsewhere.

Video compositing
-----------------
Each typography segment PNG (RGBA) is composited onto the motion video
with the ``overlay`` filter using a time-gated ``enable`` expression and
a 0.15-second fade-in/fade-out alpha.

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

_FADE = 0.15  # fade-in / fade-out duration in seconds


class FFmpegNotFoundError(RuntimeError):
    """Raised when FFmpeg is absent from $PATH."""


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def compose_scene(
    timeline_path: Path,
    timing_path: Path,
    out_path: Path,
) -> Path:
    """Compose a scene MP4 from the timeline artifact and typography timing manifest.

    Parameters
    ----------
    timeline_path:
        Path to ``video/timeline_<scene_id>.json`` (Stage 7.5 output).
    timing_path:
        Path to ``video/typography_<scene_id>_timing.json`` (Stage 7 output).
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
        If any artifact referenced in the timeline or timing manifest is missing.
    """
    if not ffmpeg_available():
        raise FFmpegNotFoundError("ffmpeg not found in $PATH")

    timeline: dict[str, Any] = json.loads(timeline_path.read_text())

    scene_id: str = timeline["scene_id"]
    story_id: str = timeline["story_id"]
    duration_s: float = float(timeline["duration_s"])

    video_tracks: list[dict[str, Any]] = timeline["video_tracks"]
    audio_tracks: list[dict[str, Any]] = timeline["audio_tracks"]

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

    # Resolve per-segment PNGs from the timing manifest
    timing: dict[str, Any] = json.loads(timing_path.read_text())
    timing_dir = timing_path.parent
    seg_entries: list[dict[str, Any]] = timing["segments"]
    seg_pngs: list[Path] = []
    for entry in seg_entries:
        png_path = (timing_dir / entry["png"]).resolve()
        if not png_path.exists():
            raise FileNotFoundError(f"Segment PNG not found: {png_path}")
        seg_pngs.append(png_path)

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
    #   1..N: segment PNGs (one per timing segment)
    #   N+1...: audio tracks (narration, dialogue, ambient — each with delay)
    cmd: list[str] = ["ffmpeg", "-y"]

    # Video inputs
    cmd += ["-i", str(motion_path)]
    for seg_png in seg_pngs:
        # -loop 1 makes FFmpeg generate frames continuously so fade/overlay
        # filters see a proper advancing PTS instead of a single frame at t=0.
        cmd += ["-loop", "1", "-i", str(seg_png)]

    # Audio inputs with their start offsets
    n_segments = len(seg_pngs)
    audio_input_indices: list[tuple[int, float]] = []
    base_input_idx = 1 + n_segments
    for track in audio_tracks:
        wav_path = _resolve(track["source_path"])
        cmd += ["-i", str(wav_path)]
        audio_input_indices.append((base_input_idx, float(track["start_s"])))
        base_input_idx += 1

    n_audio = len(audio_input_indices)

    # Filter graph ----------------------------------------------------------
    # Step 1: Build per-segment overlay chain for video.
    # Step 2: adelay each audio input to its absolute start offset (ms).
    # Step 3: amix all delayed streams.

    filter_parts: list[str] = []

    # Video overlay chain: fade each PNG then overlay with enable window.
    # Step 1: apply fade-in and fade-out to each PNG stream.
    # Step 2: chain overlay filters so each PNG appears only in its time window.
    prev_label = "[0:v]"
    for i, (entry, _png_path) in enumerate(zip(seg_entries, seg_pngs)):
        start_s: float = float(entry["start_s"])
        end_s: float = float(entry["end_s"])
        seg_dur = end_s - start_s
        fade_out_start = end_s - _FADE
        png_input_idx = 1 + i
        is_last = i == n_segments - 1
        faded_label = f"[faded{i}]"
        out_label = "[vout]" if is_last else f"[tmp{i}]"

        # Apply fade-in at start_s and fade-out at end_s - _FADE.
        # alpha=1 preserves the alpha channel of the RGBA PNG.
        fade_in_filter = (
            f"[{png_input_idx}:v]"
            f"fade=t=in:st={start_s}:d={_FADE}:alpha=1,"
            f"fade=t=out:st={fade_out_start}:d={_FADE}:alpha=1"
            f"{faded_label}"
        )
        filter_parts.append(fade_in_filter)

        enable = f"between(t,{start_s},{end_s})"
        overlay_filter = (
            f"{prev_label}{faded_label}"
            f"overlay=enable='{enable}':format=auto{out_label}"
        )
        filter_parts.append(overlay_filter)
        prev_label = out_label

    # Audio: adelay + aformat (stereo upmix) for each audio input
    stereo_labels: list[str] = []
    for i, (input_idx, start_s_audio) in enumerate(audio_input_indices):
        delay_ms = int(round(start_s_audio * 1000))
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
            "typography": _rel_to_run(timing_path),
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
