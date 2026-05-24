"""Tests for Issue #006 — Mock Typography overlay adapter."""
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
# Fixtures
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


def _write_script(tmp_path: Path, data: dict) -> Path:  # type: ignore[type-arg]
    p = tmp_path / "script.json"
    p.write_text(json.dumps(data))
    return p


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
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    result = adapter.render(
        script_path=script_path,
        duration_s=2.0,
        width=640,
        height=480,
        fps=24,
        seed=42,
        out_path=out,
    )
    assert result == out
    assert out.exists()


def test_mock_typography_png_is_rgba(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.0,
        width=640,
        height=480,
        fps=24,
        seed=1,
        out_path=out,
    )
    with Image.open(out) as img:
        assert img.mode == "RGBA"


def test_mock_typography_png_correct_dimensions(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.0,
        width=640,
        height=480,
        fps=24,
        seed=1,
        out_path=out,
    )
    with Image.open(out) as img:
        assert img.size == (640, 480)


def test_mock_typography_png_has_transparency(tmp_path: Path) -> None:
    """At least one pixel must be fully transparent (alpha == 0)."""
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.0,
        width=320,
        height=240,
        fps=24,
        seed=5,
        out_path=out,
    )
    with Image.open(out) as img:
        extrema = img.getextrema()
        # extrema for RGBA is ((r_min, r_max), (g_min, g_max), (b_min, b_max), (a_min, a_max))
        alpha_min = extrema[3][0]
        assert alpha_min == 0, "PNG must contain fully transparent pixels"


def test_mock_typography_text_visible(tmp_path: Path) -> None:
    """At least one opaque white pixel somewhere in the image (adaptive-zones layout)."""
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.0,
        width=640,
        height=480,
        fps=24,
        seed=7,
        out_path=out,
    )
    with Image.open(out) as img:
        pixels = list(img.getdata())
        white_pixels = [p for p in pixels if p[0] >= 200 and p[3] == 255]
        assert len(white_pixels) > 0, "EN text should render white pixels"


def test_mock_typography_secondary_text_visible(tmp_path: Path) -> None:
    """Secondary language text renders some non-transparent pixels."""
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.0,
        width=640,
        height=480,
        fps=24,
        seed=7,
        out_path=out,
    )
    with Image.open(out) as img:
        pixels = list(img.getdata())
        opaque_pixels = [p for p in pixels if p[3] > 0]
        assert len(opaque_pixels) > 0, "Secondary text area must have visible pixels"


def test_mock_typography_dialogue_included(tmp_path: Path) -> None:
    """Script with dialogue also renders without error and produces valid PNG."""
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_WITH_DIALOGUE)
    out = tmp_path / "overlay_dlg.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.5,
        width=640,
        height=480,
        fps=24,
        seed=10,
        out_path=out,
    )
    assert out.exists()
    with Image.open(out) as img:
        assert img.mode == "RGBA"
        assert img.size == (640, 480)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_mock_typography_deterministic_bytes(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out1 = tmp_path / "run1.png"
    out2 = tmp_path / "run2.png"
    kwargs = dict(
        script_path=script_path,
        duration_s=2.0,
        width=320,
        height=240,
        fps=24,
        seed=42,
    )
    adapter.render(**kwargs, out_path=out1)  # type: ignore[arg-type]
    adapter.render(**kwargs, out_path=out2)  # type: ignore[arg-type]
    assert out1.read_bytes() == out2.read_bytes()


def test_mock_typography_deterministic_sidecar(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out1 = tmp_path / "run1.png"
    out2 = tmp_path / "run2.png"
    kwargs = dict(
        script_path=script_path,
        duration_s=2.0,
        width=320,
        height=240,
        fps=24,
        seed=42,
    )
    adapter.render(**kwargs, out_path=out1)  # type: ignore[arg-type]
    adapter.render(**kwargs, out_path=out2)  # type: ignore[arg-type]
    j1 = json.loads(out1.with_suffix(".json").read_text())
    j2 = json.loads(out2.with_suffix(".json").read_text())
    for key in ("schema_version", "story_id", "scene_id", "duration_s", "width", "height", "fps", "seed", "adapter", "status"):
        assert j1[key] == j2[key], f"sidecar field {key!r} differs"


def test_mock_typography_different_seeds_differ(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out1 = tmp_path / "seed1.png"
    out2 = tmp_path / "seed2.png"
    base = dict(
        script_path=script_path,
        duration_s=2.0,
        width=320,
        height=240,
        fps=24,
    )
    adapter.render(**base, seed=1, out_path=out1)  # type: ignore[arg-type]
    adapter.render(**base, seed=200, out_path=out2)  # type: ignore[arg-type]
    # Sidecar seeds differ; PNG bytes may or may not (mock doesn't use seed for pixels)
    j1 = json.loads(out1.with_suffix(".json").read_text())
    j2 = json.loads(out2.with_suffix(".json").read_text())
    assert j1["seed"] != j2["seed"]


# ---------------------------------------------------------------------------
# Sidecar JSON
# ---------------------------------------------------------------------------


def test_mock_typography_sidecar_exists(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.0,
        width=640,
        height=360,
        fps=24,
        seed=5,
        out_path=out,
    )
    assert out.with_suffix(".json").exists()


def test_mock_typography_sidecar_validates_schema(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.0,
        width=640,
        height=360,
        fps=24,
        seed=99,
        out_path=out,
    )
    data = json.loads(out.with_suffix(".json").read_text())
    validate(data, "typography_artifact.schema.json")


def test_mock_typography_sidecar_fields(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    adapter.render(
        script_path=script_path,
        duration_s=3.5,
        width=640,
        height=360,
        fps=24,
        seed=33,
        out_path=out,
    )
    data = json.loads(out.with_suffix(".json").read_text())
    assert data["schema_version"] == "1.0"
    assert data["story_id"] == "pigeons-from-hell"
    assert data["scene_id"] == "scene-01"
    assert data["duration_s"] == 3.5
    assert data["width"] == 640
    assert data["height"] == 360
    assert data["fps"] == 24
    assert data["seed"] == 33
    assert data["adapter"] == "mock"
    assert data["status"] == "generated"
    assert data["error"] is None


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_mock_typography_rejects_small_width(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    with pytest.raises(ValueError, match="width"):
        adapter.render(
            script_path=script_path,
            duration_s=2.0,
            width=100,
            height=480,
            fps=24,
            seed=0,
            out_path=tmp_path / "out.png",
        )


def test_mock_typography_rejects_small_height(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    with pytest.raises(ValueError, match="height"):
        adapter.render(
            script_path=script_path,
            duration_s=2.0,
            width=640,
            height=100,
            fps=24,
            seed=0,
            out_path=tmp_path / "out.png",
        )


def test_mock_typography_rejects_negative_duration(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    with pytest.raises(ValueError, match="duration_s"):
        adapter.render(
            script_path=script_path,
            duration_s=-1.0,
            width=640,
            height=480,
            fps=24,
            seed=0,
            out_path=tmp_path / "out.png",
        )


def test_mock_typography_rejects_zero_fps(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    with pytest.raises(ValueError, match="fps"):
        adapter.render(
            script_path=script_path,
            duration_s=2.0,
            width=640,
            height=480,
            fps=0,
            seed=0,
            out_path=tmp_path / "out.png",
        )


def test_mock_typography_rejects_negative_seed(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    with pytest.raises(ValueError, match="seed"):
        adapter.render(
            script_path=script_path,
            duration_s=2.0,
            width=640,
            height=480,
            fps=24,
            seed=-1,
            out_path=tmp_path / "out.png",
        )


def test_mock_typography_rejects_missing_script(tmp_path: Path) -> None:
    adapter = MockTypographyAdapter()
    with pytest.raises(FileNotFoundError):
        adapter.render(
            script_path=tmp_path / "no_such_file.json",
            duration_s=2.0,
            width=640,
            height=480,
            fps=24,
            seed=0,
            out_path=tmp_path / "out.png",
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
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out = tmp_path / "overlay.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.0,
        width=320,
        height=240,
        fps=24,
        seed=42,
        out_path=out,
    )
    with Image.open(out) as img:
        total_pixels = 320 * 240
        opaque = _count_opaque(img)
        fraction = opaque / total_pixels
        assert fraction < 0.5, (
            f"Opaque pixels cover {fraction:.1%} of frame — must be < 50%"
        )


def test_two_zone_layout_when_dialogue_present(tmp_path: Path) -> None:
    """With dialogue, opaque pixels must appear in two distinct vertical bands."""
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_WITH_DIALOGUE)
    out = tmp_path / "overlay_dlg.png"
    adapter.render(
        script_path=script_path,
        duration_s=2.5,
        width=640,
        height=480,
        fps=24,
        seed=10,
        out_path=out,
    )
    with Image.open(out) as img:
        # Split into top half and bottom half; both should have opaque pixels.
        top_half = img.crop((0, 0, 640, 240))
        bottom_half = img.crop((0, 240, 640, 480))
        assert _count_opaque(top_half) > 0, "Top zone must have opaque pixels"
        assert _count_opaque(bottom_half) > 0, "Bottom zone must have opaque pixels"


def test_layout_deterministic_pixels(tmp_path: Path) -> None:
    """Same inputs → byte-identical PNG (layout is deterministic)."""
    adapter = MockTypographyAdapter()
    script_path = _write_script(tmp_path, _SCRIPT_MINIMAL)
    out1 = tmp_path / "det1.png"
    out2 = tmp_path / "det2.png"
    kwargs = dict(
        script_path=script_path,
        duration_s=2.0,
        width=320,
        height=240,
        fps=24,
        seed=77,
    )
    adapter.render(**kwargs, out_path=out1)  # type: ignore[arg-type]
    adapter.render(**kwargs, out_path=out2)  # type: ignore[arg-type]
    assert out1.read_bytes() == out2.read_bytes()


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
