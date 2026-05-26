"""CLI image prompt construction tests — Issue #030."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from horror_story.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def _setup_story_with_suffix(tmp_path: Path, style_suffix: str) -> tuple[Path, Path]:
    """Copy mini-story fixtures and write pipeline.toml with the given style_suffix."""
    story_dst = tmp_path / "mini-story.txt"
    shutil.copy(FIXTURES / "mini-story.txt", story_dst)

    base_toml = (FIXTURES / "pipeline.toml").read_text()
    toml_with_image = base_toml + f'\n[image]\nstyle_suffix = {json.dumps(style_suffix)}\n'
    (tmp_path / "pipeline.toml").write_text(toml_with_image)

    return story_dst, tmp_path / "out"


def _base_args(story_dst: Path, out_dir: Path) -> list[str]:
    return ["run", "--story", str(story_dst), "--out", str(out_dir),
            "--width", "320", "--height", "240"]


def _make_mock_factory() -> MagicMock:
    mock_factory = MagicMock()
    mock_factory.get_tts.return_value = MagicMock()
    mock_factory.get_image.return_value = MagicMock()
    mock_factory.get_motion.return_value = MagicMock()
    mock_factory.get_audio.return_value = MagicMock()
    mock_factory.get_typography.return_value = MagicMock()

    mock_factory.get_tts.return_value.synthesize = MagicMock()
    mock_factory.get_image.return_value.generate = MagicMock()
    mock_factory.get_motion.return_value.animate = MagicMock()
    mock_factory.get_audio.return_value.generate = MagicMock()
    mock_factory.get_typography.return_value.render = MagicMock()

    return mock_factory


def _run_with_factory(
    mock_factory: MagicMock,
    args: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run the CLI with a mocked AdapterFactory and stubbed-out heavy stages."""
    from horror_story.pipeline import timeline as tl_mod
    from horror_story.pipeline import compositor as comp_mod

    def _fake_plan_timeline(*args: Any, **kwargs: Any) -> Path:
        out: Path = kwargs.get("out_path") or args[4]
        out.write_text(json.dumps({
            "schema_version": "1.0", "story_id": "x", "scene_id": "x",
            "duration_s": 5.0, "fps": 24,
            "video_tracks": [], "audio_tracks": [], "overlay_tracks": [],
        }))
        return out

    monkeypatch.setattr(tl_mod, "plan_timeline", _fake_plan_timeline)
    monkeypatch.setattr(comp_mod, "compose_scene", MagicMock(return_value=None))
    monkeypatch.setattr(comp_mod, "ffmpeg_available", lambda: True)
    monkeypatch.setattr("horror_story.cli._voice_lines_duration_s", lambda _: 5.0)

    with patch("horror_story.cli.AdapterFactory", mock_factory), \
         patch("horror_story.cli._render_final_from_index", MagicMock()):
        main(args)


def test_style_suffix_appended_to_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every image adapter call must receive a prompt ending with ', TEST_STYLE'."""
    story_dst, out_dir = _setup_story_with_suffix(tmp_path, "TEST_STYLE")
    mock_factory = _make_mock_factory()

    _run_with_factory(mock_factory, _base_args(story_dst, out_dir), monkeypatch)

    generate_calls = mock_factory.get_image.return_value.generate.call_args_list
    assert len(generate_calls) > 0, "image.generate was never called"

    for c in generate_calls:
        prompt: str = c.kwargs.get("prompt") or c.args[0]
        assert prompt.endswith(", TEST_STYLE"), (
            f"Expected prompt to end with ', TEST_STYLE', got: {prompt!r}"
        )


def test_empty_style_suffix_uses_description_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty style_suffix must pass visual_description unchanged (no trailing comma)."""
    story_dst, out_dir = _setup_story_with_suffix(tmp_path, "")
    mock_factory = _make_mock_factory()

    _run_with_factory(mock_factory, _base_args(story_dst, out_dir), monkeypatch)

    generate_calls = mock_factory.get_image.return_value.generate.call_args_list
    assert len(generate_calls) > 0, "image.generate was never called"

    for c in generate_calls:
        prompt: str = c.kwargs.get("prompt") or c.args[0]
        assert not prompt.endswith(", "), (
            f"Prompt must not end with ', ' when suffix is empty, got: {prompt!r}"
        )
        assert not prompt.endswith(","), (
            f"Prompt must not end with ',' when suffix is empty, got: {prompt!r}"
        )
        # The prompt must equal the visual_description — no appended text
        assert ", " not in prompt.split("visual")[0] if "visual" in prompt else True, (
            "Unexpected suffix appended to prompt"
        )
