#!/usr/bin/env python3
"""
Notion content uploader for GBF Story Extractor.

Notion Structure:
    GBF/
    ├── Story/                    # story/translated/ (BLHXFY scenarios)
    └── Character/                # characters/{char}/
        └── {display_name}/
            ├── Story/            # story/{event}/trans/
            ├── Lore/             # lore/trans/
            └── Voice/            # voice/trans/

Requirements:
    Set in .env file:
        NOTION_API_KEY=ntn_xxx
        NOTION_ROOT_PAGE_ID=xxx (32-char ID from page URL)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))

from notion.sync import SyncContext
from notion.render import render_story_blocks, render_profile_blocks
from notion.parsers import parse_cast_table, parse_voice_table
from notion.database import sync_cast_database, sync_voice_database
from utils.config import NOTION_API_KEY, NOTION_ROOT_PAGE_ID


# =============================================================================
# CONFIGURATION
# =============================================================================

CHARACTERS_CONFIG = Path("characters.json")


def log(msg: str):
    print(msg, flush=True)


def get_cache_path(name: str) -> Path:
    cache_dir = Path(".cache/notion")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{name}.json"


def load_characters_config() -> list:
    """Load character list from characters.json."""
    if CHARACTERS_CONFIG.exists():
        with open(CHARACTERS_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


# =============================================================================
# CLEANUP
# =============================================================================

def delete_all_children(ctx: SyncContext, parent_id: str) -> int:
    """Delete all child pages/databases under a parent."""
    cursor = None
    deleted = 0
    while True:
        res = ctx.client.blocks.children.list(block_id=parent_id, page_size=100, start_cursor=cursor)
        for b in res.get("results", []):
            if b.get("type") in ("child_page", "child_database"):
                try:
                    ctx.client.blocks.delete(block_id=b["id"])
                    deleted += 1
                    time.sleep(0.1)
                except Exception as e:
                    log(f"    Failed to delete {b['id']}: {e}")
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return deleted


# =============================================================================
# SYNC UTILITIES
# =============================================================================

def sync_md_to_page(ctx: SyncContext, parent_id: str, md_file: Path, cache_prefix: str, is_profile: bool = False):
    """Sync a single .md file to Notion."""
    title = md_file.stem
    try:
        content = md_file.read_text(encoding="utf-8", errors="ignore").strip()
        
        if md_file.name == "cast.md":
            rows = parse_cast_table(content)
            if rows:
                sync_cast_database(
                    ctx.client, parent_id, rows,
                    cache=ctx._cache, mode=ctx.mode, dry_run=ctx.dry_run
                )
                log(f"    Cast: {len(rows)} entries")
        else:
            # Use profile renderer for profile files
            if is_profile:
                blocks = render_profile_blocks(content)
            else:
                blocks = render_story_blocks(content)
            cache_key = f"{cache_prefix}:{title}"

            if ctx.mode == "force":
                page_id = ctx.recreate_page(parent_id, title)
                ctx.sync_page_blocks(page_id, blocks, cache_key, skip_clear=True)
                status = "recreated"
            else:
                page_id = ctx.ensure_page(parent_id, title)
                updated = ctx.sync_page_blocks(page_id, blocks, cache_key)
                status = "updated" if updated else "skipped"

            log(f"    {title}: {status}")

        time.sleep(0.05)

    except Exception as e:
        log(f"    {title}: ERROR - {e}")


def sync_lore_content(ctx: SyncContext, lore_page_id: str, lore_root: Path, char_folder: str):
    """
    Sync lore content with specialized handling for different types.
    Supports nested directories (e.g., versioned folders).
    """
    for item in sorted(lore_root.iterdir()):
        if item.is_dir():
            # Create a subpage for the directory
            category_name = item.name.replace('_', ' ').title()
            category_page_id = ctx.ensure_page(lore_page_id, category_name)
            
            # Check if this directory contains further directories or just files
            has_subdirs = any(child.is_dir() for child in item.iterdir())
            
            if has_subdirs:
                # Recurse into subdirectories
                sync_lore_content(ctx, category_page_id, item, char_folder)
            else:
                # Process files in this directory
                for file_item in sorted(item.iterdir()):
                    if file_item.suffix != ".md":
                        continue
                    
                    # Special handling for quotes (database)
                    if file_item.stem == "quotes" or "quote" in file_item.stem.lower():
                        try:
                            content = file_item.read_text(encoding='utf-8')
                            from lib.notion.parsers import parse_voice_table
                            from lib.notion.database import sync_voice_database
                            
                            rows = parse_voice_table(content)
                            if rows:
                                title = file_item.stem.replace('_', ' ').title()
                                sync_voice_database(
                                    ctx.client,
                                    category_page_id,
                                    title,
                                    rows,
                                    mode=ctx.mode
                                )
                                log(f"    {file_item.stem}: {len(rows)} quotes")
                        except Exception as e:
                            log(f"    {file_item.stem}: ERROR - {e}")
                    
                    # Profile: special card format
                    elif item.name == "profile":
                        sync_md_to_page(ctx, category_page_id, file_item, f"lore:{char_folder}:{item.name}", is_profile=True)
                    
                    # Others: story format
                    else:
                        sync_md_to_page(ctx, category_page_id, file_item, f"lore:{char_folder}:{item.name}")
        elif item.suffix == ".md":
            # Files in the root lore folder
            sync_md_to_page(ctx, lore_page_id, item, f"lore:{char_folder}:root")


def sync_folder_recursive(ctx: SyncContext, parent_id: str, folder: Path, cache_prefix: str):
    """Recursively sync folder contents (deprecated, use specialized functions)."""
    for item in sorted(folder.iterdir()):
        if item.is_dir():
            sub_page_id = ctx.ensure_page(parent_id, item.name)
            sync_folder_recursive(ctx, sub_page_id, item, f"{cache_prefix}:{item.name}")
        elif item.suffix == ".md":
            sync_md_to_page(ctx, parent_id, item, cache_prefix)


def sync_voice_tables(ctx: SyncContext, voice_page_id: str, voice_root: Path, display_name: str):
    """Sync voice markdown files as Notion databases."""
    for item in sorted(voice_root.iterdir()):
        if item.is_dir():
            # Create subpage for category (e.g., holidays, battle)
            sub_page_id = ctx.ensure_page(voice_page_id, item.name)
            sync_voice_tables(ctx, sub_page_id, item, display_name)
        elif item.suffix == ".md":
            try:
                content = item.read_text(encoding='utf-8')
                voice_data = parse_voice_table(content)
                
                if not voice_data:
                    log(f"    {item.stem}: no data")
                    continue
                
                # Use file stem as database title
                title = item.stem.replace('_', ' ').title()
                
                sync_voice_database(
                    ctx.client,
                    voice_page_id,
                    title,
                    voice_data,
                    cache=ctx._cache,
                    mode=ctx.mode,
                    dry_run=ctx.dry_run,
                )
                log(f"    {title}: {len(voice_data)} entries")
                time.sleep(0.1)
            except Exception as e:
                log(f"    {item.stem}: ERROR - {e}")


# =============================================================================
# ROOT STORY UPLOAD
# =============================================================================

def sync_root_stories(ctx: SyncContext, story_section_id: str, story_filter: str = "", clean: bool = False):
    """Upload story/translated/ to GBF/Story/."""
    story_root = Path("story/translated")
    if not story_root.exists():
        log(f"  Folder not found: {story_root}")
        return

    if clean and not ctx.dry_run:
        log("  Cleaning Story section...")
        deleted = delete_all_children(ctx, story_section_id)
        log(f"  Deleted {deleted} items")

    events = sorted(d for d in story_root.iterdir() if d.is_dir())
    
    if story_filter:
        events = [e for e in events if story_filter.lower() in e.name.lower()]
    
    log(f"  Found {len(events)} story folders")

    for event_dir in events:
        log(f"\n  [{event_dir.name}]")
        
        try:
            event_page_id = ctx.ensure_page(story_section_id, event_dir.name)
        except Exception as e:
            log(f"    ERROR: {e}")
            continue

        for md_file in sorted(event_dir.glob("*.md")):
            sync_md_to_page(ctx, event_page_id, md_file, f"root_story:{event_dir.name}")


# =============================================================================
# CHARACTER UPLOAD
# =============================================================================

def sync_character(ctx: SyncContext, char_section_id: str, char_folder: str, display_name: str, 
                   event_filter: str = "", clean: bool = False, voice_only: bool = False, lore_only: bool = False):
    """Upload character content to GBF/Character/{name}/."""
    content_root = Path(f"characters/{char_folder}")
    if not content_root.exists():
        log(f"  Folder not found: {content_root}")
        return

    char_page_id = ctx.ensure_page(char_section_id, display_name)
    log(f"  {display_name}: {char_page_id}")

    if clean and not ctx.dry_run:
        log(f"  Cleaning {display_name} content...")
        deleted = delete_all_children(ctx, char_page_id)
        log(f"  Deleted {deleted} items")

    # Voice only mode
    if voice_only:
        voice_root = content_root / "voice" / "trans"
        if voice_root.exists():
            log("\n  [Voice]")
            voice_page_id = ctx.ensure_page(char_page_id, "Voice")
            sync_voice_tables(ctx, voice_page_id, voice_root, display_name)
        else:
            log(f"  No voice folder: {voice_root}")
        return

    # Lore only mode
    if lore_only:
        lore_root = content_root / "lore" / "trans"
        if lore_root.exists():
            log("\n  [Lore]")
            lore_page_id = ctx.ensure_page(char_page_id, "Lore")
            sync_lore_content(ctx, lore_page_id, lore_root, char_folder)
        else:
            log(f"  No lore folder: {lore_root}")
        return

    # Story (always sync, filtered by event_filter if specified)
    story_root = content_root / "story"
    if story_root.exists():
        log("\n  [Story]")
        story_page_id = ctx.ensure_page(char_page_id, "Story")
        sync_character_stories(ctx, story_page_id, story_root, char_folder, event_filter)

    # Skip Lore and Voice if specific event is requested
    if event_filter:
        log(f"\n  (Skipping Lore/Voice - event filter active)")
        return

    # Lore
    lore_root = content_root / "lore" / "trans"
    if lore_root.exists():
        log("\n  [Lore]")
        lore_page_id = ctx.ensure_page(char_page_id, "Lore")
        sync_lore_content(ctx, lore_page_id, lore_root, char_folder)

    # Voice - sync as databases
    voice_root = content_root / "voice" / "trans"
    if voice_root.exists():
        log("\n  [Voice]")
        voice_page_id = ctx.ensure_page(char_page_id, "Voice")
        sync_voice_tables(ctx, voice_page_id, voice_root, display_name)


def sync_character_stories(ctx: SyncContext, story_page_id: str, story_root: Path, 
                           char_folder: str, event_filter: str = ""):
    """Upload character event stories."""
    events = sorted(d for d in story_root.iterdir() if d.is_dir())
    
    for event_dir in events:
        if event_filter and event_filter.lower() not in event_dir.name.lower():
            continue

        trans_path = event_dir / "trans"
        if not trans_path.exists():
            continue

        log(f"    {event_dir.name}")
        event_page_id = ctx.ensure_page(story_page_id, event_dir.name)

        for md_file in sorted(trans_path.glob("*.md")):
            sync_md_to_page(ctx, event_page_id, md_file, f"char_story:{char_folder}:{event_dir.name}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Upload GBF content to Notion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 notion_upload.py --mode story                    # Root stories only
  python3 notion_upload.py --mode story --name "12.17"     # Specific story
  python3 notion_upload.py vajra 瓦姬拉                     # Single character
  python3 notion_upload.py vajra 瓦姬拉 --event zodiacamp   # Specific event
  python3 notion_upload.py --all                           # All characters
  python3 notion_upload.py --all --clean                   # Clean and re-upload all
        """
    )
    parser.add_argument("character", nargs="?", default="", help="Character folder name")
    parser.add_argument("display_name", nargs="?", default="", help="Display name in Notion")
    parser.add_argument("--mode", choices=["story", "character", "both"], default="both",
                        help="story=root stories, character=char content, both=all")
    parser.add_argument("--sync-mode", choices=["diff", "force"], default="diff",
                        help="diff=update changed, force=recreate all")
    parser.add_argument("--all", action="store_true", help="Upload all characters from characters.json")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument("--event", default="", help="Filter character stories by event name")
    parser.add_argument("--name", default="", help="Filter root stories by name")
    parser.add_argument("--clean", action="store_true", help="Delete content before uploading")
    parser.add_argument("--voice-only", action="store_true", help="Upload only voice content")
    parser.add_argument("--lore-only", action="store_true", help="Upload only lore content")
    args = parser.parse_args()

    # Validate API credentials
    api_key = NOTION_API_KEY or os.environ.get("NOTION_API_KEY", "")
    root_page_id = NOTION_ROOT_PAGE_ID or os.environ.get("NOTION_ROOT_PAGE_ID", "")

    if not api_key:
        log("ERROR: NOTION_API_KEY not set")
        log("Add to .env: NOTION_API_KEY=ntn_xxx")
        sys.exit(1)

    if not root_page_id:
        log("ERROR: NOTION_ROOT_PAGE_ID not set")
        log("Add to .env: NOTION_ROOT_PAGE_ID=xxx")
        log("Get ID from Notion page URL: https://notion.so/workspace/Title-{ID}")
        sys.exit(1)

    # Determine characters to upload
    characters = []
    if args.all:
        characters = load_characters_config()
        if not characters:
            log("ERROR: No characters in characters.json")
            log('Create characters.json: [{"folder": "vajra", "name": "瓦姬拉"}, ...]')
            sys.exit(1)
        # Only set mode to both if not using voice-only or lore-only
        if not (args.voice_only or args.lore_only):
            args.mode = "both"
        else:
            args.mode = "character"  # Skip root stories when using --voice-only or --lore-only
    elif args.character and args.display_name:
        characters = [{"folder": args.character, "name": args.display_name}]
        # Single character: only upload character content, not root stories
        args.mode = "character"
    elif args.mode == "story":
        pass  # No characters needed
    else:
        log("ERROR: Specify character or use --all")
        log("Usage: python3 notion_upload.py vajra 瓦姬拉")
        log("       python3 notion_upload.py --all")
        sys.exit(1)

    log(f"Mode: {args.mode}, Sync: {args.sync_mode}, Dry-run: {args.dry_run}")
    if args.clean:
        log("Clean mode: will delete existing content before uploading")

    # Initialize context
    cache_name = "all" if args.all else (args.character or "root")
    ctx = SyncContext(api_key, cache_path=get_cache_path(cache_name), 
                      mode=args.sync_mode, dry_run=args.dry_run)

    # Build hierarchy
    log("\nConnecting to Notion...")
    gbf_id = ctx.ensure_page(root_page_id, "GBF")
    log(f"  GBF page: {gbf_id}")

    # Upload root stories
    if args.mode in ("story", "both"):
        log("\n=== Root Stories ===")
        story_id = ctx.ensure_page(gbf_id, "Story")
        sync_root_stories(ctx, story_id, args.name, clean=args.clean)

    # Upload characters
    if args.mode in ("character", "both") and characters:
        char_section_id = ctx.ensure_page(gbf_id, "Character")
        
        for char in characters:
            folder = char.get("folder", "")
            name = char.get("name", "")
            if not folder or not name:
                continue
            
            log(f"\n=== Character: {name} ===")
            sync_character(ctx, char_section_id, folder, name, args.event, 
                          clean=args.clean, voice_only=args.voice_only, lore_only=args.lore_only)

    ctx.save()
    log("\nDone.")


if __name__ == "__main__":
    main()
