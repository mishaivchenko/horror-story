"""Tests for Issue #023 — Per-segment typography adapter."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from horror_story.adapters import AdapterFactory
from horror_story.adapters.typography.base import TypographyAdapter
from horror_story.adapters.typography.mock import MockTypographyAdapter
from horror_story.schemas import validate

# ---------------------------------------------------------------------------
# Script fixtures
# ---------------------------------------------------------------------------

_SCRIPT_MINIMAL = {
    "schema_version": "1.0",
    "story_id": "pigeons-from-hell",
    "scene_id": "scene-01",
    "segments": [
        {
            "segment_id": "seg-0",
            "text_en": "The house loomed against the storm-grey sky.",
            "text_secondary": "[uk] sky grey storm the against loomed house The",
            "pacing_ms": 2000,
            "voice_id": "en-narrator-01",
        }
    ],
    "dialogue_lines": [],
    "total_duration_ms": 2000,
}

_SCRIPT_WITH_DIALOGUE = {
    "schema_version": "1.0",
    "story_id": "pigeons-from-hell",
    "scene_id": "scene-02",
    "segments": [
        {
            "segment_id": "seg-0",
            "text_en": "A door creaked in the darkness.",
            "text_secondary": "[uk] darkness the in creaked door A",
            "pacing_ms": 1500,
            "voice_id": "en-narrator-01",
        }
    ],
    "dialogue_lines": [
        {
            "line_id": "dlg-0",
            "character": "Branner",
            "text_en": "Something evil walks these halls.",
            "text_secondary": "[uk] halls these walks evil Something",
            "pacing_ms": 1000,
            "voice_id": "en-male-deep",
            "insert_after_segment": "seg-0",
        }
    ],
    "total_duration_ms": 2500,
}

_SCRIPT_THREE_SEGMENTS = {
    "schema_version": "1.0",
    "story_id": "pigeons-from-hell",
    "scene_id": "scene-03",
    "segments": [
        {
            "segment_id": "seg-0",
            "text_en": "First segment.",
            "text_secondary": "[uk] first",
            "pacing_ms": 1000,
            "voice_id": "en-narrator-01",
        },
        {
            "segment_id": "seg-1",
            "text_en": "Second segment.",
            "text_secondary": "[uk] second",
            "pacing_ms": 1500,
            "voice_id": "en-narrator-01",
        },
        {
            "segment_id": "seg-2",
            "text_en": "Third segment.",
            "text_secondary": "[uk] third",
            "pacing_ms": 2000,
            "voice_id": "en-narrator-01",
        },
    ],
    "dialogue_lines": [],
    "total_duration_ms": 4500,
}


def _write_script(tmp_path: Path, data: dict) -> Path:  # type: ignore[type-arg]
    p = tmp_path / "script.json"
    p.write_text(json.dumps(data))
    return p


# ---------------------------------------------------------------------------
# Timeline helper fixtures
# ---------------------------------------------------------------------------


def _make_minimal_timeline(scene_id: str, segments: list[dict]) -> dict:  # type: ignore[type-arg]
    """Build a minimal timeline dict with narration audio tracks."""
    cursor = 0.0
    tracks = []
    for i, seg in enumerate(segments):
        dur = seg["pacing_ms"] / 1000.0
        tracks.append({
            "track_id": f"audio-{seg['segment_id']}",
            "track_type": "narration",
            "source_path": f"audio/narration_{scene_id}_{seg['segment_id']}.wav",
            "start_s": round(cursor, 6),
            "end_s": round(cursor + dur, 6),
            "line_ref": seg["segment_id"],
        })
        cursor += dur
    return {
        "schema_version": "1.0",
        "story_id": "pigeons-from-hell",
        "scene_id": scene_id,
        "duration_s": cursor,
        "fps": 24,
        "video_tracks": [],
        "audio_tracks": tracks,
        "overlay_tracks": [],
    }


# ---------------------------------------------------------------------------
# TypographyAdapter ABC
# ---------------------------------------------------------------------------


def test_typography_adapter_is_abstract() -> None:
    with pytest.raises(TypeError):
        TypographyAdapter()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# MockTypographyAdapter — PNG properties
# ---------------------------------------------------------------------------


def test_mock_typography_writes_png(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    script_data = _SCRIPT_MINIMAL
    timeline = _make_minimal_timeline(scene_id, script_data["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    result = adapter.render(
        script=script_data,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    # result is the timing manifest path
    assert result == out_timing
    assert out_timing.exists()
    # The PNG for segment 0 must exist
    png = tmp_path / f"typography_{scene_id}_seg-0.png"
    assert png.exists()


def test_mock_typography_png_is_rgba(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=1,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    png = tmp_path / f"typography_{scene_id}_seg-0.png"
    with Image.open(png) as img:
        assert img.mode == "RGBA"


def test_mock_typography_png_correct_dimensions(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=1,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    png = tmp_path / f"typography_{scene_id}_seg-0.png"
    with Image.open(png) as img:
        assert img.size == (640, 480)


def test_mock_typography_png_has_transparency(tmp_path: Path) -> None:
    """At least one pixel must be fully transparent (alpha == 0)."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=5,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=320,
        height=240,
    )
    png = tmp_path / f"typography_{scene_id}_seg-0.png"
    with Image.open(png) as img:
        extrema = img.getextrema()
        # extrema for RGBA is ((r_min, r_max), (g_min, g_max), (b_min, b_max), (a_min, a_max))
        alpha_min = extrema[3][0]
        assert alpha_min == 0, "PNG must contain fully transparent pixels"


def test_mock_typography_text_visible(tmp_path: Path) -> None:
    """At least one opaque white pixel somewhere in the image (adaptive-zones layout)."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=7,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    png = tmp_path / f"typography_{scene_id}_seg-0.png"
    with Image.open(png) as img:
        pixels = list(img.getdata())
        white_pixels = [p for p in pixels if p[0] >= 200 and p[3] == 255]
        assert len(white_pixels) > 0, "EN text should render white pixels"


def test_mock_typography_secondary_text_visible(tmp_path: Path) -> None:
    """Secondary language text renders some non-transparent pixels."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=7,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    png = tmp_path / f"typography_{scene_id}_seg-0.png"
    with Image.open(png) as img:
        pixels = list(img.getdata())
        opaque_pixels = [p for p in pixels if p[3] > 0]
        assert len(opaque_pixels) > 0, "Secondary text area must have visible pixels"


def test_mock_typography_dialogue_included(tmp_path: Path) -> None:
    """Script with dialogue also renders without error and produces valid PNG."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-02"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_WITH_DIALOGUE["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_WITH_DIALOGUE,
        timeline=timeline,
        scene_id=scene_id,
        seed=10,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    png = tmp_path / f"typography_{scene_id}_seg-0.png"
    assert png.exists()
    with Image.open(png) as img:
        assert img.mode == "RGBA"
        assert img.size == (640, 480)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_mock_typography_deterministic_bytes(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out1 = tmp_path / "run1" / f"typography_{scene_id}_timing.json"
    out2 = tmp_path / "run2" / f"typography_{scene_id}_timing.json"
    out1.parent.mkdir()
    out2.parent.mkdir()
    kwargs = dict(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        width=320,
        height=240,
    )
    adapter.render(**kwargs, out_dir=out1.parent, out_timing=out1)  # type: ignore[arg-type]
    adapter.render(**kwargs, out_dir=out2.parent, out_timing=out2)  # type: ignore[arg-type]
    png1 = out1.parent / f"typography_{scene_id}_seg-0.png"
    png2 = out2.parent / f"typography_{scene_id}_seg-0.png"
    assert png1.read_bytes() == png2.read_bytes()


def test_mock_typography_deterministic_timing_manifest(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out1 = tmp_path / "run1" / f"typography_{scene_id}_timing.json"
    out2 = tmp_path / "run2" / f"typography_{scene_id}_timing.json"
    out1.parent.mkdir()
    out2.parent.mkdir()
    kwargs = dict(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        width=320,
        height=240,
    )
    adapter.render(**kwargs, out_dir=out1.parent, out_timing=out1)  # type: ignore[arg-type]
    adapter.render(**kwargs, out_dir=out2.parent, out_timing=out2)  # type: ignore[arg-type]
    j1 = json.loads(out1.read_text())
    j2 = json.loads(out2.read_text())
    for key in ("schema_version", "scene_id"):
        assert j1[key] == j2[key], f"timing manifest field {key!r} differs"
    assert len(j1["segments"]) == len(j2["segments"])
    for s1, s2 in zip(j1["segments"], j2["segments"]):
        for field in ("seg_id", "start_s", "end_s", "text_en", "text_uk"):
            assert s1[field] == s2[field], f"segment field {field!r} differs"


# ---------------------------------------------------------------------------
# Timing manifest content
# ---------------------------------------------------------------------------


def test_timing_manifest_has_correct_start_end(tmp_path: Path) -> None:
    """start_s / end_s in timing manifest must match input timeline audio_tracks."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    timing = json.loads(out_timing.read_text())
    assert len(timing["segments"]) == 1
    seg = timing["segments"][0]
    narr_track = timeline["audio_tracks"][0]
    assert seg["start_s"] == pytest.approx(narr_track["start_s"])
    assert seg["end_s"] == pytest.approx(narr_track["end_s"])


def test_timing_manifest_validates_schema(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=99,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=360,
    )
    timing = json.loads(out_timing.read_text())
    validate(timing, "typography_timing.schema.json")


def test_timing_manifest_fields(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=33,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=360,
    )
    data = json.loads(out_timing.read_text())
    assert data["schema_version"] == "1.0"
    assert data["scene_id"] == "scene-01"
    assert isinstance(data["segments"], list)
    assert len(data["segments"]) == 1
    seg = data["segments"][0]
    assert seg["seg_id"] == "seg-0"
    assert seg["text_en"] == "The house loomed against the storm-grey sky."
    assert "text_uk" in seg
    assert seg["png"] == f"typography_{scene_id}_seg-0.png"


# ---------------------------------------------------------------------------
# N segments → N PNGs + 1 timing manifest
# ---------------------------------------------------------------------------


def test_n_segments_n_pngs_one_timing_manifest(tmp_path: Path) -> None:
    """With a 3-segment script/timeline, 3 PNGs exist and timing has 3 entries."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-03"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_THREE_SEGMENTS["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_THREE_SEGMENTS,
        timeline=timeline,
        scene_id=scene_id,
        seed=7,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    for i in range(3):
        png = tmp_path / f"typography_{scene_id}_seg-{i}.png"
        assert png.exists(), f"PNG for segment {i} must exist"
    timing = json.loads(out_timing.read_text())
    assert len(timing["segments"]) == 3


def test_three_segment_timing_start_end_values(tmp_path: Path) -> None:
    """start_s/end_s from timeline propagate correctly to all 3 segments."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-03"
    segments = _SCRIPT_THREE_SEGMENTS["segments"]
    timeline = _make_minimal_timeline(scene_id, segments)
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_THREE_SEGMENTS,
        timeline=timeline,
        scene_id=scene_id,
        seed=7,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    timing = json.loads(out_timing.read_text())
    narr_tracks = [tr for tr in timeline["audio_tracks"] if tr["track_type"] == "narration"]
    for i, (seg_entry, narr_track) in enumerate(zip(timing["segments"], narr_tracks)):
        assert seg_entry["start_s"] == pytest.approx(narr_track["start_s"]), (
            f"segment {i} start_s mismatch"
        )
        assert seg_entry["end_s"] == pytest.approx(narr_track["end_s"]), (
            f"segment {i} end_s mismatch"
        )


def test_three_segment_schema_valid(tmp_path: Path) -> None:
    """Timing manifest with 3 segments must validate against typography_timing.schema.json."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-03"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_THREE_SEGMENTS["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_THREE_SEGMENTS,
        timeline=timeline,
        scene_id=scene_id,
        seed=7,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    timing = json.loads(out_timing.read_text())
    validate(timing, "typography_timing.schema.json")


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_mock_typography_rejects_small_width(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    with pytest.raises(ValueError, match="width"):
        adapter.render(
            script=_SCRIPT_MINIMAL,
            timeline=timeline,
            scene_id=scene_id,
            seed=0,
            out_dir=tmp_path,
            out_timing=tmp_path / f"typography_{scene_id}_timing.json",
            width=100,
            height=480,
        )


def test_mock_typography_rejects_small_height(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    with pytest.raises(ValueError, match="height"):
        adapter.render(
            script=_SCRIPT_MINIMAL,
            timeline=timeline,
            scene_id=scene_id,
            seed=0,
            out_dir=tmp_path,
            out_timing=tmp_path / f"typography_{scene_id}_timing.json",
            width=640,
            height=100,
        )


def test_mock_typography_rejects_negative_seed(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    with pytest.raises(ValueError, match="seed"):
        adapter.render(
            script=_SCRIPT_MINIMAL,
            timeline=timeline,
            scene_id=scene_id,
            seed=-1,
            out_dir=tmp_path,
            out_timing=tmp_path / f"typography_{scene_id}_timing.json",
            width=640,
            height=480,
        )


# ---------------------------------------------------------------------------
# AdapterFactory
# ---------------------------------------------------------------------------


def test_adapter_factory_get_typography_mock() -> None:
    adapter = AdapterFactory.get_typography("mock")
    assert isinstance(adapter, MockTypographyAdapter)


def test_adapter_factory_get_typography_unknown() -> None:
    with pytest.raises(ValueError, match="unknown typography adapter"):
        AdapterFactory.get_typography("real-provider")


# ---------------------------------------------------------------------------
# Adaptive zones v1 — new layout contract
# ---------------------------------------------------------------------------


def _count_opaque(img: Image.Image) -> int:
    return sum(1 for p in img.getdata() if p[3] > 0)  # type: ignore[union-attr]


def test_text_boxes_not_full_frame_coverage(tmp_path: Path) -> None:
    """Opaque/text pixels must not cover the majority of the frame."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=320,
        height=240,
    )
    png = tmp_path / f"typography_{scene_id}_seg-0.png"
    with Image.open(png) as img:
        total_pixels = 320 * 240
        opaque = _count_opaque(img)
        fraction = opaque / total_pixels
        assert fraction < 0.5, (
            f"Opaque pixels cover {fraction:.1%} of frame — must be < 50%"
        )


def test_two_zone_layout_when_dialogue_present(tmp_path: Path) -> None:
    """With dialogue, opaque pixels must appear in two distinct vertical bands."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-02"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_WITH_DIALOGUE["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_WITH_DIALOGUE,
        timeline=timeline,
        scene_id=scene_id,
        seed=10,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    png = tmp_path / f"typography_{scene_id}_seg-0.png"
    with Image.open(png) as img:
        # Split into top half and bottom half; both should have opaque pixels.
        top_half = img.crop((0, 0, 640, 240))
        bottom_half = img.crop((0, 240, 640, 480))
        assert _count_opaque(top_half) > 0, "Top zone must have opaque pixels"
        assert _count_opaque(bottom_half) > 0, "Bottom zone must have opaque pixels"


def test_layout_deterministic_pixels(tmp_path: Path) -> None:
    """Same inputs → byte-identical PNG (layout is deterministic)."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out1 = tmp_path / "det1" / f"typography_{scene_id}_timing.json"
    out2 = tmp_path / "det2" / f"typography_{scene_id}_timing.json"
    out1.parent.mkdir()
    out2.parent.mkdir()
    kwargs = dict(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=77,
        width=320,
        height=240,
    )
    adapter.render(**kwargs, out_dir=out1.parent, out_timing=out1)  # type: ignore[arg-type]
    adapter.render(**kwargs, out_dir=out2.parent, out_timing=out2)  # type: ignore[arg-type]
    png1 = out1.parent / f"typography_{scene_id}_seg-0.png"
    png2 = out2.parent / f"typography_{scene_id}_seg-0.png"
    assert png1.read_bytes() == png2.read_bytes()


def test_zone_choice_stable_across_python_hash_seeds() -> None:
    """Layout must not depend on Python's salted process-local hash()."""
    script = (
        "from horror_story.adapters.typography.mock import _pick_zones; "
        "z=_pick_zones('scene-02', 10, True, 640, 480)[1]; "
        "print((z.x0, z.y0, z.x1, z.y1))"
    )
    outputs: set[str] = set()
    for hash_seed in ("0", "1", "2", "3"):
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = hash_seed
        proc = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        outputs.add(proc.stdout.strip())

    assert len(outputs) == 1


def test_no_zone_overlap(tmp_path: Path) -> None:
    """Zones must not overlap: no pixel column/row claimed by both boxes."""
    from horror_story.adapters.typography.mock import _pick_zones

    zones = _pick_zones("scene-02", 10, True, 640, 480)
    assert len(zones) == 2
    z1, z2 = zones
    # Rectangles (x0,y0,x1,y1) must not intersect.
    x_overlap = z1[2] > z2[0] and z2[2] > z1[0]
    y_overlap = z1[3] > z2[1] and z2[3] > z1[1]
    assert not (x_overlap and y_overlap), "Zone rectangles must not overlap"


def test_single_zone_no_dialogue(tmp_path: Path) -> None:
    """Script without dialogue renders exactly one zone."""
    from horror_story.adapters.typography.mock import _pick_zones

    zones = _pick_zones("scene-01", 42, False, 640, 480)
    assert len(zones) == 1


def test_versioned_rerun_produces_versioned_pngs(tmp_path: Path) -> None:
    """--scene reruns must not overwrite original PNGs.

    When out_timing carries a _r1 suffix the PNGs must also be _r1 variants,
    leaving the original unversioned PNGs untouched.
    """
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])

    # Original run (no suffix)
    out_timing_v0 = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing_v0,
        width=320,
        height=240,
    )
    original_png = tmp_path / f"typography_{scene_id}_seg-0.png"
    assert original_png.exists()
    original_mtime = original_png.stat().st_mtime

    # Rerun (suffix _r1)
    out_timing_r1 = tmp_path / f"typography_{scene_id}_r1_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing_r1,
        width=320,
        height=240,
    )

    # Original PNG must be untouched
    assert original_png.stat().st_mtime == original_mtime, (
        "Original typography PNG was overwritten by a rerun"
    )
    # Versioned PNG must exist
    versioned_png = tmp_path / f"typography_{scene_id}_r1_seg-0.png"
    assert versioned_png.exists(), "_r1 segment PNG was not created"
    # Timing manifest must reference the versioned PNG
    timing_data = json.loads(out_timing_r1.read_text())
    assert timing_data["segments"][0]["png"] == versioned_png.name


def test_zones_respect_frame_bounds(tmp_path: Path) -> None:
    """Every zone must fit within the frame dimensions."""
    from horror_story.adapters.typography.mock import _pick_zones

    for has_dlg in (True, False):
        zones = _pick_zones("scene-01", 42, has_dlg, 320, 240)
        for x0, y0, x1, y1 in zones:
            assert x0 >= 0 and y0 >= 0
            assert x1 <= 320 and y1 <= 240
            assert x1 > x0 and y1 > y0


# ---------------------------------------------------------------------------
# Auto-split long narration segments (#028)
# ---------------------------------------------------------------------------

# 78-word text that exceeds max_lines at small dimensions
_LONG_TEXT = (
    "It was a dark and stormy night when the traveller arrived at the ancient "
    "manor house standing alone upon the hill overlooking the fog-filled valley "
    "below where no birds sang and no crickets chirped and the very air itself "
    "seemed thick with dread and foreboding as the iron gate swung open with a "
    "rusted shriek that echoed across the empty grounds"
)

_SCRIPT_LONG_SEGMENT = {
    "schema_version": "1.0",
    "story_id": "pigeons-from-hell",
    "scene_id": "scene-long",
    "segments": [
        {
            "segment_id": "seg-0",
            "text_en": _LONG_TEXT,
            "text_secondary": "",
            "pacing_ms": 10000,
            "voice_id": "en-narrator-01",
        }
    ],
    "dialogue_lines": [],
    "total_duration_ms": 10000,
}


def test_split_text_into_chunks_unit() -> None:
    """Every chunk wraps to ≤ max_lines; joined chunks contain all original words."""
    from horror_story.adapters.typography.mock import _split_text_into_chunks
    import textwrap

    max_lines = 3
    char_w = 30
    chunks = _split_text_into_chunks(_LONG_TEXT, max_lines, char_w)
    assert len(chunks) >= 1
    for chunk in chunks:
        lines = textwrap.fill(chunk, width=char_w).splitlines()
        assert len(lines) <= max_lines, (
            f"chunk has {len(lines)} lines, expected <= {max_lines}: {chunk!r}"
        )
    # All words preserved
    original_words = _LONG_TEXT.split()
    chunked_words = " ".join(chunks).split()
    assert chunked_words == original_words


def test_long_segment_splits_into_multiple_pngs(tmp_path: Path) -> None:
    """A segment that exceeds max_lines produces >1 timing entries and all PNGs exist."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-long"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_LONG_SEGMENT["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_LONG_SEGMENT,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=320,
        height=240,
    )
    timing = json.loads(out_timing.read_text())
    entries = timing["segments"]
    assert len(entries) > 1, "Long segment must produce multiple timing entries"
    for entry in entries:
        png_path = tmp_path / entry["png"]
        assert png_path.exists(), f"PNG missing: {entry['png']}"
    # Consecutive entries are contiguous
    for i in range(len(entries) - 1):
        assert entries[i]["end_s"] == pytest.approx(entries[i + 1]["start_s"]), (
            f"Gap between entries {i} and {i+1}"
        )


def test_split_covers_full_duration(tmp_path: Path) -> None:
    """First entry start_s == original start_s; last entry end_s == original end_s."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-long"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_LONG_SEGMENT["segments"])
    original_track = timeline["audio_tracks"][0]
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_LONG_SEGMENT,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=320,
        height=240,
    )
    entries = json.loads(out_timing.read_text())["segments"]
    assert entries[0]["start_s"] == pytest.approx(original_track["start_s"])
    assert entries[-1]["end_s"] == pytest.approx(original_track["end_s"])


def test_short_segment_not_split(tmp_path: Path) -> None:
    """Short text that fits in max_lines produces exactly one entry, seg_id unchanged."""
    adapter = MockTypographyAdapter()
    scene_id = "scene-01"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_MINIMAL["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_MINIMAL,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=640,
        height=480,
    )
    entries = json.loads(out_timing.read_text())["segments"]
    assert len(entries) == 1
    assert entries[0]["seg_id"] == "seg-0"


# ---------------------------------------------------------------------------
# UK-based chunking (#033 / bilingual fix Workstream B)
# ---------------------------------------------------------------------------

# Short English (fits in 1 chunk) but long Ukrainian that needs 2+ chunks
_SHORT_EN_LONG_UK = (
    "The door creaked."
)

# 75-word Ukrainian-style text that will overflow a small max_lines budget
_LONG_UK_TEXT = (
    "Двері заскрипіли в темряві старого маєтку де тіні танцювали по стінах "
    "і холодний вітер завивав крізь розбиті шибки нагадуючи про давно забуті "
    "страхи та жахіття що колись населяли ці похмурі кімнати сповнені болем "
    "і розпачем покинутих душ які не знаходять спокою навіть після смерті"
)

_SCRIPT_SHORT_EN_LONG_UK = {
    "schema_version": "1.0",
    "story_id": "pigeons-from-hell",
    "scene_id": "scene-uk-long",
    "segments": [
        {
            "segment_id": "seg-0",
            "text_en": _SHORT_EN_LONG_UK,
            "text_secondary": _LONG_UK_TEXT,
            "pacing_ms": 10000,
            "voice_id": "en-narrator-01",
        }
    ],
    "dialogue_lines": [],
    "total_duration_ms": 10000,
}

_SCRIPT_NO_SECONDARY = {
    "schema_version": "1.0",
    "story_id": "pigeons-from-hell",
    "scene_id": "scene-no-uk",
    "segments": [
        {
            "segment_id": "seg-0",
            "text_en": _LONG_TEXT,
            "text_secondary": "",
            "pacing_ms": 10000,
            "voice_id": "en-narrator-01",
        }
    ],
    "dialogue_lines": [],
    "total_duration_ms": 10000,
}


def test_long_secondary_short_english_splits_on_uk(tmp_path: Path) -> None:
    """When text_secondary is long but text_en is short, chunking uses UK text.

    Expected:
    - Multiple timing entries are emitted (UK text overflows one chunk).
    - No timing entry has text_uk == "".
    - Each text_uk chunk is a non-empty substring of the original UK text.
    - text_en is preserved as the full English original on every entry.
    """
    adapter = MockTypographyAdapter()
    scene_id = "scene-uk-long"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_SHORT_EN_LONG_UK["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_SHORT_EN_LONG_UK,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=320,
        height=240,
    )
    entries = json.loads(out_timing.read_text())["segments"]

    assert len(entries) > 1, (
        "Long UK text must force the segment to split into multiple timing entries"
    )

    for entry in entries:
        assert entry["text_uk"] != "", (
            f"text_uk must not be empty on any chunk, got empty on seg_id={entry['seg_id']!r}"
        )
        # Each chunk must be a contiguous word-run present in the original UK text
        chunk_words = entry["text_uk"].split()
        assert len(chunk_words) > 0, "text_uk chunk must contain words"
        # Verify the chunk words appear in order in the original UK text
        uk_words = _LONG_UK_TEXT.split()
        chunk_str = " ".join(chunk_words)
        assert chunk_str in _LONG_UK_TEXT, (
            f"text_uk chunk {chunk_str!r} not found in original UK text"
        )
        # text_en is the full English original (unchanged)
        assert entry["text_en"] == _SHORT_EN_LONG_UK, (
            f"text_en must be full EN original, got {entry['text_en']!r}"
        )


def test_no_secondary_text_falls_back_to_en_chunking(tmp_path: Path) -> None:
    """When text_secondary is empty, chunking falls back to text_en.

    Expected:
    - Multiple entries are emitted for long EN text (same as existing split tests).
    - Each entry has text_uk equal to the EN chunk rendered in that slot.
    - No entry has text_uk == "".
    """
    adapter = MockTypographyAdapter()
    scene_id = "scene-no-uk"
    timeline = _make_minimal_timeline(scene_id, _SCRIPT_NO_SECONDARY["segments"])
    out_timing = tmp_path / f"typography_{scene_id}_timing.json"
    adapter.render(
        script=_SCRIPT_NO_SECONDARY,
        timeline=timeline,
        scene_id=scene_id,
        seed=42,
        out_dir=tmp_path,
        out_timing=out_timing,
        width=320,
        height=240,
    )
    entries = json.loads(out_timing.read_text())["segments"]

    # Should still split since _LONG_TEXT is long
    assert len(entries) > 1, (
        "Long EN text with no secondary must still split into multiple entries"
    )

    all_uk = [e["text_uk"] for e in entries]
    for i, (entry, uk_chunk) in enumerate(zip(entries, all_uk)):
        assert uk_chunk != "", (
            f"text_uk must not be empty when falling back to EN (entry {i})"
        )
        # text_uk chunk must appear in the original EN text
        assert uk_chunk in _LONG_TEXT, (
            f"text_uk chunk {uk_chunk!r} not found in EN source text"
        )
    # Reassembled chunks must cover all original EN words
    all_uk_joined = " ".join(all_uk)
    assert all_uk_joined.split() == _LONG_TEXT.split(), (
        "Reassembled text_uk chunks must cover all words of the original EN text"
    )
