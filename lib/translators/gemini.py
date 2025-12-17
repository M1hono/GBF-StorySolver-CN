"""
Google Gemini Translation Module

Supports: Gemini 2.0 Flash, Gemini 1.5 Pro

Pricing (Dec 2024):
- Gemini 2.0 Flash: $0.075/1M input, $0.30/1M output (CHEAPEST!)
- Gemini 1.5 Pro: $1.25/1M input, $5/1M output

Usage:
    from lib.translators.gemini import translate_story
    result = translate_story(content)
"""
import os
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Use new SDK if available, fallback to old
try:
    from google import genai
    USE_NEW_SDK = True
except ImportError:
    import google.generativeai as genai
    USE_NEW_SDK = False

try:
    from ..utils.config import Config
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.config import Config

# Config
config = Config.load()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = getattr(config.translation, 'gemini_model', 'gemini-2.0-flash')


def get_terminology(content: str = "") -> str:
    """
    Get terminology section for prompt.
    Filters to relevant names if content is provided.
    """
    try:
        from .blhxfy import translator
        import re
        
        lines = []
        jp_to_cn = translator.npc_names.get("jp_to_cn", {})
        en_to_cn = translator.npc_names.get("en_to_cn", {})
        
        if content:
            # Filter to names appearing in content
            potential_names = set(re.findall(r'\*\*([^*:]+):\*\*', content))
            potential_names.update(re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', content))
            
            for jp, cn in jp_to_cn.items():
                if jp and cn and (jp in content or any(n in jp for n in potential_names)):
                    lines.append(f"{jp} = {cn}")
            
            for en, cn in en_to_cn.items():
                if en and cn and en in content:
                    lines.append(f"{en} = {cn}")
        else:
            for jp, cn in list(jp_to_cn.items())[:100]:
                if jp and cn:
                    lines.append(f"{jp} = {cn}")
        
        # Add key terminology
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
    
    # Minimal prompt
    term_section = f"术语:{terminology}" if terminology else ""
    
    return f"""GBF翻译。EN/JP→CN。保留**角色:**、*旁白*、#标题。Captain=团长。自然口语化。
{term_section}
直接输出译文：

{content}"""


def fix_repetition(text: str, max_repeat: int = 10) -> str:
    """Fix LLM repetition hallucinations (e.g. 啊啊啊啊啊啊...)."""
    import re
    
    # Fix repeated single characters (e.g. 啊啊啊啊啊 -> 啊啊啊)
    def limit_char_repeat(match):
        char = match.group(1)
        return char * min(len(match.group(0)) // len(char), max_repeat)
    
    # Common repeated chars in Chinese exclamations
    for char in ['啊', '呀', '哇', '嗯', '哦', '唔', '呜', '嘶', '！', '？']:
        pattern = f'({re.escape(char)}){{4,}}'
        text = re.sub(pattern, limit_char_repeat, text)
    
    # Fix any character repeated more than max_repeat times
    text = re.sub(r'(.)\1{' + str(max_repeat) + r',}', r'\1' * max_repeat, text)
    
    return text


def translate_chunk(prompt: str) -> str:
    """Translate a single chunk."""
    if USE_NEW_SDK:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                max_output_tokens=16000,
                temperature=0.2
            )
        )
        return response.text
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=16000,
                temperature=0.2
            )
        )
        return response.text


def translate_story(content: str) -> str:
    """Translate story content using Gemini with chunking for long files."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set. Add to .env file.")
    
    lines = content.split('\n')
    print(f"  Gemini: {GEMINI_MODEL}, Lines: {len(lines)}")
    
    # For short files, translate directly
    if len(lines) <= 500:
        prompt = build_prompt(content)
        result = translate_chunk(prompt)
        return fix_repetition(result)
    
    # For long files, split by chapters/sections
    chunks = []
    current_chunk = []
    
    for line in lines:
        current_chunk.append(line)
        
        # Split at chapter boundaries or every 500 lines
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
        result = translate_chunk(prompt)
        
        # Remove duplicate headers from subsequent chunks
        if i > 0:
            result_lines = result.split('\n')
            filtered = [l for l in result_lines if not (l.startswith('# ') or l.startswith('## '))]
            result = '\n'.join(filtered).strip()
        
        translated_chunks.append(fix_repetition(result))
    
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
    
    print(f"Gemini: Translating {len(files)} files with {GEMINI_MODEL}")
    
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
        print("Usage: python -m lib.translators.gemini <input> <output>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if Path(input_path).is_dir():
        count = translate_directory(input_path, output_path)
        print(f"\nTranslated {count} files")
    else:
        translate_file(input_path, output_path)
