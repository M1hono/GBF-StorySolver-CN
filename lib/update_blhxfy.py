#!/usr/bin/env python3
"""
Update local BLHXFY data from official repository.

Usage:
    python -m lib.update_blhxfy [--force]
    
Options:
    --force    Force re-download even if files exist
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Repository URLs
BLHXFY_REPO = "https://github.com/BLHXFY-Group/BLHXFY.git"
AI_TRANSLATION_REPO = "https://github.com/BLHXFY-Group/AI-Translation.git"

# Local paths - always use lib/ as base
LIB_DIR = Path(__file__).parent.resolve()
LOCAL_DATA_DIR = LIB_DIR / "local_data"
BLHXFY_DIR = LOCAL_DATA_DIR / "blhxfy"
TEMP_DIR = LOCAL_DATA_DIR / ".temp"


def run_git(args: list, cwd: Path = None) -> bool:
    """Run git command and return success status."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Git error: {e}")
        return False


def clone_or_update_repo(repo_url: str, local_path: Path, name: str) -> bool:
    """Clone repository or update existing one."""
    if local_path.exists():
        print(f"  Updating {name}...")
        if run_git(["pull", "--ff-only"], cwd=local_path):
            print(f"  ✓ {name} updated")
            return True
        else:
            print(f"  ! Pull failed, trying fresh clone...")
            shutil.rmtree(local_path)
    
    print(f"  Cloning {name}...")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if run_git(["clone", "--depth", "1", repo_url, str(local_path)]):
        print(f"  ✓ {name} cloned")
        return True
    
    print(f"  ✗ Failed to clone {name}")
    return False


def sync_etc_files(blhxfy_root: Path, target_dir: Path) -> int:
    """Sync CSV files from BLHXFY repo to target."""
    count = 0
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Files in data/ directory
    data_files = ["npc-name-en.csv", "npc-name-jp.csv"]
    # Files in data/etc/ directory  
    etc_files = ["noun.csv", "noun-fix.csv", "caiyun-prefix.csv"]
    
    # Sync from data/
    for filename in data_files:
        src = blhxfy_root / "data" / filename
        dst = target_dir / filename
        if src.exists():
            shutil.copy2(src, dst)
            count += 1
            print(f"    ✓ {filename}")
        else:
            print(f"    - {filename} (not found in data/)")
    
    # Sync from data/etc/
    for filename in etc_files:
        src = blhxfy_root / "data" / "etc" / filename
        dst = target_dir / filename
        if src.exists():
            shutil.copy2(src, dst)
            count += 1
            print(f"    ✓ {filename}")
        else:
            print(f"    - {filename} (not found in data/etc/)")
    
    return count


def extract_race_mappings(common_skill_path: Path, noun_path: Path) -> int:
    """Extract race mappings from common-skill.csv and append to noun.csv."""
    if not common_skill_path.exists():
        print(f"    - common-skill.csv (not found)")
        return 0
    
    # Race mappings from common-skill.csv
    race_mappings = {
        # Japanese -> Chinese
        "ヒューマン": "人类",
        "エルーン": "艾伦族",
        "ドラフ": "德拉夫族",
        "ハーヴィン": "哈文族",
        "星晶獣": "星晶兽",
        "不明": "不明",
        # English -> Chinese
        "Human": "人类",
        "Erune": "艾伦族",
        "Draph": "德拉夫族",
        "Harvin": "哈文族",
        "Primal": "星晶兽",
        "Unknown": "不明",
    }
    
    # Read existing noun.csv
    existing = set()
    if noun_path.exists():
        with open(noun_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(',')
                if parts:
                    existing.add(parts[0])
    
    # Append new race mappings
    added = 0
    with open(noun_path, 'a', encoding='utf-8') as f:
        for orig, trans in race_mappings.items():
            if orig not in existing:
                f.write(f"{orig},{trans}\n")
                added += 1
    
    if added > 0:
        print(f"    ✓ Added {added} race mappings to noun.csv")
    else:
        print(f"    - Race mappings already present")
    
    return added


def sync_scenario_files(source_dir: Path, target_dir: Path, clear_first: bool = False) -> int:
    """
    Sync scenario translation files.
    
    Args:
        source_dir: Source directory containing CSV files
        target_dir: Target directory to copy to
        clear_first: If True, clear target directory before syncing
    
    Returns:
        Number of files synced
    """
    count = 0
    
    if not source_dir.exists():
        print(f"    Source directory not found: {source_dir}")
        return 0
    
    if clear_first and target_dir.exists():
        print(f"    Clearing existing scenario directory...")
        shutil.rmtree(target_dir)
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy all CSV files recursively, preserving directory structure
    for src_file in source_dir.rglob("*.csv"):
        rel_path = src_file.relative_to(source_dir)
        dst_file = target_dir / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        count += 1
    
    return count


def update_blhxfy(force: bool = False):
    """Main update function."""
    print("=" * 50)
    print("BLHXFY Data Update")
    print("=" * 50)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Ensure temp directory exists
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clone/update main BLHXFY repo (for etc/ and data/ files)
    blhxfy_temp = TEMP_DIR / "BLHXFY"
    print("[1/3] Fetching BLHXFY-Group/BLHXFY repository...")
    if not clone_or_update_repo(BLHXFY_REPO, blhxfy_temp, "BLHXFY"):
        return False
    
    # Clone/update AI-Translation repo (for story translations)
    ai_trans_temp = TEMP_DIR / "AI-Translation"
    print("\n[2/3] Fetching BLHXFY-Group/AI-Translation repository...")
    if not clone_or_update_repo(AI_TRANSLATION_REPO, ai_trans_temp, "AI-Translation"):
        print("  (AI Translation data will not be updated)")
    
    # Sync files
    print("\n[3/3] Syncing files to local_data/blhxfy/...")
    
    # Sync etc/ files
    etc_target = BLHXFY_DIR / "etc"
    print("  etc/ files:")
    etc_count = sync_etc_files(blhxfy_temp, etc_target)
    
    # Extract race mappings from common-skill.csv
    common_skill = blhxfy_temp / "data" / "etc" / "common-skill.csv"
    noun_target = etc_target / "noun.csv"
    extract_race_mappings(common_skill, noun_target)
    
    # Sync scenario files - merge from both sources
    scenario_target = BLHXFY_DIR / "scenario"
    scenario_count = 0
    
    # First, sync from BLHXFY/data/scenario (clear first)
    blhxfy_scenario = blhxfy_temp / "data" / "scenario"
    print(f"  scenario/ files:")
    if blhxfy_scenario.exists():
        count = sync_scenario_files(blhxfy_scenario, scenario_target, clear_first=True)
        scenario_count += count
        print(f"    ✓ {count} files from BLHXFY/data/scenario")
    
    # Then, sync from AI-Translation/story (merge, don't clear)
    if ai_trans_temp.exists():
        ai_scenario = ai_trans_temp / "story"
        count = sync_scenario_files(ai_scenario, scenario_target, clear_first=False)
        scenario_count += count
        print(f"    ✓ {count} files from AI-Translation/story")
    
    print()
    print("=" * 50)
    print(f"Update complete!")
    print(f"  - {etc_count} etc files synced")
    print(f"  - {scenario_count} scenario files synced")
    print(f"  - Data location: {BLHXFY_DIR}")
    print("=" * 50)
    
    return True


def check_status():
    """Check current BLHXFY data status."""
    print("BLHXFY Local Data Status")
    print("-" * 40)
    
    if not BLHXFY_DIR.exists():
        print("✗ No local BLHXFY data found")
        print(f"  Run: python -m lib.update_blhxfy")
        return
    
    etc_dir = BLHXFY_DIR / "etc"
    scenario_dir = BLHXFY_DIR / "scenario"
    
    print(f"Location: {BLHXFY_DIR}")
    print()
    
    # Check etc files
    print("etc/ files:")
    if etc_dir.exists():
        for f in sorted(etc_dir.glob("*.csv")):
            stat = f.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
            lines = sum(1 for _ in open(f, encoding='utf-8-sig'))
            print(f"  ✓ {f.name}: {lines} lines (updated: {mtime})")
    else:
        print("  ✗ etc/ directory not found")
    
    print()
    
    # Check scenario files
    print("scenario/ files:")
    if scenario_dir.exists():
        csv_count = sum(1 for _ in scenario_dir.rglob("*.csv"))
        print(f"  ✓ {csv_count} scenario translation files")
    else:
        print("  - No scenario data (run update to fetch)")


def main():
    parser = argparse.ArgumentParser(
        description="Update BLHXFY local data from official repositories"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force fresh clone instead of update"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show current data status"
    )
    
    args = parser.parse_args()
    
    if args.status:
        check_status()
        return
    
    if args.force:
        print("Force mode: removing existing temp data...")
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
    
    success = update_blhxfy(args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

