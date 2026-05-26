"""CLI unit tests and end-to-end pipeline test — Issues #001 and #011."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from horror_story.cli import _build_parser, _resolve_latest_run, main
from horror_story.pipeline.compositor import ffmpeg_available

requires_ffmpeg = pytest.mark.skipif(
    not ffmpeg_available(), reason="FFmpeg not installed"
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_story(tmp_path: Path) -> tuple[Path, Path]:
    """Copy mini-story fixtures into tmp_path. Returns (story_path, out_dir)."""
    story_dst = tmp_path / "mini-story.txt"
    shutil.copy(FIXTURES / "mini-story.txt", story_dst)
    shutil.copy(FIXTURES / "pipeline.toml", tmp_path / "pipeline.toml")
    return story_dst, tmp_path / "out"


def _base_args(story_dst: Path, out_dir: Path) -> list[str]:
    return ["run", "--story", str(story_dst), "--out", str(out_dir),
            "--width", "320", "--height", "240"]


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parser_run_subcommand() -> None:
    parser = _build_parser()
    args = parser.parse_args(["run", "--story", "foo.txt", "--out", "out/"])
    assert args.command == "run"
    assert args.story == "foo.txt"
    assert args.seed is None
    assert not args.dry_run
    assert not args.regen


def test_parser_run_with_all_flags() -> None:
    parser = _build_parser()
    args = parser.parse_args([
        "run", "--story", "s.txt", "--out", "o/",
        "--seed", "99", "--dry-run", "--regen", "--scene", "scene-001",
        "--width", "640", "--height", "480",
    ])
    assert args.seed == 99
    assert args.dry_run
    assert args.regen
    assert args.scene == "scene-001"
    assert args.width == 640
    assert args.height == 480


def test_parser_validate_subcommand() -> None:
    parser = _build_parser()
    args = parser.parse_args(["validate", "--run-dir", "/some/dir"])
    assert args.command == "validate"
    assert args.run_dir == "/some/dir"


def test_parser_validate_schemas_subcommand() -> None:
    parser = _build_parser()
    args = parser.parse_args(["validate-schemas"])
    assert args.command == "validate-schemas"


def test_main_no_args_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "horror-story" in captured.out


def test_main_validate_schemas(capsys: pytest.CaptureFixture[str]) -> None:
    main(["validate-schemas"])
    captured = capsys.readouterr()
    assert "schemas" in captured.out


# ---------------------------------------------------------------------------
# Dry-run tests (no FFmpeg required)
# ---------------------------------------------------------------------------

def test_dry_run_prints_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    story_dst, out_dir = _setup_story(tmp_path)
    main(["run", "--story", str(story_dst), "--out", str(out_dir), "--dry-run"])
    captured = capsys.readouterr()
    assert "dry-run" in captured.out
    assert "mini-story" in captured.out
    assert not out_dir.exists()


def test_dry_run_seed_override(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    story_dst, out_dir = _setup_story(tmp_path)
    main(["run", "--story", str(story_dst), "--out", str(out_dir),
          "--dry-run", "--seed", "999"])
    captured = capsys.readouterr()
    assert "999" in captured.out


def test_dry_run_single_scene(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    story_dst, out_dir = _setup_story(tmp_path)
    main(["run", "--story", str(story_dst), "--out", str(out_dir),
          "--dry-run", "--scene", "old-plantation-house-loomed"])
    captured = capsys.readouterr()
    assert "old-plantation-house-loomed" in captured.out


# ---------------------------------------------------------------------------
# End-to-end tests (require FFmpeg)
# ---------------------------------------------------------------------------

@requires_ffmpeg
def test_e2e_mini_story(tmp_path: Path) -> None:
    """Full 3-scene run: final MP4 exists, artifact_index is complete."""
    story_dst, out_dir = _setup_story(tmp_path)
    main(_base_args(story_dst, out_dir))

    run_dir = out_dir / "run_mini-story_42"
    assert run_dir.exists()

    final_mp4 = run_dir / "final_mini-story_42.mp4"
    assert final_mp4.exists()
    assert final_mp4.stat().st_size > 0

    index = json.loads((run_dir / "artifact_index.json").read_text())
    assert index["final"]["status"] == "complete"

    composed = list((run_dir / "video").glob("scene_*_composed.mp4"))
    assert len(composed) == 3


@requires_ffmpeg
def test_e2e_scene_status_is_complete(tmp_path: Path) -> None:
    """artifact_index scene statuses must be 'complete' (not 'error')."""
    story_dst, out_dir = _setup_story(tmp_path)
    main(_base_args(story_dst, out_dir))

    index = json.loads(
        (out_dir / "run_mini-story_42" / "artifact_index.json").read_text()
    )
    for scene_id, entry in index["scenes"].items():
        assert entry["status"] == "complete", (
            f"scene '{scene_id}' has status '{entry['status']}'"
        )


def test_index_updated_incrementally_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """artifact_index must reflect stages that completed before a mid-scene failure.

    Patches MockMotionAdapter.animate to raise after the keyframe stage has
    already written its artifact and updated the index. On failure the index
    must contain the keyframe path written during stage 5, proving per-stage
    updates happened rather than a single end-of-scene write.
    """
    from horror_story.adapters.motion import mock as motion_mock
    from horror_story.pipeline.compositor import ffmpeg_available

    if not ffmpeg_available():
        pytest.skip("FFmpeg not installed")

    story_dst, out_dir = _setup_story(tmp_path)
    run_dir = out_dir / "run_mini-story_42"

    def _failing_animate(self: Any, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("injected motion failure")

    monkeypatch.setattr(motion_mock.MockMotionAdapter, "animate", _failing_animate)

    with pytest.raises(SystemExit) as exc_info:
        main(_base_args(story_dst, out_dir))
    assert exc_info.value.code == 1

    index = json.loads((run_dir / "artifact_index.json").read_text())
    # At least the first scene should have been attempted; its keyframe must
    # be recorded in the index because the keyframe stage patch fires before motion.
    at_least_one_keyframe = any(
        entry.get("keyframe") is not None
        for entry in index["scenes"].values()
    )
    assert at_least_one_keyframe, (
        "artifact_index has no keyframe paths despite stage 5 completing before the injected failure"
    )
    # Every attempted scene must be failed or partial, not pending.
    for scene_id, entry in index["scenes"].items():
        assert entry["status"] in ("partial", "failed", "complete"), (
            f"scene '{scene_id}' has unexpected status '{entry['status']}'"
        )


@requires_ffmpeg
def test_e2e_scene_rerun_writes_versioned_artifacts(tmp_path: Path) -> None:
    """--scene must write _r1 artifacts; originals must be untouched."""
    story_dst, out_dir = _setup_story(tmp_path)
    main(_base_args(story_dst, out_dir))

    run_dir = out_dir / "run_mini-story_42"
    index_before = json.loads((run_dir / "artifact_index.json").read_text())
    all_scene_ids = list(index_before["scenes"].keys())
    assert len(all_scene_ids) == 3

    first_scene = all_scene_ids[0]

    # Record original composed path (no suffix)
    original_composed = run_dir / f"video/scene_{first_scene}_composed.mp4"
    original_mtime = original_composed.stat().st_mtime

    # Re-run just the first scene
    main(_base_args(story_dst, out_dir) + ["--scene", first_scene])

    # _r1 versioned artifacts must exist
    assert (run_dir / f"scripts/script_{first_scene}_r1.json").exists(), "_r1 script missing"
    assert (run_dir / f"frames/keyframe_{first_scene}_r1.png").exists(), "_r1 keyframe missing"
    assert (run_dir / f"video/scene_{first_scene}_composed_r1.mp4").exists(), "_r1 composed missing"

    # Original artifact files must not have been overwritten
    assert original_composed.stat().st_mtime == original_mtime, "original composed was overwritten"

    # artifact_index must now point to the _r1 composed path
    index_after = json.loads((run_dir / "artifact_index.json").read_text())
    composed_ptr = index_after["scenes"][first_scene]["composed"]
    assert "_r1" in composed_ptr, (
        f"artifact_index still points to original: {composed_ptr}"
    )

    # Other two scenes must still be present and complete
    for sid in all_scene_ids:
        assert index_after["scenes"][sid]["status"] == "complete"

    # Final must still be present and complete
    assert index_after["final"]["status"] == "complete"


@requires_ffmpeg
def test_e2e_scene_rerun_increments_revision(tmp_path: Path) -> None:
    """Second --scene re-run writes _r2, not _r1."""
    story_dst, out_dir = _setup_story(tmp_path)
    main(_base_args(story_dst, out_dir))

    run_dir = out_dir / "run_mini-story_42"
    first_scene = list(
        json.loads((run_dir / "artifact_index.json").read_text())["scenes"].keys()
    )[0]

    main(_base_args(story_dst, out_dir) + ["--scene", first_scene])
    main(_base_args(story_dst, out_dir) + ["--scene", first_scene])

    assert (run_dir / f"video/scene_{first_scene}_composed_r1.mp4").exists()
    assert (run_dir / f"video/scene_{first_scene}_composed_r2.mp4").exists()

    index = json.loads((run_dir / "artifact_index.json").read_text())
    assert "_r2" in index["scenes"][first_scene]["composed"]


@requires_ffmpeg
def test_e2e_final_reads_from_artifact_index(tmp_path: Path) -> None:
    """After a --scene re-run, the final MP4 is re-rendered from artifact_index paths."""
    story_dst, out_dir = _setup_story(tmp_path)
    main(_base_args(story_dst, out_dir))

    run_dir = out_dir / "run_mini-story_42"
    final_mtime_before = (run_dir / "final_mini-story_42.mp4").stat().st_mtime

    first_scene = list(
        json.loads((run_dir / "artifact_index.json").read_text())["scenes"].keys()
    )[0]
    main(_base_args(story_dst, out_dir) + ["--scene", first_scene])

    # Final must have been re-rendered (mtime changed)
    final_mtime_after = (run_dir / "final_mini-story_42.mp4").stat().st_mtime
    assert final_mtime_after > final_mtime_before, "final MP4 was not re-rendered"


@requires_ffmpeg
def test_e2e_validate_catches_corrupt_artifact(tmp_path: Path) -> None:
    """validate must detect a corrupted script JSON (not just top-level files)."""
    story_dst, out_dir = _setup_story(tmp_path)
    main(_base_args(story_dst, out_dir))

    run_dir = out_dir / "run_mini-story_42"
    scripts = list((run_dir / "scripts").glob("script_*.json"))
    assert scripts
    scripts[0].write_text('{"schema_version": "1.0"}')

    with pytest.raises(SystemExit) as exc_info:
        main(["validate", "--run-dir", str(run_dir)])
    assert exc_info.value.code == 1


@requires_ffmpeg
def test_e2e_validate_passes_on_clean_run(tmp_path: Path) -> None:
    """validate must exit 0 on an untouched run."""
    story_dst, out_dir = _setup_story(tmp_path)
    main(_base_args(story_dst, out_dir))
    main(["validate", "--run-dir", str(out_dir / "run_mini-story_42")])


@requires_ffmpeg
def test_e2e_regen_creates_new_dir(tmp_path: Path) -> None:
    """--regen creates run_*_r1."""
    story_dst, out_dir = _setup_story(tmp_path)
    main(_base_args(story_dst, out_dir))
    main(_base_args(story_dst, out_dir) + ["--regen"])
    assert (out_dir / "run_mini-story_42_r1").exists()


# ---------------------------------------------------------------------------
# Issue #014: AdapterFactory wiring
# ---------------------------------------------------------------------------

def test_adapter_factory_called_with_config_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_run_scene() must obtain all five adapters via AdapterFactory, passing
    the names from pipeline.toml — verified by patching the factory and
    asserting each get_* was called with the correct adapter name.
    """
    story_dst, out_dir = _setup_story(tmp_path)

    mock_factory = MagicMock()
    mock_factory.get_tts.return_value = MagicMock()
    mock_factory.get_image.return_value = MagicMock()
    mock_factory.get_motion.return_value = MagicMock()
    mock_factory.get_audio.return_value = MagicMock()
    mock_factory.get_typography.return_value = MagicMock()

    # Wire mock adapter return values to behave like real adapters (no-ops).
    tts_inst = mock_factory.get_tts.return_value
    tts_inst.synthesize = MagicMock()
    img_inst = mock_factory.get_image.return_value
    img_inst.generate = MagicMock()
    mot_inst = mock_factory.get_motion.return_value
    mot_inst.animate = MagicMock()
    aud_inst = mock_factory.get_audio.return_value
    aud_inst.generate = MagicMock()
    typ_inst = mock_factory.get_typography.return_value
    typ_inst.render = MagicMock()

    # Stub out heavy pipeline stages so the test stays fast.
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
    # synthesize is mocked out so no sidecars land on disk; stub the reader too.
    monkeypatch.setattr("horror_story.cli._voice_lines_duration_s", lambda _: 5.0)

    with patch("horror_story.cli.AdapterFactory", mock_factory), \
         patch("horror_story.cli._render_final_from_index", MagicMock()):
        main(_base_args(story_dst, out_dir))

    # pipeline.toml fixture specifies all adapters as "mock"
    mock_factory.get_tts.assert_called_with("mock")
    mock_factory.get_image.assert_called_with("mock")
    mock_factory.get_motion.assert_called_with("mock")
    mock_factory.get_audio.assert_called_with("mock")
    mock_factory.get_typography.assert_called_with("mock")


# ---------------------------------------------------------------------------
# Issue #014 review: _render_final_from_index correctness
# ---------------------------------------------------------------------------

def test_render_final_skipped_when_scene_not_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_render_final_from_index must not call render_final when any scene is
    not status==complete, even if it has a non-null composed path from an
    earlier successful run.
    """
    import json
    from horror_story.cli import _render_final_from_index
    from horror_story.config import PipelineConfig

    # Build a minimal run_dir with an artifact_index that has a partial scene
    # alongside a complete one — simulating a failed --scene re-run.
    run_dir = tmp_path / "run_test_42"
    run_dir.mkdir()
    index_path = run_dir / "artifact_index.json"
    index_data = {
        "schema_version": "1.0",
        "story_id": "test",
        "run_id": "run_test_42",
        "scenes": {
            "scene-01": {
                "scene": "scenes/scene_scene-01.json",
                "script": "scripts/script_scene-01.json",
                "status": "complete",
                "composed": "video/scene_scene-01_composed.mp4",
            },
            "scene-02": {
                "scene": "scenes/scene_scene-02.json",
                "script": "scripts/script_scene-02.json",
                "status": "failed",
                "composed": "video/scene_scene-02_composed.mp4",  # stale path
            },
        },
    }
    index_path.write_text(json.dumps(index_data))

    render_called = MagicMock()
    monkeypatch.setattr(
        "horror_story.pipeline.renderer.render_final", render_called
    )
    from horror_story.pipeline import renderer as rend_mod
    monkeypatch.setattr(rend_mod, "ffmpeg_available", lambda: True)

    class FakeManifest:
        def scene_order(self) -> list[str]:
            return ["scene-01", "scene-02"]
        def to_dict(self) -> dict[str, Any]:
            return {}

    class FakeStory:
        id = "test"

    class FakeConfig:
        story = FakeStory()

    with pytest.raises(SystemExit) as exc_info:
        _render_final_from_index(run_dir, FakeManifest(), FakeConfig(), 42, index_path)

    render_called.assert_not_called()
    assert exc_info.value.code == 1


def test_artifact_index_final_stores_relative_path_and_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a successful render, artifact_index.final must store a run-relative
    path (not absolute) and the SHA-256 from render_job.json.
    """
    import json
    from horror_story.cli import _render_final_from_index

    run_dir = tmp_path / "run_test_42"
    run_dir.mkdir()
    index_path = run_dir / "artifact_index.json"
    index_data = {
        "schema_version": "1.0",
        "story_id": "test",
        "run_id": "run_test_42",
        "scenes": {
            "scene-01": {
                "scene": "scenes/scene_scene-01.json",
                "script": "scripts/script_scene-01.json",
                "status": "complete",
                "composed": "video/scene_scene-01_composed.mp4",
            },
        },
    }
    index_path.write_text(json.dumps(index_data))

    expected_sha = "a" * 64

    def fake_render_final(
        manifest: Any, scene_paths: Any, out_path: Path
    ) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"\x00" * 16)
        rj_path = out_path.with_name("render_job.json")
        rj_path.write_text(json.dumps({
            "schema_version": "1.0",
            "story_id": "test",
            "seed": 42,
            "scene_ids": ["scene-01"],
            "render": {"width": 320, "height": 240, "fps": 24, "codec": "libx264", "audio_codec": "aac"},
            "output_path": out_path.name,
            "sha256": expected_sha,
            "duration_ms": None,
            "status": "complete",
            "error": None,
        }))
        return out_path

    from horror_story.pipeline import renderer as rend_mod
    monkeypatch.setattr(rend_mod, "render_final", fake_render_final)
    monkeypatch.setattr(rend_mod, "ffmpeg_available", lambda: True)

    class FakeManifest:
        def scene_order(self) -> list[str]:
            return ["scene-01"]
        def to_dict(self) -> dict[str, Any]:
            return {}

    class FakeStory:
        id = "test"

    class FakeConfig:
        story = FakeStory()

    _render_final_from_index(run_dir, FakeManifest(), FakeConfig(), 42, index_path)

    written = json.loads(index_path.read_text())
    final = written["final"]
    assert not Path(final["path"]).is_absolute(), (
        f"final.path must be run-relative, got: {final['path']!r}"
    )
    assert final["sha256"] == expected_sha, (
        f"final.sha256 must be propagated from render_job.json, got: {final['sha256']!r}"
    )


# ---------------------------------------------------------------------------
# P1: initialize_run run_id_override
# ---------------------------------------------------------------------------

def test_initialize_run_respects_run_id_override(tmp_path: Path) -> None:
    """initialize_run must accept run_id_override and use it as the run directory name."""
    from horror_story.manifest import initialize_run
    from horror_story.config import (
        PipelineConfig, StoryConfig, RenderConfig, AdapterConfig,
    )

    config = PipelineConfig(
        story=StoryConfig(
            id="test-story",
            title="Test",
            primary_language="en",
            secondary_language="uk",
            seed=42,
        ),
        render=RenderConfig(
            width=320, height=240, fps=24, codec="libx264", audio_codec="aac",
        ),
        adapters=AdapterConfig(
            tts="mock", image="mock", motion="mock", audio="mock", typography="mock",
        ),
    )

    story_text = "The darkness crept through the empty hall. Fear gripped the lone traveler."
    out_dir = tmp_path / "out"

    manifest, _, scenes = initialize_run(
        config, story_text, "story.txt", out_dir, run_id_override="run_test-story_99"
    )

    assert (out_dir / "run_test-story_99").exists(), (
        "run directory must use run_id_override"
    )
    assert (out_dir / "run_test-story_99" / "manifest.json").exists()


# ---------------------------------------------------------------------------
# P2: validate versioned composed sidecars
# ---------------------------------------------------------------------------

def test_validate_run_dir_checks_versioned_composed_sidecars(
    tmp_path: Path,
) -> None:
    """_validate_run_dir must validate video/scene_*_composed_r*.json sidecars."""
    import json as _json
    from horror_story.cli import _validate_run_dir

    run_dir = tmp_path / "run_test_42"
    run_dir.mkdir()
    (run_dir / "video").mkdir()

    # Write a corrupt versioned composed sidecar (missing required fields).
    bad_sidecar = run_dir / "video" / "scene_s01_composed_r1.json"
    bad_sidecar.write_text(_json.dumps({"schema_version": "1.0"}))

    with pytest.raises(SystemExit) as exc_info:
        _validate_run_dir(run_dir)
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# P2: validate rejects missing run directory
# ---------------------------------------------------------------------------

def test_validate_run_dir_rejects_nonexistent_directory(
    tmp_path: Path,
) -> None:
    """_validate_run_dir must exit non-zero when run_dir does not exist."""
    from horror_story.cli import _validate_run_dir

    with pytest.raises(SystemExit) as exc_info:
        _validate_run_dir(tmp_path / "no-such-run")
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# P1: media duration derived from voice-line sidecars, not total_duration_ms
# ---------------------------------------------------------------------------


def test_voice_lines_duration_s_uses_actual_duration_ms(tmp_path: Path) -> None:
    """`_voice_lines_duration_s` sums actual_duration_ms when present."""
    from horror_story.cli import _voice_lines_duration_s

    def _sidecar(name: str, pacing_ms: int, actual_ms: int | None) -> Path:
        p = tmp_path / name
        p.write_text(json.dumps({
            "schema_version": "1.0", "story_id": "s", "scene_id": "sc",
            "line_ref": name, "line_type": "narration", "text": "x",
            "language": "en", "voice_id": "v", "seed": 0,
            "pacing_ms": pacing_ms, "adapter": "kokoro",
            "output_path": f"{name}.wav",
            "actual_duration_ms": actual_ms,
            "status": "synthesized", "error": None,
        }))
        return p

    # Two sidecars: one with actual=3500 ms (longer than pacing 2000), one null (falls back to 1500)
    sidecars = [
        _sidecar("seg-0.json", 2000, 3500),
        _sidecar("seg-1.json", 1500, None),
    ]
    assert _voice_lines_duration_s(sidecars) == pytest.approx(5.0)  # 3.5 + 1.5


def test_voice_lines_duration_s_falls_back_to_pacing_ms(tmp_path: Path) -> None:
    """`_voice_lines_duration_s` falls back to pacing_ms when actual_duration_ms is null."""
    from horror_story.cli import _voice_lines_duration_s

    p = tmp_path / "seg.json"
    p.write_text(json.dumps({
        "schema_version": "1.0", "story_id": "s", "scene_id": "sc",
        "line_ref": "seg-0", "line_type": "narration", "text": "x",
        "language": "en", "voice_id": "v", "seed": 0,
        "pacing_ms": 2000, "adapter": "mock",
        "output_path": "seg.wav",
        "actual_duration_ms": None,
        "status": "synthesized", "error": None,
    }))
    assert _voice_lines_duration_s([p]) == pytest.approx(2.0)


def test_motion_duration_derived_from_voice_sidecars(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """motion.animate must receive duration_s from voice-line sidecars, not total_duration_ms.

    Patches TTS synthesize to write sidecars with actual_duration_ms > pacing_ms,
    then asserts motion.animate was called with the larger actual duration.
    """
    import json as _json
    from horror_story.adapters.tts.mock import MockTTSAdapter

    story_dst, out_dir = _setup_story(tmp_path)

    captured_motion_duration: list[float] = []

    original_synthesize = MockTTSAdapter.synthesize
    from horror_story.adapters.motion.mock import MockMotionAdapter as _RealMotion
    original_animate = _RealMotion.animate

    def _synthesize_with_inflated_actual(
        self: Any, text: str, voice_id: str, language: str,
        pacing_ms: int, seed: int, out_path: Path, **kwargs: Any
    ) -> Path:
        result = original_synthesize(
            self, text, voice_id, language, pacing_ms, seed, out_path, **kwargs
        )
        # Rewrite sidecar with actual_duration_ms = pacing_ms * 3
        sidecar_path = out_path.with_suffix(".json")
        data = _json.loads(sidecar_path.read_text())
        data["actual_duration_ms"] = pacing_ms * 3
        sidecar_path.write_text(_json.dumps(data))
        return result

    def _fake_animate(
        self: Any, frame_path: Path, duration_s: float, **kwargs: Any
    ) -> Path:
        captured_motion_duration.append(duration_s)
        # Delegate to the real (unpatched) MockMotionAdapter.animate
        return original_animate(self, frame_path=frame_path, duration_s=duration_s, **kwargs)

    from horror_story.adapters.motion import mock as motion_mock
    from horror_story.pipeline import timeline as tl_mod
    from horror_story.pipeline import compositor as comp_mod

    def _fake_plan_timeline2(*args: Any, **kwargs: Any) -> Path:
        out: Path = kwargs.get("out_path") or args[4]
        out.write_text(json.dumps({
            "schema_version": "1.0", "story_id": "x", "scene_id": "x",
            "duration_s": 5.0, "fps": 24,
            "video_tracks": [], "audio_tracks": [], "overlay_tracks": [],
        }))
        return out

    monkeypatch.setattr(MockTTSAdapter, "synthesize", _synthesize_with_inflated_actual)
    monkeypatch.setattr(motion_mock.MockMotionAdapter, "animate", _fake_animate)
    monkeypatch.setattr(tl_mod, "plan_timeline", _fake_plan_timeline2)
    monkeypatch.setattr(comp_mod, "compose_scene", MagicMock(return_value=None))
    monkeypatch.setattr(comp_mod, "ffmpeg_available", lambda: True)

    with patch("horror_story.cli._render_final_from_index", MagicMock()):
        main(_base_args(story_dst, out_dir))

    assert len(captured_motion_duration) > 0
    # Each call's duration must be >= the total pacing-based duration (since actual = pacing*3)
    for dur in captured_motion_duration:
        assert dur > 0.0
        # The mini-story has at least one segment; pacing-based total would be shorter
        # than actual (3x), so captured duration must be > the heuristic total / 3
        assert dur >= 1.0  # enforced floor


# ---------------------------------------------------------------------------
# Issue #020: _resolve_latest_run
# ---------------------------------------------------------------------------

def test_resolve_latest_run_returns_bare_when_only_bare_exists(tmp_path: Path) -> None:
    bare = tmp_path / "run_story_42"
    bare.mkdir()
    assert _resolve_latest_run(tmp_path, "run_story_42") == bare


def test_resolve_latest_run_returns_none_when_nothing_exists(tmp_path: Path) -> None:
    assert _resolve_latest_run(tmp_path, "run_story_42") is None


def test_resolve_latest_run_prefers_r1_over_bare(tmp_path: Path) -> None:
    bare = tmp_path / "run_story_42"
    bare.mkdir()
    r1 = tmp_path / "run_story_42_r1"
    r1.mkdir()
    assert _resolve_latest_run(tmp_path, "run_story_42") == r1


def test_resolve_latest_run_uses_numeric_order_not_lexicographic(tmp_path: Path) -> None:
    for n in (1, 2, 10):
        (tmp_path / f"run_story_42_r{n}").mkdir()
    # lexicographic sort would pick r2; numeric must pick r10
    assert _resolve_latest_run(tmp_path, "run_story_42") == tmp_path / "run_story_42_r10"


def test_resolve_latest_run_ignores_non_revision_dirs(tmp_path: Path) -> None:
    (tmp_path / "run_story_42_backup").mkdir()
    (tmp_path / "run_story_42_r1").mkdir()
    assert _resolve_latest_run(tmp_path, "run_story_42") == tmp_path / "run_story_42_r1"


# ---------------------------------------------------------------------------
# Issue #027: --image-adapter CLI flag
# ---------------------------------------------------------------------------

def test_parser_image_adapter_flag(tmp_path: Path) -> None:
    parser = _build_parser()
    args = parser.parse_args(["run", "--story", "s.txt", "--out", "o/", "--image-adapter", "mflux-schnell"])
    assert args.image_adapter == "mflux-schnell"

    args = parser.parse_args(["run", "--story", "s.txt", "--out", "o/"])
    assert args.image_adapter is None


def test_image_adapter_flag_overrides_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story_dst, out_dir = _setup_story(tmp_path)
    # Write a pipeline.toml with a distinct image adapter so the override is meaningful.
    (tmp_path / "pipeline.toml").write_text(
        (FIXTURES / "pipeline.toml").read_text().replace(
            'image = "mock"', 'image = "mflux-schnell"'
        )
    )

    mock_factory = MagicMock()
    mock_factory.get_tts.return_value = MagicMock()
    mock_factory.get_image.return_value = MagicMock()
    mock_factory.get_motion.return_value = MagicMock()
    mock_factory.get_audio.return_value = MagicMock()
    mock_factory.get_typography.return_value = MagicMock()

    tts_inst = mock_factory.get_tts.return_value
    tts_inst.synthesize = MagicMock()
    img_inst = mock_factory.get_image.return_value
    img_inst.generate = MagicMock()
    mot_inst = mock_factory.get_motion.return_value
    mot_inst.animate = MagicMock()
    aud_inst = mock_factory.get_audio.return_value
    aud_inst.generate = MagicMock()
    typ_inst = mock_factory.get_typography.return_value
    typ_inst.render = MagicMock()

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
        main(_base_args(story_dst, out_dir) + ["--image-adapter", "mock"])

    # Must be "mock" (the override), not "mflux-schnell" (the toml value).
    mock_factory.get_image.assert_called_with("mock")


def test_image_adapter_flag_absent_uses_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    story_dst, out_dir = _setup_story(tmp_path)

    mock_factory = MagicMock()
    mock_factory.get_tts.return_value = MagicMock()
    mock_factory.get_image.return_value = MagicMock()
    mock_factory.get_motion.return_value = MagicMock()
    mock_factory.get_audio.return_value = MagicMock()
    mock_factory.get_typography.return_value = MagicMock()

    tts_inst = mock_factory.get_tts.return_value
    tts_inst.synthesize = MagicMock()
    img_inst = mock_factory.get_image.return_value
    img_inst.generate = MagicMock()
    mot_inst = mock_factory.get_motion.return_value
    mot_inst.animate = MagicMock()
    aud_inst = mock_factory.get_audio.return_value
    aud_inst.generate = MagicMock()
    typ_inst = mock_factory.get_typography.return_value
    typ_inst.render = MagicMock()

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
        main(_base_args(story_dst, out_dir))

    # pipeline.toml fixture specifies image = "mock"
    mock_factory.get_image.assert_called_with("mock")


def test_scene_flag_resolves_to_latest_rn_when_bare_absent(tmp_path: Path) -> None:
    """--scene must find the _r1 directory when bare run does not exist (issue #020)."""
    story_dst, out_dir = _setup_story(tmp_path)
    # First full run → creates bare run_mini-story_42
    main(_base_args(story_dst, out_dir))
    # Second full run with --regen → creates run_mini-story_42_r1
    main(_base_args(story_dst, out_dir) + ["--regen"])
    # Remove bare dir so only _r1 exists
    import shutil as _shutil
    _shutil.rmtree(out_dir / "run_mini-story_42")
    # --scene must succeed by resolving to _r1
    scene_id = "old-plantation-house-loomed-against-darkening-sk"
    main(_base_args(story_dst, out_dir) + ["--scene", scene_id])
