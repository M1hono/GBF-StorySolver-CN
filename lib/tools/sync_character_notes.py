#!/usr/bin/env python3
"""Sync selected GBF character notes to Notion without traversing all story files.

This is intended for digest/act-react/speaking-only updates after a large corpus
is already present or too large for a single full dry-run log.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "lib"))

from notion.render import render_story_blocks
from notion.sync import SyncContext
from utils.config import NOTION_API_KEY, NOTION_ROOT_PAGE_ID


def cache_path(name: str) -> Path:
    p = REPO_ROOT / ".cache" / "notion"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{name}.json"


def sync_md(ctx: SyncContext, parent_id: str, title: str, md_path: Path, cache_key: str) -> str:
    content = md_path.read_text(encoding="utf-8", errors="ignore").strip()
    blocks = render_story_blocks(content)
    page_id = ctx.ensure_page(parent_id, title)
    updated = ctx.sync_page_blocks(page_id, blocks, cache_key)
    return "updated" if updated else "skipped"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync GBF character notes only")
    parser.add_argument("character", help="character folder under characters/")
    parser.add_argument("display_name", help="Notion display name")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sync-mode", choices=["diff", "force"], default="diff")
    parser.add_argument("--include-story-index", action="store_true", help="Sync lightweight index pages for every story directory")
    args = parser.parse_args()

    api_key = NOTION_API_KEY or os.environ.get("NOTION_API_KEY", "")
    root_id = NOTION_ROOT_PAGE_ID or os.environ.get("NOTION_ROOT_PAGE_ID", "")
    if not api_key or not root_id:
        print("ERROR: Notion env missing: NOTION_API_KEY or NOTION_ROOT_PAGE_ID")
        return 1

    char_root = REPO_ROOT / "characters" / args.character
    if not char_root.exists():
        print(f"ERROR: missing character folder: {char_root}")
        return 1

    ctx = SyncContext(api_key, cache_path=cache_path(args.character), mode=args.sync_mode, dry_run=args.dry_run)
    gbf_id = ctx.ensure_page(root_id, "GBF")
    character_section_id = ctx.ensure_page(gbf_id, "Character")
    char_page_id = ctx.ensure_page(character_section_id, args.display_name)

    targets = [
        (char_page_id, "Digest", char_root / f"{args.character}_story_digest.md", f"digest:{args.character}"),
        (char_page_id, "Act React Guide", char_root / f"{args.character}_act_react_guide.md", f"guide:{args.character}:act_react"),
        (char_page_id, "Speaking Only", char_root / "speaking_only" / f"{args.character}_only_lines.md", f"speaking_only:{args.character}"),
    ]

    story_root = char_root / "story"
    if args.include_story_index and story_root.exists():
        story_page_id = ctx.ensure_page(char_page_id, "Story")
        for event_dir in sorted(p for p in story_root.iterdir() if p.is_dir()):
            title = event_dir.name
            index = event_dir / "trans" / "index.md"
            if not index.exists():
                md_files = sorted((event_dir / "trans").glob("*.md")) if (event_dir / "trans").exists() else []
                body = [f"# {title}", "", "本页是 Galleon 语料同步索引。完整 Markdown 保留在本地仓库；Notion 先同步 digest、act/react 与关键剧情，避免一次性上传过大导致超时。", "", f"文件数：{len(md_files)}", "", "## Local Files"]
                for md in md_files[:80]:
                    body.append(f"- `{md.name}`")
                if len(md_files) > 80:
                    body.append(f"- ... 另有 {len(md_files)-80} 个文件")
                tmp_dir = char_root / ".generated" / "notion_story_index"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                index = tmp_dir / f"{title.replace('/', '__')}.md"
                index.write_text("\n".join(body) + "\n", encoding="utf-8")
            targets.append((story_page_id, title, index, f"story_index:{args.character}:{title}"))
    print(f"Mode: notes-only, Sync: {args.sync_mode}, Dry-run: {args.dry_run}")
    print(f"Character: {args.display_name}")
    for parent_id, title, path, key in targets:
        if not path.exists():
            print(f"  {title}: missing ({path.relative_to(REPO_ROOT)})")
            continue
        status = sync_md(ctx, parent_id, title, path, key)
        print(f"  {title}: {status}")
    ctx.save()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
