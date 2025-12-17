"""
DeepL Translation Module - with Glossary support

Supports: DeepL API Free (500K chars/month), DeepL API Pro

Features:
- Native glossary support for consistent terminology
- Best translation quality for JP→CN
- 500K free characters/month

Usage:
    from lib.translators.deepl import translate_story, translate_file
    result = translate_story(content)
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

import deepl

# Config
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "")
GLOSSARY_NAME = "gbf_terminology"


def get_client() -> deepl.Translator:
    """Get DeepL client."""
    if not DEEPL_API_KEY:
        raise ValueError("DEEPL_API_KEY not set. Add to .env file.")
    return deepl.Translator(DEEPL_API_KEY)


def get_glossary_entries() -> Dict[str, str]:
    """Get glossary entries from BLHXFY data."""
    try:
        from .blhxfy import translator
        entries = {}
        
        # Add character names (JP→CN)
        jp_to_cn = translator.npc_names.get("jp_to_cn", {})
        for jp, cn in jp_to_cn.items():
            if jp and cn and jp != cn:
                entries[jp] = cn
        
        # Add key terminology
        nouns = translator.nouns
        for jp, cn in nouns.items():
            if jp and cn and jp != cn and len(jp) > 1:
                entries[jp] = cn
        
        return entries
    except Exception as e:
        print(f"Warning: Could not load glossary entries: {e}")
        return {}


def setup_glossary(translator_client: deepl.Translator) -> Optional[str]:
    """Setup or get existing glossary. Returns glossary_id."""
    try:
        # Check existing glossaries
        glossaries = translator_client.list_glossaries()
        for g in glossaries:
            if g.name == GLOSSARY_NAME:
                print(f"  Using existing glossary: {g.glossary_id}")
                return g.glossary_id
        
        # Create new glossary
        entries = get_glossary_entries()
        if not entries:
            return None
        
        # DeepL has limits on glossary size, take top entries
        max_entries = 5000
        sorted_entries = dict(list(entries.items())[:max_entries])
        
        glossary = translator_client.create_glossary(
            GLOSSARY_NAME,
            source_lang="JA",
            target_lang="ZH",
            entries=sorted_entries
        )
        print(f"  Created glossary with {len(sorted_entries)} entries")
        return glossary.glossary_id
        
    except Exception as e:
        print(f"  Glossary setup failed: {e}")
        return None


def translate_text(
    client: deepl.Translator,
    text: str,
    source_lang: str = "JA",
    target_lang: str = "ZH",
    glossary_id: Optional[str] = None
) -> str:
    """Translate single text."""
    result = client.translate_text(
        text,
        source_lang=source_lang,
        target_lang=target_lang,
        glossary=glossary_id
    )
    return result.text


def translate_story(
    content: str,
    source_lang: str = "JA",
    target_lang: str = "ZH"
) -> str:
    """
    Translate story content using DeepL with glossary.
    
    Args:
        content: Markdown story content
        source_lang: Source language (JA, EN)
        target_lang: Target language (ZH)
    
    Returns:
        Translated content
    """
    client = get_client()
    
    # Setup glossary for consistent terminology
    glossary_id = None
    if source_lang == "JA":
        glossary_id = setup_glossary(client)
    
    print(f"  DeepL: {source_lang} → {target_lang}")
    
    # Translate entire content at once (DeepL handles it well)
    result = client.translate_text(
        content,
        source_lang=source_lang,
        target_lang=target_lang,
        glossary=glossary_id,
        preserve_formatting=True
    )
    
    return result.text


def translate_file(
    input_path: str,
    output_path: str,
    source_lang: str = "JA",
    target_lang: str = "ZH"
) -> bool:
    """Translate a single file."""
    input_p = Path(input_path)
    output_p = Path(output_path)
    
    if not input_p.exists():
        print(f"File not found: {input_p}")
        return False
    
    content = input_p.read_text(encoding='utf-8')
    translated = translate_story(content, source_lang, target_lang)
    
    output_p.parent.mkdir(parents=True, exist_ok=True)
    output_p.write_text(translated, encoding='utf-8')
    print(f"  Saved: {output_p}")
    return True


def translate_directory(
    input_dir: str,
    output_dir: str,
    source_lang: str = "JA",
    target_lang: str = "ZH"
) -> int:
    """Translate all markdown files in directory."""
    input_p = Path(input_dir)
    output_p = Path(output_dir)
    
    if not input_p.exists():
        print(f"Directory not found: {input_p}")
        return 0
    
    files = list(input_p.glob("*.md"))
    if not files:
        print(f"No markdown files in: {input_p}")
        return 0
    
    print(f"DeepL: Translating {len(files)} files")
    
    count = 0
    for md_file in sorted(files):
        output_file = output_p / md_file.name
        print(f"\n[{count+1}/{len(files)}] {md_file.name}")
        if translate_file(str(md_file), str(output_file), source_lang, target_lang):
            count += 1
    
    return count


def get_usage() -> dict:
    """Get current API usage."""
    client = get_client()
    usage = client.get_usage()
    return {
        "used": usage.character.count,
        "limit": usage.character.limit,
        "remaining": usage.character.limit - usage.character.count if usage.character.limit else None
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m lib.translators.deepl <input> <output>")
        print("  python -m lib.translators.deepl --usage")
        sys.exit(1)
    
    if sys.argv[1] == "--usage":
        usage = get_usage()
        print(f"DeepL API Usage:")
        print(f"  Used: {usage['used']:,} characters")
        print(f"  Limit: {usage['limit']:,} characters")
        if usage['remaining']:
            print(f"  Remaining: {usage['remaining']:,} characters")
        sys.exit(0)
    
    if len(sys.argv) < 3:
        print("Usage: python -m lib.translators.deepl <input> <output>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if Path(input_path).is_dir():
        count = translate_directory(input_path, output_path)
        print(f"\nTranslated {count} files")
    else:
        translate_file(input_path, output_path)
