# Horror Story — AI Cinematic Pipeline

A local-first, deterministic pipeline that converts public-domain horror stories into
atmospheric bilingual cinematic videos.

**First target:** *Pigeons from Hell* by Robert E. Howard

## What it produces

Per story, the pipeline outputs:
- Bilingual narration (EN + target language) with atmospheric voice acting
- Cinematic keyframe illustrations, one per scene
- Subtle motion/VFX applied to still frames
- Ambient sound design per scene
- Bilingual typography overlays
- A deterministic 4K rendered video

## How it works

```
story text
    └─► scene parser
            └─► script generator  (bilingual narration + dialogue)
                    ├─► narration TTS
                    ├─► dialogue TTS (per character voice)
                    ├─► keyframe generator (image per scene)
                    │       └─► motion adapter (subtle animation)
                    ├─► ambient audio adapter
                    └─► scene compositor
                            └─► final renderer (4K, deterministic)
```

Every stage reads and writes immutable JSON/media artifacts under `output/`.
Each stage can be re-run independently by scene ID.

## Status

**Phase 1 — Scaffold complete** (Issue #001 done; Sprint 01 in progress)

See [`spec/MVP_PLUS.md`](spec/MVP_PLUS.md) for the feature specification.
See [`docs/sprints/sprint-01.md`](docs/sprints/sprint-01.md) for the current sprint.
See [`backlog/issues/`](backlog/issues/) for the GitHub Issues backlog.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m horror_story --help
```

## Development

```bash
# Install deps
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=horror_story

# Type check
mypy --strict src/

# Validate spec schemas are well-formed
python -m horror_story validate-schemas

# Lint specs
markdownlint spec/
```

## Repository layout

```
spec/           Spec Kit — specs, constitution, schemas (source of truth)
backlog/        Draft GitHub Issues
docs/           ADRs, sprint plans
src/            Implementation (not yet started)
tests/          Test suite (not yet started)
output/         Generated artifacts (gitignored)
.github/        CI workflows and issue templates
```

## Constraints

- Local-first, no cloud dependencies at runtime
- No microservices, no Kafka, no plugin framework
- All media adapters are mock-first; real providers are drop-in replacements
- Deterministic output: same inputs → same render

See [`spec/constitution.md`](spec/constitution.md) for the full constraint list.
