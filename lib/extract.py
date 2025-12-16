#!/usr/bin/env python3
"""
Quick extraction utility.

Usage:
    # Story + Cast for an event
    python -m lib.extract story Auld_Lang_Fry_PREMIUM characters/vajra
    python -m lib.extract cast Auld_Lang_Fry_PREMIUM characters/vajra
    
    # Voice and Lore for a character
    python -m lib.extract voice Vajra characters/vajra
    python -m lib.extract lore Vajra characters/vajra

Output structure:
    characters/{character}/
    ├── story/{event}/
    │   ├── raw/*.md
    │   └── trans/cast.md
    ├── voice/raw/{battle,menu,holidays,...}/*.md
    └── lore/raw/lore.md
"""

import sys
import argparse
from pathlib import Path

try:
    from .extractors import StoryExtractor, CastExtractor, VoiceExtractor, LoreExtractor, PortraitExtractor
except ImportError:
    from extractors import StoryExtractor, CastExtractor, VoiceExtractor, LoreExtractor, PortraitExtractor


def cmd_story(args):
    """Extract story chapters."""
    ext = StoryExtractor(headless=args.headless)
    result = ext.extract(args.slug, args.character_dir, args.folder)
    
    print(f"\n{'='*50}")
    print(f"Story: {'Success' if result['success'] else 'Failed'}")
    print(f"Output: {result.get('output_dir')}")
    print(f"Chapters: {result.get('chapters', [])}")
    return result


def cmd_cast(args):
    """Extract cast information."""
    ext = CastExtractor(headless=args.headless)
    result = ext.extract(args.slug, args.character_dir, args.folder)
    
    print(f"\n{'='*50}")
    print(f"Cast: {'Success' if result['success'] else 'Failed'}")
    print(f"Output: {result.get('output_path')}")
    print(f"Characters: {len(result.get('cast', []))}")
    return result


def cmd_voice(args):
    """Extract voice lines."""
    ext = VoiceExtractor(headless=args.headless)
    result = ext.extract(args.slug, args.character_dir)
    
    print(f"\n{'='*50}")
    print(f"Voice: {'Success' if result['success'] else 'Failed'}")
    print(f"Files: {len(result.get('files', []))}")
    return result


def cmd_lore(args):
    """Extract lore content."""
    ext = LoreExtractor(headless=args.headless)
    result = ext.extract(args.slug, args.character_dir)
    
    print(f"\n{'='*50}")
    print(f"Lore: {'Success' if result['success'] else 'Failed'}")
    print(f"Output: {result.get('output_path')}")
    print(f"Sections: {len(result.get('sections', []))}")
    return result


def cmd_portraits(args):
    """Download character expression portraits."""
    ext = PortraitExtractor()
    stats = ext.download_portraits(
        args.name, 
        args.output_dir,
        include_skycompass=args.skycompass,
        prefer_up=args.prefer_up
    )
    
    if stats['total'] == 0:
        print("\nFailed to download portraits. Check character name.")
        sys.exit(1)
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="GBF Wiki content extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m lib.extract story Auld_Lang_Fry_PREMIUM characters/vajra
    python -m lib.extract cast Auld_Lang_Fry_PREMIUM characters/vajra
    python -m lib.extract voice Vajra characters/vajra
    python -m lib.extract lore Vajra characters/vajra
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Story command
    story_parser = subparsers.add_parser("story", help="Extract story chapters")
    story_parser.add_argument("slug", help="Event slug (e.g., Auld_Lang_Fry_PREMIUM)")
    story_parser.add_argument("character_dir", help="Character directory (e.g., characters/vajra)")
    story_parser.add_argument("--folder", help="Custom output folder name")
    story_parser.add_argument("--headless", action="store_true")
    story_parser.set_defaults(func=cmd_story)
    
    # Cast command
    cast_parser = subparsers.add_parser("cast", help="Extract cast portraits")
    cast_parser.add_argument("slug", help="Event slug (e.g., Auld_Lang_Fry_PREMIUM)")
    cast_parser.add_argument("character_dir", help="Character directory")
    cast_parser.add_argument("--folder", help="Custom output folder name")
    cast_parser.add_argument("--headless", action="store_true")
    cast_parser.set_defaults(func=cmd_cast)
    
    # Voice command
    voice_parser = subparsers.add_parser("voice", help="Extract voice lines")
    voice_parser.add_argument("slug", help="Character slug (e.g., Vajra)")
    voice_parser.add_argument("character_dir", help="Character directory")
    voice_parser.add_argument("--headless", action="store_true")
    voice_parser.set_defaults(func=cmd_voice)
    
    # Lore command
    lore_parser = subparsers.add_parser("lore", help="Extract lore content")
    lore_parser.add_argument("slug", help="Character slug (e.g., Vajra)")
    lore_parser.add_argument("character_dir", help="Character directory")
    lore_parser.add_argument("--headless", action="store_true")
    lore_parser.set_defaults(func=cmd_lore)
    
    # Portraits command
    portraits_parser = subparsers.add_parser("portraits", help="Download character expression portraits")
    portraits_parser.add_argument("name", help="Character name (e.g., Yuisis, Vajra)")
    portraits_parser.add_argument("output_dir", nargs="?", help="Output directory (default: portraits/{name})")
    portraits_parser.add_argument("--skycompass", action="store_true", help="Also download Skycompass high-res portraits")
    portraits_parser.add_argument("--prefer-up", action="store_true", help="Only download '_up' variants (best quality)")
    portraits_parser.set_defaults(func=cmd_portraits)
    
    args = parser.parse_args()
    
    # Set default output_dir for portraits
    if args.command == "portraits" and not args.output_dir:
        args.output_dir = f"portraits/{args.name.lower()}"
    
    args.func(args)


if __name__ == "__main__":
    main()
