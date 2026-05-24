# CLAUDE.md — Horror Story Pipeline

## Project context

AI-driven cinematic horror narration pipeline. Converts public-domain horror text into
bilingual cinematic videos. First target: *Pigeons from Hell* (Robert E. Howard, 1938).

## Working agreements

- **Spec-driven**: every non-trivial change has a spec entry in `spec/`. Write or update
  the spec before touching implementation.
- **TDD-first**: write a failing test before writing implementation code.
- **Mock-first adapters**: all media generation (TTS, image, animation, audio) starts as
  a deterministic mock. Real provider integrations come later.
- **Issue-linked**: every implementation task maps to a backlog issue in `backlog/issues/`
  and eventually a GitHub Issue.
- **Immutable artifacts**: pipeline stages write to `output/<story_id>/<stage>/`. Never
  mutate an existing artifact in place; write a new one.

## Repository structure

```
spec/           Spec Kit — source of truth. Read this before implementing anything.
backlog/issues/ Draft GitHub Issues backlog — one file per issue
docs/adr/       Architecture Decision Records
docs/sprints/   Sprint plans
src/            Python source (package: horror_story)
tests/          Pytest test suite
output/         Generated artifacts (gitignored)
.github/        GitHub Actions workflows + issue templates
```

## Key specs to read first

1. `spec/constitution.md` — hard constraints and working principles
2. `spec/MVP_PLUS.md` — what the MVP+ delivers
3. `spec/TECHNICAL_PLAN.md` — architecture and module breakdown
4. `spec/PIPELINE.md` — stage-by-stage data flow
5. `spec/schemas/` — JSON schemas for every artifact type

## Commands

```bash
pytest                         # run tests
pytest --cov=horror_story      # with coverage
python -m horror_story --help  # CLI (once scaffolded)
python -m horror_story validate-schemas   # schema validation
```

## Coding conventions

- Python ≥ 3.11
- Type hints everywhere; `mypy --strict` must pass
- No global mutable state; pipeline state flows through explicit artifact paths
- Each pipeline stage is a pure function: `(config, input_path) -> output_path`
- All randomness seeded via manifest `seed` field; same seed → same output
- One module per pipeline stage; no cross-stage imports

## What NOT to do

- Do not add distributed systems, message queues, or microservices
- Do not integrate real media APIs until the mock layer is tested and spec-complete
- Do not add a plugin framework
- Do not emit artifacts that depend on wall-clock time (use deterministic seeds)
- Do not accumulate dead code; delete it

## CI

GitHub Actions runs on every PR:
- `pytest` with coverage
- `mypy --strict`
- JSON schema validation for all artifacts in `output/fixtures/`
- Markdown lint on `spec/`
