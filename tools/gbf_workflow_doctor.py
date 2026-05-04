#!/usr/bin/env python3
"""GBF workflow doctor: verifies local-first character workflow readiness."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "gbf-character-corpus-workflow"
SKILL_PATHS = [
    Path.home() / ".hermes" / "skills" / "gbf" / SKILL_NAME / "SKILL.md",
    Path.home() / ".claude" / "skills" / SKILL_NAME / "SKILL.md",
    Path.home() / ".codex" / "skills" / SKILL_NAME / "SKILL.md",
]
REQUIRED_REPO_PATHS = [
    "lib/tools/extract_character_corpus.py",
    "lib/tools/generate_character_guides.py",
    "docs/darwin-gbf-workflow.md",
    "evolution/results.tsv",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify GBF character corpus workflow setup")
    parser.add_argument("--character", default="galleon", help="character folder under characters/")
    args = parser.parse_args()
    failures = []

    print("GBF workflow doctor")
    print(f"repo: {ROOT}")

    for rel in REQUIRED_REPO_PATHS:
        p = ROOT / rel
        ok = p.exists()
        print(f"{status(ok)} repo:{rel}")
        if not ok:
            failures.append(rel)

    existing = [p for p in SKILL_PATHS if p.exists()]
    for p in SKILL_PATHS:
        ok = p.exists()
        print(f"{status(ok)} skill:{p}")
        if not ok:
            failures.append(str(p))
    if len(existing) == len(SKILL_PATHS):
        hashes = {sha(p) for p in existing}
        ok = len(hashes) == 1
        print(f"{status(ok)} skill-sync: Hermes/Claude/Codex hashes {'match' if ok else 'differ'}")
        if not ok:
            failures.append("skill hash mismatch")

    char_root = ROOT / "characters" / args.character
    checks = [
        char_root / "README.md",
        char_root / f"{args.character}_story_digest.md",
        char_root / f"{args.character}_act_react_guide.md",
        char_root / "speaking_only" / f"{args.character}_only_lines.md",
        char_root / "story",
    ]
    for p in checks:
        ok = p.exists()
        print(f"{status(ok)} character:{p.relative_to(ROOT) if p.exists() or ROOT in p.parents else p}")
        if not ok:
            failures.append(str(p))

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
