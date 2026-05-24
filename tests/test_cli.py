"""CLI unit tests — Issue #001."""

import pytest

from horror_story.cli import _build_parser, main


def test_parser_run_subcommand() -> None:
    parser = _build_parser()
    args = parser.parse_args(["run", "--story", "foo.txt", "--out", "out/"])
    assert args.command == "run"
    assert args.story == "foo.txt"
    assert args.seed == 42
    assert not args.dry_run
    assert not args.regen


def test_parser_run_with_all_flags() -> None:
    parser = _build_parser()
    args = parser.parse_args([
        "run", "--story", "s.txt", "--out", "o/",
        "--seed", "99", "--dry-run", "--regen", "--scene", "scene-001",
    ])
    assert args.seed == 99
    assert args.dry_run
    assert args.regen
    assert args.scene == "scene-001"


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


def test_main_run_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    main(["run", "--story", "s.txt", "--out", "o/", "--dry-run"])
    captured = capsys.readouterr()
    assert "dry-run" in captured.out


def test_main_run_normal(capsys: pytest.CaptureFixture[str]) -> None:
    main(["run", "--story", "s.txt", "--out", "o/"])
    captured = capsys.readouterr()
    assert "run" in captured.out


def test_main_validate(capsys: pytest.CaptureFixture[str]) -> None:
    main(["validate", "--run-dir", "/some/path"])
    captured = capsys.readouterr()
    assert "validate" in captured.out


def test_main_validate_schemas(capsys: pytest.CaptureFixture[str]) -> None:
    main(["validate-schemas"])
    captured = capsys.readouterr()
    assert "schemas" in captured.out
