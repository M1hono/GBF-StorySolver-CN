"""
OpenAI GPT Translation Module

Supports: GPT-4o, GPT-4o-mini, GPT-4.1, GPT-4.1-mini

Pricing (Dec 2024):
- GPT-4o-mini: $0.15/1M input, $0.60/1M output (recommended)
- GPT-4o: $2.50/1M input, $10/1M output

Usage:
    from lib.translators.openai_translator import translate_story
    result = translate_story(content)
"""
import os
from pathlib import Path
from typing import Set

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from openai import OpenAI

try:
    from ..utils.config import Config
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.config import Config

# Config
config = Config.load()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = getattr(config.translation, 'openai_model', 'gpt-4o-mini')


def get_client() -> OpenAI:
    """Get OpenAI client."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set. Add to .env file.")
    return OpenAI(api_key=OPENAI_API_KEY)


def get_terminology(content: str = "") -> str:
    """
    Get terminology section for prompt.
    
    OpenAI doesn't have native glossary API like DeepL, but we can inject
    terminology into system prompt for consistent translations.
    """
    try:
        from .blhxfy import translator
        
        lines = []
        
        # Character names (JP → CN)
        jp_to_cn = translator.npc_names.get("jp_to_cn", {})
        en_to_cn = translator.npc_names.get("en_to_cn", {})
        
        # If content provided, filter to relevant names only
        if content:
            import re
            # Extract potential names from content
            potential_names = set(re.findall(r'\*\*([^*:]+):\*\*', content))
            potential_names.update(re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', content))
            
            # Add relevant JP names
            for jp, cn in jp_to_cn.items():
                if jp and cn and (jp in content or any(n in jp for n in potential_names)):
                    lines.append(f"{jp} = {cn}")
            
            # Add relevant EN names
            for en, cn in en_to_cn.items():
                if en and cn and en in content:
                    lines.append(f"{en} = {cn}")
        else:
            # No content, return top entries
            for jp, cn in list(jp_to_cn.items())[:100]:
                if jp and cn:
                    lines.append(f"{jp} = {cn}")
        
        # Add key terminology from nouns
        nouns = translator.nouns
        for term, trans in list(nouns.items())[:50]:
            if term and trans and len(term) > 1:
                lines.append(f"{term} = {trans}")
        
        return "\n".join(lines[:150]) if lines else ""
    except:
        return ""


def build_prompt(content: str) -> str:
    """Build minimal translation prompt with terminology."""
    terminology = get_terminology(content)
    
    # Minimal prompt - only include what's necessary
    term_section = f"术语:{terminology}" if terminology else ""
    
    return f"""GBF翻译。EN/JP→CN。保留**角色:**、*旁白*、#标题。Captain=团长。自然口语化。
{term_section}
直接输出译文。"""


def translate_chunk(client, prompt: str, content: str) -> str:
    """Translate a single chunk."""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": content}
        ],
        max_tokens=16000,
        temperature=0.3
    )
    return response.choices[0].message.content


def translate_story(content: str) -> str:
    """Translate story content using OpenAI with chunking for long files."""
    client = get_client()
    lines = content.split('\n')
    
    print(f"  OpenAI: {OPENAI_MODEL}, Lines: {len(lines)}")
    
    # For short files, translate directly
    if len(lines) <= 500:
        prompt = build_prompt(content)
        return translate_chunk(client, prompt, content)
    
    # For long files, split by sections
    chunks = []
    current_chunk = []
    
    for line in lines:
        current_chunk.append(line)
        
        if (line.startswith('## ') and len(current_chunk) > 250) or len(current_chunk) >= 500:
            chunks.append('\n'.join(current_chunk))
            current_chunk = []
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    print(f"  Chunks: {len(chunks)}")
    
    # Translate each chunk
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"    Chunk {i+1}/{len(chunks)}...")
        prompt = build_prompt(chunk)
        result = translate_chunk(client, prompt, chunk)
        
        # Remove duplicate headers from subsequent chunks
        if i > 0:
            result_lines = result.split('\n')
            filtered = [l for l in result_lines if not (l.startswith('# ') or l.startswith('## '))]
            result = '\n'.join(filtered).strip()
        
        translated_chunks.append(result)
    
    return '\n\n'.join(translated_chunks)


def translate_file(input_path: str, output_path: str) -> bool:
    """Translate a single file."""
    input_p = Path(input_path)
    output_p = Path(output_path)
    
    if not input_p.exists():
        print(f"File not found: {input_p}")
        return False
    
    content = input_p.read_text(encoding='utf-8')
    translated = translate_story(content)
    
    output_p.parent.mkdir(parents=True, exist_ok=True)
    output_p.write_text(translated, encoding='utf-8')
    print(f"  Saved: {output_p}")
    return True


def translate_directory(input_dir: str, output_dir: str) -> int:
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
    
    print(f"OpenAI: Translating {len(files)} files with {OPENAI_MODEL}")
    
    count = 0
    for md_file in sorted(files):
        output_file = output_p / md_file.name
        print(f"\n[{count+1}/{len(files)}] {md_file.name}")
        if translate_file(str(md_file), str(output_file)):
            count += 1
    
    return count


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m lib.translators.openai_translator <input> <output>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if Path(input_path).is_dir():
        count = translate_directory(input_path, output_path)
        print(f"\nTranslated {count} files")
    else:
        translate_file(input_path, output_path)
