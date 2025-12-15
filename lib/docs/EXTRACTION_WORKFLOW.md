# GBF Content Extraction Workflow

## Overview

This document describes the complete workflow for extracting, translating, and organizing GBF content.

## Directory Layout

```text
characters/{character}/
├── story/{event_slug}/
│   ├── raw/                    # English source
│   │   ├── 00_opening.md
│   │   └── 01_ending.md
│   └── trans/                  # Chinese translation
│       ├── cast.md             # REQUIRED
│       ├── 00_opening.md
│       └── 01_ending.md
│
├── voice/
│   ├── raw/                    # JP/EN + audio links
│   │   ├── general/
│   │   │   └── base_sprite.md
│   │   ├── chain_burst.md
│   │   ├── character_banter/
│   │   ├── holidays/
│   │   └── outfits/
│   └── trans/                  # JP/CN + audio links
│       └── (same structure)
│
└── lore/
    ├── raw/
    │   ├── profile/
    │   │   ├── english.md
    │   │   └── japanese.md
    │   ├── fate_episodes/
    │   │   ├── intro.md
    │   │   └── ...
    │   ├── special_cutscenes/
    │   │   └── happy_birthday.md
    │   └── side_scrolling/
    │       └── quotes.md
    └── trans/
        └── (same structure)
```

## Quick Commands

### Story Extraction
```bash
# Extract story chapters
python -m lib.extract story Auld_Lang_Fry_PREMIUM characters/vajra

# Extract cast portraits
python -m lib.extract cast Auld_Lang_Fry_PREMIUM characters/vajra

# Translate story
python -m lib.translate claude characters/vajra/story/auld_lang_fry_premium/raw characters/vajra/story/auld_lang_fry_premium/trans
```

### Voice Extraction
```bash
# Extract voice lines
python -m lib.extract voice Vajra characters/vajra

# Translate voice
python3 << 'EOF'
import sys
sys.path.insert(0, 'lib')
from translators.claude import translate_voice_directory
translate_voice_directory('characters/vajra/voice/raw', 'characters/vajra/voice/trans')
EOF
```

### Lore Extraction
```bash
# Extract lore
python -m lib.extract lore Vajra characters/vajra

# Translate lore
python3 << 'EOF'
import sys
sys.path.insert(0, 'lib')
from translators.claude import translate_lore_file
from pathlib import Path
for f in Path('characters/vajra/lore/raw').rglob('*.md'):
    rel = f.relative_to('characters/vajra/lore/raw')
    out = Path('characters/vajra/lore/trans') / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    translate_lore_file(str(f), str(out))
EOF
```

## Data Source Priority

1. **Local BLHXFY data** (`lib/local_data/blhxfy/scenario/`)
   - If exists, use directly - DO NOT machine translate
   
2. **GBF Wiki** (`https://gbf.wiki/`)
   - Use when local data unavailable
   - Extract raw → translate → save trans

## File Formats

### Story (Markdown)
```markdown
# Chapter Title

**Character:** Dialogue text here.

**Lyria:** Another line.

*Narration or stage direction.*
```

### Cast Table
```markdown
# Event Name - Cast Portraits

数据源：`https://gbf.wiki/Event_Name/Story`

| 角色（英 / 中） | 头像 |
| --- | --- |
| [English / 中文](wiki_url) | ![Name](200px_url) |
```

### Voice Table
```markdown
# Character - Section

数据源：`https://gbf.wiki/Character/Voice#Section`

| Label | Japanese | Chinese | English | Notes | Audio |
| --- | --- | --- | --- | --- | --- |
| Normal Attack | やあっ！ | 呀！ | Yah! |  | [mp3](url) |
```

### Lore Profile
```markdown
# Character - Profile (Language)

数据源：`https://gbf.wiki/Character/Lore#Official_Profile`

**Age**: 14
**Height**: 147 cm
**Race**: Erune
```

### Lore Fate Episode (Story Format)
```markdown
# Character - Episode Name

数据源：`https://gbf.wiki/Character/Lore#Fate_Episodes`

## Scene Title

**Character:** Dialogue.
```

### Side-scrolling Quotes
```markdown
# Character - Side-scrolling Quotes

| Japanese | Chinese | English |
| --- | --- | --- |
| もう終わりか？ | 已经结束了吗？ | Finished already? |
```

## Python API

```python
import sys
sys.path.insert(0, 'lib')

from extractors import StoryExtractor, CastExtractor, VoiceExtractor, LoreExtractor
from translators.claude import translate_voice_directory, translate_lore_file, translate_directory

# Extract
story_ext = StoryExtractor(headless=False)
cast_ext = CastExtractor(headless=False)
voice_ext = VoiceExtractor(headless=False)
lore_ext = LoreExtractor(headless=False)

# Use
story_ext.extract("Event_Slug", "output/raw")
cast_ext.extract("Event_Slug", "output/trans/cast.md")
voice_ext.extract("Character", "characters/char")
lore_ext.extract("Character", "characters/char")

# Translate
translate_directory("raw/", "trans/")
translate_voice_directory("voice/raw/", "voice/trans/")
```

## Notion Upload

After extraction and translation, upload to Notion:

```bash
python notion_upload.py --character vajra --section all
```

Cache stored in `.cache/notion/{character}.json`.

## Validation Checklist

- [ ] `story/{event}/trans/cast.md` exists with correct format
- [ ] All story chapters in `trans/` have corresponding `raw/` files
- [ ] Voice tables have `| Label | Japanese | Chinese | English | Notes | Audio |` header
- [ ] Lore files preserve source URL in header
- [ ] Chinese column is filled for all voice/quote rows
