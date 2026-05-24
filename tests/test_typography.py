"""Tests for Issue #006 — Mock Typography overlay adapter."""
from __future__ import annotations

import json
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
    """At least one opaque white pixel in the upper region (EN text area)."""
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
        upper_third = img.crop((0, 0, 640, 160))
        pixels = list(upper_third.getdata())
        white_pixels = [p for p in pixels if p[0] >= 200 and p[3] == 255]
        assert len(white_pixels) > 0, "EN text should render white pixels in upper region"


def test_mock_typography_secondary_text_visible(tmp_path: Path) -> None:
    """Secondary language text renders some non-transparent pixels below EN text."""
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
        # Lower half of the top region; secondary text should appear here
        mid_region = img.crop((0, 30, 640, 300))
        pixels = list(mid_region.getdata())
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
