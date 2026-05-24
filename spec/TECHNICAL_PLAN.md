# Technical Plan

**Status:** Draft

---

## Technology choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.11+ | Strong ML ecosystem, good FFmpeg bindings |
| CLI | argparse (stdlib) | No extra dep; sufficient for this scope |
| Config models | dataclasses (stdlib) | No Pydantic; keeps deps minimal |
| Type checking | mypy --strict | Catches contract violations early |
| Testing | pytest + pytest-cov | Standard, integrates with CI |
| Schema validation | jsonschema (Python) | Validates artifacts between stages |
| Audio/video mux | FFmpeg (subprocess) | Best-in-class, deterministic with fixed args |
| Mock image generation | Pillow | Zero-dependency, pure Python |
| Mock audio generation | wave (stdlib) | No deps, deterministic |
| Atomic file writes | pathlib.Path.replace() (stdlib) | No atomicwrites package needed |
| Serialization | json (stdlib) | Human-readable, diffable, schema-validatable |
| Config format | TOML (tomllib, stdlib 3.11) | Better than INI, no YAML edge cases |
| Package management | pip + pyproject.toml | Standard |
| CI | GitHub Actions | Free for public repos, integrates with Issues |

---

## Module breakdown

```
src/horror_story/
├── __main__.py             # CLI entry point
├── cli.py                  # Argument parsing (argparse), orchestration
├── config.py               # Config loading (tomllib) and dataclasses
├── manifest.py             # Manifest read/write + scene ordering
├── pipeline/
│   ├── __init__.py
│   ├── parse.py            # F-01: Story parser → scene JSONs
│   ├── script.py           # F-02: Script generator (mock bilingual)
│   ├── compositor.py       # F-09: Scene compositor (FFmpeg)
│   └── renderer.py         # F-10: Final renderer (FFmpeg)
├── adapters/
│   ├── __init__.py
│   ├── base.py             # Abstract base classes for all adapters
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── base.py         # TTSAdapter ABC
│   │   └── mock.py         # MockTTSAdapter (F-03, F-04)
│   ├── image/
│   │   ├── __init__.py
│   │   ├── base.py         # ImageAdapter ABC
│   │   └── mock.py         # MockImageAdapter (F-05)
│   ├── motion/
│   │   ├── __init__.py
│   │   ├── base.py         # MotionAdapter ABC
│   │   └── mock.py         # MockMotionAdapter (F-06)
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── base.py         # AudioAdapter ABC
│   │   └── mock.py         # MockAudioAdapter (F-07)
│   └── typography/
│       ├── __init__.py
│       ├── base.py         # TypographyAdapter ABC
│       └── mock.py         # MockTypographyAdapter (F-08)
└── schemas.py              # Schema path lookup + validation helper
```

---

## Data flow

```
[story.txt]
    │
    ▼ parse.py
[manifest.json]  +  [scenes/scene_<id>.json ...]
    │
    ▼ script.py (per scene)
[scripts/script_<id>.json ...]
    │
    ├─▶ tts/mock.py (narration, per segment)
    │       [audio/narration_<id>_<seg>.wav ...]
    │
    ├─▶ tts/mock.py (dialogue, per line)
    │       [audio/dialogue_<id>_<line>.wav ...]
    │
    ├─▶ image/mock.py (keyframe)
    │       [frames/keyframe_<id>.png]
    │       │
    │       ▼ motion/mock.py
    │       [frames/motion_<id>.mp4]
    │
    ├─▶ audio/mock.py (ambient)
    │       [audio/ambient_<id>.wav]
    │
    └─▶ typography/mock.py
            [video/typography_<id>.mp4]
                │
                ▼ compositor.py (FFmpeg)
            [video/scene_<id>_composed.mp4]
                │
                ▼ renderer.py (FFmpeg)
            [final_<story_id>_<seed>.mp4]
```

---

## Adapter interface contracts

All adapters follow the same structural pattern: one primary method, `seed` always last,
returns the `Path` of the written artifact. A JSON sidecar (artifact record) is written
alongside each artifact by the adapter.

```python
# TTS (narration + dialogue — same interface)
class TTSAdapter(ABC):
    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        language: str,
        pacing_ms: int,
        seed: int,
        out_path: Path,
    ) -> Path: ...

# Image
class ImageAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        seed: int,
        out_path: Path,
    ) -> Path: ...

# Motion
class MotionAdapter(ABC):
    @abstractmethod
    def animate(
        self,
        frame_path: Path,
        duration_s: float,
        fps: int,
        effect: str,
        seed: int,
        out_path: Path,
    ) -> Path: ...

# Ambient audio
class AudioAdapter(ABC):
    @abstractmethod
    def generate(
        self,
        mood: str,
        duration_s: float,
        seed: int,
        out_path: Path,
    ) -> Path: ...

# Typography
class TypographyAdapter(ABC):
    @abstractmethod
    def render(
        self,
        script_path: Path,
        duration_s: float,
        width: int,
        height: int,
        fps: int,
        seed: int,
        out_path: Path,
    ) -> Path: ...
```

**Rules:**
- `out_path` is the caller-supplied destination; the adapter writes to a temp path and
  replaces `out_path` atomically via `Path.replace()`.
- `seed` is always the last positional argument before `out_path`.
- Adapters are instantiated once per pipeline run via a factory keyed on the adapter name
  from `pipeline.toml`. They are passed explicitly to each stage function (no globals).

---

## Configuration

`pipeline.toml` (per-story, in the story directory):

```toml
[story]
id = "pigeons-from-hell"
title = "Pigeons from Hell"
primary_language = "en"
secondary_language = "uk"
seed = 42

[render]
width = 3840
height = 2160
fps = 24
codec = "libx264"
audio_codec = "aac"

[voices]
narrator = "en-narrator-01"
griswell = "en-male-deep"
branner = "en-male-mid"

[adapters]
tts = "mock"
image = "mock"
motion = "mock"
audio = "mock"
typography = "mock"
```

---

## Artifact versioning and run directories

Each pipeline run produces artifacts under a deterministic run directory:

```
output/<story_id>/run_<story_id>_<seed>/
    manifest.json
    scenes/
    scripts/
    audio/
    frames/
    video/
    artifact_index.json
    final_<story_id>_<seed>.mp4
```

**Run ID rule:** `run_<story_id>_<seed>` — no timestamps. If the directory already exists,
the CLI exits with an error unless `--regen` is passed.

`--regen` creates a new versioned subdirectory: `run_<story_id>_<seed>_r<n>` where `<n>`
increments from 1. The CLI never overwrites existing artifact files in place.

`--scene <id>` re-runs only the specified scene's stages within the existing run directory,
writing new artifact files suffixed `_r<n>` and updating `artifact_index.json` to point to
the latest version. The final renderer always reads paths from `artifact_index.json`.

`artifact_index.json` is the mutable "latest artifact" registry for a run. It is the only
file that is updated (not replaced) after initial creation. All artifact files themselves
are write-once.

---

## Determinism strategy

**Deterministic content:** given the same `story.txt`, `pipeline.toml` (same `seed`), and
adapter versions, every artifact's *content* is reproducible. This is the guarantee.

**Not guaranteed:** file-level metadata (inode, mtime, filesystem timestamps). These are
non-contract metadata and may differ across runs or machines.

**Practical rules:**
1. Every adapter's primary method accepts `seed: int` as its last argument.
2. Per-artifact seed: `manifest.seed ^ (scene_index * 1000) ^ stage_index`. This is
   computed by the calling stage function, not the adapter.
3. FFmpeg is invoked with fixed ordered arguments. No `-metadata` flags that embed timestamps.
4. The run directory name uses `run_<story_id>_<seed>` — no wall-clock time in the path.
5. File writes use `tmp_path.write_bytes(data); tmp_path.replace(final_path)` (stdlib
   `pathlib`) for crash safety. No external `atomicwrites` package.
6. SHA-256 of deterministic artifacts (mock mode only) must be identical across runs.
   The `render_job.json` records this hash.

---

## FFmpeg dependency

FFmpeg must be available in `$PATH`. The CLI checks at startup and exits with a clear
error if not found. No bundled FFmpeg.

---

## Test strategy

- **Unit tests** for each stage function: pure-function tests with temp directories.
- **Adapter tests** for each mock adapter: generate an artifact, validate it.
- **Schema tests**: every fixture in `tests/fixtures/` validates against its schema.
- **Sprint 01 integration test** (`tests/test_integration_s01.py`): runs parse + script +
  TTS mock + image mock on the 3-scene mini-story fixture. Asserts all scene JSONs, script
  JSONs, WAV files, and PNG files exist and validate. No video output.
- **Sprint 02 integration test** (`tests/test_integration_s02.py`): adds motion, audio,
  typography, compositor, renderer. Asserts the final MP4 exists. Skipped if FFmpeg absent.
- **Determinism test** (Sprint 02): runs the mini-story twice with `--seed 42`, asserts
  SHA-256 of the final MP4 matches. Requires FFmpeg.
- Coverage target: ≥ 80% on `src/`.
