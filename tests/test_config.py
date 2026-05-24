"""Config loading tests — Issue #001."""

import textwrap
from pathlib import Path

import pytest

from horror_story.config import PipelineConfig


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
