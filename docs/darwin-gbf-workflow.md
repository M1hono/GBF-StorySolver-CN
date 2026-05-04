# Darwin-style GBF Workflow Evolution

This repository adapts the Darwin Motion Loop pattern from the VideoMaking workspace to GBF content operations.

Principle: improve extraction/translation workflows like a training loop. Make one focused change, measure it, keep it only if it improves the objective.

## What Can Evolve

- Hermes skills under `/Users/gedwen/.hermes/skills/gbf/`
- Claude Code skills under `/Users/gedwen/.claude/skills/gbf/`
- Codex skills under `/Users/gedwen/.codex/skills/gbf/`
- GBF extraction tools in `lib/tools/`
- Extractor/translator modules in `lib/extractors/` and `lib/translators/`
- Workflow docs in `lib/docs/` and `docs/`
- Local-first test prompts and regression tests

## Evolution Folders

- `evolution/results.tsv`: append-only experiment log.
- `evolution/experiments/`: detailed notes for specific experiments.
- `evolution/skill-candidates/`: reusable lessons waiting for promotion.
- `evolution/patterns/`: promoted reusable patterns.
- `evolution/reports/`: summaries and scorecards.
- `evolution/test-prompts/`: prompts for workflow validation.

## Ratchet Rules

1. One primary target per round.
2. One weak dimension per improvement.
3. Capture reusable lessons during development, promote after scoring and verification.
4. Keep only measurable improvements.
5. Record dry-run evaluations when full tests are not practical.
6. Revert regressions with targeted patching or normal git revert, never destructive reset.
7. Ask before major rewrites, dependency changes, or deleting old workflow pieces.

## GBF-Specific Objectives

Good changes should improve at least one of these:

- stronger Local-First enforcement,
- fewer repeated extraction scripts,
- safer name/term mapping use,
- clearer character corpus output contracts,
- better speaker-only collection accuracy,
- shared Hermes/Claude/Codex compatibility,
- stronger verification evidence.
