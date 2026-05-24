from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from horror_story.config import PipelineConfig
from horror_story.models import Scene


@dataclass(frozen=True)
class Manifest:
    schema_version: str
    story_id: str
    title: str
    seed: int
    languages: dict[str, str]
    render: dict[str, object]
    voices: dict[str, str]
    adapters: dict[str, str]
    scenes: list[str]
    author: str = ""
    source_file: str = ""

    @staticmethod
    def from_path(path: Path) -> "Manifest":
        data: dict[str, Any] = json.loads(path.read_text())
        return Manifest(
            schema_version=str(data["schema_version"]),
            story_id=str(data["story_id"]),
            title=str(data["title"]),
            seed=int(data["seed"]),
            languages=dict(data["languages"]),
            render=dict(data["render"]),
            voices=dict(data["voices"]),
            adapters=dict(data["adapters"]),
            scenes=list(data["scenes"]),
            author=str(data.get("author", "")),
            source_file=str(data.get("source_file", "")),
        )

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "schema_version": self.schema_version,
            "story_id": self.story_id,
            "title": self.title,
            "seed": self.seed,
            "languages": self.languages,
            "render": self.render,
            "voices": self.voices,
            "adapters": self.adapters,
            "scenes": self.scenes,
        }
        if self.author:
            d["author"] = self.author
        if self.source_file:
            d["source_file"] = self.source_file
        return d

    def write(self, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2))
        tmp.replace(path)

    def scene_order(self) -> list[str]:
        return list(self.scenes)


@dataclass
class SceneEntry:
    """Latest artifact paths for one scene. Matches artifact_index.schema.json."""
    scene: str | None = None
    script: str | None = None
    keyframe: str | None = None
    motion: str | None = None
    ambient: str | None = None
    typography: str | None = None
    composed: str | None = None
    status: str = "pending"

    def to_dict(self) -> dict[str, object]:
        return {
            "scene": self.scene,
            "script": self.script,
            "keyframe": self.keyframe,
            "motion": self.motion,
            "ambient": self.ambient,
            "typography": self.typography,
            "composed": self.composed,
            "status": self.status,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "SceneEntry":
        return SceneEntry(
            scene=d.get("scene"),
            script=d.get("script"),
            keyframe=d.get("keyframe"),
            motion=d.get("motion"),
            ambient=d.get("ambient"),
            typography=d.get("typography"),
            composed=d.get("composed"),
            status=str(d.get("status", "pending")),
        )


@dataclass
class ArtifactIndex:
    schema_version: str
    story_id: str
    run_id: str
    scenes: dict[str, SceneEntry] = field(default_factory=dict)
    final: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_path(path: Path) -> "ArtifactIndex":
        data: dict[str, Any] = json.loads(path.read_text())
        scenes = {
            k: SceneEntry.from_dict(v)
            for k, v in data.get("scenes", {}).items()
        }
        return ArtifactIndex(
            schema_version=str(data["schema_version"]),
            story_id=str(data["story_id"]),
            run_id=str(data["run_id"]),
            scenes=scenes,
            final=dict(data.get("final", {})),
        )

    def write(self, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._to_dict(), indent=2))
        tmp.replace(path)

    def _to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "schema_version": self.schema_version,
            "story_id": self.story_id,
            "run_id": self.run_id,
            "scenes": {k: v.to_dict() for k, v in self.scenes.items()},
        }
        if self.final:
            d["final"] = self.final
        return d


def initialize_run(
    config: PipelineConfig,
    story_text: str,
    story_filename: str,
    out_dir: Path,
    *,
    run_id_override: str | None = None,
) -> tuple[Manifest, ArtifactIndex, list[Scene]]:
    """Stage 0+1: parse story, write scene JSONs, manifest, and artifact_index."""
    from horror_story.pipeline.parse import parse_story
    import re

    scenes = parse_story(story_text, config.story.id)

    run_id = run_id_override if run_id_override is not None else f"run_{config.story.id}_{config.story.seed}"
    run_dir = out_dir / run_id
    scenes_dir = run_dir / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    # Write scene JSON files atomically
    for scene in scenes:
        scene_path = scenes_dir / f"scene_{scene.scene_id}.json"
        _atomic_write(scene_path, json.dumps(scene.to_dict(), indent=2))

    manifest = Manifest(
        schema_version="1.0",
        story_id=config.story.id,
        title=config.story.title,
        seed=config.story.seed,
        languages={
            "primary": config.story.primary_language,
            "secondary": config.story.secondary_language,
        },
        render={
            "width": config.render.width,
            "height": config.render.height,
            "fps": config.render.fps,
            "codec": config.render.codec,
            "audio_codec": config.render.audio_codec,
        },
        voices=config.voices,
        adapters={
            "tts": config.adapters.tts,
            "image": config.adapters.image,
            "motion": config.adapters.motion,
            "audio": config.adapters.audio,
            "typography": config.adapters.typography,
        },
        scenes=[s.scene_id for s in scenes],
        source_file=story_filename,
    )
    manifest.write(run_dir / "manifest.json")

    index_scenes = {
        scene.scene_id: SceneEntry(
            scene=f"scenes/scene_{scene.scene_id}.json",
            status="pending",
        )
        for scene in scenes
    }
    artifact_index = ArtifactIndex(
        schema_version="1.0",
        story_id=config.story.id,
        run_id=run_id,
        scenes=index_scenes,
        final={"path": None, "sha256": None, "status": "pending"},
    )
    artifact_index.write(run_dir / "artifact_index.json")

    return manifest, artifact_index, scenes


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content)
    tmp.replace(path)
