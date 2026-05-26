"""Config loading tests — Issue #001."""

import textwrap
from pathlib import Path

import pytest

from horror_story.config import ImageConfig, PipelineConfig


def test_from_toml_loads_correctly(tmp_path: Path) -> None:
    toml_content = textwrap.dedent("""\
        [story]
        id = "pigeons-from-hell"
        title = "Pigeons from Hell"
        primary_language = "en"
        secondary_language = "uk"
        seed = 42

        [render]
        width = 3840
        height = 2160
        fps = 24
        codec = "libx264"
        audio_codec = "aac"

        [voices]
        narrator = "en-narrator-01"

        [adapters]
        tts = "mock"
        image = "mock"
        motion = "mock"
        audio = "mock"
        typography = "mock"
    """)
    toml_path = tmp_path / "pipeline.toml"
    toml_path.write_text(toml_content)

    cfg = PipelineConfig.from_toml(toml_path)

    assert cfg.story.id == "pigeons-from-hell"
    assert cfg.story.seed == 42
    assert cfg.render.width == 3840
    assert cfg.render.fps == 24
    assert cfg.adapters.tts == "mock"
    assert cfg.voices["narrator"] == "en-narrator-01"


_MINIMAL_TOML = textwrap.dedent("""\
    [story]
    id = "test-story"
    title = "Test Story"
    primary_language = "en"
    secondary_language = "uk"
    seed = 1

    [render]
    width = 320
    height = 240
    fps = 24
    codec = "libx264"
    audio_codec = "aac"

    [adapters]
    tts = "mock"
    image = "mock"
    motion = "mock"
    audio = "mock"
    typography = "mock"
""")


def test_image_style_suffix_default(tmp_path: Path) -> None:
    """Missing [image] section uses ImageConfig default without error."""
    toml_path = tmp_path / "pipeline.toml"
    toml_path.write_text(_MINIMAL_TOML)

    cfg = PipelineConfig.from_toml(toml_path)

    assert cfg.image.style_suffix == ImageConfig().style_suffix


def test_image_style_suffix_override(tmp_path: Path) -> None:
    """[image] style_suffix overrides the default when present in TOML."""
    toml_content = _MINIMAL_TOML + '\n[image]\nstyle_suffix = "flat design"\n'
    toml_path = tmp_path / "pipeline.toml"
    toml_path.write_text(toml_content)

    cfg = PipelineConfig.from_toml(toml_path)

    assert cfg.image.style_suffix == "flat design"
