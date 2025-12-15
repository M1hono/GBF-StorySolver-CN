#!/usr/bin/env python3
"""
Quick translation utility.

Usage:
    python -m lib.translate claude ./raw ./trans
    python -m lib.translate caiyun ./raw ./trans
    python -m lib.translate lookup "Vajra"  # Lookup character name
"""

import sys
import argparse
from pathlib import Path


def translate_claude(raw_dir: str, trans_dir: str, source_lang: str = 'en'):
    """Translate using Claude (auto-detects voice tables)."""
    from .translators.claude import claude_translate_directory
    return claude_translate_directory(raw_dir, trans_dir, source_lang)


def translate_caiyun(raw_dir: str, trans_dir: str, source_lang: str = 'en'):
    """Translate using Caiyun."""
    from .translators.caiyun import translate_directory
    return translate_directory(raw_dir, trans_dir, source_lang)


def lookup_name(name: str):
    """Lookup character name in local database."""
    from .translators import translator
    
    # Try smart lookup
    cn = translator.smart_lookup(name)
    if cn:
        print(f"Found: {name} → {cn}")
        return cn
    
    # Show similar names
    print(f"Not found: {name}")
    similar = [k for k in translator.npc_names.keys() if name.lower() in k.lower()]
    if similar:
        print("Similar names:")
        for s in similar[:5]:
            print(f"  {s} → {translator.npc_names[s]}")
    
    return None


def main():
    parser = argparse.ArgumentParser(description="GBF content translator")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Claude command
    claude_parser = subparsers.add_parser("claude", help="Translate with Claude")
    claude_parser.add_argument("raw_dir", help="Raw content directory")
    claude_parser.add_argument("trans_dir", help="Output directory")
    claude_parser.add_argument("--lang", default="en", help="Source language")
    
    # Caiyun command
    caiyun_parser = subparsers.add_parser("caiyun", help="Translate with Caiyun")
    caiyun_parser.add_argument("raw_dir", help="Raw content directory")
    caiyun_parser.add_argument("trans_dir", help="Output directory")
    caiyun_parser.add_argument("--lang", default="en", help="Source language")
    
    # Lookup command
    lookup_parser = subparsers.add_parser("lookup", help="Lookup character name")
    lookup_parser.add_argument("name", help="Character name to lookup")
    
    args = parser.parse_args()
    
    if args.command == "claude":
        result = translate_claude(args.raw_dir, args.trans_dir, args.lang)
        print(f"Translated {result.get('translated', 0)} files")
    elif args.command == "caiyun":
        result = translate_caiyun(args.raw_dir, args.trans_dir, args.lang)
        print(f"Translated {result.get('translated', 0)} files")
    elif args.command == "lookup":
        lookup_name(args.name)


if __name__ == "__main__":
    main()

