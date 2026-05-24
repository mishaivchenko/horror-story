"""Basic scaffold smoke tests — Issue #001."""

import subprocess
import sys

import horror_story
from horror_story import __version__


def test_package_version_is_set() -> None:
    assert __version__ == "0.1.0"


def test_help_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "horror_story", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "horror-story" in result.stdout


def test_no_command_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "horror_story"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_run_subcommand_in_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "horror_story", "--help"],
        capture_output=True,
        text=True,
    )
    assert "run" in result.stdout
    assert "validate" in result.stdout
