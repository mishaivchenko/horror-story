from __future__ import annotations

import re
from dataclasses import dataclass


_STOP_WORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "up", "as", "is", "was",
        "it", "its", "that", "this", "he", "she", "they", "we", "i",
        "his", "her", "their", "our", "my", "your", "had", "has", "have",
        "be", "been", "not", "no", "so", "if", "then", "than", "into",
        "out", "over", "after", "before", "there", "where", "which",
        "who", "what", "when", "all", "were",
    }
)

_MOOD_KEYWORDS: dict[str, list[str]] = {
    "dread":          ["dread", "fear", "terror", "horror", "doom", "evil", "dark", "shadow", "death", "dead", "corpse", "ghost"],
    "tension":        ["tense", "sudden", "burst", "crash", "shout", "shot", "quick", "danger", "alert", "sharp", "jerk", "gun", "pistol", "froze"],
    "violence":       ["blood", "wound", "kill", "stab", "struck", "blow", "slash", "axe", "knife", "murder", "attack", "shot", "body"],
    "mystery":        ["strange", "mystery", "unknown", "secret", "hidden", "vanish", "disappear", "bizarre", "odd", "peculiar", "ancient", "ruin", "haunted"],
    "silence":        ["silence", "quiet", "still", "hush", "mute", "motionless", "pause", "empty", "alone", "desolate"],
    "night_insects":  ["cricket", "insect", "cicada", "buzz", "chirp", "frog", "night", "swamp", "bayou", "humid"],
    "wind":           ["wind", "breeze", "storm", "gust", "howl", "rustle", "creak", "moan", "wail", "leaves"],
    "relief":         ["relief", "safe", "escape", "free", "dawn", "light", "rescued", "survived", "breath", "peace"],
}


def slugify(text: str, max_chars: int = 48) -> str:
    words = re.sub(r"[^a-z0-9 ]", "", text.lower()).split()
    content_words = [w for w in words if w not in _STOP_WORDS]
    slug_words = content_words[:8] if content_words else words[:8]
    slug = "-".join(slug_words)
    return slug[:max_chars].rstrip("-")


def classify_mood(text: str) -> str:
    lower = text.lower()
    scores: dict[str, int] = {}
    for mood, keywords in _MOOD_KEYWORDS.items():
        count = sum(lower.count(kw) for kw in keywords)
        if count:
            scores[mood] = count
    if not scores:
        return "neutral"
    return max(scores, key=lambda m: scores[m])


def _extract_visual_description(text: str) -> str:
    dialogue_pattern = re.compile(r'^[A-Z][a-zA-Z\s]+:\s*.+$', re.MULTILINE)
    cleaned = dialogue_pattern.sub("", text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    sentences = [s.strip() for s in sentences if s.strip()]
    return " ".join(sentences[:2])


@dataclass(frozen=True)
class Scene:
    story_id: str
    scene_id: str
    index: int
    text: str
    visual_description: str
    mood: str
    word_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "story_id": self.story_id,
            "scene_id": self.scene_id,
            "index": self.index,
            "text": self.text,
            "visual_description": self.visual_description,
            "mood": self.mood,
            "word_count": self.word_count,
        }
