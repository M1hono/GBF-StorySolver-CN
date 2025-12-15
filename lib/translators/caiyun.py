"""
Caiyun Translation module.

Full translation: titles, dialogue, narration, unmapped character names.
Uses Caiyun API for machine translation.
"""
import re
import time
import requests
from typing import List, Dict, Any, Set
from pathlib import Path

try:
    from .blhxfy import translator
    from ..utils.config import CAIYUN_API_KEY, CAIYUN_TOKEN
except ImportError:
    import os
    translator = None
    CAIYUN_API_KEY = os.environ.get("CAIYUN_API_KEY", "")
    CAIYUN_TOKEN = os.environ.get("CAIYUN_TOKEN", "")

# Caiyun API configuration
CAIYUN_API = "http://api.interpreter.caiyunai.com/v1/translator"

# Cache for translated speaker names (avoid repeat API calls)
_speaker_cache: Dict[str, str] = {}


def translate_texts(texts: List[str], source_lang: str = 'en') -> List[str]:
    """Call Caiyun API to translate text list."""
    if not texts:
        return []
    
    # Filter empty texts
    texts = [t if t else ' ' for t in texts]
    
    headers = {
        'content-type': 'application/json',
        'x-authorization': f'token {CAIYUN_TOKEN}'
    }
    
    payload = {
        'source': texts,
        'trans_type': f'{source_lang}2zh',
        'request_id': 'gbf_wiki_mcp',
        'detect': True
    }
    
    try:
        response = requests.post(CAIYUN_API, json=payload, headers=headers, timeout=30)
        result = response.json()
        if 'target' in result:
            return result['target']
    except Exception as e:
        print(f"Translation API error: {e}")
    
    return texts  # Return original on failure


def translate_speaker(name: str) -> str:
    """
    Translate character name with auto-learning.
    
    Lookup order:
    1. Already Chinese -> return directly
    2. EN->CN mapping (npc-name-en.csv) -> return if found
    3. JP->CN mapping (npc-name-jp.csv) -> add to EN mapping and return
    4. Cache -> return if found
    5. API translation -> translate and add to EN mapping
    """
    # Already Chinese, return directly
    if re.search(r'[\u4e00-\u9fff]', name):
        return name
    
    # 1. Check EN->CN mapping
    cn_name = translator.lookup_cn_name(name)
    if cn_name:
        return cn_name
    
    # 2. Check JP->CN mapping (try to find from Japanese mapping)
    jp_cn = translator.find_cn_from_jp_mapping(name)
    if jp_cn:
        # Found, add to EN mapping
        translator.add_en_mapping(name, jp_cn)
        print(f"Learned from JP mapping: {name} -> {jp_cn}")
        return jp_cn
    
    # 3. Check cache
    if name in _speaker_cache:
        return _speaker_cache[name]
    
    # 4. API translation
    print(f"API translating character name: {name}")
    translated = translate_texts([name], 'en')
    if translated and translated[0]:
        cn_result = translated[0]
        _speaker_cache[name] = cn_result
        # Add to EN mapping (persistent learning)
        translator.add_en_mapping(name, cn_result)
        print(f"Learned new mapping: {name} -> {cn_result}")
        return cn_result
    
    return name


def translate_markdown(lines: List[str], source_lang: str = 'en', batch_size: int = 20) -> List[str]:
    """
    Translate Markdown file content.
    
    Handles:
    1. Titles (# ## ###)
    2. Dialogue (**Name:** text)
    3. Narration (*text*)
    4. Regular text paragraphs
    """
    result_lines = []
    to_translate = []  # (line_number, type, extra_info)
    translate_texts_list = []
    speakers_to_translate: Set[str] = set()
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Empty line or separator
        if not stripped or stripped == '---':
            result_lines.append(line)
            continue
        
        # Title: # ## ### etc.
        title_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if title_match:
            level, title_text = title_match.groups()
            preprocessed = translator.apply_translation(title_text, "pre")
            translate_texts_list.append(preprocessed)
            to_translate.append((i, 'title', level))
            result_lines.append(line)
            continue
        
        # Dialogue: **Speaker:** text or **Speaker：** text
        dialogue_match = re.match(r'\*\*([^:：]+)[：:]\*\*\s*(.+)', stripped)
        if dialogue_match:
            speaker, text = dialogue_match.groups()
            speaker = speaker.strip()
            
            # Collect character names that need translation
            cn_speaker = translator.translate_speaker_name(speaker)
            if cn_speaker == speaker and not re.search(r'[\u4e00-\u9fff]', speaker):
                speakers_to_translate.add(speaker)
            
            preprocessed = translator.apply_translation(text, "pre")
            translate_texts_list.append(preprocessed)
            to_translate.append((i, 'dialogue', speaker))
            result_lines.append(line)
            continue
        
        # Narration: *text*
        if stripped.startswith('*') and stripped.endswith('*') and len(stripped) > 2:
            text = stripped[1:-1]
            preprocessed = translator.apply_translation(text, "pre")
            translate_texts_list.append(preprocessed)
            to_translate.append((i, 'narration', None))
            result_lines.append(line)
            continue
        
        # Regular text paragraph (not empty, not special characters)
        if stripped and not stripped.startswith(('|', '-', '>', '`', '[')):
            preprocessed = translator.apply_translation(stripped, "pre")
            translate_texts_list.append(preprocessed)
            to_translate.append((i, 'text', None))
            result_lines.append(line)
            continue
        
        # Other content unchanged
        result_lines.append(line)
    
    # Batch translate unmapped character names first
    if speakers_to_translate:
        print(f"Translating {len(speakers_to_translate)} unmapped character names...")
        speaker_list = list(speakers_to_translate)
        translated_speakers = translate_texts(speaker_list, source_lang)
        for orig, trans in zip(speaker_list, translated_speakers):
            if trans:
                _speaker_cache[orig] = trans
    
    # Batch translate content
    if translate_texts_list:
        print(f"Translating {len(translate_texts_list)} lines...")
        all_translations = []
        
        for i in range(0, len(translate_texts_list), batch_size):
            batch = translate_texts_list[i:i+batch_size]
            translations = translate_texts(batch, source_lang)
            all_translations.extend(translations)
            print(f"Progress: {min(i+batch_size, len(translate_texts_list))}/{len(translate_texts_list)}")
            time.sleep(0.3)  # Rate limiting
        
        # Post-process and replace
        for (idx, text_type, extra), translated in zip(to_translate, all_translations):
            # BLHXFY post-processing
            final_text = translator.apply_translation(translated, "post")
            
            if text_type == 'title':
                level = extra
                result_lines[idx] = f"{level} {final_text}\n"
            elif text_type == 'dialogue':
                # Translate character name
                cn_speaker = translate_speaker(extra)
                result_lines[idx] = f"**{cn_speaker}：** {final_text}\n"
            elif text_type == 'narration':
                result_lines[idx] = f"*{final_text}*\n"
            elif text_type == 'text':
                result_lines[idx] = f"{final_text}\n"
    
    return result_lines


def translate_file(input_file: str, output_file: str, source_lang: str = 'en') -> Dict[str, Any]:
    """Translate single Markdown file."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        translated = translate_markdown(lines, source_lang)
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(translated)
        
        return {"status": "success", "input": input_file, "output": output_file}
    except Exception as e:
        return {"status": "error", "input": input_file, "error": str(e)}


def translate_directory(raw_dir: str, trans_dir: str, source_lang: str = 'en') -> Dict[str, Any]:
    """Batch translate all Markdown files in directory."""
    raw_path = Path(raw_dir)
    trans_path = Path(trans_dir)
    trans_path.mkdir(parents=True, exist_ok=True)
    
    results = []
    md_files = sorted(raw_path.glob('*.md'))
    
    print(f"\nBatch translating: {len(md_files)} files")
    
    for md_file in md_files:
        output = trans_path / md_file.name
        print(f"\n{'='*50}")
        print(f"Translating: {md_file.name}")
        print(f"{'='*50}")
        result = translate_file(str(md_file), str(output), source_lang)
        results.append(result)
        if result['status'] == 'success':
            print(f"OK: {md_file.name}")
        else:
            print(f"FAIL: {md_file.name}: {result.get('error')}")
    
    success = len([r for r in results if r['status'] == 'success'])
    print(f"\n{'='*50}")
    print(f"Translation complete: {success}/{len(results)} succeeded")
    print(f"{'='*50}")
    
    return {"total": len(results), "success": success, "results": results}


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Caiyun Translator - Batch translate Markdown files")
        print()
        print("Usage:")
        print("  python caiyun_translator.py <raw_dir> <trans_dir> [source_lang]")
        print()
        print("Arguments:")
        print("  raw_dir      Source directory with .md files")
        print("  trans_dir    Output directory for translated files")
        print("  source_lang  Source language: en (default) or ja")
        print()
        print("Example:")
        print("  python caiyun_translator.py raw/ trans/")
        print("  python caiyun_translator.py raw/ trans/ ja")
        sys.exit(1)
    
    raw_dir = sys.argv[1]
    trans_dir = sys.argv[2]
    source_lang = sys.argv[3] if len(sys.argv) > 3 else 'en'
    
    result = translate_directory(raw_dir, trans_dir, source_lang)
    sys.exit(0 if result['success'] == result['total'] else 1)
