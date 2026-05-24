"""Tests for Issue #003 — Script generator."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from horror_story.config import AdapterConfig, PipelineConfig, RenderConfig, StoryConfig
from horror_story.manifest import Manifest
from horror_story.models import DialogueLine, Scene, Script, Segment
from horror_story.pipeline.parse import parse_story
from horror_story.pipeline.script import (
    generate_script,
    generate_script_from_path,
    mock_translate,
)
from horror_story.schemas import validate

FIXTURES = Path(__file__).parent / "fixtures"
STORY_TEXT = (FIXTURES / "mini-story.txt").read_text()
STORY_ID = "pigeons-from-hell"

_MANIFEST = Manifest(
    schema_version="1.0",
    story_id=STORY_ID,
    title="Pigeons from Hell",
    seed=42,
    languages={"primary": "en", "secondary": "uk"},
    render={"width": 3840, "height": 2160, "fps": 24, "codec": "libx264", "audio_codec": "aac"},
    voices={"narrator": "en-narrator-01", "griswell": "en-male-deep", "branner": "en-male-mid"},
    adapters={"tts": "mock", "image": "mock", "motion": "mock", "audio": "mock", "typography": "mock"},
    scenes=[],
)


def _scenes() -> list[Scene]:
    return parse_story(STORY_TEXT, STORY_ID)


# ---------------------------------------------------------------------------
# mock_translate
# ---------------------------------------------------------------------------

def test_mock_translate_prefix() -> None:
    assert mock_translate("hello world").startswith("[uk] ")


def test_mock_translate_reverses_words() -> None:
    result = mock_translate("one two three")
    assert result == "[uk] three two one"


def test_mock_translate_single_word() -> None:
    assert mock_translate("darkness") == "[uk] darkness"


def test_mock_translate_deterministic() -> None:
    text = "the dark and ancient horror"
    assert mock_translate(text) == mock_translate(text)


# ---------------------------------------------------------------------------
# generate_script: return type and structure
# ---------------------------------------------------------------------------

def test_generate_script_returns_script() -> None:
    scene = _scenes()[0]
    script = generate_script(scene, _MANIFEST)
    assert isinstance(script, Script)


def test_generate_script_story_and_scene_ids_match() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        assert script.story_id == scene.story_id
        assert script.scene_id == scene.scene_id


# ---------------------------------------------------------------------------
# Segment requirements
# ---------------------------------------------------------------------------

def test_segments_max_40_words() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for seg in script.segments:
            assert len(seg.text_en.split()) <= 40, (
                f"segment {seg.segment_id} exceeds 40 words in scene {scene.scene_id}"
            )


def test_segment_ids_are_sequential() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for i, seg in enumerate(script.segments):
            assert seg.segment_id == f"seg-{i}"


def test_segment_ids_match_schema_pattern() -> None:
    import re
    pattern = re.compile(r"^seg-[0-9]+$")
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for seg in script.segments:
            assert pattern.match(seg.segment_id)


def test_segment_pacing_ms_minimum_500() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for seg in script.segments:
            assert seg.pacing_ms >= 500


def test_segment_pacing_ms_formula() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for seg in script.segments:
            expected = max(500, len(seg.text_en.split()) * 100)
            assert seg.pacing_ms == expected


def test_segment_text_secondary_present() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for seg in script.segments:
            assert seg.text_secondary
            assert seg.text_secondary.startswith("[uk] ")


def test_segment_voice_id_is_narrator() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for seg in script.segments:
            assert seg.voice_id == _MANIFEST.voices["narrator"]


def test_segments_cover_narration_text() -> None:
    """Concatenated segment words should account for all non-dialogue words."""
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        all_seg_words = " ".join(seg.text_en for seg in script.segments).split()
        assert len(all_seg_words) > 0


# ---------------------------------------------------------------------------
# Dialogue requirements
# ---------------------------------------------------------------------------

def test_dialogue_extracted_for_all_three_scenes() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        assert len(script.dialogue_lines) >= 1, (
            f"expected dialogue in scene {scene.scene_id}"
        )


def test_dialogue_regex_does_not_cross_line_boundaries() -> None:
    """Narration line immediately before dialogue must not bleed into character name."""
    scene = Scene(
        story_id=STORY_ID,
        scene_id="test-regression",
        index=0,
        text="Shadows gathered in the room.\nBranner: Hello there.",
        visual_description="Shadows gathered in the room.",
        mood="dread",
        word_count=8,
    )
    script = generate_script(scene, _MANIFEST)
    assert len(script.dialogue_lines) == 1
    assert script.dialogue_lines[0].character == "Branner"
    # narration text must not be empty
    assert len(script.segments) >= 1
    narration = " ".join(seg.text_en for seg in script.segments)
    assert "Shadows" in narration


def test_dialogue_ids_are_sequential() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for j, dlg in enumerate(script.dialogue_lines):
            assert dlg.line_id == f"dlg-{j}"


def test_dialogue_ids_match_schema_pattern() -> None:
    import re
    pattern = re.compile(r"^dlg-[0-9]+$")
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for dlg in script.dialogue_lines:
            assert pattern.match(dlg.line_id)


def test_dialogue_character_names() -> None:
    scenes = _scenes()
    expected = [("Branner",), ("Griswell",), ("Branner",)]
    for scene, chars in zip(scenes, expected):
        script = generate_script(scene, _MANIFEST)
        extracted = tuple(d.character for d in script.dialogue_lines)
        assert extracted == chars


def test_dialogue_voice_id_lookup() -> None:
    scenes = _scenes()
    script0 = generate_script(scenes[0], _MANIFEST)
    assert script0.dialogue_lines[0].voice_id == _MANIFEST.voices["branner"]

    script1 = generate_script(scenes[1], _MANIFEST)
    assert script1.dialogue_lines[0].voice_id == _MANIFEST.voices["griswell"]


def test_dialogue_voice_id_fallback_to_narrator() -> None:
    manifest_no_char = Manifest(
        schema_version="1.0",
        story_id=STORY_ID,
        title="Test",
        seed=1,
        languages={"primary": "en", "secondary": "uk"},
        render={},
        voices={"narrator": "en-narrator-01"},
        adapters={},
        scenes=[],
    )
    scene = _scenes()[0]
    script = generate_script(scene, manifest_no_char)
    for dlg in script.dialogue_lines:
        assert dlg.voice_id == manifest_no_char.voices["narrator"]


def test_dialogue_pacing_ms_formula() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for dlg in script.dialogue_lines:
            expected = max(500, len(dlg.text_en.split()) * 100)
            assert dlg.pacing_ms == expected


def test_dialogue_text_secondary_present() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for dlg in script.dialogue_lines:
            assert dlg.text_secondary
            assert dlg.text_secondary.startswith("[uk] ")


def test_dialogue_insert_after_segment_type() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        for dlg in script.dialogue_lines:
            assert dlg.insert_after_segment is None or dlg.insert_after_segment.startswith("seg-")


def test_dialogue_insert_after_none_when_dialogue_first() -> None:
    """insert_after_segment is None when dialogue appears before any narration."""
    scene = Scene(
        story_id=STORY_ID,
        scene_id="test-scene",
        index=0,
        text="Branner: I see something dark.\n\nThe shadows gathered.",
        visual_description="The shadows gathered.",
        mood="dread",
        word_count=9,
    )
    script = generate_script(scene, _MANIFEST)
    assert script.dialogue_lines[0].insert_after_segment is None


# ---------------------------------------------------------------------------
# total_duration_ms
# ---------------------------------------------------------------------------

def test_total_duration_ms_equals_sum() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        expected = sum(s.pacing_ms for s in script.segments) + sum(
            d.pacing_ms for d in script.dialogue_lines
        )
        assert script.total_duration_ms == expected


def test_total_duration_ms_in_dict_matches_property() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        d = script.to_dict()
        assert d["total_duration_ms"] == script.total_duration_ms


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_all_scenes_validate_against_schema() -> None:
    for scene in _scenes():
        script = generate_script(scene, _MANIFEST)
        validate(script.to_dict(), "script.schema.json")


def test_fixture_scene_001_validates_against_scene_schema() -> None:
    data = json.loads((FIXTURES / "scene_001.json").read_text())
    validate(data, "scene.schema.json")


def test_scene_001_fixture_script_validates() -> None:
    data = json.loads((FIXTURES / "scene_001.json").read_text())
    scene = Scene(
        story_id=str(data["story_id"]),
        scene_id=str(data["scene_id"]),
        index=int(data["index"]),
        text=str(data["text"]),
        visual_description=str(data["visual_description"]),
        mood=str(data["mood"]),
        word_count=int(data["word_count"]),
    )
    script = generate_script(scene, _MANIFEST)
    validate(script.to_dict(), "script.schema.json")


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_repeated_runs_produce_identical_scripts() -> None:
    for scene in _scenes():
        run1 = generate_script(scene, _MANIFEST).to_dict()
        run2 = generate_script(scene, _MANIFEST).to_dict()
        assert run1 == run2


def test_dialogue_parsing_is_deterministic() -> None:
    for scene in _scenes():
        s1 = generate_script(scene, _MANIFEST)
        s2 = generate_script(scene, _MANIFEST)
        assert [d.to_dict() for d in s1.dialogue_lines] == [d.to_dict() for d in s2.dialogue_lines]


# ---------------------------------------------------------------------------
# generate_script_from_path (disk round-trip)
# ---------------------------------------------------------------------------

def test_generate_script_from_path(tmp_path: Path) -> None:
    scene_path = FIXTURES / "scene_001.json"
    script = generate_script_from_path(scene_path, _MANIFEST)
    validate(script.to_dict(), "script.schema.json")


# ---------------------------------------------------------------------------
# artifact_index update
# ---------------------------------------------------------------------------

def test_script_artifact_index_update(tmp_path: Path) -> None:
    """Script path is recorded in artifact_index after writing."""
    from horror_story.manifest import ArtifactIndex, SceneEntry, initialize_run
    from horror_story.config import PipelineConfig, StoryConfig, RenderConfig, AdapterConfig

    config = PipelineConfig(
        story=StoryConfig(
            id=STORY_ID,
            title="Pigeons from Hell",
            primary_language="en",
            secondary_language="uk",
            seed=42,
        ),
        render=RenderConfig(width=3840, height=2160, fps=24, codec="libx264", audio_codec="aac"),
        adapters=AdapterConfig(tts="mock", image="mock", motion="mock", audio="mock", typography="mock"),
        voices={"narrator": "en-narrator-01", "griswell": "en-male-deep", "branner": "en-male-mid"},
    )

    manifest, artifact_index, scenes = initialize_run(
        config, STORY_TEXT, "mini-story.txt", tmp_path
    )

    run_dir = tmp_path / "run_pigeons-from-hell_42"
    scripts_dir = run_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    index_path = run_dir / "artifact_index.json"

    for scene in scenes:
        script = generate_script(scene, manifest)
        script_path = scripts_dir / f"script_{scene.scene_id}.json"
        script_json = json.dumps(script.to_dict(), indent=2)
        tmp = script_path.with_suffix(".tmp")
        tmp.write_text(script_json)
        tmp.replace(script_path)

        rel_path = f"scripts/script_{scene.scene_id}.json"
        artifact_index.scenes[scene.scene_id].script = rel_path
        artifact_index.scenes[scene.scene_id].status = "partial"

    artifact_index.write(index_path)

    updated = json.loads(index_path.read_text())
    validate(updated, "artifact_index.schema.json")
    for scene in scenes:
        entry = updated["scenes"][scene.scene_id]
        assert entry["script"] == f"scripts/script_{scene.scene_id}.json"
        assert entry["status"] == "partial"
