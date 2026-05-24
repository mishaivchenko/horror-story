# AGENTS.md — Horror Story Pipeline

## Operating model

This repository uses a human-directed AI-assisted workflow.

AI tools assist with implementation and review. The human maintainer keeps final
architectural authority.

## Roles

### Human maintainer

Responsibilities:

- approve scope
- review tradeoffs
- merge PRs
- resolve ambiguity
- protect project direction

### Claude Code

Responsibilities:

- primary implementation
- issue execution
- test execution
- schema alignment
- local fixes

Must follow `CLAUDE.md`, `spec/`, and the active issue scope.

### Codex

Responsibilities:

- independent review
- architecture criticism
- test validation
- scope enforcement

Must follow `CODEX.md`, `spec/`, and the active issue scope.

## Workflow

```text
issue -> implementation -> tests -> review -> fixes -> merge
```

Implementation work should use one issue per branch and one issue per PR. Direct commits
are acceptable for maintainer-directed repository maintenance, documentation updates, or
other explicitly requested small changes.

## Definition of done

A task is done only if:

- acceptance criteria are met
- relevant tests pass
- schemas validate when schema-backed artifacts are affected
- `mypy --strict src/` passes for Python implementation changes
- scope is respected
- deterministic behavior is preserved
- review comments are resolved

## Fan-out subagents

Subagents may be used only when:

- contracts are stable
- issue boundaries are clear
- work can be isolated safely

Avoid parallel implementation on unstable foundation layers.

## Current project phase

Current phase: MVP deterministic mock pipeline.

Not yet:

- real AI provider integrations
- cinematic AI generation
- autonomous orchestration
- production rendering system
