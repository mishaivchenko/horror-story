"""Tests for Issue #002 — Story parser MVP."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from horror_story.models import Scene, slugify, classify_mood
from horror_story.pipeline.parse import parse_story
from horror_story.schemas import validate

FIXTURE = Path(__file__).parent / "fixtures" / "mini-story.txt"

_STORY_TEXT = FIXTURE.read_text()
_STORY_ID = "pigeons-from-hell"


# ---------------------------------------------------------------------------
# Core parsing
# ---------------------------------------------------------------------------

def test_parse_produces_three_scenes() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    assert len(scenes) == 3


def test_scenes_are_ordered_by_index() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    assert [s.index for s in scenes] == [0, 1, 2]


def test_scene_text_is_non_empty() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    for scene in scenes:
        assert scene.text.strip()


def test_scene_word_count_positive() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    for scene in scenes:
        assert scene.word_count > 0


def test_story_id_propagated() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    for scene in scenes:
        assert scene.story_id == _STORY_ID


# ---------------------------------------------------------------------------
# scene_id determinism and stability
# ---------------------------------------------------------------------------

def test_scene_ids_are_deterministic() -> None:
    scenes_a = parse_story(_STORY_TEXT, _STORY_ID)
    scenes_b = parse_story(_STORY_TEXT, _STORY_ID)
    assert [s.scene_id for s in scenes_a] == [s.scene_id for s in scenes_b]


def test_scene_ids_unique() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    ids = [s.scene_id for s in scenes]
    assert len(ids) == len(set(ids))


def test_scene_id_is_kebab_slug() -> None:
    import re
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    for scene in scenes:
        assert re.fullmatch(r"[a-z0-9-]{1,64}", scene.scene_id), (
            f"Bad scene_id: {scene.scene_id!r}"
        )


def test_scene_id_max_48_chars() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    for scene in scenes:
        assert len(scene.scene_id) <= 48


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_scene_dicts_validate_against_schema() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    for scene in scenes:
        validate(scene.to_dict(), "scene.schema.json")


def test_scene_to_dict_round_trips() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    for scene in scenes:
        d = scene.to_dict()
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        assert decoded["scene_id"] == scene.scene_id
        assert decoded["index"] == scene.index
        assert decoded["schema_version"] == "1.0"


# ---------------------------------------------------------------------------
# Mood classification
# ---------------------------------------------------------------------------

def test_mood_values_are_valid_enum() -> None:
    valid_moods = {
        "dread", "tension", "silence", "violence", "mystery",
        "relief", "night_insects", "wind", "neutral",
    }
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    for scene in scenes:
        assert scene.mood in valid_moods


def test_first_scene_has_expected_mood() -> None:
    # First scene has 'dread', 'shadow', 'silence', 'night', 'bayou' → night_insects or dread
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    assert scenes[0].mood in {"dread", "night_insects", "silence"}


def test_second_scene_has_tension_or_violence() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    assert scenes[1].mood in {"tension", "violence"}


def test_third_scene_has_mystery_or_dread() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    assert scenes[2].mood in {"mystery", "dread"}


# ---------------------------------------------------------------------------
# Visual description
# ---------------------------------------------------------------------------

def test_visual_description_is_non_empty() -> None:
    scenes = parse_story(_STORY_TEXT, _STORY_ID)
    for scene in scenes:
        assert scene.visual_description.strip()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

def test_empty_text_raises_value_error() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_story("", _STORY_ID)


def test_whitespace_only_raises_value_error() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_story("   \n\n\t  ", _STORY_ID)


def test_no_separator_gives_single_scene() -> None:
    text = "Once upon a time in the dark and dreadful swamp."
    scenes = parse_story(text, _STORY_ID)
    assert len(scenes) == 1


def test_separator_only_text_skipped() -> None:
    text = "First scene with dread.\n\n---\n\nSecond scene with mystery.\n\n---"
    scenes = parse_story(text, _STORY_ID)
    assert len(scenes) == 2


# ---------------------------------------------------------------------------
# Slugify helper
# ---------------------------------------------------------------------------

def test_slugify_max_chars() -> None:
    long_text = "a " * 100
    result = slugify(long_text, max_chars=48)
    assert len(result) <= 48


def test_slugify_removes_stop_words() -> None:
    result = slugify("the dark and ancient horror of the swamp")
    assert "the" not in result.split("-")
    assert "and" not in result.split("-")
    assert "of" not in result.split("-")


def test_slugify_stable() -> None:
    text = "darkness and ancient evil"
    assert slugify(text) == slugify(text)


# ---------------------------------------------------------------------------
# Repeated runs produce same content
# ---------------------------------------------------------------------------

def test_repeated_runs_identical_scene_dicts() -> None:
    run1 = [s.to_dict() for s in parse_story(_STORY_TEXT, _STORY_ID)]
    run2 = [s.to_dict() for s in parse_story(_STORY_TEXT, _STORY_ID)]
    assert run1 == run2


# ---------------------------------------------------------------------------
# initialize_run integration
# ---------------------------------------------------------------------------

def test_initialize_run_writes_files(tmp_path: Path) -> None:
    from horror_story.config import PipelineConfig, StoryConfig, RenderConfig, AdapterConfig
    from horror_story.manifest import initialize_run
    from horror_story.schemas import validate

    config = PipelineConfig(
        story=StoryConfig(
            id="pigeons-from-hell",
            title="Pigeons from Hell",
            primary_language="en",
            secondary_language="uk",
            seed=42,
        ),
        render=RenderConfig(
            width=3840, height=2160, fps=24,
            codec="libx264", audio_codec="aac",
        ),
        adapters=AdapterConfig(
            tts="mock", image="mock", motion="mock",
            audio="mock", typography="mock",
        ),
        voices={"narrator": "en-narrator-01"},
    )

    manifest, artifact_index, scenes = initialize_run(
        config, _STORY_TEXT, "mini-story.txt", tmp_path
    )

    run_dir = tmp_path / "run_pigeons-from-hell_42"
    assert run_dir.is_dir()

    manifest_path = run_dir / "manifest.json"
    assert manifest_path.exists()
    validate(json.loads(manifest_path.read_text()), "manifest.schema.json")

    artifact_index_path = run_dir / "artifact_index.json"
    assert artifact_index_path.exists()
    validate(json.loads(artifact_index_path.read_text()), "artifact_index.schema.json")

    assert len(scenes) == 3
    for scene in scenes:
        scene_path = run_dir / "scenes" / f"scene_{scene.scene_id}.json"
        assert scene_path.exists()
        validate(json.loads(scene_path.read_text()), "scene.schema.json")

    # Artifact index content: scene path set, all downstream null, status pending
    index_data = json.loads(artifact_index_path.read_text())
    for scene in scenes:
        entry = index_data["scenes"][scene.scene_id]
        assert entry["scene"] == f"scenes/scene_{scene.scene_id}.json"
        assert entry["status"] == "pending"
        assert entry["script"] is None
        assert entry["keyframe"] is None
        assert entry["motion"] is None
        assert entry["ambient"] is None
        assert entry["typography"] is None
        assert entry["composed"] is None


def test_initialize_run_deterministic(tmp_path: Path) -> None:
    from horror_story.config import PipelineConfig, StoryConfig, RenderConfig, AdapterConfig
    from horror_story.manifest import initialize_run

    config = PipelineConfig(
        story=StoryConfig(
            id="pigeons-from-hell",
            title="Pigeons from Hell",
            primary_language="en",
            secondary_language="uk",
            seed=42,
        ),
        render=RenderConfig(
            width=3840, height=2160, fps=24,
            codec="libx264", audio_codec="aac",
        ),
        adapters=AdapterConfig(
            tts="mock", image="mock", motion="mock",
            audio="mock", typography="mock",
        ),
        voices={"narrator": "en-narrator-01"},
    )

    run_dir_a = tmp_path / "a"
    run_dir_b = tmp_path / "b"

    _, _, scenes_a = initialize_run(config, _STORY_TEXT, "mini-story.txt", run_dir_a)
    _, _, scenes_b = initialize_run(config, _STORY_TEXT, "mini-story.txt", run_dir_b)

    assert [s.to_dict() for s in scenes_a] == [s.to_dict() for s in scenes_b]
