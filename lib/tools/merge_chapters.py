#!/usr/bin/env python3
"""
Merge episode files into chapter files to reduce API costs.

Usage:
    python -m lib.tools.merge_chapters characters/tikoh/story/marionette_stars/raw
    python -m lib.tools.merge_chapters characters/tikoh/story/*/raw --all
"""

import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple


def parse_filename(filename: str) -> Tuple[int, str, str, str, str]:
    """
    Parse story filename to extract components.
    
    Returns:
        (order, event, chapter, episode, title)
    
    Examples:
        01_marionette_stars_opening.md
        → (1, "marionette_stars", "", "", "Opening")
        
        02_marionette_stars_chapter_1_nova_episode_1.md
        → (2, "marionette_stars", "Chapter 1 - Nova", "Episode 1", "Chapter 1 - Nova - Episode 1")
    """
    # Remove .md extension
    name = filename.replace('.md', '')
    
    # Extract order number
    match = re.match(r'(\d+)_(.*)', name)
    if not match:
        return (999, "", "", "", name)
    
    order = int(match.group(1))
    rest = match.group(2)
    
    # Extract event name (first part before chapter/ending/etc)
    parts = rest.split('_')
    
    # Find where chapter/ending/opening/etc starts
    chapter_idx = -1
    for i, part in enumerate(parts):
        if part in ['chapter', 'ending', 'opening', 'transit', 'observation']:
            chapter_idx = i
            break
    
    if chapter_idx == -1:
        return (order, rest, "", "", rest.replace('_', ' ').title())
    
    event = '_'.join(parts[:chapter_idx])
    title_parts = parts[chapter_idx:]
    
    # Parse chapter and episode
    chapter = ""
    episode = ""
    
    if 'chapter' in title_parts:
        ch_idx = title_parts.index('chapter')
        if ch_idx + 1 < len(title_parts):
            chapter_num = title_parts[ch_idx + 1]
            # Find chapter subtitle (between chapter number and episode)
            subtitle_parts = []
            for i in range(ch_idx + 2, len(title_parts)):
                if title_parts[i] == 'episode':
                    break
                subtitle_parts.append(title_parts[i])
            
            if subtitle_parts:
                chapter = f"Chapter {chapter_num} - {' '.join(subtitle_parts).title()}"
            else:
                chapter = f"Chapter {chapter_num}"
    
    if 'episode' in title_parts:
        ep_idx = title_parts.index('episode')
        if ep_idx + 1 < len(title_parts):
            episode = f"Episode {title_parts[ep_idx + 1]}"
    
    # Build full title
    if chapter and episode:
        title = f"{chapter} - {episode}"
    elif chapter:
        title = chapter
    elif 'opening' in title_parts:
        title = "Opening"
    elif 'ending' in title_parts:
        # Handle ending episodes
        if 'episode' in title_parts:
            ep_idx = title_parts.index('episode')
            if ep_idx + 1 < len(title_parts):
                title = f"Ending - Episode {title_parts[ep_idx + 1]}"
            else:
                title = "Ending"
        else:
            title = "Ending"
    elif 'transit' in title_parts:
        if 'episode' in title_parts:
            ep_idx = title_parts.index('episode')
            if ep_idx + 1 < len(title_parts):
                title = f"Transit - Episode {title_parts[ep_idx + 1]}"
            else:
                title = "Transit"
        else:
            title = "Transit"
    elif 'observation' in title_parts:
        if 'episode' in title_parts:
            ep_idx = title_parts.index('episode')
            if ep_idx + 1 < len(title_parts):
                title = f"Observation - Episode {title_parts[ep_idx + 1]}"
            else:
                title = "Observation"
        else:
            title = "Observation"
    else:
        title = ' '.join(title_parts).title()
    
    return (order, event, chapter, episode, title)


def merge_chapters(raw_dir: Path, dry_run: bool = False) -> Dict:
    """
    Merge episode files by chapter.
    
    Args:
        raw_dir: Directory containing raw/*.md files
        dry_run: If True, only show what would be done
    
    Returns:
        {merged_count, file_count_before, file_count_after}
    """
    if not raw_dir.exists():
        print(f"Error: Directory not found: {raw_dir}")
        return {"error": "Directory not found"}
    
    md_files = sorted(raw_dir.glob('*.md'))
    if not md_files:
        print(f"No .md files found in {raw_dir}")
        return {"error": "No files found"}
    
    print(f"Found {len(md_files)} files in {raw_dir}")
    
    # Group files by chapter
    chapters = defaultdict(list)
    standalone = []
    
    for md_file in md_files:
        order, event, chapter, episode, title = parse_filename(md_file.name)
        
        if chapter:
            # It's a chapter episode - group it
            chapters[chapter].append((order, md_file, title, episode))
        else:
            # Standalone file (Opening, Ending, etc)
            standalone.append((order, md_file, title))
    
    print(f"\nGrouping:")
    print(f"  Chapters: {len(chapters)}")
    print(f"  Standalone: {len(standalone)}")
    
    if dry_run:
        print("\n[DRY RUN] Would create these merged files:")
        for chapter, episodes in sorted(chapters.items()):
            print(f"\n  {chapter} ({len(episodes)} episodes):")
            for _, _, title, _ in sorted(episodes):
                print(f"    - {title}")
        
        print(f"\n[DRY RUN] Would keep these standalone files:")
        for _, _, title in sorted(standalone):
            print(f"    - {title}")
        
        return {
            "dry_run": True,
            "merged_count": len(chapters),
            "file_count_before": len(md_files),
            "file_count_after": len(chapters) + len(standalone)
        }
    
    # Create merged directory
    merged_dir = raw_dir.parent / "raw_merged"
    merged_dir.mkdir(exist_ok=True)
    
    file_index = 1
    
    # Process standalone files first
    for order, md_file, title in sorted(standalone):
        content = md_file.read_text(encoding='utf-8')
        
        # Create new filename
        slug = title.lower().replace(' ', '_').replace('-', '')
        new_filename = f"{file_index:02d}_{slug}.md"
        new_path = merged_dir / new_filename
        
        new_path.write_text(content, encoding='utf-8')
        print(f"  [{file_index:02d}] {title} (standalone)")
        file_index += 1
    
    # Process chapters
    for chapter in sorted(chapters.keys()):
        episodes = sorted(chapters[chapter])
        
        # Merge all episodes of this chapter
        merged_content = []
        event_name = None
        
        for order, md_file, title, episode in episodes:
            content = md_file.read_text(encoding='utf-8')
            
            # Extract event name from first line if present
            lines = content.split('\n')
            if lines and lines[0].startswith('#'):
                if not event_name:
                    # Extract event name from first episode
                    event_name = lines[0].replace('#', '').strip().split('-')[0].strip()
                # Remove the title line
                content = '\n'.join(lines[1:]).strip()
            
            # Add episode header
            if episode:
                merged_content.append(f"## {episode}\n\n{content}")
            else:
                merged_content.append(content)
        
        # Create merged file
        slug = chapter.lower().replace(' ', '_').replace('-', '')
        new_filename = f"{file_index:02d}_{slug}.md"
        new_path = merged_dir / new_filename
        
        # Add main chapter title
        full_title = f"{event_name} - {chapter}" if event_name else chapter
        full_content = f"# {full_title}\n\n" + '\n\n'.join(merged_content)
        
        new_path.write_text(full_content, encoding='utf-8')
        print(f"  [{file_index:02d}] {chapter} ({len(episodes)} episodes merged)")
        file_index += 1
    
    print(f"\nMerged files saved to: {merged_dir}")
    print(f"File count: {len(md_files)} → {file_index - 1} ({len(md_files) - (file_index - 1)} fewer files)")
    
    return {
        "merged_count": len(chapters),
        "file_count_before": len(md_files),
        "file_count_after": file_index - 1,
        "output_dir": str(merged_dir)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Merge episode files by chapter to reduce API costs"
    )
    parser.add_argument(
        "directory",
        help="Directory containing raw/*.md files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all story/*/raw directories under the parent"
    )
    
    args = parser.parse_args()
    
    if args.all:
        # Find all raw directories
        base_dir = Path(args.directory).parent
        raw_dirs = list(base_dir.glob('*/raw'))
        
        print(f"Found {len(raw_dirs)} raw directories")
        for raw_dir in raw_dirs:
            print(f"\n{'='*60}")
            print(f"Processing: {raw_dir}")
            print(f"{'='*60}")
            merge_chapters(raw_dir, args.dry_run)
    else:
        merge_chapters(Path(args.directory), args.dry_run)


if __name__ == "__main__":
    main()


