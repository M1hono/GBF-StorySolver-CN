#!/usr/bin/env python3
"""
Find local stories containing a specific character.

This tool searches lib/local_data/blhxfy/scenario/ for stories that mention
a character. It supports searching by:
- Chinese name (directly matches content)
- English name (auto-converted to Chinese via mappings)
- Japanese name (auto-converted to Chinese via mappings)

Usage:
    python -m lib.tools.find_character_stories "缇可"
    python -m lib.tools.find_character_stories "Tikoh"
    python -m lib.tools.find_character_stories "缇可" --extract characters/tikoh

Output:
    Lists all activities (folder names) containing the character.
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict

# Add lib to path
LIB_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(LIB_DIR.parent))

from lib.utils.config import LOCAL_BLHXFY_SCENARIO, LOCAL_BLHXFY_ETC


def load_name_mappings() -> Dict[str, str]:
    """Load EN->CN and JP->CN name mappings from CSV files."""
    mappings = {}
    
    # Load EN->CN mappings
    en_csv = Path(LOCAL_BLHXFY_ETC) / "npc-name-en.csv"
    if en_csv.exists():
        with open(en_csv, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 2 and parts[0] and parts[1]:
                    # EN name -> CN name
                    mappings[parts[0].strip().lower()] = parts[1].strip()
    
    # Load added EN mappings
    added_csv = Path(LOCAL_BLHXFY_ETC) / "added_en_mapping.csv"
    if added_csv.exists():
        with open(added_csv, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 2 and parts[0] and parts[1]:
                    mappings[parts[0].strip().lower()] = parts[1].strip()
    
    # Load JP->CN mappings
    jp_csv = Path(LOCAL_BLHXFY_ETC) / "npc-name-jp.csv"
    if jp_csv.exists():
        with open(jp_csv, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 2 and parts[0] and parts[1]:
                    # JP name -> CN name
                    mappings[parts[0].strip()] = parts[1].strip()
    
    return mappings


def resolve_name(name: str, mappings: Dict[str, str]) -> List[str]:
    """
    Resolve a name to its Chinese equivalent(s).
    Returns list of possible Chinese names to search for.
    """
    results = [name]  # Always include original
    
    # Check if it's already Chinese (contains Chinese characters)
    if any('\u4e00' <= c <= '\u9fff' for c in name):
        return results
    
    # Try to find CN mapping
    name_lower = name.lower()
    if name_lower in mappings:
        results.append(mappings[name_lower])
    
    # Also try with original case
    if name in mappings:
        results.append(mappings[name])
    
    return list(set(results))


def search_scenarios(search_names: List[str], scenario_dir: str) -> Dict[str, List[str]]:
    """
    Search scenario files for character mentions.
    
    IMPORTANT: Only searches story-related activities (活动剧情, SIDE-STORY, 主线剧情, 支线剧情).
    Skips character-specific fate episodes (角色剧情/SSR, 角色剧情/SR).
    
    Returns:
        Dict mapping activity folder name -> list of files containing the character
    """
    results = defaultdict(list)
    scenario_path = Path(scenario_dir)
    
    if not scenario_path.exists():
        print(f"Warning: Scenario directory not found: {scenario_dir}")
        return results
    
    # Allowed categories (story-related only)
    allowed_categories = {'活动剧情', 'SIDE-STORY', 'SIDE_STORY', '主线剧情', '支线剧情', '新手教程'}
    
    # Search all CSV files recursively
    for file_path in scenario_path.rglob('*.csv'):
        if not file_path.is_file():
            continue
        
        # Get category from path
        rel_to_scenario = file_path.relative_to(scenario_path)
        parts = rel_to_scenario.parts
        
        if len(parts) < 2:
            continue
        
        category = parts[0]
        
        # Skip character fate episodes (角色剧情)
        if '角色剧情' in category or category in ['SSR', 'SR']:
            continue
        
        # Only process allowed categories
        if category not in allowed_categories:
            continue
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Check if any search name is in the content
            for name in search_names:
                if name in content:
                    # activity is everything between category and the filename
                    if len(parts) > 2:
                        activity = '/'.join(parts[1:-1])
                    else:
                        activity = parts[0]
                    
                    activity_key = f"{category}/{activity}"
                    file_rel = parts[-1]
                    results[activity_key].append(file_rel)
                    break
                    
        except (UnicodeDecodeError, IOError):
            continue
    
    return dict(results)


def extract_activity(
    activity_key: str, 
    scenario_dir: str, 
    output_dir: str,
    copy_to_story_translated: bool = True
) -> bool:
    """
    Extract an activity's CSV files using ScenarioExtractor.
    
    Args:
        activity_key: Activity path like "活动剧情/金月3"
        scenario_dir: Path to scenario directory
        output_dir: Target directory (e.g., characters/tikoh/story)
        copy_to_story_translated: Also copy to story/translated/
    
    Returns:
        True if extraction succeeded
    """
    source = Path(scenario_dir) / activity_key
    if not source.exists():
        print(f"Error: Activity not found: {source}")
        return False
    
    # Import scenario extractor
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from lib.extractors.scenario import ScenarioExtractor
    
    # Get just the activity name (last part of key)
    activity_name = Path(activity_key).name
    
    # Use ScenarioExtractor to convert CSV to markdown
    extractor = ScenarioExtractor()
    
    # Extract to character story folder
    char_target = Path(output_dir) / activity_name / "trans"
    result = extractor.extract(str(source), str(char_target))
    
    if not result.get('success'):
        print(f"Failed to extract {activity_key}: {result.get('error', 'Unknown error')}")
        return False
    
    print(f"Extracted to {char_target}")
    
    # Also copy to story/translated/
    if copy_to_story_translated:
        repo_root = Path(scenario_dir).parent.parent.parent.parent
        story_target = repo_root / "story" / "translated" / activity_name
        
        # Extract again to story/translated
        result2 = extractor.extract(str(source), str(story_target))
        
        if result2.get('success'):
            print(f"Also copied to {story_target}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Find local stories containing a specific character"
    )
    parser.add_argument(
        "name",
        help="Character name (Chinese, English, or Japanese)"
    )
    parser.add_argument(
        "--extract",
        metavar="DIR",
        help="Extract found activities to this character directory (e.g., characters/tikoh)"
    )
    parser.add_argument(
        "--no-story-translated",
        action="store_true",
        help="Don't also copy to story/translated/"
    )
    parser.add_argument(
        "--scenario-dir",
        default=LOCAL_BLHXFY_SCENARIO,
        help="Path to scenario directory"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed file matches"
    )
    
    args = parser.parse_args()
    
    # Load mappings
    print("Loading name mappings...")
    mappings = load_name_mappings()
    print(f"Loaded {len(mappings)} name mappings")
    
    # Resolve name to Chinese
    search_names = resolve_name(args.name, mappings)
    print(f"Searching for: {', '.join(search_names)}")
    
    # Search scenarios
    print(f"\nSearching in: {args.scenario_dir}")
    results = search_scenarios(search_names, args.scenario_dir)
    
    if not results:
        print("\nNo matching activities found.")
        return 1
    
    # Display results
    print(f"\n{'='*60}")
    print(f"Found {len(results)} activities containing '{args.name}':")
    print(f"{'='*60}")
    
    for activity, files in sorted(results.items()):
        print(f"\n📁 {activity}")
        if args.verbose:
            for f in files[:5]:  # Show first 5 files
                print(f"   └─ {f}")
            if len(files) > 5:
                print(f"   └─ ... and {len(files) - 5} more files")
        else:
            print(f"   ({len(files)} files)")
    
    # Extract if requested
    if args.extract:
        print(f"\n{'='*60}")
        print(f"Extracting to: {args.extract}")
        print(f"{'='*60}")
        
        for activity_key in results.keys():
            extract_activity(
                activity_key,
                args.scenario_dir,
                args.extract + "/story",
                copy_to_story_translated=not args.no_story_translated
            )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

