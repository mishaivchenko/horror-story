# Issue #030 — Config: image style suffix for consistent visual style

**Status:** Open
**Sprint:** backlog
**Priority:** P1
**Labels:** image, config, visual-quality
**Estimate:** 0.5d
**Depends on:** #026, #027
**Blocks:** —

---

## Problem

`visual_description` in scene JSON is the first two sentences of the scene's
narrative text — no style directives at all. FLUX.1-schnell receives bare prose
like *"He was lying in his blankets, staring tensely through the dim door..."*
and chooses an arbitrary style for each image: sometimes photorealistic, sometimes
black-and-white, sometimes illustrated. Frames have no shared visual language.

---

## Goal

Add an `[image]` section to `pipeline.toml` with a `style_suffix` field. The
pipeline appends this string to every image prompt before calling the adapter, so
all frames are generated in a consistent style.

---

## Scope

### `src/horror_story/config.py`

Add a new frozen dataclass:

```python
@dataclass(frozen=True)
class ImageConfig:
    style_suffix: str = (
        "cinematic horror film still, 1930s American South, "
        "high contrast chiaroscuro lighting, desaturated color palette, "
        "dramatic shadows, photorealistic, no text, no watermark"
    )
```

Add `image: ImageConfig` field to `PipelineConfig` with a default:

```python
@dataclass(frozen=True)
class PipelineConfig:
    story: StoryConfig
    render: RenderConfig
    adapters: AdapterConfig
    image: ImageConfig = field(default_factory=ImageConfig)
    voices: dict[str, str] = field(default_factory=dict)
```

In `PipelineConfig.from_toml`, parse the optional `[image]` block:

```python
image_raw = data.get("image", {})
image = ImageConfig(
    style_suffix=image_raw.get("style_suffix", ImageConfig().style_suffix),
)
```

### `pipeline.toml` (project config file)

Add the new section so the default is visible and overridable:

```toml
[image]
style_suffix = "cinematic horror film still, 1930s American South, high contrast chiaroscuro lighting, desaturated color palette, dramatic shadows, photorealistic, no text, no watermark"
```

### `src/horror_story/cli.py`

In the image keyframe stage (around line 212), build the final prompt by
appending the suffix when it is non-empty:

```python
visual = scene_data.get("visual_description", scene_id)
suffix = config.image.style_suffix.strip()
prompt = f"{visual}, {suffix}" if suffix else visual
```

No changes to adapter interfaces.

---

## Tests

### `tests/test_config.py`

**`test_image_style_suffix_default`**: load a minimal TOML without `[image]`
section; assert `config.image.style_suffix` equals the class default.

**`test_image_style_suffix_override`**: load a TOML with
`[image] style_suffix = "flat design"`;
assert `config.image.style_suffix == "flat design"`.

### `tests/test_cli_image_prompt.py` (or extend existing CLI tests)

**`test_style_suffix_appended_to_prompt`**: mock `AdapterFactory.get_image` and
capture the `prompt` kwarg; run a single-scene pipeline with a config that has
`style_suffix = "TEST_STYLE"`; assert the captured prompt ends with `", TEST_STYLE"`.

**`test_empty_style_suffix_uses_description_only`**: set `style_suffix = ""`; assert
the prompt equals `visual_description` with no trailing comma or space.

---

## Acceptance criteria

1. `PipelineConfig.from_toml` parses `[image] style_suffix` when present.
2. Missing `[image]` section uses the default suffix without error.
3. Every image adapter call receives `f"{visual_description}, {style_suffix}"`.
4. Empty `style_suffix` passes `visual_description` unchanged.
5. All existing tests pass.
6. `mypy --strict` passes.

---

## Notes

- The suffix is intentionally long — FLUX.1-schnell responds well to repeated
  style keywords. It can be tuned in `pipeline.toml` without code changes.
- The concatenation happens in the CLI orchestration layer, not inside the adapter,
  so mock and real adapters are unaffected.
- If a scene's `visual_description` already ends with punctuation, the `, ` joiner
  is still correct for FLUX prompt syntax.
