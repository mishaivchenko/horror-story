"""Schema loading and validation tests — Issue #001."""

from horror_story.schemas import load_all_schemas, validate


def test_load_all_schemas_returns_thirteen() -> None:
    schemas = load_all_schemas()
    assert len(schemas) == 13


def test_all_schemas_have_type_field() -> None:
    schemas = load_all_schemas()
    for name, schema in schemas.items():
        assert "type" in schema or "$ref" in schema or "properties" in schema, (
            f"{name} missing type/properties"
        )


def test_validate_manifest_fixture() -> None:
    fixture = {
        "schema_version": "1.0",
        "story_id": "pigeons-from-hell",
        "title": "Pigeons from Hell",
        "author": "Robert E. Howard",
        "source_file": "pigeons-from-hell.txt",
        "seed": 42,
        "languages": {"primary": "en", "secondary": "uk"},
        "render": {
            "width": 3840,
            "height": 2160,
            "fps": 24,
            "codec": "libx264",
            "audio_codec": "aac",
        },
        "voices": {"narrator": "en-narrator-01"},
        "adapters": {
            "tts": "mock",
            "image": "mock",
            "motion": "mock",
            "audio": "mock",
            "typography": "mock",
        },
        "scenes": ["scene-001"],
    }
    validate(fixture, "manifest.schema.json")
