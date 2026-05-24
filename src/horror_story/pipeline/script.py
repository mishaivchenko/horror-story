from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from horror_story.manifest import Manifest
from horror_story.models import DialogueLine, Scene, Script, Segment

# Matches "Word: text" — character name is letters and spaces only (no newlines)
_DIALOGUE_RE = re.compile(r'^([A-Z][a-zA-Z ]+):\s+(.+)$', re.MULTILINE)
_MAX_SEGMENT_WORDS = 40


def mock_translate(text: str) -> str:
    """Reverse word order and prefix with '[uk] ' as a mock Ukrainian translation."""
    words = text.split()
    return "[uk] " + " ".join(reversed(words))


def _pacing_ms(word_count: int) -> int:
    return max(500, word_count * 100)


def _split_narration(text: str) -> list[str]:
    """Remove dialogue lines then split remaining text into ≤40-word segments."""
    cleaned = _DIALOGUE_RE.sub("", text)
    words = cleaned.split()
    segments: list[str] = []
    while words:
        chunk = words[:_MAX_SEGMENT_WORDS]
        words = words[_MAX_SEGMENT_WORDS:]
        segments.append(" ".join(chunk))
    return [s for s in segments if s]


def _find_insert_after(text: str, dialogue_match: re.Match[str]) -> Optional[str]:
    """Return segment_id of the segment whose text ends before the dialogue match start."""
    narration_text = text[: dialogue_match.start()]
    words_before = narration_text.split()
    if not words_before:
        return None
    seg_index = (len(words_before) - 1) // _MAX_SEGMENT_WORDS
    return f"seg-{seg_index}"


def generate_script(scene: Scene, manifest: Manifest) -> Script:
    """Convert a Scene into a Script with narration segments and dialogue lines."""
    narrator_voice = manifest.voices.get("narrator", "narrator")

    segments: list[Segment] = []
    for i, seg_text in enumerate(_split_narration(scene.text)):
        word_count = len(seg_text.split())
        segments.append(
            Segment(
                segment_id=f"seg-{i}",
                text_en=seg_text,
                text_secondary=mock_translate(seg_text),
                pacing_ms=_pacing_ms(word_count),
                voice_id=narrator_voice,
            )
        )

    dialogue_lines: list[DialogueLine] = []
    for j, match in enumerate(_DIALOGUE_RE.finditer(scene.text)):
        character = match.group(1).strip()
        text_en = match.group(2).strip()
        word_count = len(text_en.split())
        voice_id = manifest.voices.get(character.lower(), narrator_voice)
        insert_after = _find_insert_after(scene.text, match)
        dialogue_lines.append(
            DialogueLine(
                line_id=f"dlg-{j}",
                character=character,
                text_en=text_en,
                text_secondary=mock_translate(text_en),
                pacing_ms=_pacing_ms(word_count),
                voice_id=voice_id,
                insert_after_segment=insert_after,
            )
        )

    return Script(
        story_id=scene.story_id,
        scene_id=scene.scene_id,
        segments=segments,
        dialogue_lines=dialogue_lines,
    )


def generate_script_from_path(scene_path: Path, manifest: Manifest) -> Script:
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
    return generate_script(scene, manifest)
