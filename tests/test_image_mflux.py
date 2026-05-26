"""Tests for Issue #026 — MfluxImageAdapter."""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from horror_story.adapters import AdapterFactory
from horror_story.adapters.image.mflux import MfluxImageAdapter
from horror_story.schemas import validate


def _make_fake_mflux(tmp_path: Path) -> tuple[MagicMock, MagicMock]:
    """Return (fake_Flux1_class, fake_generated_image) for patching."""
    fake_image = MagicMock()

    def _fake_save(path: str, **kwargs: object) -> None:
        img = Image.new("RGB", (320, 240), color=(42, 42, 42))
        img.save(path, format="PNG")

    fake_image.save.side_effect = _fake_save

    fake_flux_instance = MagicMock()
    fake_flux_instance.generate_image.return_value = fake_image

    fake_Flux1 = MagicMock(return_value=fake_flux_instance)

    fake_model_config = MagicMock()
    fake_ModelConfig = MagicMock()
    fake_ModelConfig.schnell.return_value = fake_model_config

    return fake_Flux1, fake_ModelConfig


# ---------------------------------------------------------------------------
# ImportError when mflux is not installed
# ---------------------------------------------------------------------------


def test_mflux_adapter_missing_import(tmp_path: Path) -> None:
    adapter = MfluxImageAdapter()
    flux_mod = "mflux.models.flux.variants.txt2img.flux"
    cfg_mod = "mflux.models.common.config"
    with patch.dict("sys.modules", {flux_mod: None, cfg_mod: None}):  # type: ignore[dict-item]
        with pytest.raises(ImportError, match="pip install"):
            adapter.generate(
                prompt="A dark corridor stretches into shadow.",
                width=640,
                height=480,
                seed=42,
                out_path=tmp_path / "frame.png",
                story_id="pigeons-from-hell",
                scene_id="scene_001",
            )


# ---------------------------------------------------------------------------
# AdapterFactory returns MfluxImageAdapter (no generation)
# ---------------------------------------------------------------------------


def test_adapter_factory_mflux_schnell() -> None:
    adapter = AdapterFactory.get_image("mflux-schnell")
    assert isinstance(adapter, MfluxImageAdapter)


# ---------------------------------------------------------------------------
# Mocked unit tests — full success path without real model
# ---------------------------------------------------------------------------


def test_mflux_generate_writes_png_and_sidecar(tmp_path: Path) -> None:
    fake_Flux1, fake_ModelConfig = _make_fake_mflux(tmp_path)
    out = tmp_path / "frame.png"

    flux_mod = ModuleType("mflux.models.flux.variants.txt2img.flux")
    flux_mod.Flux1 = fake_Flux1  # type: ignore[attr-defined]
    cfg_mod = ModuleType("mflux.models.common.config")
    cfg_mod.ModelConfig = fake_ModelConfig  # type: ignore[attr-defined]

    with patch.dict("sys.modules", {
        "mflux.models.flux.variants.txt2img.flux": flux_mod,
        "mflux.models.common.config": cfg_mod,
    }):
        result = MfluxImageAdapter().generate(
            prompt="A shadowy corridor.",
            width=320,
            height=240,
            seed=42,
            out_path=out,
            story_id="pigeons-from-hell",
            scene_id="scene_001",
        )

    assert result == out
    assert out.exists()

    sidecar = json.loads(out.with_suffix(".json").read_text())
    validate(sidecar, "keyframe.schema.json")
    assert sidecar["schema_version"] == "1.0"
    assert sidecar["adapter"] == "mflux-schnell"
    assert sidecar["status"] == "generated"
    assert sidecar["seed"] == 42
    assert sidecar["story_id"] == "pigeons-from-hell"
    assert sidecar["scene_id"] == "scene_001"
    assert sidecar["error"] is None


def test_mflux_generate_forwards_seed(tmp_path: Path) -> None:
    fake_Flux1, fake_ModelConfig = _make_fake_mflux(tmp_path)
    fake_flux_instance = fake_Flux1.return_value

    flux_mod = ModuleType("mflux.models.flux.variants.txt2img.flux")
    flux_mod.Flux1 = fake_Flux1  # type: ignore[attr-defined]
    cfg_mod = ModuleType("mflux.models.common.config")
    cfg_mod.ModelConfig = fake_ModelConfig  # type: ignore[attr-defined]

    with patch.dict("sys.modules", {
        "mflux.models.flux.variants.txt2img.flux": flux_mod,
        "mflux.models.common.config": cfg_mod,
    }):
        MfluxImageAdapter().generate(
            prompt="Test.", width=320, height=240, seed=99,
            out_path=tmp_path / "f.png",
        )

    call_kwargs = fake_flux_instance.generate_image.call_args
    assert call_kwargs.kwargs["seed"] == 99


def test_mflux_generate_deterministic_sidecar(tmp_path: Path) -> None:
    """Same inputs → identical sidecar JSON content."""
    fake_Flux1, fake_ModelConfig = _make_fake_mflux(tmp_path)

    flux_mod = ModuleType("mflux.models.flux.variants.txt2img.flux")
    flux_mod.Flux1 = fake_Flux1  # type: ignore[attr-defined]
    cfg_mod = ModuleType("mflux.models.common.config")
    cfg_mod.ModelConfig = fake_ModelConfig  # type: ignore[attr-defined]

    kwargs = dict(
        prompt="Fog over the swamp.",
        width=320,
        height=240,
        seed=7,
        story_id="pigeons-from-hell",
        scene_id="scene_002",
    )

    with patch.dict("sys.modules", {
        "mflux.models.flux.variants.txt2img.flux": flux_mod,
        "mflux.models.common.config": cfg_mod,
    }):
        out1 = tmp_path / "f1.png"
        out2 = tmp_path / "f2.png"
        MfluxImageAdapter().generate(**kwargs, out_path=out1)  # type: ignore[arg-type]
        MfluxImageAdapter().generate(**kwargs, out_path=out2)  # type: ignore[arg-type]

    j1 = json.loads(out1.with_suffix(".json").read_text())
    j2 = json.loads(out2.with_suffix(".json").read_text())
    for key in ("schema_version", "story_id", "scene_id", "prompt", "width", "height", "seed", "adapter", "status"):
        assert j1[key] == j2[key], f"sidecar field {key!r} differs"


# ---------------------------------------------------------------------------
# Smoke test — real generation (skipped unless HORROR_STORY_TEST_MFLUX=1)
# ---------------------------------------------------------------------------


@pytest.mark.mflux
@pytest.mark.skipif(
    os.environ.get("HORROR_STORY_TEST_MFLUX") != "1",
    reason="Set HORROR_STORY_TEST_MFLUX=1 to run real mflux generation",
)
def test_mflux_generate_smoke(tmp_path: Path) -> None:
    pytest.importorskip("mflux")
    from PIL import Image

    adapter = MfluxImageAdapter()
    out = tmp_path / "frame.png"
    result = adapter.generate(
        prompt="A shadowy antebellum mansion at dusk, horror atmosphere.",
        width=512,
        height=512,
        seed=42,
        out_path=out,
        story_id="pigeons-from-hell",
        scene_id="scene_001",
    )

    assert result == out
    assert out.exists()

    with Image.open(out) as img:
        assert img.size == (512, 512)

    sidecar_path = out.with_suffix(".json")
    assert sidecar_path.exists()
    sidecar = json.loads(sidecar_path.read_text())
    validate(sidecar, "keyframe.schema.json")
    assert sidecar["adapter"] == "mflux-schnell"
    assert sidecar["status"] == "generated"
