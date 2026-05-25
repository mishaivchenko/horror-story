from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

_SCHEMAS_DIR = Path(__file__).parent.parent.parent / "spec" / "schemas"

_SCHEMA_FILES = [
    "manifest.schema.json",
    "scene.schema.json",
    "script.schema.json",
    "voice_line.schema.json",
    "keyframe.schema.json",
    "ambient_artifact.schema.json",
    "motion_artifact.schema.json",
    "typography_artifact.schema.json",
    "composed_scene.schema.json",
    "artifact_index.schema.json",
    "render_job.schema.json",
    "timeline.schema.json",
    "typography_timing.schema.json",
]


@lru_cache(maxsize=1)
def load_all_schemas() -> dict[str, Any]:
    schemas: dict[str, Any] = {}
    for filename in _SCHEMA_FILES:
        path = _SCHEMAS_DIR / filename
        schemas[filename] = json.loads(path.read_text())
    return schemas


def validate(instance: Any, schema_filename: str) -> None:
    schemas = load_all_schemas()
    schema = schemas[schema_filename]
    jsonschema.validate(instance, schema)
