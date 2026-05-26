# #035 — Align EN and UK story file formats

**Status:** Open
**Sprint:** 07

## Problem

The two story files have different formats:

| File | Scene separators | Structure |
|------|-----------------|-----------|
| `pigeons_from_hell_EN.txt` | 18 × `---` (19 scenes) | Plain paragraphs |
| `pigeons_from_hell_uk.txt` | 0 × `---` | Chapter headings (`1. СВИСТ ІЗ ТЕМРЯВИ`), indented paragraphs |

Because the UK file has no `---` separators, `ParallelTextTranslator` must guess paragraph
distribution using word-count proportions. This is fragile and causes alignment drift.

## Proposed solution

Add `---` scene separators to `pigeons_from_hell_uk.txt` at positions matching the EN file.

Rules:
- One `---` per scene break (same 18 breaks as EN)
- Chapter headings (`1. СВИСТ ІЗ ТЕМРЯВИ`) kept as-is (they are treated as paragraphs by the translator)
- Indentation removed (leading spaces stripped per line)
- Blank lines between paragraphs preserved

Once aligned, `ParallelTextTranslator` can use exact scene slices instead of proportional
distribution, improving subtitle accuracy.

## Acceptance

- `pigeons_from_hell_uk.txt` contains exactly 18 `---` separators
- Scene N in UK file corresponds to scene N in EN file (same narrative beat)
- `ParallelTextTranslator` test: scene-aware mode produces correct chunks from aligned file
- No regression in existing tests
