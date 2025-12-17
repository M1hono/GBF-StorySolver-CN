"""
Voice table translation module.

Handles translation of GBF voice line tables with proper column management.
"""

from __future__ import annotations

import re
import json
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from anthropic import Anthropic

from .prompts import build_jp_translate_prompt, build_batch_jp_prompt


def is_voice_table(content: str) -> bool:
    """Check if content is a voice line table."""
    return '| Label |' in content and '| Japanese |' in content


def has_chinese_column(content: str) -> bool:
    """Check if voice table already has Chinese column."""
    for line in content.split('\n'):
        if '| Label |' in line and '| Chinese |' in line:
            return True
    return False


def _detect_column_indices(header_line: str) -> Dict[str, int]:
    """Detect column indices from header line."""
    col_map = {}
    cells = [c.strip() for c in header_line.split('|')]
    
    for i, cell in enumerate(cells):
        cl = cell.lower()
        if 'label' in cl:
            col_map['label'] = i
        elif 'japanese' in cl or cl == 'jp':
            col_map['japanese'] = i
        elif 'chinese' in cl or cl == 'cn':
            col_map['chinese'] = i
        elif 'english' in cl or cl == 'en':
            col_map['english'] = i
        elif 'notes' in cl:
            col_map['notes'] = i
        elif 'audio' in cl:
            col_map['audio'] = i
    
    return col_map


def translate_jp_text(client: "Anthropic", model: str, text: str) -> str:
    """Translate single Japanese text to Chinese."""
    if not text or text.strip() == '':
        return ''
    
    prompt = build_jp_translate_prompt()
    
    try:
        response = client.messages.create(
            model=model,
            max_tokens=256,
            temperature=0.1,
            system=prompt,
            messages=[{"role": "user", "content": text}]
        )
        return response.content[0].text.strip()
    except:
        return ''


def batch_translate_jp(client: "Anthropic", model: str, texts: List[str]) -> Dict[int, str]:
    """Batch translate Japanese texts to Chinese."""
    if not texts:
        return {}
    
    input_json = {str(i): t for i, t in enumerate(texts)}
    prompt = build_batch_jp_prompt()
    
    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0.1,
            system=prompt,
            messages=[{"role": "user", "content": json.dumps(input_json, ensure_ascii=False)}]
        )
        
        result_text = response.content[0].text.strip()
        if '{' in result_text:
            json_str = result_text[result_text.index('{'):result_text.rindex('}')+1]
            parsed = json.loads(json_str)
            return {int(k): v for k, v in parsed.items()}
    except Exception as e:
        print(f"    Batch error: {e}")
    
    return {}


def translate_voice_table(client: "Anthropic", model: str, content: str) -> str:
    """
    Translate voice table by filling in Chinese column.
    
    Raw format: | Label | Japanese | Chinese | English | Notes | Audio |
    (Chinese column exists but is empty, needs to be filled)
    """
    already_has_chinese = has_chinese_column(content)
    
    lines = content.split('\n')
    result = []
    
    # Detect column indices from header
    col_map = {}
    header_line_idx = -1
    
    for i, line in enumerate(lines):
        if '| Label |' in line and '| Japanese |' in line:
            header_line_idx = i
            col_map = _detect_column_indices(line)
            break
    
    # If no Chinese column detected, need to add it after Japanese
    if 'chinese' not in col_map:
        if 'japanese' in col_map:
            col_map['chinese'] = col_map['japanese'] + 1
            # Shift downstream indices
            for key in ['english', 'notes', 'audio']:
                if key in col_map:
                    col_map[key] += 1
    
    # Collect Japanese texts for batch translation
    jp_texts = []
    jp_line_indices = []
    
    for i, line in enumerate(lines):
        if not line.startswith('|') or '---' in line or i == header_line_idx:
            continue
        
        cells = [c.strip() for c in line.split('|')]
        if len(cells) <= 1:
            continue
        
        jp_idx = col_map.get('japanese', 2)
        cn_idx = col_map.get('chinese', 3)
        
        if jp_idx < len(cells):
            jp_text = cells[jp_idx]
            cn_text = cells[cn_idx] if cn_idx < len(cells) else ''
            # Only translate if Chinese column is empty
            if jp_text and not cn_text:
                jp_texts.append(jp_text)
                jp_line_indices.append(i)
    
    # Batch translate
    translations = batch_translate_jp(client, model, jp_texts) if jp_texts else {}
    
    # Build result
    for i, line in enumerate(lines):
        if i == header_line_idx:
            if already_has_chinese:
                result.append(line)
            else:
                result.append(line.replace('| English |', '| Chinese | English |'))
            continue
        
        if line.startswith('|') and '---' in line:
            if not already_has_chinese:
                parts = line.split('|')
                if len(parts) > 3:
                    parts.insert(4, ' --- ')
                result.append('|'.join(parts))
            else:
                result.append(line)
            continue
        
        if not line.startswith('|') or i == header_line_idx:
            result.append(line)
            continue
        
        cells = [c.strip() for c in line.split('|')]
        if len(cells) <= 1:
            result.append(line)
            continue
        
        # Fill in Chinese translation if this line was translated
        if i in jp_line_indices:
            batch_idx = jp_line_indices.index(i)
            cn_text = translations.get(batch_idx, '')
            cn_idx = col_map.get('chinese', 3)
            
            if already_has_chinese:
                if cn_idx < len(cells):
                    cells[cn_idx] = cn_text
            else:
                cells.insert(cn_idx, cn_text)
        
        # Rebuild line
        result.append('| ' + ' | '.join(cells[1:-1] if cells[-1] == '' else cells[1:]) + ' |')
    
    return '\n'.join(result)



