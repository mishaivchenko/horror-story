from __future__ import annotations


class ParallelTextTranslator:
    """Maps narration segments to paragraphs from a parallel translation text.

    Paragraphs are split on blank lines. Segments are addressed by a flat
    global index (counting across all scenes in story order). If the index
    exceeds available paragraphs, returns the fallback string.
    """

    def __init__(self, text: str) -> None:
        self._paragraphs: list[str] = [
            p.strip() for p in text.split("\n\n") if p.strip()
        ]

    def get_paragraph(self, index: int, fallback: str) -> str:
        if not self._paragraphs or index < 0 or index >= len(self._paragraphs):
            return fallback
        return self._paragraphs[index]

    @property
    def paragraph_count(self) -> int:
        return len(self._paragraphs)
