"""Stage 7.5: Timeline planner.

Pure function that converts script + sidecar metadata into a deterministic
Scene Timeline artifact (JSON). No FFmpeg, no media generation.

Timing rules
------------
* Narration segments play sequentially in script order, starting at 0.0 s.
* Dialogue lines are inserted after the narration segment named by
  ``insert_after_segment``.  The dialogue line plays *immediately* after
  that segment's end time.  No gap is added between a segment and its
  following dialogue.
* If ``insert_after_segment`` is ``None`` or references a segment_id not
  present in the script, the dialogue line is appended after all narration
  and any previously-placed dialogue (deterministic fallback: ordered by
  ``line_id``).
* Ambient audio starts at 0.0 and spans the full scene duration.
* Motion video starts at 0.0 and spans the full scene duration.
* Typography overlay starts at 0.0 and spans the full scene duration.
* Scene ``duration_s`` = max(motion_duration_s, audio_timeline_end_s,
  ambient_duration_s).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _pacing_s(pacing_ms: int) -> float:
    return pacing_ms / 1000.0


def _build_audio_sequence(
    script: dict[str, Any],
) -> list[tuple[str, str, float]]:
    """Return ordered list of (line_ref, track_type, duration_s).

    Dialogue lines are inserted after their ``insert_after_segment`` if
    valid; otherwise they are appended at the end in line_id order.
    """
    segments: list[dict[str, Any]] = script.get("segments", [])
    dialogue_lines: list[dict[str, Any]] = script.get("dialogue_lines", [])

    valid_segment_ids = {s["segment_id"] for s in segments}

    # group dialogue by insert point; None = fallback (append at end)
    insert_map: dict[str | None, list[dict[str, Any]]] = {}
    for dlg in sorted(dialogue_lines, key=lambda d: d["line_id"]):
        after = dlg.get("insert_after_segment")
        if after not in valid_segment_ids:
            after = None  # invalid → fallback
        insert_map.setdefault(after, []).append(dlg)

    result: list[tuple[str, str, float]] = []
    for seg in segments:
        result.append((
            seg["segment_id"],
            "narration",
            _pacing_s(seg["pacing_ms"]),
        ))
        for dlg in insert_map.get(seg["segment_id"], []):
            result.append((
                dlg["line_id"],
                "dialogue",
                _pacing_s(dlg["pacing_ms"]),
            ))

    # fallback dialogue (invalid / no insert_after_segment)
    for dlg in insert_map.get(None, []):
        result.append((
            dlg["line_id"],
            "dialogue",
            _pacing_s(dlg["pacing_ms"]),
        ))

    return result


def _index_voice_lines(voice_line_sidecar_paths: list[Path]) -> dict[str, str]:
    """Return {line_ref: output_path} from a list of voice-line sidecar files."""
    index: dict[str, str] = {}
    for p in voice_line_sidecar_paths:
        data = json.loads(p.read_text())
        index[str(data["line_ref"])] = str(data["output_path"])
    return index


def plan_timeline(
    script_path: Path,
    motion_sidecar_path: Path,
    ambient_sidecar_path: Path,
    typography_sidecar_path: Path,
    voice_line_sidecar_paths: list[Path],
    out_path: Path,
) -> Path:
    """Produce a timeline JSON artifact from sidecar metadata.

    Parameters
    ----------
    script_path:
        Path to the ``scripts/script_<scene_id>.json`` artifact.
    motion_sidecar_path:
        Path to the ``frames/motion_<scene_id>.json`` sidecar.
    ambient_sidecar_path:
        Path to the ``audio/ambient_<scene_id>.json`` sidecar.
    typography_sidecar_path:
        Path to the ``video/typography_<scene_id>.json`` sidecar.
    voice_line_sidecar_paths:
        Paths to all voice-line sidecar JSONs for this scene (both narration
        and dialogue).  Each sidecar's ``line_ref`` field is used to map the
        segment/dialogue id to its actual WAV ``output_path``.
    out_path:
        Destination for the timeline JSON file.

    Returns
    -------
    Path
        ``out_path`` after writing.

    Raises
    ------
    KeyError
        If a segment or dialogue ``line_ref`` has no corresponding voice-line
        sidecar in ``voice_line_sidecar_paths``.
    """
    script = json.loads(script_path.read_text())
    motion_sidecar = json.loads(motion_sidecar_path.read_text())
    ambient_sidecar = json.loads(ambient_sidecar_path.read_text())
    typography_sidecar = json.loads(typography_sidecar_path.read_text())

    story_id: str = script["story_id"]
    scene_id: str = script["scene_id"]
    fps: int = int(motion_sidecar["fps"])

    motion_duration_s: float = float(motion_sidecar["duration_s"])
    ambient_duration_s: float = float(ambient_sidecar["duration_s"])

    voice_line_index = _index_voice_lines(voice_line_sidecar_paths)

    # Build ordered audio sequence
    audio_sequence = _build_audio_sequence(script)

    audio_tracks: list[dict[str, Any]] = []
    cursor = 0.0
    for line_ref, track_type, dur in audio_sequence:
        if line_ref not in voice_line_index:
            raise KeyError(
                f"No voice-line sidecar found for {track_type} '{line_ref}' "
                f"in scene '{scene_id}'. Pass its sidecar in voice_line_sidecar_paths."
            )
        audio_tracks.append({
            "track_id": f"audio-{line_ref}",
            "track_type": track_type,
            "source_path": voice_line_index[line_ref],
            "start_s": round(cursor, 6),
            "end_s": round(cursor + dur, 6),
            "line_ref": line_ref,
        })
        cursor += dur

    audio_timeline_end_s = cursor

    scene_duration_s = max(motion_duration_s, audio_timeline_end_s, ambient_duration_s)

    # Ambient track spans full scene
    audio_tracks.append({
        "track_id": "audio-ambient",
        "track_type": "ambient",
        "source_path": ambient_sidecar["output_path"],
        "start_s": 0.0,
        "end_s": round(scene_duration_s, 6),
        "line_ref": "ambient",
    })

    video_tracks = [{
        "track_id": "video-motion",
        "source_path": motion_sidecar["output_path"],
        "start_s": 0.0,
        "end_s": round(scene_duration_s, 6),
    }]

    overlay_tracks = [{
        "track_id": "overlay-typography",
        "source_path": typography_sidecar["output_path"],
        "start_s": 0.0,
        "end_s": round(scene_duration_s, 6),
    }]

    timeline: dict[str, Any] = {
        "schema_version": "1.0",
        "story_id": story_id,
        "scene_id": scene_id,
        "duration_s": round(scene_duration_s, 6),
        "fps": fps,
        "sources": {
            "script": str(script_path),
            "motion_sidecar": str(motion_sidecar_path),
            "ambient_sidecar": str(ambient_sidecar_path),
            "typography_sidecar": str(typography_sidecar_path),
            "voice_line_sidecars": [str(p) for p in voice_line_sidecar_paths],
        },
        "video_tracks": video_tracks,
        "audio_tracks": audio_tracks,
        "overlay_tracks": overlay_tracks,
    }

    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(timeline, indent=2))
    tmp.replace(out_path)

    return out_path
