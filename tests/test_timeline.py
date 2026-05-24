"""Tests for the timeline planner (intermediate issue before #009)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from horror_story.pipeline.timeline import plan_timeline, _build_audio_sequence
from horror_story.schemas import validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _motion_sidecar(tmp_path: Path, scene_id: str, duration_s: float, fps: int = 24) -> Path:
    p = tmp_path / f"motion_{scene_id}.json"
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "story_id": "test-story",
        "scene_id": scene_id,
        "source_keyframe": f"frames/keyframe_{scene_id}.png",
        "duration_s": duration_s,
        "fps": fps,
        "effect": "none",
        "seed": 1,
        "adapter": "mock",
        "output_path": f"frames/motion_{scene_id}.mp4",
        "status": "generated",
    }
    p.write_text(json.dumps(data))
    return p


def _ambient_sidecar(tmp_path: Path, scene_id: str, duration_s: float) -> Path:
    p = tmp_path / f"ambient_{scene_id}.json"
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "story_id": "test-story",
        "scene_id": scene_id,
        "mood": "dread",
        "duration_s": duration_s,
        "seed": 1,
        "adapter": "mock",
        "output_path": f"audio/ambient_{scene_id}.wav",
        "actual_duration_s": duration_s,
        "status": "generated",
        "error": None,
    }
    p.write_text(json.dumps(data))
    return p


def _typography_sidecar(tmp_path: Path, scene_id: str, duration_s: float) -> Path:
    p = tmp_path / f"typography_{scene_id}.json"
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "story_id": "test-story",
        "scene_id": scene_id,
        "source_script": f"scripts/script_{scene_id}.json",
        "duration_s": duration_s,
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "seed": 1,
        "adapter": "mock",
        "output_path": f"video/typography_{scene_id}.png",
        "status": "generated",
        "error": None,
    }
    p.write_text(json.dumps(data))
    return p


def _voice_line_sidecar(
    tmp_path: Path,
    scene_id: str,
    line_ref: str,
    line_type: str,
    pacing_ms: int,
) -> Path:
    """Write a voice-line sidecar and return its path.

    The ``output_path`` value uses a predictable pattern:
    ``audio/<line_type>_<scene_id>_<line_ref>.wav`` so tests can assert on it.
    """
    wav_path = f"audio/{line_type}_{scene_id}_{line_ref}.wav"
    p = tmp_path / f"vl_{scene_id}_{line_ref}.json"
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "story_id": "test-story",
        "scene_id": scene_id,
        "line_ref": line_ref,
        "line_type": line_type,
        "text": f"text for {line_ref}",
        "language": "en",
        "voice_id": "narrator",
        "seed": 1,
        "pacing_ms": pacing_ms,
        "adapter": "mock",
        "output_path": wav_path,
        "actual_duration_ms": pacing_ms,
        "status": "synthesized",
        "error": None,
    }
    p.write_text(json.dumps(data))
    return p


def _script(
    tmp_path: Path,
    scene_id: str,
    segments: list[dict[str, Any]],
    dialogue_lines: list[dict[str, Any]] | None = None,
) -> Path:
    p = tmp_path / f"script_{scene_id}.json"
    dlg = dialogue_lines or []
    total_ms = sum(s["pacing_ms"] for s in segments) + sum(d["pacing_ms"] for d in dlg)
    data: dict[str, Any] = {
        "schema_version": "1.0",
        "story_id": "test-story",
        "scene_id": scene_id,
        "segments": segments,
        "dialogue_lines": dlg,
        "total_duration_ms": total_ms,
    }
    p.write_text(json.dumps(data))
    return p


def _seg(seg_id: str, pacing_ms: int) -> dict[str, Any]:
    return {
        "segment_id": seg_id,
        "text_en": f"narration text for {seg_id}",
        "text_secondary": "[uk] text",
        "pacing_ms": pacing_ms,
        "voice_id": "narrator",
    }


def _dlg(line_id: str, pacing_ms: int, insert_after: str | None) -> dict[str, Any]:
    return {
        "line_id": line_id,
        "character": "Ghost",
        "text_en": f"dialogue text for {line_id}",
        "text_secondary": "[uk] text",
        "pacing_ms": pacing_ms,
        "voice_id": "ghost-voice",
        "insert_after_segment": insert_after,
    }


def _vl_sidecars(
    tmp_path: Path,
    scene_id: str,
    segments: list[dict[str, Any]],
    dialogue_lines: list[dict[str, Any]] | None = None,
) -> list[Path]:
    """Build voice-line sidecars for all segments and dialogue lines."""
    sidecars: list[Path] = []
    for seg in segments:
        sidecars.append(
            _voice_line_sidecar(tmp_path, scene_id, seg["segment_id"], "narration", seg["pacing_ms"])
        )
    for dlg in (dialogue_lines or []):
        sidecars.append(
            _voice_line_sidecar(tmp_path, scene_id, dlg["line_id"], "dialogue", dlg["pacing_ms"])
        )
    return sidecars


# ---------------------------------------------------------------------------
# Narration-only scene
# ---------------------------------------------------------------------------


def test_narration_only_timeline(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 2000), _seg("seg-1", 3000)]
    s = _script(tmp_path, "s01", segs)
    m = _motion_sidecar(tmp_path, "s01", 5.0)
    a = _ambient_sidecar(tmp_path, "s01", 5.0)
    t = _typography_sidecar(tmp_path, "s01", 5.0)
    vl = _vl_sidecars(tmp_path, "s01", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    assert out.exists()
    data = json.loads(out.read_text())

    narration_tracks = [tr for tr in data["audio_tracks"] if tr["track_type"] == "narration"]
    assert len(narration_tracks) == 2

    # sequential: seg-0 at 0.0–2.0, seg-1 at 2.0–5.0
    seg0 = next(tr for tr in narration_tracks if tr["line_ref"] == "seg-0")
    seg1 = next(tr for tr in narration_tracks if tr["line_ref"] == "seg-1")
    assert seg0["start_s"] == pytest.approx(0.0)
    assert seg0["end_s"] == pytest.approx(2.0)
    assert seg1["start_s"] == pytest.approx(2.0)
    assert seg1["end_s"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Audio source_path correctness — the core contract
# ---------------------------------------------------------------------------


def test_narration_track_source_path_is_wav_not_mp4(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 2000), _seg("seg-1", 1000)]
    s = _script(tmp_path, "sp1", segs)
    m = _motion_sidecar(tmp_path, "sp1", 3.0)
    a = _ambient_sidecar(tmp_path, "sp1", 3.0)
    t = _typography_sidecar(tmp_path, "sp1", 3.0)
    vl = _vl_sidecars(tmp_path, "sp1", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())

    for track in data["audio_tracks"]:
        if track["track_type"] == "narration":
            assert track["source_path"].endswith(".wav"), (
                f"narration track '{track['track_id']}' source_path must be a WAV, "
                f"got: {track['source_path']!r}"
            )
            assert ".mp4" not in track["source_path"]


def test_dialogue_track_source_path_is_wav_not_mp4(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 2000)]
    dlgs = [_dlg("dlg-0", 1000, "seg-0")]
    s = _script(tmp_path, "sp2", segs, dlgs)
    m = _motion_sidecar(tmp_path, "sp2", 3.0)
    a = _ambient_sidecar(tmp_path, "sp2", 3.0)
    t = _typography_sidecar(tmp_path, "sp2", 3.0)
    vl = _vl_sidecars(tmp_path, "sp2", segs, dlgs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())

    for track in data["audio_tracks"]:
        if track["track_type"] == "dialogue":
            assert track["source_path"].endswith(".wav"), (
                f"dialogue track '{track['track_id']}' source_path must be a WAV, "
                f"got: {track['source_path']!r}"
            )
            assert ".mp4" not in track["source_path"]


def test_audio_source_paths_match_voice_line_sidecars(tmp_path: Path) -> None:
    """Each narration/dialogue track's source_path must equal the output_path from its sidecar."""
    segs = [_seg("seg-0", 2000), _seg("seg-1", 1500)]
    dlgs = [_dlg("dlg-0", 800, "seg-0")]
    s = _script(tmp_path, "sp3", segs, dlgs)
    m = _motion_sidecar(tmp_path, "sp3", 5.0)
    a = _ambient_sidecar(tmp_path, "sp3", 5.0)
    t = _typography_sidecar(tmp_path, "sp3", 5.0)
    vl = _vl_sidecars(tmp_path, "sp3", segs, dlgs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())

    # Build expected mapping from sidecars
    expected: dict[str, str] = {}
    for p in vl:
        sd = json.loads(p.read_text())
        expected[sd["line_ref"]] = sd["output_path"]

    for track in data["audio_tracks"]:
        if track["track_type"] in ("narration", "dialogue"):
            assert track["source_path"] == expected[track["line_ref"]], (
                f"track '{track['track_id']}': expected source_path "
                f"{expected[track['line_ref']]!r}, got {track['source_path']!r}"
            )


def test_missing_voice_line_sidecar_raises_key_error(tmp_path: Path) -> None:
    """plan_timeline must raise KeyError if a segment has no voice-line sidecar."""
    segs = [_seg("seg-0", 2000), _seg("seg-1", 1000)]
    s = _script(tmp_path, "sp4", segs)
    m = _motion_sidecar(tmp_path, "sp4", 3.0)
    a = _ambient_sidecar(tmp_path, "sp4", 3.0)
    t = _typography_sidecar(tmp_path, "sp4", 3.0)
    # Only provide sidecar for seg-0; seg-1 is missing
    vl = [_voice_line_sidecar(tmp_path, "sp4", "seg-0", "narration", 2000)]
    out = tmp_path / "timeline.json"

    with pytest.raises(KeyError, match="seg-1"):
        plan_timeline(s, m, a, t, vl, out)


# ---------------------------------------------------------------------------
# Narration + dialogue inserted after segment
# ---------------------------------------------------------------------------


def test_dialogue_inserted_after_segment(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 2000), _seg("seg-1", 2000)]
    dlgs = [_dlg("dlg-0", 1000, "seg-0")]
    s = _script(tmp_path, "s02", segs, dlgs)
    m = _motion_sidecar(tmp_path, "s02", 5.0)
    a = _ambient_sidecar(tmp_path, "s02", 5.0)
    t = _typography_sidecar(tmp_path, "s02", 5.0)
    vl = _vl_sidecars(tmp_path, "s02", segs, dlgs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    audio = data["audio_tracks"]

    # Expected order: seg-0 (0–2), dlg-0 (2–3), seg-1 (3–5)
    by_ref = {tr["line_ref"]: tr for tr in audio if tr["track_type"] != "ambient"}
    assert by_ref["seg-0"]["start_s"] == pytest.approx(0.0)
    assert by_ref["seg-0"]["end_s"] == pytest.approx(2.0)
    assert by_ref["dlg-0"]["start_s"] == pytest.approx(2.0)
    assert by_ref["dlg-0"]["end_s"] == pytest.approx(3.0)
    assert by_ref["seg-1"]["start_s"] == pytest.approx(3.0)
    assert by_ref["seg-1"]["end_s"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# Invalid insert_after_segment fallback
# ---------------------------------------------------------------------------


def test_invalid_insert_after_falls_back_to_end(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 2000)]
    dlgs = [_dlg("dlg-0", 1000, "seg-99")]  # seg-99 does not exist
    s = _script(tmp_path, "s03", segs, dlgs)
    m = _motion_sidecar(tmp_path, "s03", 3.0)
    a = _ambient_sidecar(tmp_path, "s03", 3.0)
    t = _typography_sidecar(tmp_path, "s03", 3.0)
    vl = _vl_sidecars(tmp_path, "s03", segs, dlgs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    by_ref = {tr["line_ref"]: tr for tr in data["audio_tracks"] if tr["track_type"] != "ambient"}

    # seg-0: 0–2, dlg-0 appended: 2–3
    assert by_ref["seg-0"]["end_s"] == pytest.approx(2.0)
    assert by_ref["dlg-0"]["start_s"] == pytest.approx(2.0)
    assert by_ref["dlg-0"]["end_s"] == pytest.approx(3.0)


def test_null_insert_after_falls_back_to_end(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 2000)]
    dlgs = [_dlg("dlg-0", 1500, None)]
    s = _script(tmp_path, "s04", segs, dlgs)
    m = _motion_sidecar(tmp_path, "s04", 4.0)
    a = _ambient_sidecar(tmp_path, "s04", 4.0)
    t = _typography_sidecar(tmp_path, "s04", 4.0)
    vl = _vl_sidecars(tmp_path, "s04", segs, dlgs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    by_ref = {tr["line_ref"]: tr for tr in data["audio_tracks"] if tr["track_type"] != "ambient"}

    assert by_ref["dlg-0"]["start_s"] == pytest.approx(2.0)
    assert by_ref["dlg-0"]["end_s"] == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# Ambient spans full scene
# ---------------------------------------------------------------------------


def test_ambient_spans_full_scene(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 3000)]
    s = _script(tmp_path, "s05", segs)
    m = _motion_sidecar(tmp_path, "s05", 3.0)
    a = _ambient_sidecar(tmp_path, "s05", 3.0)
    t = _typography_sidecar(tmp_path, "s05", 3.0)
    vl = _vl_sidecars(tmp_path, "s05", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    ambient = next(tr for tr in data["audio_tracks"] if tr["track_type"] == "ambient")
    assert ambient["start_s"] == pytest.approx(0.0)
    assert ambient["end_s"] == pytest.approx(data["duration_s"])


# ---------------------------------------------------------------------------
# Typography spans full scene
# ---------------------------------------------------------------------------


def test_typography_spans_full_scene(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 2000)]
    s = _script(tmp_path, "s06", segs)
    m = _motion_sidecar(tmp_path, "s06", 2.0)
    a = _ambient_sidecar(tmp_path, "s06", 2.0)
    t = _typography_sidecar(tmp_path, "s06", 2.0)
    vl = _vl_sidecars(tmp_path, "s06", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    assert len(data["overlay_tracks"]) == 1
    overlay = data["overlay_tracks"][0]
    assert overlay["start_s"] == pytest.approx(0.0)
    assert overlay["end_s"] == pytest.approx(data["duration_s"])


# ---------------------------------------------------------------------------
# Motion spans full scene
# ---------------------------------------------------------------------------


def test_motion_spans_full_scene(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 4000)]
    s = _script(tmp_path, "s07", segs)
    m = _motion_sidecar(tmp_path, "s07", 4.0)
    a = _ambient_sidecar(tmp_path, "s07", 4.0)
    t = _typography_sidecar(tmp_path, "s07", 4.0)
    vl = _vl_sidecars(tmp_path, "s07", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    assert len(data["video_tracks"]) == 1
    video = data["video_tracks"][0]
    assert video["start_s"] == pytest.approx(0.0)
    assert video["end_s"] == pytest.approx(data["duration_s"])


# ---------------------------------------------------------------------------
# Scene duration = max of all tracks
# ---------------------------------------------------------------------------


def test_duration_is_max_of_all_tracks_motion_longest(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 1000)]  # audio timeline = 1.0 s
    s = _script(tmp_path, "s08", segs)
    m = _motion_sidecar(tmp_path, "s08", 10.0)  # motion = 10 s
    a = _ambient_sidecar(tmp_path, "s08", 5.0)   # ambient = 5 s
    t = _typography_sidecar(tmp_path, "s08", 5.0)
    vl = _vl_sidecars(tmp_path, "s08", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    assert data["duration_s"] == pytest.approx(10.0)


def test_duration_is_max_of_all_tracks_audio_longest(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 8000)]  # audio timeline = 8.0 s
    s = _script(tmp_path, "s09", segs)
    m = _motion_sidecar(tmp_path, "s09", 3.0)   # motion = 3 s
    a = _ambient_sidecar(tmp_path, "s09", 2.0)  # ambient = 2 s
    t = _typography_sidecar(tmp_path, "s09", 3.0)
    vl = _vl_sidecars(tmp_path, "s09", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    assert data["duration_s"] == pytest.approx(8.0)


def test_duration_is_max_of_all_tracks_ambient_longest(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 1000)]  # audio timeline = 1.0 s
    s = _script(tmp_path, "s10", segs)
    m = _motion_sidecar(tmp_path, "s10", 3.0)    # motion = 3 s
    a = _ambient_sidecar(tmp_path, "s10", 12.0)  # ambient = 12 s
    t = _typography_sidecar(tmp_path, "s10", 12.0)
    vl = _vl_sidecars(tmp_path, "s10", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    assert data["duration_s"] == pytest.approx(12.0)


# ---------------------------------------------------------------------------
# Deterministic ordering and content
# ---------------------------------------------------------------------------


def test_deterministic_output_same_inputs(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 2000), _seg("seg-1", 1500)]
    dlgs = [_dlg("dlg-0", 1000, "seg-0")]

    def make_timeline(subdir: str) -> dict[str, Any]:
        d = tmp_path / subdir
        d.mkdir(exist_ok=True)
        s = _script(d, "sdet", segs, dlgs)
        m = _motion_sidecar(d, "sdet", 5.0)
        amb = _ambient_sidecar(d, "sdet", 5.0)
        typ = _typography_sidecar(d, "sdet", 5.0)
        vl = _vl_sidecars(d, "sdet", segs, dlgs)
        out = d / "timeline.json"
        plan_timeline(s, m, amb, typ, vl, out)
        return json.loads(out.read_text())

    d1 = make_timeline("run1")
    d2 = make_timeline("run2")

    # Compare track ordering and timing (paths differ due to tmp dirs)
    for key in ("duration_s", "fps", "scene_id", "story_id"):
        assert d1[key] == d2[key]
    for tracks_key in ("video_tracks", "audio_tracks", "overlay_tracks"):
        assert len(d1[tracks_key]) == len(d2[tracks_key])
        for t1, t2 in zip(d1[tracks_key], d2[tracks_key]):
            assert t1["track_id"] == t2["track_id"]
            assert t1["start_s"] == t2["start_s"]
            assert t1["end_s"] == t2["end_s"]


def test_audio_track_ids_are_unique(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 1000), _seg("seg-1", 1000)]
    dlgs = [_dlg("dlg-0", 500, "seg-0"), _dlg("dlg-1", 500, "seg-1")]
    s = _script(tmp_path, "suid", segs, dlgs)
    m = _motion_sidecar(tmp_path, "suid", 4.0)
    a = _ambient_sidecar(tmp_path, "suid", 4.0)
    t = _typography_sidecar(tmp_path, "suid", 4.0)
    vl = _vl_sidecars(tmp_path, "suid", segs, dlgs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    ids = [tr["track_id"] for tr in data["audio_tracks"]]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_timeline_schema_valid_narration_only(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 3000), _seg("seg-1", 2000)]
    s = _script(tmp_path, "sv1", segs)
    m = _motion_sidecar(tmp_path, "sv1", 5.0)
    a = _ambient_sidecar(tmp_path, "sv1", 5.0)
    t = _typography_sidecar(tmp_path, "sv1", 5.0)
    vl = _vl_sidecars(tmp_path, "sv1", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    validate(data, "timeline.schema.json")


def test_timeline_schema_valid_with_dialogue(tmp_path: Path) -> None:
    segs = [_seg("seg-0", 2000), _seg("seg-1", 1000)]
    dlgs = [_dlg("dlg-0", 800, "seg-0")]
    s = _script(tmp_path, "sv2", segs, dlgs)
    m = _motion_sidecar(tmp_path, "sv2", 4.0)
    a = _ambient_sidecar(tmp_path, "sv2", 4.0)
    t = _typography_sidecar(tmp_path, "sv2", 4.0)
    vl = _vl_sidecars(tmp_path, "sv2", segs, dlgs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    data = json.loads(out.read_text())
    validate(data, "timeline.schema.json")


# ---------------------------------------------------------------------------
# No FFmpeg required — guard test
# ---------------------------------------------------------------------------


def test_plan_timeline_does_not_use_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure plan_timeline never calls subprocess/shutil to invoke ffmpeg."""
    import subprocess
    import shutil

    original_run = subprocess.run
    original_which = shutil.which
    ffmpeg_called: list[str] = []

    def patched_run(args: Any, **kwargs: Any) -> Any:
        if isinstance(args, (list, tuple)) and args and "ffmpeg" in str(args[0]):
            ffmpeg_called.append(str(args))
        return original_run(args, **kwargs)

    def patched_which(name: str, **kwargs: Any) -> Any:
        if "ffmpeg" in name:
            ffmpeg_called.append(f"shutil.which({name})")
        return original_which(name, **kwargs)

    monkeypatch.setattr(subprocess, "run", patched_run)
    monkeypatch.setattr(shutil, "which", patched_which)

    segs = [_seg("seg-0", 2000)]
    s = _script(tmp_path, "sff", segs)
    m = _motion_sidecar(tmp_path, "sff", 2.0)
    a = _ambient_sidecar(tmp_path, "sff", 2.0)
    t = _typography_sidecar(tmp_path, "sff", 2.0)
    vl = _vl_sidecars(tmp_path, "sff", segs)
    out = tmp_path / "timeline.json"

    plan_timeline(s, m, a, t, vl, out)
    assert ffmpeg_called == [], f"FFmpeg was invoked unexpectedly: {ffmpeg_called}"


# ---------------------------------------------------------------------------
# _build_audio_sequence unit tests
# ---------------------------------------------------------------------------


def test_build_audio_sequence_empty_script() -> None:
    script: dict[str, Any] = {
        "segments": [],
        "dialogue_lines": [],
    }
    result = _build_audio_sequence(script)
    assert result == []


def test_build_audio_sequence_narration_order() -> None:
    script: dict[str, Any] = {
        "segments": [_seg("seg-0", 1000), _seg("seg-1", 2000)],
        "dialogue_lines": [],
    }
    result = _build_audio_sequence(script)
    assert [r[0] for r in result] == ["seg-0", "seg-1"]
    assert all(r[1] == "narration" for r in result)


def test_build_audio_sequence_dialogue_insertion() -> None:
    script: dict[str, Any] = {
        "segments": [_seg("seg-0", 1000), _seg("seg-1", 1000)],
        "dialogue_lines": [_dlg("dlg-0", 500, "seg-0")],
    }
    result = _build_audio_sequence(script)
    refs = [r[0] for r in result]
    assert refs == ["seg-0", "dlg-0", "seg-1"]
