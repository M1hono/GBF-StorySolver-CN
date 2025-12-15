# Local Data Reference

## Overview

The `local_data/` directory contains authoritative translation data from BLHXFY and other sources.

**IMPORTANT: Local data takes priority over machine translation.** Always check local data first before using Claude/Caiyun translation.

## Directory Structure

```
local_data/
├── blhxfy/
│   ├── etc/                    # Character name mappings
│   │   ├── npc-name-en.csv     # EN → ZH name mapping (PRIMARY)
│   │   ├── npc-name-jp.csv     # JP → ZH name mapping (reference)
│   │   ├── noun.csv            # Terminology mapping
│   │   └── noun-fix.csv        # Terminology fixes
│   └── scenario/               # Story translations
│       └── blhxfy/
│           └── 主线剧情/        # Main story chapters
├── events/                     # Event configuration files
│   └── {Event_Slug}.json
├── cn_character_names.txt      # Chinese name corpus
└── aliases.json                # Character alias mappings
```

## Character Content Structure

```
characters/{character}/
├── story/{event_slug}/
│   ├── raw/                    # English source
│   │   ├── 00_opening.md
│   │   └── 01_chapter_1.md
│   └── trans/                  # Chinese translation
│       ├── cast.md             # REQUIRED: Character portraits
│       ├── 00_opening.md
│       └── 01_chapter_1.md
│
├── voice/
│   ├── raw/                    # Japanese + English + audio links
│   │   ├── general/
│   │   │   ├── base_sprite.md
│   │   │   ├── uncap_sprite.md
│   │   │   └── final_uncap.md
│   │   ├── chain_burst.md
│   │   ├── character_banter/
│   │   │   └── {character}.md
│   │   ├── holidays/
│   │   │   ├── happy_birthday.md
│   │   │   ├── happy_new_year.md
│   │   │   └── ...
│   │   └── outfits/
│   │       └── {outfit}.md
│   └── trans/                  # (same structure as raw, with Chinese)
│
└── lore/
    ├── raw/
    │   ├── profile/
    │   │   ├── english.md       # Official profile (EN)
    │   │   └── japanese.md      # Official profile (JP)
    │   ├── fate_episodes/
    │   │   ├── intro.md         # Story format dialogue
    │   │   ├── skill.md
    │   │   ├── lvl_cap_1.md
    │   │   └── ...
    │   ├── special_cutscenes/
    │   │   ├── happy_birthday.md
    │   │   ├── happy_holidays.md
    │   │   └── ...
    │   └── side_scrolling/
    │       └── quotes.md        # JP/CN/EN table format
    └── trans/                   # (same structure as raw, translated)
```

## Voice Table Format

```markdown
# Character - Section

数据源：`https://gbf.wiki/Character/Voice#Section`

| Label | Japanese | Chinese | English | Notes | Audio |
| --- | --- | --- | --- | --- | --- |
| Normal Attack | やあっ！ | 呀！ | Yah! |  | [mp3](url) |
```

## Side-scrolling Quotes Format

```markdown
# Character - Side-scrolling Quotes

| Japanese | Chinese | English |
| --- | --- | --- |
| もう終わりか？ | 已经结束了吗？ | Finished already? |
```

## Usage Priority

### For Story Translation

1. **First**: Check `local_data/blhxfy/scenario/` for existing Chinese translation
2. **Second**: If not found, extract from Wiki and use machine translation

### For Character Names

1. **First**: Lookup in `npc-name-en.csv` (English → Chinese)
2. **Second**: Lookup in `npc-name-jp.csv` (Japanese → Chinese) 
3. **Third**: Use Claude AI for smart matching with `cn_character_names.txt`
4. **Last resort**: Leave untranslated or use machine translation

### For Terminology

1. Apply `noun.csv` mappings before translation
2. Apply `noun-fix.csv` corrections after translation

## File Formats

### npc-name-en.csv
```csv
en,zh
Captain,团长
Lyria,露莉亚
Vyrn,比依
Vajra,瓦姬拉
```

### noun.csv
```csv
en,zh
Sky Realm,空之世界
Astrals,星晶兽
```

## API Usage

```python
from lib.translators import translator

# Lookup character name
cn_name = translator.smart_lookup("Vajra")  # Returns "瓦姬拉"

# Apply terminology
text = translator.apply_noun_mapping("The Captain went to Sky Realm")
```

## Extraction Commands

```bash
# Extract story + cast for an event (from Wiki)
python -m lib.extract story Auld_Lang_Fry_PREMIUM characters/vajra
python -m lib.extract cast Auld_Lang_Fry_PREMIUM characters/vajra

# Extract voice (auto-categorized)
python -m lib.extract voice Vajra characters/vajra

# Extract lore (profile, fate episodes, cutscenes, quotes)
python -m lib.extract lore Vajra characters/vajra

# Extract story from LOCAL CSV (BLHXFY/AI-Translation)
python -m lib.extract scenario "活动剧情/12.17" story/translated/12.17
```

## Scenario Extraction (Local CSV)

Extract translated stories directly from BLHXFY/AI-Translation CSV files:

```bash
# Basic usage - extracts from lib/local_data/blhxfy/scenario/
python -m lib.extract scenario "活动剧情/12.17" story/translated/12.17

# Custom path - provide absolute or relative path
python -m lib.extract scenario "/path/to/csv/folder" output/folder

# Combined mode - single file output instead of per-CSV
python -m lib.extract scenario "活动剧情/12.17" output/ --combined
```

### Programmatic Usage

```python
from lib.extractors.scenario import ScenarioExtractor

ext = ScenarioExtractor()

# Extract with original file structure (1 CSV = 1 MD)
ext.extract("lib/local_data/blhxfy/scenario/ai-translation/活动剧情/12.17", 
            "story/translated/12.17", 
            combined=False)

# Extract to single combined file
ext.extract("lib/local_data/blhxfy/scenario/ai-translation/活动剧情/12.17", 
            "story/translated/12.17.md", 
            combined=True)

# Batch extract multiple folders
ext.batch_extract([
    "BLHXFY/data/scenario/活动剧情/202511 黑白调色盘",
    "AI-Translation/story/活动剧情/12.29",
], "story/translated/")
```

### Translation Priority

1. **Chinese (trans column)** - Use directly if available
2. **Japanese (text column)** - Apply name mappings from `npc-name-jp.csv`
3. **Skip** - If neither available

### Output Format

```markdown
**角色名:** 对话内容在同一行

*旁白使用斜体格式*

**另一角色:** 继续对话...
```

## Translation Commands

```bash
# Translate voice files
python -c "
from lib.translators.claude import translate_voice_directory
translate_voice_directory('characters/vajra/voice/raw', 'characters/vajra/voice/trans')
"

# Translate lore files
python -c "
from lib.translators.claude import translate_lore_file
from pathlib import Path
for f in Path('characters/vajra/lore/raw').rglob('*.md'):
    rel = f.relative_to('characters/vajra/lore/raw')
    out = Path('characters/vajra/lore/trans') / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    translate_lore_file(str(f), str(out))
"
```

## Maintenance

When a character name is missing:

1. Check `cn_character_names.txt` for potential matches
2. Add new entry to `npc-name-en.csv`
3. Re-run translation pipeline

## Data Sources

- **BLHXFY**: https://github.com/biuuu/BLHXFY
- Sync with upstream periodically
