from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from horror_story.manifest import Manifest
from horror_story.models import DialogueLine, Scene, Script, Segment
from horror_story.pipeline.translate import ParallelTextTranslator

# Matches "Word: text" — character name is letters and spaces only (no newlines)
_DIALOGUE_RE = re.compile(r'^([A-Z][a-zA-Z ]+):\s+(.+)$', re.MULTILINE)
_MAX_SEGMENT_WORDS = 200

# Sentence-ending punctuation patterns used for mid-paragraph splits.
_SENTENCE_END_RE = re.compile(r'(?<=[.?!])\s+')


def mock_translate(text: str) -> str:
    """Reverse word order and prefix with '[uk] ' as a mock Ukrainian translation."""
    words = text.split()
    return "[uk] " + " ".join(reversed(words))


_MOOD_PACING: dict[str, float] = {
    "tension":  0.80,
    "violence": 0.80,
    "silence":  1.25,
    "mystery":  1.25,
}


def _pacing_ms(word_count: int, mood: str = "neutral") -> int:
    base = max(500, word_count * 100)
    return round(base * _MOOD_PACING.get(mood, 1.0))


def _split_at_sentences(text: str) -> list[str]:
    """Split text at sentence boundaries into chunks of ≤ _MAX_SEGMENT_WORDS words.

    If an individual sentence exceeds the limit it is emitted as its own chunk;
    no mid-word splitting occurs.
    """
    sentences = _SENTENCE_END_RE.split(text)
    chunks: list[str] = []
    current_words: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        sentence_words = sentence.split()
        if current_words and len(current_words) + len(sentence_words) > _MAX_SEGMENT_WORDS:
            chunks.append(" ".join(current_words))
            current_words = []
        # Sentence itself exceeds the limit — split by word count.
        while len(sentence_words) > _MAX_SEGMENT_WORDS:
            chunks.append(" ".join(sentence_words[:_MAX_SEGMENT_WORDS]))
            sentence_words = sentence_words[_MAX_SEGMENT_WORDS:]
        current_words.extend(sentence_words)
    if current_words:
        chunks.append(" ".join(current_words))
    return chunks


def _split_narration(text: str) -> list[str]:
    """Remove dialogue lines then split remaining text into paragraph-aware segments.

    Consecutive short paragraphs are merged until the accumulated word count
    reaches _MAX_SEGMENT_WORDS.  A single paragraph that exceeds the limit is
    split at sentence boundaries.  No mid-word or mid-sentence splitting occurs.
    """
    cleaned = _DIALOGUE_RE.sub("", text)
    # Split on blank lines to get paragraphs.
    raw_paragraphs = cleaned.split("\n\n")
    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

    segments: list[str] = []
    current_words: list[str] = []

    for para in paragraphs:
        para_words = para.split()
        if not para_words:
            continue
        if len(para_words) > _MAX_SEGMENT_WORDS:
            # Flush any accumulated words first.
            if current_words:
                segments.append(" ".join(current_words))
                current_words = []
            # Split oversized paragraph at sentence boundaries.
            segments.extend(_split_at_sentences(para))
        elif current_words and len(current_words) + len(para_words) > _MAX_SEGMENT_WORDS:
            # Merging would exceed the limit; flush and start fresh.
            segments.append(" ".join(current_words))
            current_words = para_words
        else:
            current_words.extend(para_words)

    if current_words:
        segments.append(" ".join(current_words))

    return [s for s in segments if s]


def _find_insert_after(segments: list[str], dialogue_match: re.Match[str], full_text: str) -> Optional[str]:
    """Return segment_id of the last narration segment whose content precedes the dialogue.

    We locate the dialogue in the full scene text and find the last segment whose
    words all appear before the match start position.
    """
    narration_before = _DIALOGUE_RE.sub("", full_text[: dialogue_match.start()]).split()
    if not narration_before:
        return None
    # Count how many narration words appear before the dialogue to find the segment.
    word_budget = len(narration_before)
    cumulative = 0
    result_index = 0
    for i, seg_text in enumerate(segments):
        seg_words = len(seg_text.split())
        cumulative += seg_words
        result_index = i
        if cumulative >= word_budget:
            break
    return f"seg-{result_index}"


def generate_script(
    scene: Scene,
    manifest: Manifest,
    translator: "ParallelTextTranslator | None" = None,
    segment_offset: int = 0,
) -> Script:
    """Convert a Scene into a Script with narration segments and dialogue lines."""
    narrator_voice = manifest.voices.get("narrator", "narrator")

    segments: list[Segment] = []
    for i, seg_text in enumerate(_split_narration(scene.text)):
        word_count = len(seg_text.split())
        if translator is not None:
            text_sec = translator.get_paragraph(segment_offset + i, mock_translate(seg_text))
        else:
            text_sec = mock_translate(seg_text)
        segments.append(
            Segment(
                segment_id=f"seg-{i}",
                text_en=seg_text,
                text_secondary=text_sec,
                pacing_ms=_pacing_ms(word_count, scene.mood),
                voice_id=narrator_voice,
            )
        )

    seg_texts = [seg.text_en for seg in segments]

    dialogue_lines: list[DialogueLine] = []
    for j, match in enumerate(_DIALOGUE_RE.finditer(scene.text)):
        character = match.group(1).strip()
        text_en = match.group(2).strip()
        word_count = len(text_en.split())
        voice_id = manifest.voices.get(character.lower(), narrator_voice)
        insert_after = _find_insert_after(seg_texts, match, scene.text)
        dialogue_lines.append(
            DialogueLine(
                line_id=f"dlg-{j}",
                character=character,
                text_en=text_en,
                text_secondary=mock_translate(text_en),
                pacing_ms=_pacing_ms(word_count, scene.mood),
                voice_id=voice_id,
                insert_after_segment=insert_after,
            )
        )

    return Script(
        story_id=scene.story_id,
        scene_id=scene.scene_id,
        mood=scene.mood,
        segments=segments,
        dialogue_lines=dialogue_lines,
    )


def generate_script_from_path(
    scene_path: Path,
    manifest: Manifest,
    translator: "ParallelTextTranslator | None" = None,
    segment_offset: int = 0,
) -> Script:
    """Load a scene JSON from disk and generate its script."""
    import json
    from horror_story.models import Scene as _Scene

    data = json.loads(scene_path.read_text())
    scene = _Scene(
        story_id=str(data["story_id"]),
        scene_id=str(data["scene_id"]),
        index=int(data["index"]),
        text=str(data["text"]),
        visual_description=str(data["visual_description"]),
        mood=str(data["mood"]),
        word_count=int(data["word_count"]),
    )
    return generate_script(scene, manifest, translator=translator, segment_offset=segment_offset)
