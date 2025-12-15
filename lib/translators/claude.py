"""
Claude translation module for GBF content.

Supports two translation modes:
- "replace": Pre-replace terms before translation (cheaper, faster)
- "prompt": Include all mappings in prompt (more reliable)

Usage:
    from lib.translators.claude import translate_file, translate_directory
    
    result = translate_file("raw/story.md", "trans/story.md", mode="prompt")
    result = translate_directory("raw/", "trans/")
"""

from __future__ import annotations

import re
import json
import logging
from typing import Dict, List, Literal, TypedDict, Union
from pathlib import Path

import anthropic

from .prompts import (
    build_story_prompt_full,
    build_story_prompt_simple,
    build_jp_translate_prompt,
    build_simple_text_prompt,
)
from .voice_translator import (
    is_voice_table,
    translate_voice_table,
    batch_translate_jp,
)

# =============================================================================
# INITIALIZATION
# =============================================================================

logger = logging.getLogger(__name__)

try:
    from .blhxfy import translator
    from ..utils.config import CLAUDE_API_KEY, CLAUDE_MODEL
except ImportError:
    import os
    CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")
    CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    try:
        from .blhxfy import translator
    except ImportError:
        translator = None

try:
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, timeout=180.0)
except Exception as e:
    logger.error(f"Failed to initialize Anthropic client: {e}")
    client = None


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

class TranslationResult(TypedDict, total=False):
    success: bool
    file: str
    translated: int
    total: int
    error: str


class DirectoryResult(TypedDict):
    success: int
    failed: int
    files: List[str]


# Configuration
CHUNK_SIZE = 120
MAX_TOKENS = 8192
TranslationMode = Literal["replace", "prompt"]
DEFAULT_MODE: TranslationMode = "prompt"


# =============================================================================
# UTILITIES
# =============================================================================

def extract_speakers(content: str) -> set:
    """Extract character names from dialogue format **Name:**."""
    return set(re.findall(r'\*\*([^*:]+):\*\*', content))


def split_into_chunks(content: str, chunk_size: int = CHUNK_SIZE) -> List[str]:
    """Split content into chunks at scene boundaries (## headings)."""
    lines = content.split('\n')
    
    if len(lines) <= chunk_size:
        return [content]
    
    # Extract header (lines before first ## heading)
    header_lines = []
    content_start = 0
    for i, line in enumerate(lines):
        if line.startswith('## '):
            content_start = i
            break
        header_lines.append(line)
    
    header = '\n'.join(header_lines)
    content_lines = lines[content_start:]
    
    # Split at scene boundaries
    chunks = []
    current_chunk = []
    
    for line in content_lines:
        if line.startswith('## ') and len(current_chunk) > chunk_size // 2:
            chunks.append(header + '\n\n' + '\n'.join(current_chunk))
            current_chunk = [line]
        else:
            current_chunk.append(line)
            
            if len(current_chunk) >= chunk_size:
                break_idx = len(current_chunk) - 1
                for j in range(len(current_chunk) - 1, max(0, len(current_chunk) - 30), -1):
                    if current_chunk[j].strip() == '':
                        break_idx = j
                        break
                
                chunks.append(header + '\n\n' + '\n'.join(current_chunk[:break_idx]))
                current_chunk = current_chunk[break_idx:]
    
    if current_chunk:
        chunks.append(header + '\n\n' + '\n'.join(current_chunk))
    
    return chunks if chunks else [content]


# =============================================================================
# CORE TRANSLATION
# =============================================================================

def translate_chunk(content: str, prompt: str) -> str:
    """Translate a single chunk using Claude API."""
    if client is None:
        raise RuntimeError("Claude client not initialized. Check CLAUDE_API_KEY.")
    
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0.1,
            system=prompt,
            messages=[{"role": "user", "content": content}]
        )
        return response.content[0].text
    
    except anthropic.APIConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise RuntimeError(f"Failed to connect to Claude API: {e}")
    
    except anthropic.RateLimitError as e:
        logger.warning(f"Rate limited: {e}")
        return content
    
    except anthropic.APIStatusError as e:
        logger.error(f"API error {e.status_code}: {e.message}")
        raise RuntimeError(f"Claude API error: {e.message}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return content


def translate_story(content: str, mode: TranslationMode = DEFAULT_MODE) -> str:
    """Translate story/dialogue content."""
    lines = content.split('\n')
    print(f"    Lines: {len(lines)}, Mode: {mode}")
    
    speakers = extract_speakers(content)
    
    if mode == "replace":
        processed = content
        if translator:
            processed = translator.apply_pre_translation(processed)
        prompt = build_story_prompt_simple()
    else:
        processed = content
        prompt = build_story_prompt_full(content, speakers)
    
    chunks = split_into_chunks(processed)
    print(f"    Chunks: {len(chunks)}")
    
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"    [{i+1}/{len(chunks)}] Translating...")
        translated = translate_chunk(chunk, prompt)
        
        # Remove duplicate headers from subsequent chunks
        if i > 0:
            chunk_lines = translated.split('\n')
            for j, line in enumerate(chunk_lines):
                if line.startswith('## '):
                    translated = '\n'.join(chunk_lines[j:])
                    break
        
        translated_chunks.append(translated)
    
    result = '\n\n'.join(translated_chunks)
    
    if translator:
        result = translator.apply_post_translation(result)
    
    return result


# =============================================================================
# LORE TRANSLATION
# =============================================================================

def is_lore_table(content: str) -> bool:
    """Check if content is a JP/EN lore table."""
    return '| Japanese |' in content and '| English |' in content


def translate_lore_table(content: str) -> str:
    """Translate JP/EN table by adding Chinese column."""
    lines = content.split('\n')
    result = []
    jp_texts = []
    jp_indices = []
    
    for i, line in enumerate(lines):
        if line.startswith('|') and '---' not in line and 'Japanese' not in line:
            cells = [c.strip() for c in line.split('|')]
            if len(cells) >= 3 and cells[1]:
                jp_texts.append(cells[1])
                jp_indices.append(i)
    
    translations = batch_translate_jp(client, CLAUDE_MODEL, jp_texts) if jp_texts else {}
    
    jp_idx = 0
    for i, line in enumerate(lines):
        if '| Japanese |' in line:
            result.append(line.replace('| English |', '| Chinese | English |'))
        elif line.startswith('|') and '---' in line:
            parts = line.split('|')
            if len(parts) > 3:
                parts.insert(2, ' --- ')
            result.append('|'.join(parts))
        elif i in jp_indices:
            cells = [c.strip() for c in line.split('|')]
            if len(cells) >= 3:
                cn_text = translations.get(jp_idx, '')
                cells.insert(2, cn_text)
                jp_idx += 1
            result.append('| ' + ' | '.join(cells[1:-1]) + ' |')
        else:
            result.append(line)
    
    return '\n'.join(result)


def translate_simple_text(content: str, mode: TranslationMode = DEFAULT_MODE) -> str:
    """Translate simple text content."""
    if mode == "replace" and translator:
        content = translator.apply_pre_translation(content)
    
    prompt = build_simple_text_prompt()
    
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            temperature=0.1,
            system=prompt,
            messages=[{"role": "user", "content": content}]
        )
        result = response.content[0].text
        
        if translator:
            result = translator.apply_post_translation(result)
        
        return result
    except Exception as e:
        print(f"    Error: {e}")
        return content


def translate_lore(content: str, mode: TranslationMode = DEFAULT_MODE) -> str:
    """Translate lore content (auto-detect format)."""
    if is_lore_table(content):
        print("    Format: JP/EN table")
        return translate_lore_table(content)
    elif '**' in content and ':**' in content:
        print("    Format: Story dialogue")
        return translate_story(content, mode)
    else:
        print("    Format: Simple text")
        return translate_simple_text(content, mode)


# =============================================================================
# FILE/DIRECTORY API
# =============================================================================

def translate_file(
    input_file: Union[str, Path], 
    output_file: Union[str, Path], 
    mode: TranslationMode = DEFAULT_MODE
) -> TranslationResult:
    """
    Translate single file with auto-detected format.
    
    Supports:
    - Story/dialogue format (Markdown with **Name:** patterns)
    - Voice table format (| Label | Japanese | ... |)
    - Lore table format (| Japanese | English |)
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        return {"success": False, "file": input_path.name, "error": f"File not found: {input_path}"}
    
    try:
        content = input_path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, IOError) as e:
        return {"success": False, "file": input_path.name, "error": str(e)}
    
    if not content.strip():
        return {"success": False, "file": input_path.name, "error": "Empty file"}
    
    # Auto-detect format and translate
    try:
        if is_voice_table(content):
            logger.info("  Format: Voice table")
            translated = translate_voice_table(client, CLAUDE_MODEL, content)
        elif is_lore_table(content):
            logger.info("  Format: Lore table")
            translated = translate_lore_table(content)
        else:
            logger.info("  Format: Story/dialogue")
            translated = translate_story(content, mode)
    except RuntimeError as e:
        return {"success": False, "file": input_path.name, "error": str(e)}
    except Exception as e:
        return {"success": False, "file": input_path.name, "error": f"Translation failed: {e}"}
    
    # Write output
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(translated, encoding='utf-8')
    except IOError as e:
        return {"success": False, "file": input_path.name, "error": f"Write error: {e}"}
    
    return {"success": True, "file": input_path.name}


def translate_directory(
    raw_dir: Union[str, Path], 
    trans_dir: Union[str, Path], 
    mode: TranslationMode = DEFAULT_MODE,
    show_progress: bool = True
) -> DirectoryResult:
    """Translate all markdown files in a directory."""
    raw_path = Path(raw_dir)
    trans_path = Path(trans_dir)
    
    if not raw_path.exists() or not raw_path.is_dir():
        return {"success": 0, "failed": 0, "files": []}
    
    results: DirectoryResult = {"success": 0, "failed": 0, "files": []}
    files = sorted(raw_path.rglob('*.md'))
    
    if not files:
        return results
    
    logger.info(f"Found {len(files)} files to translate")
    
    for i, raw_file in enumerate(files):
        rel_path = raw_file.relative_to(raw_path)
        trans_file = trans_path / rel_path
        
        if show_progress:
            print(f"[{i+1}/{len(files)}] {rel_path}")
        
        result = translate_file(raw_file, trans_file, mode)
        
        if result.get("success"):
            results["success"] += 1
            results["files"].append(str(rel_path))
        else:
            results["failed"] += 1
            logger.error(f"Failed: {rel_path} - {result.get('error')}")
    
    return results


# Aliases for backward compatibility
translate_lore_file = translate_file
translate_lore_content = translate_lore
claude_translate_file = translate_file
claude_translate_directory = translate_directory


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python claude.py <raw_dir> <trans_dir> [mode]")
        sys.exit(1)
    
    raw_dir = sys.argv[1]
    trans_dir = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MODE
    
    if mode not in ("replace", "prompt"):
        print(f"Invalid mode: {mode}")
        sys.exit(1)
    
    result = translate_directory(raw_dir, trans_dir, mode)
    print(f"\nDone: {result['success']} success, {result['failed']} failed")
