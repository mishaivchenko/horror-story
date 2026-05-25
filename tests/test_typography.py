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


def test_zones_respect_frame_bounds(tmp_path: Path) -> None:
    """Every zone must fit within the frame dimensions."""
    from horror_story.adapters.typography.mock import _pick_zones

    for has_dlg in (True, False):
        zones = _pick_zones("scene-01", 42, has_dlg, 320, 240)
        for x0, y0, x1, y1 in zones:
            assert x0 >= 0 and y0 >= 0
            assert x1 <= 320 and y1 <= 240
            assert x1 > x0 and y1 > y0
