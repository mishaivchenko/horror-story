"""Tests for Issue #005 — Mock Image adapter."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from horror_story.adapters import AdapterFactory
from horror_story.adapters.image.base import ImageAdapter
from horror_story.adapters.image.mock import MockImageAdapter
from horror_story.schemas import validate

# ---------------------------------------------------------------------------
# ImageAdapter ABC
# ---------------------------------------------------------------------------


def test_image_adapter_is_abstract() -> None:
    with pytest.raises(TypeError):
        ImageAdapter()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# MockImageAdapter — PNG properties
# ---------------------------------------------------------------------------


def test_mock_image_writes_png(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out = tmp_path / "frame.png"
    result = adapter.generate(
        prompt="A dark corridor stretches into shadow.",
        width=640,
        height=480,
        seed=42,
        out_path=out,
    )
    assert result == out
    assert out.exists()


def test_mock_image_correct_dimensions(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out = tmp_path / "frame.png"
    adapter.generate(
        prompt="Moonlight filters through broken shutters.",
        width=640,
        height=480,
        seed=1,
        out_path=out,
    )
    with Image.open(out) as img:
        assert img.size == (640, 480)
        assert img.mode == "RGB"


def test_mock_image_grey_value_from_seed(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out = tmp_path / "frame.png"
    seed = 100
    expected_grey = seed % 128 + 64
    adapter.generate(
        prompt="The house loomed against the storm-grey sky.",
        width=320,
        height=240,
        seed=seed,
        out_path=out,
    )
    with Image.open(out) as img:
        # Sample a pixel far from the text label (bottom-right area)
        r, g, b = img.getpixel((300, 220))  # type: ignore[misc]
    assert r == expected_grey
    assert g == expected_grey
    assert b == expected_grey


def test_mock_image_deterministic_bytes(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out1 = tmp_path / "frame1.png"
    out2 = tmp_path / "frame2.png"
    kwargs = dict(
        prompt="Swamp fog rolled across the grounds.",
        width=320,
        height=240,
        seed=7,
        story_id="pigeons-from-hell",
        scene_id="scene_001",
    )
    adapter.generate(**kwargs, out_path=out1)  # type: ignore[arg-type]
    adapter.generate(**kwargs, out_path=out2)  # type: ignore[arg-type]
    assert out1.read_bytes() == out2.read_bytes()


def test_mock_image_sidecar_deterministic_content(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out1 = tmp_path / "frame1.png"
    out2 = tmp_path / "frame2.png"
    kwargs = dict(
        prompt="Swamp fog rolled across the grounds.",
        width=320,
        height=240,
        seed=7,
        story_id="pigeons-from-hell",
        scene_id="scene_001",
    )
    adapter.generate(**kwargs, out_path=out1)  # type: ignore[arg-type]
    adapter.generate(**kwargs, out_path=out2)  # type: ignore[arg-type]
    j1 = json.loads(out1.with_suffix(".json").read_text())
    j2 = json.loads(out2.with_suffix(".json").read_text())
    # All fields except output_path must be identical
    for key in ("schema_version", "story_id", "scene_id", "prompt", "width", "height", "seed", "adapter", "status"):
        assert j1[key] == j2[key], f"sidecar field {key!r} differs between identical calls"


def test_mock_image_different_seeds_differ(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out1 = tmp_path / "frame_seed1.png"
    out2 = tmp_path / "frame_seed2.png"
    base = dict(
        prompt="The staircase creaked under invisible weight.",
        width=320,
        height=240,
    )
    adapter.generate(**base, seed=10, out_path=out1)  # type: ignore[arg-type]
    adapter.generate(**base, seed=200, out_path=out2)  # type: ignore[arg-type]
    assert out1.read_bytes() != out2.read_bytes()


def test_mock_image_different_scene_ids_differ(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out1 = tmp_path / "frame_s1.png"
    out2 = tmp_path / "frame_s2.png"
    base = dict(prompt="Ancient evil stirred.", width=320, height=240, seed=42)
    adapter.generate(**base, scene_id="scene_001", out_path=out1)  # type: ignore[arg-type]
    adapter.generate(**base, scene_id="scene_002", out_path=out2)  # type: ignore[arg-type]
    # JSON sidecars differ; PNGs may be visually similar but labels differ
    j1 = json.loads(out1.with_suffix(".json").read_text())
    j2 = json.loads(out2.with_suffix(".json").read_text())
    assert j1["scene_id"] != j2["scene_id"]


# ---------------------------------------------------------------------------
# Sidecar JSON
# ---------------------------------------------------------------------------


def test_mock_image_sidecar_exists(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out = tmp_path / "frame.png"
    adapter.generate(
        prompt="Darkness pressed against the windows.",
        width=640,
        height=360,
        seed=5,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene_001",
    )
    sidecar_path = out.with_suffix(".json")
    assert sidecar_path.exists()


def test_mock_image_sidecar_validates_schema(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out = tmp_path / "frame.png"
    adapter.generate(
        prompt="The hound bayed in the distance.",
        width=640,
        height=360,
        seed=99,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene_002",
    )
    sidecar = json.loads(out.with_suffix(".json").read_text())
    validate(sidecar, "keyframe.schema.json")


def test_mock_image_sidecar_fields(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    out = tmp_path / "frame.png"
    adapter.generate(
        prompt="Torchlight flickered in the swamp.",
        width=640,
        height=360,
        seed=33,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene_003",
    )
    sidecar = json.loads(out.with_suffix(".json").read_text())
    assert sidecar["schema_version"] == "1.0"
    assert sidecar["story_id"] == "pigeons-from-hell"
    assert sidecar["scene_id"] == "scene_003"
    assert sidecar["prompt"] == "Torchlight flickered in the swamp."
    assert sidecar["width"] == 640
    assert sidecar["height"] == 360
    assert sidecar["seed"] == 33
    assert sidecar["adapter"] == "mock"
    assert sidecar["status"] == "generated"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_mock_image_rejects_empty_prompt(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    with pytest.raises(ValueError, match="prompt"):
        adapter.generate(prompt="", width=640, height=480, seed=0, out_path=tmp_path / "f.png")


def test_mock_image_rejects_small_width(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    with pytest.raises(ValueError, match="width"):
        adapter.generate(
            prompt="X", width=100, height=480, seed=0, out_path=tmp_path / "f.png"
        )


def test_mock_image_rejects_small_height(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    with pytest.raises(ValueError, match="height"):
        adapter.generate(
            prompt="X", width=640, height=100, seed=0, out_path=tmp_path / "f.png"
        )


def test_mock_image_rejects_negative_seed(tmp_path: Path) -> None:
    adapter = MockImageAdapter()
    with pytest.raises(ValueError, match="seed"):
        adapter.generate(
            prompt="X", width=640, height=480, seed=-1, out_path=tmp_path / "f.png"
        )


# ---------------------------------------------------------------------------
# AdapterFactory
# ---------------------------------------------------------------------------


def test_adapter_factory_get_image_mock() -> None:
    adapter = AdapterFactory.get_image("mock")
    assert isinstance(adapter, MockImageAdapter)


def test_adapter_factory_get_image_unknown() -> None:
    with pytest.raises(ValueError, match="unknown image adapter"):
        AdapterFactory.get_image("real-midjourney")
