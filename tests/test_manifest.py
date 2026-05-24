"""Manifest read/write tests — Issue #001."""

import json
from pathlib import Path

from horror_story.manifest import ArtifactIndex, Manifest, SceneEntry


_MANIFEST_DATA = {
    "schema_version": "1.0",
    "story_id": "pigeons-from-hell",
    "title": "Pigeons from Hell",
    "author": "Robert E. Howard",
    "source_file": "pigeons-from-hell.txt",
    "seed": 42,
    "languages": {"primary": "en", "secondary": "uk"},
    "render": {
        "width": 3840,
        "height": 2160,
        "fps": 24,
        "codec": "libx264",
        "audio_codec": "aac",
    },
    "voices": {"narrator": "en-narrator-01"},
    "adapters": {
        "tts": "mock",
        "image": "mock",
        "motion": "mock",
        "audio": "mock",
        "typography": "mock",
    },
    "scenes": ["scene-001", "scene-002"],
}


def test_manifest_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(_MANIFEST_DATA))

    m = Manifest.from_path(path)
    assert m.story_id == "pigeons-from-hell"
    assert m.seed == 42
    assert m.scene_order() == ["scene-001", "scene-002"]


def test_manifest_write_is_atomic(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(_MANIFEST_DATA))

    m = Manifest.from_path(path)
    out = tmp_path / "out.json"
    m.write(out)

    reloaded = json.loads(out.read_text())
    assert reloaded["story_id"] == "pigeons-from-hell"
    assert not (tmp_path / "out.tmp").exists()


def test_artifact_index_roundtrip(tmp_path: Path) -> None:
    data = {
        "schema_version": "1.0",
        "story_id": "pigeons-from-hell",
        "run_id": "run_pigeons-from-hell_42",
        "scenes": {
            "scene-001": {
                "scene": "scenes/scene_scene-001.json",
                "script": None,
                "keyframe": None,
                "motion": None,
                "ambient": None,
                "typography": None,
                "composed": None,
                "status": "pending",
            }
        },
    }
    path = tmp_path / "artifact_index.json"
    path.write_text(json.dumps(data))

    idx = ArtifactIndex.from_path(path)
    assert idx.story_id == "pigeons-from-hell"
    assert idx.run_id == "run_pigeons-from-hell_42"
    assert "scene-001" in idx.scenes
    assert idx.scenes["scene-001"].status == "pending"
    assert idx.scenes["scene-001"].scene == "scenes/scene_scene-001.json"


def test_artifact_index_write_roundtrip(tmp_path: Path) -> None:
    idx = ArtifactIndex(
        schema_version="1.0",
        story_id="pigeons-from-hell",
        run_id="run_pigeons-from-hell_42",
        scenes={"scene-001": SceneEntry(scene="scenes/s.json", status="complete")},
    )
    out = tmp_path / "artifact_index.json"
    idx.write(out)

    reloaded = ArtifactIndex.from_path(out)
    assert reloaded.scenes["scene-001"].status == "complete"
    assert not (tmp_path / "artifact_index.tmp").exists()
