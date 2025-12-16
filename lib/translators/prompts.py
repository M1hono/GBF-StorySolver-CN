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
    
    return f"""你是《碧蓝幻想》资深本地化专家。你的任务是将英文剧本翻译成**地道的中文对白**，而不是"英文的中文版"。

## 角色名映射（必须严格遵循）
{char_section}

**注意**: 遇到所有格形式（如 "Fiorito's dad"）应译为 "菲欧丽特的父亲"，不要保留英文名。

## 术语映射
{noun_section}

## 核心原则：消灭译制腔

### ❌ 译制腔特征（必须避免）
- "你今天怎么样？" ← How are you today?
- "我听说我们要去冒险了！" ← I heard we're going on an adventure!
- "让他们见识一下我们的厉害！" ← Let's show them what we've got!
- "我会用我的力量保护大家" ← I'll protect everyone with my strength
- 过度使用"的"、"了"、"我们"
- 主语过多（中文常省略主语）

### ✅ 自然中文表达（应该这样）
- "今天感觉怎么样？" / "精神不错嘛！"
- "听说要去冒险了~！"
- "放马过来！" / "干就完了！"
- "有我在，大家放心！"
- 适当省略主语，用语气词代替

### 角色语气指南
- **活泼角色**：语气词多（呀、呢、嘛、啦），节奏轻快
- **沉稳角色**：简洁有力，少用语气词
- **可爱角色**：叠词（好好、乖乖）、撒娇语气
- **热血角色**：感叹句多，气势强

### 常见表达转换
| 英文直译 | 自然中文 |
|---------|---------|
| How are you? | 最近怎么样？/ 感觉如何？ |
| I think... | 我觉得... / 依我看... |
| Don't worry | 放心 / 没事 / 别担心 |
| Let's go! | 走！/ 出发！/ 上！ |
| Of course! | 那当然！/ 必须的！ |
| I heard that... | 听说... (省略"我") |

## 格式要求
- 保留 `**角色名:**` `*旁白*` `# 标题` 格式
- Captain → 团长
- 直接输出译文"""


def build_story_prompt_simple() -> str:
    """
    Build simple prompt without mappings.
    Used in "replace" mode where terms are pre-replaced.
    """
    return """你是《碧蓝幻想》资深本地化专家。翻译成**地道中文对白**，消灭译制腔。

## 核心要求
- 写出中国人说的话，不是"英文的中文版"
- 对话口语化，适当使用语气词（呀、呢、嘛、啦）
- 省略不必要的主语（中文特点）
- 旁白文学性强，对话生活化

## 常见转换
- How are you? → 最近咋样？
- Of course! → 那当然！/ 必须的！
- Don't worry → 放心 / 没事
- Let's go! → 走！/ 出发！

## 格式
- 保留 **角色名:** *旁白* # 标题
- 已有中文名保持不变
- Captain → 团长

直接输出译文。"""


def build_jp_translate_prompt() -> str:
    """Build prompt for Japanese to Chinese translation."""
    all_maps = get_all_mappings()
    
    # Include some JP mappings in prompt
    jp_lines = []
    for jp, cn in list(all_maps["jp_to_cn"].items())[:30]:
        jp_lines.append(f"- {jp} → {cn}")
    jp_section = '\n'.join(jp_lines) if jp_lines else ""
    
    return f"""你是《碧蓝幻想》资深翻译专家，擅长日译中。

## 角色名映射（必须严格遵循）
- 団長 → 团长
- 騎空団 → 骑空团
{jp_section}

## 翻译要求
- 译文自然流畅，符合中文表达习惯
- 对话口语化，体现角色个性
- 严格保留原文格式
- 角色名使用上方映射，未列出的保留原文

直接输出译文，无需说明。"""


def build_simple_text_prompt() -> str:
    """Build prompt for simple text translation."""
    return """你是《碧蓝幻想》翻译。将英文/日文翻译成简体中文。
保留格式（#标题、**粗体**、空行）。
直接输出翻译。"""


def build_batch_jp_prompt() -> str:
    """Build prompt for batch Japanese translation with JSON output."""
    base = build_jp_translate_prompt()
    return base + '\n\nReturn JSON: {"0": "translation", "1": "translation", ...}'

