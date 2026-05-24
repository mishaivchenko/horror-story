# Project Constitution

**Status:** Accepted

This document is immutable in spirit. Changes require explicit team consensus and a new
ADR explaining the reason.

---

## Purpose

Build a reproducible, local-first pipeline that converts public-domain horror stories into
atmospheric bilingual cinematic videos. The pipeline must be usable by a single developer
on a consumer laptop without cloud dependencies at runtime.

---

## Hard constraints

These are non-negotiable. Any proposal that violates them is out of scope.

### Infrastructure
- **No distributed systems.** No message queues (Kafka, RabbitMQ, etc.), no service mesh,
  no container orchestration (Kubernetes).
- **No microservices.** The pipeline is a single Python process driven by a CLI.
- **No plugin framework.** Adapters are swapped by configuration, not dynamic loading.
- **Local-first at runtime.** The pipeline must produce output without internet access once
  all local models/assets are cached.

### Media generation
- **Mock-first.** Every media adapter (TTS, image gen, animation, audio) must have a
  deterministic mock implementation before any real provider is integrated.
- **Replaceable adapters.** Each adapter is a thin shim behind a typed interface. Real
  providers are drop-in replacements. The interface must be specified before the mock is
  written.
- **No hard dependency on any single provider.** The pipeline must not fail if any given
  SaaS API is unavailable; the mock adapter must always work.

### Output
- **Deterministic content.** Given the same inputs and `seed`, every artifact's *content*
  is reproducible. File-level metadata (inode, mtime) is not part of the contract.
  With mock adapters only, SHA-256 of each content artifact must be identical across runs
  on the same platform. Real media providers are exempt from this constraint.
- **Immutable artifacts.** Once written, an artifact file is never overwritten. Regeneration
  writes a new versioned file (`_r<n>` suffix). The `artifact_index.json` tracks latest
  versions. The CLI provides `--regen` (full re-run) and `--scene` (partial re-run) flags.
- **4K target.** Final render resolution is 3840×2160. Development can use lower res;
  the schema must always carry the target resolution.

### Engineering
- **TDD-first.** Write a failing test before writing implementation code. No implementation
  PR is merged without tests.
- **Spec-driven.** Every feature traces back to an entry in `spec/`. No spec, no
  implementation.
- **Type-safe.** Python source must pass `mypy --strict`. No `Any` escape hatches without
  a comment explaining why.
- **No dead code.** Unused code is deleted, not commented out.

---

## Working agreements

- GitHub Issues are the primary execution unit. Every sprint task maps to an issue.
- Claude Code is the primary implementer. Codex acts as reviewer, test engineer, and
  architecture critic.
- Every issue has acceptance criteria. An issue is done when all criteria pass in CI.
- Spec changes require a PR with at least one review before merging.
- ADRs document every significant architectural decision. See `docs/adr/`.

---

## Definition of done (per issue)

1. All acceptance criteria pass.
2. `pytest` green with ≥ 80% coverage on new code.
3. `mypy --strict` passes.
4. JSON schema validation passes for any new artifact types.
5. Spec updated if the issue changes a contract or adds a stage.

---

## Out of scope (forever, for this project)

- Real-time streaming pipeline
- Web UI or API server
- Multi-user or multi-tenant access
- Cloud storage or CDN integration
- Any form of user authentication
- Adaptive bitrate video streaming

---

## Out of scope (for now, revisit after MVP+)

- Real TTS provider integration (ElevenLabs, Azure, etc.)
- Real image generation integration (Stable Diffusion, Midjourney, etc.)
- Real motion/VFX integration (RunwayML, etc.)
- Real ambient audio generation
- Languages beyond EN + one target language
- Stories other than *Pigeons from Hell*
- Any distribution or publishing automation
