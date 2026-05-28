"""Tests for ParallelTextTranslator — aligned mode and proportional fallback."""
from __future__ import annotations

import pytest

from horror_story.pipeline.translate import ParallelTextTranslator


# ---------------------------------------------------------------------------
# Aligned mode (``\n---\n`` separators present)
# ---------------------------------------------------------------------------


def test_aligned_mode_scene_chunks_count() -> None:
    """Text with N separators produces N+1 scene chunks."""
    text = "Секція А.\n\nПараграф А2.\n---\nСекція Б.\n\nПараграф Б2.\n---\nСекція В."
    t = ParallelTextTranslator(text)
    assert len(t._scene_chunks) == 3


def test_aligned_mode_drops_leading_preamble_title() -> None:
    """A leading section with a single title-like paragraph (no terminal punctuation)
    is treated as a preamble and excluded from scene chunks so that scene 0
    maps to the first narrative section.
    """
    text = (
        "1. РОЗДІЛ ПЕРШИЙ\n"  # title — no terminal punctuation
        "---\n"
        "Перша наративна секція.\n\nДруга наративна секція.\n"
        "---\n"
        "Третя наративна секція."
    )
    t = ParallelTextTranslator(text)
    # Preamble is dropped: 2 sections remain (not 3).
    assert len(t._scene_chunks) == 2
    # Scene 0 gets the first narrative section, NOT the title.
    assert t._scene_chunks[0][0] == "Перша наративна секція."


def test_aligned_mode_scene0_gets_section0_paragraphs() -> None:
    """Scene 0 gets paragraphs only from the first section."""
    text = (
        "Перший параграф.\n\nДругий параграф.\n"
        "---\n"
        "Третій параграф.\n\nЧетвертий параграф.\n"
        "---\n"
        "П'ятий параграф."
    )
    t = ParallelTextTranslator(text)
    result = t.prepare_scene(0, 2)
    assert "Перший параграф." in result[0]
    assert "Другий параграф." in result[1]
    # Section 1 content must NOT appear in scene 0
    assert "Третій параграф." not in " ".join(result)


def test_aligned_mode_scene1_gets_section1_paragraphs() -> None:
    """Scene 1 gets paragraphs only from section 1."""
    text = (
        "Секція 0.\n"
        "---\n"
        "Секція 1 перший.\n\nСекція 1 другий.\n"
        "---\n"
        "Секція 2."
    )
    t = ParallelTextTranslator(text)
    result = t.prepare_scene(1, 2)
    assert "Секція 1 перший." in result[0]
    assert "Секція 1 другий." in result[1]


def test_aligned_mode_no_mock_fallback() -> None:
    """In aligned mode no segment text starts with '[uk]' mock prefix."""
    text = (
        "Справжній текст.\n\nЩе текст.\n"
        "---\n"
        "Другий розділ текст.\n"
        "---\n"
        "Третій розділ."
    )
    t = ParallelTextTranslator(text)
    for scene_idx in range(3):
        result = t.prepare_scene(scene_idx, 1)
        for chunk in result:
            assert not chunk.startswith("[uk] "), (
                f"Got mock-translate fallback at scene {scene_idx}: {chunk!r}"
            )


def test_aligned_mode_paragraph_count_is_total() -> None:
    """paragraph_count returns total paragraph count across all scene chunks."""
    text = (
        "А.\n\nБ.\n"
        "---\n"
        "В.\n\nГ.\n\nД.\n"
        "---\n"
        "Е."
    )
    t = ParallelTextTranslator(text)
    assert t.paragraph_count == 6


# ---------------------------------------------------------------------------
# Proportional fallback (no separators)
# ---------------------------------------------------------------------------


def test_proportional_paragraph_count() -> None:
    t = ParallelTextTranslator("А.\n\nБ.\n\nВ.")
    assert t.paragraph_count == 3


def test_proportional_get_paragraph() -> None:
    t = ParallelTextTranslator("Перший параграф.\n\nДругий параграф.")
    assert t.get_paragraph(0, "FB") == "Перший параграф."
    assert t.get_paragraph(1, "FB") == "Другий параграф."


def test_proportional_fallback_on_out_of_range() -> None:
    t = ParallelTextTranslator("Один.")
    assert t.get_paragraph(5, "FALLBACK") == "FALLBACK"


def test_proportional_empty_text() -> None:
    t = ParallelTextTranslator("")
    assert t.paragraph_count == 0
    assert t.get_paragraph(0, "FB") == "FB"


def test_proportional_scene_distribution() -> None:
    """Two equal-weight scenes get equal shares of the UK paragraphs."""
    uk_text = "\n\n".join([f"Параграф {i}." for i in range(10)])
    t = ParallelTextTranslator(
        uk_text, en_total_words=20, scene_word_counts=[10, 10]
    )
    result0 = t.prepare_scene(0, 1)
    result1 = t.prepare_scene(1, 1)
    assert "Параграф 0" in result0[0]
    assert "Параграф 5" in result1[0]


# ---------------------------------------------------------------------------
# Edge case: out-of-bounds scene in aligned mode
# ---------------------------------------------------------------------------


def test_aligned_mode_out_of_bounds_scene_returns_empty() -> None:
    """Requesting a scene index beyond the number of sections returns empty strings."""
    text = "Перша секція.\n---\nДруга секція."
    t = ParallelTextTranslator(text)
    # Only 2 sections (indices 0 and 1); scene 5 is out of bounds
    result = t.prepare_scene(5, 3)
    assert result == ["", "", ""]
