from __future__ import annotations

_ALIGNED_SEP = "\n---\n"
# Characters that end narrative sentences (used to distinguish preamble titles
# from prose paragraphs).
_SENTENCE_TERMINALS = frozenset(".!?\"»")


def _is_preamble(paragraphs: list[str]) -> bool:
    """Return True if *paragraphs* looks like a chapter-title preamble.

    A preamble is a single short paragraph that does not end with a
    sentence-terminal character (i.e. it's a title, not prose).
    """
    return (
        len(paragraphs) == 1
        and bool(paragraphs[0])
        and paragraphs[0][-1] not in _SENTENCE_TERMINALS
    )


class ParallelTextTranslator:
    """Maps narration segments to chunks of a parallel translation text.

    If the text contains ``\\n---\\n`` separators (aligned mode), each section
    between separators maps exactly to one scene.  A leading preamble section
    (single chapter-title paragraph, no terminal punctuation) is silently
    dropped so that ``_scene_chunks[0]`` always contains narrative prose.
    Otherwise paragraphs are distributed across scenes proportionally by
    English word count (proportional fallback).

    Usage:
        translator = ParallelTextTranslator(uk_text, en_scenes)
        translator.prepare_scene(scene_index, scene_en_word_count, n_segments)
        text = translator.get_segment(segment_index_within_scene, fallback)
    """

    def __init__(
        self,
        text: str,
        en_total_words: int = 0,
        scene_word_counts: list[int] | None = None,
    ) -> None:
        if _ALIGNED_SEP in text:
            # Aligned mode: each section maps exactly to one scene.
            sections = [s.strip() for s in text.split(_ALIGNED_SEP)]
            self._paragraphs: list[str] = []
            all_chunks: list[list[str]] = [
                [p.strip() for p in sec.split("\n\n") if p.strip()]
                for sec in sections
            ]
            # Drop a leading preamble (chapter title) so scene_index 0
            # maps to the first narrative section.
            if all_chunks and _is_preamble(all_chunks[0]):
                all_chunks = all_chunks[1:]
            self._scene_chunks: list[list[str]] = all_chunks
        else:
            # Proportional fallback (existing behaviour).
            self._paragraphs = [
                p.strip() for p in text.split("\n\n") if p.strip()
            ]
            self._scene_chunks = []
            self._build_scene_chunks(en_total_words, scene_word_counts or [])

    def _build_scene_chunks(
        self, en_total_words: int, scene_word_counts: list[int]
    ) -> None:
        """Distribute UK paragraphs across scenes proportionally, then record offsets."""
        n_paras = len(self._paragraphs)
        if n_paras == 0 or en_total_words == 0:
            self._scene_chunks = [[] for _ in scene_word_counts]
            return

        # Assign paragraph counts per scene proportionally by EN word count.
        # Use largest-remainder method to ensure total == n_paras.
        raw = [wc / en_total_words * n_paras for wc in scene_word_counts]
        floors = [int(r) for r in raw]
        remainders = [(raw[i] - floors[i], i) for i in range(len(raw))]
        deficit = n_paras - sum(floors)
        for _, i in sorted(remainders, reverse=True)[:deficit]:
            floors[i] += 1

        # Slice paragraphs and store per-scene lists.
        offset = 0
        for count in floors:
            self._scene_chunks.append(self._paragraphs[offset: offset + count])
            offset += count

    def prepare_scene(self, scene_index: int, n_segments: int) -> list[str]:
        """Merge this scene's UK paragraphs into exactly n_segments chunks.

        Returns a list of n_segments strings. Called once per scene before
        iterating over segments.
        """
        if scene_index >= len(self._scene_chunks):
            return [""] * n_segments
        paras = self._scene_chunks[scene_index]
        if not paras or n_segments == 0:
            return [""] * n_segments
        if n_segments >= len(paras):
            # More segments than paragraphs: pad with empty strings.
            result = list(paras)
            result += [""] * (n_segments - len(paras))
            return result
        # Fewer segments than paragraphs: distribute paragraphs into n_segments
        # buckets as evenly as possible (round-robin extra paragraphs).
        buckets: list[list[str]] = [[] for _ in range(n_segments)]
        for i, para in enumerate(paras):
            buckets[i % n_segments].append(para)
        return [" ".join(b) for b in buckets]

    @property
    def paragraph_count(self) -> int:
        if self._scene_chunks and not self._paragraphs:
            # Aligned mode: total paragraph count across all scene chunks.
            return sum(len(chunk) for chunk in self._scene_chunks)
        return len(self._paragraphs)

    # ── Legacy flat-index API (kept for backward compatibility with tests) ──

    def get_paragraph(self, index: int, fallback: str) -> str:
        if not self._paragraphs or index < 0 or index >= len(self._paragraphs):
            return fallback
        return self._paragraphs[index]
