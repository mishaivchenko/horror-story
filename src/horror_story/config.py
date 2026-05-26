from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class StoryConfig:
    id: str
    title: str
    primary_language: str
    secondary_language: str
    seed: int


@dataclass(frozen=True)
class RenderConfig:
    width: int
    height: int
    fps: int
    codec: str
    audio_codec: str


@dataclass(frozen=True)
class AdapterConfig:
    tts: str
    image: str
    motion: str
    audio: str
    typography: str


@dataclass(frozen=True)
class ImageConfig:
    style_suffix: str = (
        "cinematic horror film still, 1930s American South, "
        "high contrast chiaroscuro lighting, desaturated color palette, "
        "dramatic shadows, photorealistic, no text, no watermark"
    )


@dataclass(frozen=True)
class PipelineConfig:
    story: StoryConfig
    render: RenderConfig
    adapters: AdapterConfig
    image: ImageConfig = field(default_factory=ImageConfig)
    voices: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def from_toml(path: Path) -> "PipelineConfig":
        with path.open("rb") as fh:
            data = tomllib.load(fh)

        story_raw = data["story"]
        story = StoryConfig(
            id=story_raw["id"],
            title=story_raw["title"],
            primary_language=story_raw["primary_language"],
            secondary_language=story_raw["secondary_language"],
            seed=story_raw["seed"],
        )

        render_raw = data["render"]
        render = RenderConfig(
            width=render_raw["width"],
            height=render_raw["height"],
            fps=render_raw["fps"],
            codec=render_raw["codec"],
            audio_codec=render_raw["audio_codec"],
        )

        adapters_raw = data["adapters"]
        adapters = AdapterConfig(
            tts=adapters_raw["tts"],
            image=adapters_raw["image"],
            motion=adapters_raw["motion"],
            audio=adapters_raw["audio"],
            typography=adapters_raw["typography"],
        )

        image_raw = data.get("image", {})
        image = ImageConfig(
            style_suffix=image_raw.get("style_suffix", ImageConfig().style_suffix),
        )

        voices: dict[str, str] = {k: str(v) for k, v in data.get("voices", {}).items()}

        return PipelineConfig(story=story, render=render, adapters=adapters, image=image, voices=voices)
