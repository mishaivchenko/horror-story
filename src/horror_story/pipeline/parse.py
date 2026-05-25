from __future__ import annotations

import re
from horror_story.models import Scene, classify_mood, slugify, _extract_visual_description


def parse_story(text: str, story_id: str) -> list[Scene]:
    """Split story text into scenes on standalone '---' markers."""
    if not text.strip():
        raise ValueError("Story text is empty.")

    raw_scenes = re.split(r'(?m)^---$', text)
    scenes = [chunk.strip() for chunk in raw_scenes if chunk.strip()]

    if not scenes:
        raise ValueError("No scenes found after splitting on '---'.")

    result: list[Scene] = []
    for index, scene_text in enumerate(scenes):
        scene_id = slugify(scene_text)
        if not scene_id:
            scene_id = f"scene-{index}"
        visual_description = _extract_visual_description(scene_text)
        mood = classify_mood(scene_text)
        word_count = len(scene_text.split())
        result.append(
            Scene(
                story_id=story_id,
                scene_id=scene_id,
                index=index,
                text=scene_text,
                visual_description=visual_description,
                mood=mood,
                word_count=word_count,
            )
        )
    return result
