"""
Translation prompt builders for GBF content.

Contains specialized prompts for:
- Story/dialogue translation (EN → CN)
- Japanese voice line translation (JP → CN)
- Lore content translation
"""

from __future__ import annotations

from typing import Set, Dict

try:
    from .blhxfy import translator
except ImportError:
    translator = None


def get_all_mappings() -> Dict[str, Dict[str, str]]:
    """
    Collect all mappings from BLHXFY data.
    
    Returns:
        {
            "en_to_cn": {"Vajra": "瓦姬拉", ...},
            "jp_to_cn": {"ヴァジラ": "瓦姬拉", ...},
            "nouns": {"Captain": "团长", ...}
        }
    """
    result = {"en_to_cn": {}, "jp_to_cn": {}, "nouns": {}}
    
    if not translator:
        return result
    
    if hasattr(translator, 'npc_names') and translator.npc_names:
        result["en_to_cn"] = dict(translator.npc_names)
    
    if hasattr(translator, 'npc_names_jp') and translator.npc_names_jp:
        result["jp_to_cn"] = dict(translator.npc_names_jp)
    
    if hasattr(translator, 'nouns') and translator.nouns:
        result["nouns"] = dict(translator.nouns)
    
    return result


def get_relevant_mappings(content: str, speakers: Set[str]) -> Dict[str, str]:
    """
    Get mappings relevant to the content.
    
    Returns combined dict of character names and terms found in content.
    """
    all_maps = get_all_mappings()
    relevant = {}
    
    # Add speaker mappings
    for speaker in speakers:
        if speaker in all_maps["en_to_cn"]:
            relevant[speaker] = all_maps["en_to_cn"][speaker]
    
    # Add ALL character names that appear in content (not just speakers)
    for en_name, cn_name in all_maps["en_to_cn"].items():
        if en_name in content or f"{en_name}'s" in content or f"{en_name}'" in content:
            relevant[en_name] = cn_name
    
    # Add nouns/terms
    for en, cn in all_maps["nouns"].items():
        if en in content:
            relevant[en] = cn
    
    return relevant


def build_story_prompt_full(content: str, speakers: Set[str]) -> str:
    """
    Build comprehensive prompt with all relevant mappings.
    Used in "prompt" mode for maximum reliability.
    """
    all_maps = get_all_mappings()
    
    # Character mappings section - include ALL names appearing in content
    char_lines = []
    found_names = set()
    
    # First add speakers
    for speaker in sorted(speakers):
        if speaker in all_maps["en_to_cn"]:
            found_names.add(speaker)
            char_lines.append(f"- {speaker} → {all_maps['en_to_cn'][speaker]}")
    
    # Then add other character names appearing in content (including possessives)
    for en_name, cn_name in sorted(all_maps["en_to_cn"].items()):
        if en_name not in found_names:
            # Check if name appears in content (including possessive forms)
            if en_name in content or f"{en_name}'s" in content or f"{en_name}'" in content:
                found_names.add(en_name)
                char_lines.append(f"- {en_name} → {cn_name}")
    
    char_section = '\n'.join(char_lines) if char_lines else "（无角色名映射）"
    
    # Noun mappings section (only include terms in content)
    noun_lines = []
    for en, cn in sorted(all_maps["nouns"].items()):
        if en in content and en != cn:
            noun_lines.append(f"- {en} → {cn}")
    noun_section = '\n'.join(noun_lines[:30]) if noun_lines else "（无术语映射）"
    
    return f"""《碧蓝幻想》本地化专家。将英文剧本翻译成地道中文对白。

## 角色名（严格遵循）
{char_section}

注意：所有格如 "Fiorito's dad" 译为 "菲欧丽特的父亲"。
所有的(Captain)都译为团长而不是(团长)。

## 术语
{noun_section}

## 核心：消灭译制腔

❌ 避免：过度使用"的了我们"、主语过多、逐字直译
✅ 使用：口语化、语气词（呀呢嘛啦）、适当省略主语

常见转换：
- How are you? → 最近咋样？
- Of course! → 那当然！
- Don't worry → 放心
- Let's go! → 走！

## 格式
保留 **角色:** *旁白* # 标题，Captain→团长，直接输出译文。"""


def build_story_prompt_simple() -> str:
    """
    Build simple prompt without mappings.
    Used in "replace" mode where terms are pre-replaced.
    """
    return """《碧蓝幻想》本地化。翻译成地道中文对白，消灭译制腔。

要求：
- 口语化，用语气词（呀呢嘛啦）
- 省略不必要主语
- 对话生活化，旁白文学性

格式：保留 **角色:** *旁白* # 标题，Captain→团长，直接输出译文。"""


def build_jp_translate_prompt() -> str:
    """Build prompt for Japanese to Chinese translation."""
    all_maps = get_all_mappings()
    
    # Include some JP mappings in prompt
    jp_lines = []
    for jp, cn in list(all_maps["jp_to_cn"].items())[:30]:
        jp_lines.append(f"{jp}→{cn}")
    jp_section = '\n'.join(jp_lines) if jp_lines else ""
    
    return f"""日译中。

映射：
団長→团长
騎空団→骑空团
{jp_section}

要求：自然流畅，口语化，保留格式。未列出的名称保留原文。直接输出译文。"""


def build_simple_text_prompt() -> str:
    """Build prompt for simple text translation."""
    return """《碧蓝幻想》翻译。英/日→简体中文，保留格式，直接输出。"""


def build_batch_jp_prompt() -> str:
    """Build prompt for batch Japanese translation with JSON output."""
    base = build_jp_translate_prompt()
    return base + '\n\nReturn JSON: {"0": "translation", "1": "translation", ...}'

