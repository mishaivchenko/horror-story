"""Tests for MetricsCollector and StageTimer — Issue #029."""
from __future__ import annotations

import json
import shutil
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from horror_story.metrics import MetricsCollector

FIXTURES = Path(__file__).parent / "fixtures"


def _setup_story(tmp_path: Path) -> tuple[Path, Path]:
    story_dst = tmp_path / "mini-story.txt"
    shutil.copy(FIXTURES / "mini-story.txt", story_dst)
    shutil.copy(FIXTURES / "pipeline.toml", tmp_path / "pipeline.toml")
    return story_dst, tmp_path / "out"


def _make_collector() -> MetricsCollector:
    return MetricsCollector(story_id="test-story", run_id="run_test-story_1")


def test_stage_timer_records_duration() -> None:
    metrics = _make_collector()
    with metrics.stage("parse"):
        pass
    assert len(metrics._stages) == 1
    entry = metrics._stages[0]
    assert entry.stage == "parse"
    assert entry.duration_s > 0


def test_stage_timer_records_scene_id() -> None:
    metrics = _make_collector()
    with metrics.stage("tts", scene_id="scene-01"):
        pass
    assert metrics._stages[0].scene_id == "scene-01"


def test_stage_timer_null_scene_id_by_default() -> None:
    metrics = _make_collector()
    with metrics.stage("parse"):
        pass
    assert metrics._stages[0].scene_id is None


def test_write_creates_valid_json(tmp_path: Path) -> None:
    metrics = _make_collector()
    with metrics.stage("parse"):
        pass
    out = tmp_path / "metrics.json"
    metrics.write(out)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["schema_version"] == "1.0"
    assert data["story_id"] == "test-story"
    assert data["run_id"] == "run_test-story_1"
    assert isinstance(data["stages"], list)
    assert len(data["stages"]) == 1


def test_write_total_s_nonnegative(tmp_path: Path) -> None:
    metrics = _make_collector()
    with metrics.stage("parse"):
        pass
    out = tmp_path / "metrics.json"
    metrics.write(out)
    data = json.loads(out.read_text())
    assert data["total_s"] >= 0


def test_write_scene_id_null_by_default(tmp_path: Path) -> None:
    metrics = _make_collector()
    out = tmp_path / "metrics.json"
    metrics.write(out)
    data = json.loads(out.read_text())
    assert data["scene_id"] is None


def test_write_scene_id_set(tmp_path: Path) -> None:
    metrics = MetricsCollector(
        story_id="test-story",
        run_id="run_test-story_1",
        scene_id="scene-01",
    )
    out = tmp_path / "metrics.json"
    metrics.write(out)
    data = json.loads(out.read_text())
    assert data["scene_id"] == "scene-01"


def test_write_creates_parent_dirs(tmp_path: Path) -> None:
    metrics = _make_collector()
    out = tmp_path / "nested" / "deep" / "metrics.json"
    metrics.write(out)
    assert out.exists()


def test_write_validates_against_schema(tmp_path: Path) -> None:
    """Written JSON must satisfy metrics.schema.json."""
    from horror_story.schemas import validate

    metrics = _make_collector()
    with metrics.stage("parse"):
        pass
    with metrics.stage("tts", scene_id="scene-01"):
        pass
    out = tmp_path / "metrics.json"
    metrics.write(out)
    instance = json.loads(out.read_text())
    validate(instance, "metrics.schema.json")


def test_noop_stage_duration_is_positive() -> None:
    """A no-op stage must record duration_s > 0 (clamped to 0.001)."""
    metrics = _make_collector()
    with metrics.stage("parse"):
        pass
    assert metrics._stages[0].duration_s > 0


def test_schema_rejects_zero_duration(tmp_path: Path) -> None:
    """metrics.schema.json must reject duration_s = 0."""
    import jsonschema
    from horror_story.schemas import validate

    instance = {
        "schema_version": "1.0",
        "story_id": "x",
        "run_id": "r",
        "scene_id": None,
        "total_s": 1.0,
        "stages": [{"stage": "parse", "scene_id": None, "duration_s": 0}],
    }
    try:
        validate(instance, "metrics.schema.json")
        raise AssertionError("schema should have rejected duration_s=0")
    except jsonschema.ValidationError:
        pass


def test_multiple_stages_recorded(tmp_path: Path) -> None:
    metrics = _make_collector()
    with metrics.stage("parse"):
        pass
    with metrics.stage("script_gen"):
        pass
    with metrics.stage("tts", scene_id="scene-01"):
        pass
    out = tmp_path / "metrics.json"
    metrics.write(out)
    data = json.loads(out.read_text())
    assert len(data["stages"]) == 3
    names = [s["stage"] for s in data["stages"]]
    assert names == ["parse", "script_gen", "tts"]


# ---------------------------------------------------------------------------
# stats subcommand tests
# ---------------------------------------------------------------------------

def _write_metrics(path: Path, run_id: str, stages: list[dict[str, object]]) -> None:
    total = sum(float(s["duration_s"]) for s in stages)  # type: ignore[arg-type]
    payload = {
        "schema_version": "1.0",
        "story_id": "test-story",
        "run_id": run_id,
        "scene_id": None,
        "total_s": total,
        "stages": stages,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def test_stats_prints_table(tmp_path: Path) -> None:
    from horror_story.cli import main

    story_dir = tmp_path / "test-story"
    run_dir = story_dir / "run_test-story_1"
    _write_metrics(
        run_dir / "metrics.json",
        run_id="run_test-story_1",
        stages=[
            {"stage": "parse", "scene_id": None, "duration_s": 0.5},
            {"stage": "tts", "scene_id": "scene-01", "duration_s": 2.0},
        ],
    )

    buf = StringIO()
    with patch("sys.stdout", buf):
        main(["stats", "--out", str(tmp_path), "--story", "test-story"])

    output = buf.getvalue()
    assert "run_test-story_1" in output
    assert "parse" in output
    assert "tts" in output


def test_stats_no_metrics_files(tmp_path: Path, capsys: object) -> None:
    from horror_story.cli import main

    main(["stats", "--out", str(tmp_path), "--story", "nonexistent"])
    captured = getattr(capsys, "readouterr")()
    assert "no metrics" in captured.out


# ---------------------------------------------------------------------------
# #037 — scene-rerun metrics preservation
# ---------------------------------------------------------------------------

def test_scene_rerun_does_not_overwrite_full_run_metrics(tmp_path: Path) -> None:
    """--scene rerun must write a revision-scoped metrics file, not overwrite metrics.json."""
    from horror_story.cli import main

    story_dst, out_dir = _setup_story(tmp_path)

    # Full run
    main(["run", "--story", str(story_dst), "--out", str(out_dir), "--seed", "42"])

    run_dir = out_dir / "run_mini-story_42"
    full_metrics = run_dir / "metrics.json"
    assert full_metrics.exists(), "full-run metrics.json must exist"
    original_content = full_metrics.read_text()

    # --scene rerun
    first_scene = list(
        json.loads((run_dir / "artifact_index.json").read_text())["scenes"].keys()
    )[0]
    main(["run", "--story", str(story_dst), "--out", str(out_dir),
          "--seed", "42", "--scene", first_scene])

    # Original metrics.json must be unchanged
    assert full_metrics.read_text() == original_content, (
        "--scene rerun must not overwrite the full-run metrics.json"
    )

    # A revision-scoped metrics file must exist
    rerun_metrics = list(run_dir.glob(f"metrics_{first_scene}_r*.json"))
    assert len(rerun_metrics) == 1, (
        f"Expected one revision-scoped metrics file, found: {rerun_metrics}"
    )


def test_scene_rerun_metrics_includes_pipeline_stages(tmp_path: Path) -> None:
    """Scene-rerun metrics file must contain at least the core pipeline stages."""
    from horror_story.cli import main

    story_dst, out_dir = _setup_story(tmp_path)

    main(["run", "--story", str(story_dst), "--out", str(out_dir), "--seed", "42"])

    run_dir = out_dir / "run_mini-story_42"
    first_scene = list(
        json.loads((run_dir / "artifact_index.json").read_text())["scenes"].keys()
    )[0]
    main(["run", "--story", str(story_dst), "--out", str(out_dir),
          "--seed", "42", "--scene", first_scene])

    rerun_metrics_path = list(run_dir.glob(f"metrics_{first_scene}_r*.json"))[0]
    data = json.loads(rerun_metrics_path.read_text())
    stage_names = {s["stage"] for s in data["stages"]}
    expected = {"script_gen", "tts", "image", "motion", "audio", "timeline", "typography", "compositor"}
    missing = expected - stage_names
    assert not missing, f"Scene-rerun metrics missing stages: {missing}"


def test_stats_respects_n(tmp_path: Path) -> None:
    from horror_story.cli import main

    story_dir = tmp_path / "test-story"
    for i in range(5):
        run_id = f"run_test-story_{i}"
        _write_metrics(
            story_dir / run_id / "metrics.json",
            run_id=run_id,
            stages=[{"stage": "parse", "scene_id": None, "duration_s": float(i)}],
        )

    buf = StringIO()
    with patch("sys.stdout", buf):
        main(["stats", "--out", str(tmp_path), "--story", "test-story", "-n", "2"])

    output = buf.getvalue()
    # Should show only 2 data rows (plus header)
    lines = [ln for ln in output.splitlines() if "run_test-story_" in ln]
    assert len(lines) == 2
