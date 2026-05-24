# ADR 0002 — Mock-first media adapters

**Status:** Accepted
**Date:** 2026-05-24

## Context

The pipeline requires TTS synthesis, AI image generation, motion/VFX processing, and
ambient audio generation. Each of these depends on external models or services that are
expensive, slow, require API keys, and may produce non-deterministic output. We need to
be able to develop, test, and demonstrate the pipeline end-to-end before any real
provider is integrated.

## Decision

Every media-generating stage is implemented behind an abstract base class (`TTSAdapter`,
`ImageAdapter`, `MotionAdapter`, `AudioAdapter`, `TypographyAdapter`). Each ABC has a
`MockAdapter` implementation that is:
- **Deterministic:** same inputs + seed → same bytes.
- **Fast:** completes in milliseconds.
- **Dependency-free:** uses only Python stdlib and Pillow.
- **Structurally valid:** produces files that are valid audio/video/image formats so
  downstream stages can process them.

The active adapter for each stage is chosen by `pipeline.toml`'s `[adapters]` section.
The default is always `"mock"`. Real adapters are added later as additional values in the
enum.

## Consequences

**Positive:**
- The full pipeline can be developed and CI-tested without any API keys or model downloads.
- Tests are fast, deterministic, and work offline.
- Real adapters can be integrated one at a time without touching pipeline logic.
- The mock provides a clear specification of what the real adapter must produce.

**Negative:**
- Mock output is not visually or aurally useful for human review.
- There is a risk that the mock is too simple and the real adapter produces something that
  downstream stages can't handle (mitigated by schema validation at every stage boundary).

## Alternatives considered

- **Test doubles at the test layer only:** Would require real adapters to be present even
  for CLI usage, blocking development until all providers are integrated.
- **Single hard-coded mock mode flag:** Less flexible than per-adapter configuration;
  makes partial real-adapter testing harder.
