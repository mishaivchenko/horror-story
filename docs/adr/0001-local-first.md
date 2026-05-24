# ADR 0001 — Local-first, no distributed systems

**Status:** Accepted
**Date:** 2026-05-24

## Context

The pipeline needs to generate cinematic videos. The obvious "modern" approach would be
to use a cloud job queue, microservices for each stage, and managed media APIs. However,
the primary user of this pipeline is a single developer with a capable laptop who needs
reproducible output without relying on external services being available, affordable, or
behaving consistently.

## Decision

The pipeline is a single Python process. There is no message queue, no container
orchestration, no distributed coordination. All stages run in-process, sequentially, in
the same Python interpreter. Inter-stage communication is through files written to a local
output directory.

## Consequences

**Positive:**
- Zero infrastructure to manage or pay for at runtime.
- Trivially reproducible: check out the repo, install deps, run the CLI.
- Easy to debug: a single stack trace shows the full pipeline state.
- No network partitions, rate limits, or API outages to handle.

**Negative:**
- Cannot parallelize across machines.
- A long-running pipeline cannot be resumed from the middle if the process is killed
  (mitigated by per-scene artifact files and `--scene` re-run flag).
- All media generation is bounded by local CPU/GPU.

**Mitigations:**
- Per-scene artifacts mean only the failed scene needs to be re-run, not the whole story.
- Scene-level parallelism within the process is achievable with `concurrent.futures`
  when needed — this is an internal implementation detail, not an architectural dependency.

## Alternatives considered

- **Celery + Redis:** Adds two new infrastructure dependencies, complicates local dev,
  provides no benefit for a single-user pipeline.
- **AWS Step Functions / Cloud batch:** Cloud dependency, cost unpredictability, no
  offline capability.
