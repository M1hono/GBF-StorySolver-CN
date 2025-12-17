#!/usr/bin/env python3
"""
Quick translation utility - Multi-engine support.

Usage:
    python -m lib.translate claude ./raw ./trans     # Claude (best quality)
    python -m lib.translate openai ./raw ./trans     # GPT-4o-mini (good value)
    python -m lib.translate gemini ./raw ./trans     # Gemini Flash (cheapest!)
    python -m lib.translate deepl ./raw ./trans      # DeepL (500K free/month)
    python -m lib.translate caiyun ./raw ./trans     # Caiyun (CN service)
    python -m lib.translate lookup "Vajra"           # Lookup character name
    python -m lib.translate cost ./raw               # Estimate translation cost
"""

import sys
import argparse
from pathlib import Path


def translate_claude(raw_dir: str, trans_dir: str, source_lang: str = 'en'):
    """Translate using Claude (auto-detects voice tables)."""
    from .translators.claude import claude_translate_directory
    return claude_translate_directory(raw_dir, trans_dir, source_lang)


def translate_openai(raw_dir: str, trans_dir: str, source_lang: str = 'en'):
    """Translate using OpenAI GPT."""
    from .translators.openai_translator import translate_directory
    count = translate_directory(raw_dir, trans_dir)
    return {"translated": count}


def translate_gemini(raw_dir: str, trans_dir: str, source_lang: str = 'en'):
    """Translate using Google Gemini (cheapest!)."""
    from .translators.gemini import translate_directory
    count = translate_directory(raw_dir, trans_dir)
    return {"translated": count}


def translate_deepl(raw_dir: str, trans_dir: str, source_lang: str = 'ja'):
    """Translate using DeepL (500K free chars/month)."""
    from .translators.deepl import translate_directory
    lang_map = {'ja': 'JA', 'en': 'EN', 'jp': 'JA'}
    count = translate_directory(raw_dir, trans_dir, lang_map.get(source_lang, 'JA'), 'ZH')
    return {"translated": count}


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


def estimate_cost(raw_dir: str):
    """Estimate translation cost for all engines."""
    import tiktoken
    
    path = Path(raw_dir)
    enc = tiktoken.encoding_for_model("gpt-4o")
    
    total_chars = 0
    total_tokens = 0
    
    if path.is_file():
        files = [path]
    else:
        files = list(path.glob("**/*.md"))
    
    for f in files:
        content = f.read_text(encoding='utf-8', errors='ignore')
        total_chars += len(content)
        total_tokens += len(enc.encode(content))
    
    print(f"📊 Translation Cost Estimate")
    print(f"=" * 50)
    print(f"Files: {len(files)}")
    print(f"Characters: {total_chars:,}")
    print(f"Tokens: {total_tokens:,} (~{total_tokens/1000:.1f}K)")
    print()
    print("💰 Estimated Cost (input + output):")
    print("-" * 50)
    
    # Calculate costs
    output_tokens = int(total_tokens * 1.3)  # Estimate output is 1.3x input
    
    engines = [
        ("Gemini 2.5 Flash", 0.075, 0.30),
        ("GPT-4o-mini", 0.15, 0.60),
        ("Claude Haiku", 0.25, 1.25),
        ("GPT-4.1-mini", 0.40, 1.60),
        ("GPT-4o", 2.50, 10.00),
        ("Claude Sonnet 4", 3.00, 15.00),
        ("Gemini 2.5 Pro", 1.25, 10.00),
    ]
    
    for name, input_price, output_price in engines:
        cost = (total_tokens * input_price + output_tokens * output_price) / 1_000_000
        print(f"  {name:20} ${cost:.4f}")
    
    print()
    print("📝 Character-based APIs:")
    print("-" * 50)
    print(f"  DeepL Free           FREE (if under 500K/month limit)")
    print(f"  DeepL Pro            €{total_chars * 20 / 1_000_000:.4f}")
    print(f"  彩云小译             ¥{total_chars * 19 / 1_000_000:.4f}")
    print()
    print("🏆 Recommendation: gemini (cheapest) or claude (best quality)")


def main():
    parser = argparse.ArgumentParser(
        description="GBF multi-engine translator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Engines:
  claude   Best quality (Claude Sonnet 4)
  openai   Good balance (GPT-4o-mini)
  gemini   Cheapest! (Gemini 2.5 Flash)
  deepl    Free 500K chars/month
  caiyun   Chinese service
        """
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Claude command
    claude_parser = subparsers.add_parser("claude", help="Translate with Claude (best quality)")
    claude_parser.add_argument("raw_dir", help="Raw content directory")
    claude_parser.add_argument("trans_dir", help="Output directory")
    claude_parser.add_argument("--lang", default="en", help="Source language")
    
    # OpenAI command
    openai_parser = subparsers.add_parser("openai", help="Translate with GPT-4o-mini")
    openai_parser.add_argument("raw_dir", help="Raw content directory")
    openai_parser.add_argument("trans_dir", help="Output directory")
    openai_parser.add_argument("--lang", default="en", help="Source language")
    
    # Gemini command
    gemini_parser = subparsers.add_parser("gemini", help="Translate with Gemini (cheapest!)")
    gemini_parser.add_argument("raw_dir", help="Raw content directory")
    gemini_parser.add_argument("trans_dir", help="Output directory")
    gemini_parser.add_argument("--lang", default="en", help="Source language")
    gemini_parser.add_argument("--batch", action="store_true", help="Use batch API (50% discount, 24h)")
    
    # DeepL command
    deepl_parser = subparsers.add_parser("deepl", help="Translate with DeepL (500K free/month)")
    deepl_parser.add_argument("raw_dir", help="Raw content directory")
    deepl_parser.add_argument("trans_dir", help="Output directory")
    deepl_parser.add_argument("--lang", default="ja", help="Source language (ja/en)")
    
    # Caiyun command
    caiyun_parser = subparsers.add_parser("caiyun", help="Translate with Caiyun")
    caiyun_parser.add_argument("raw_dir", help="Raw content directory")
    caiyun_parser.add_argument("trans_dir", help="Output directory")
    caiyun_parser.add_argument("--lang", default="en", help="Source language")
    
    # Lookup command
    lookup_parser = subparsers.add_parser("lookup", help="Lookup character name")
    lookup_parser.add_argument("name", help="Character name to lookup")
    
    # Cost estimate command
    cost_parser = subparsers.add_parser("cost", help="Estimate translation cost")
    cost_parser.add_argument("raw_dir", help="Raw content directory")
    
    args = parser.parse_args()
    
    if args.command == "claude":
        result = translate_claude(args.raw_dir, args.trans_dir, args.lang)
        print(f"Translated {result.get('translated', 0)} files")
    elif args.command == "openai":
        result = translate_openai(args.raw_dir, args.trans_dir, args.lang)
        print(f"Translated {result.get('translated', 0)} files")
    elif args.command == "gemini":
        if getattr(args, 'batch', False):
            from .translators.batch_translator import submit_batch
            batch_id = submit_batch(args.raw_dir, "gemini")
            print(f"\nBatch submitted: {batch_id}")
            print("Check status: python -m lib.translators.batch_translator status {batch_id}")
        else:
            result = translate_gemini(args.raw_dir, args.trans_dir, args.lang)
            print(f"Translated {result.get('translated', 0)} files")
    elif args.command == "deepl":
        result = translate_deepl(args.raw_dir, args.trans_dir, args.lang)
        print(f"Translated {result.get('translated', 0)} files")
    elif args.command == "caiyun":
        result = translate_caiyun(args.raw_dir, args.trans_dir, args.lang)
        print(f"Translated {result.get('translated', 0)} files")
    elif args.command == "lookup":
        lookup_name(args.name)
    elif args.command == "cost":
        estimate_cost(args.raw_dir)


if __name__ == "__main__":
    main()

