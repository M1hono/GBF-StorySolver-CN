# GBF Tool Library API Reference

## Environment Setup

```bash
cd lib
pip install -r requirements.txt
playwright install chromium
```

### Required Environment Variables

```bash
# .env file (create from .env.example)
CLAUDE_API_KEY=sk-ant-xxx
NOTION_API_KEY=ntn_xxx
NOTION_ROOT_PAGE_ID=xxxxx  # 32-char ID from Notion page URL
```

---

## Quick CLI Tools

### lib/extract.py - Content Extraction

```bash
# Story + Cast extraction
python -m lib.extract story Auld_Lang_Fry_PREMIUM characters/vajra
python -m lib.extract cast Auld_Lang_Fry_PREMIUM characters/vajra

# Voice extraction (auto-categorized into general/holidays/outfits/etc)
python -m lib.extract voice Vajra characters/vajra

# Lore extraction
python -m lib.extract lore Vajra characters/vajra
```

### lib/translate.py - Translation

```bash
# Translate with Claude (auto-detects format)
python -m lib.translate claude ./raw ./trans

# Translate with Caiyun
python -m lib.translate caiyun ./raw ./trans

# Lookup character name
python -m lib.translate lookup "Vajra"
```

---

## Extractors (lib/extractors/)

### StoryExtractor

Extract story chapters from GBF Wiki event pages.

```python
from lib.extractors import StoryExtractor

extractor = StoryExtractor(headless=True)
result = extractor.extract("Auld_Lang_Fry_PREMIUM", "output/raw")
# Returns: {success, chapters: [{name, file}], error?}
```

**Output:** `output/raw/{chapter_name}.md`

### CastExtractor

Extract character portraits from story pages.

```python
from lib.extractors import CastExtractor

extractor = CastExtractor(headless=True)
result = extractor.extract("Auld_Lang_Fry_PREMIUM", "output/trans/cast.md")
# Returns: {success, cast: [{en_name, cn_name, image_url, wiki_url}]}
```

**Output:** `cast.md` with format:
```markdown
# Event Name - Cast Portraits

| 角色（英 / 中） | 头像 |
| --- | --- |
| [English / 中文](wiki_url) | ![Name](200px_url) |
```

### VoiceExtractor

Extract voice lines from character Voice pages. Supports special table formats:
- **Standard tables**: General, Holidays, Outfits
- **Chain Burst**: Element + Chain Level structure with rowspan
- **Multi-line entries**: Same label with multiple voice lines

```python
from lib.extractors import VoiceExtractor

extractor = VoiceExtractor(headless=False)
result = extractor.extract("Vajra", "characters/vajra")
# Returns: {success, files, categories}
```

**Output structure:**
```
voice/raw/
├── general.md           # Menu + Battle voice lines
├── chain_burst.md       # Chain Burst (special format)
├── character_banter/
│   ├── mahira.md
│   └── kumbhira.md
├── holidays/
│   ├── happy_birthday.md
│   └── ...
└── outfits/
    └── {outfit}.md
```

**Standard Table format:**
```markdown
| Label | Japanese | Chinese | English | Notes | Audio |
| --- | --- | --- | --- | --- | --- |
| Normal Attack | やあっ！ |  | Yah! |  | [mp3](url) |
```

**Chain Burst format:**
```markdown
| Label | Japanese | Chinese | English | Audio |
| --- | --- | --- | --- | --- |
| Chain Start | 任せろ！ |  |  | [mp3](url) |
| Fire 2-Chain | レッドデトネーション！ |  | Red Detonation! | [mp3](url) |
```

### LoreExtractor

Extract lore content from character Lore pages.

```python
from lib.extractors import LoreExtractor

extractor = LoreExtractor(headless=False)
result = extractor.extract("Vajra", "characters/vajra")
# Returns: {success, files, structure}
```

**Output structure:**
```
lore/raw/
├── profile/
│   ├── english.md
│   └── japanese.md
├── fate_episodes/
│   ├── intro.md
│   └── ...
└── special_cutscenes/
    └── happy_birthday.md
```

---

## Translators (lib/translators/)

### Module Structure (Refactored)

```
lib/translators/
├── __init__.py           # Public API exports
├── blhxfy.py            # BLHXFY local data (name mappings)
├── prompts.py           # Translation prompt builders
├── voice_translator.py  # Voice table translation logic
├── claude.py            # Claude API + file/directory translation
├── caiyun.py            # Caiyun API
└── csv_translator.py    # CSV file translation
```

### BLHXFYTranslator

Local name/terminology lookup (LOCAL-FIRST policy).

```python
from lib.translators import translator

# Lookup Chinese name
cn = translator.lookup_cn_name("Vajra")  # -> "瓦姬拉"

# Smart lookup (handles variations like "Vajra (Summer)")
cn = translator.smart_lookup("Vajra")

# Apply terminology before translation
text = translator.apply_pre_translation("Captain said hello")

# Apply fixes after translation  
text = translator.apply_post_translation(translated)

# Add new mapping
translator.add_en_mapping("NewChar", "新角色")
```

### Claude Translator

High-quality AI translation with auto-format detection.

```python
from lib.translators import translate_file, translate_directory

# Auto-detect format (story/voice/lore)
result = translate_file("raw/chapter.md", "trans/chapter.md")

# Translate directory
result = translate_directory("raw/", "trans/")
# Returns: {success, failed, files}
```

**Supported formats (auto-detected):**
- **Voice tables**: `| Label | Japanese | Chinese |...` - fills Chinese column
- **Lore tables**: `| Japanese | English |` - adds Chinese column
- **Story dialogue**: `**Name:** text` format

### Voice Translator (Internal)

```python
from lib.translators.voice_translator import (
    is_voice_table,
    has_chinese_column,
    translate_voice_table,
)

# Check if content is voice table
if is_voice_table(content):
    # Check if Chinese column exists
    if has_chinese_column(content):
        # Fill existing Chinese column
        translated = translate_voice_table(client, model, content)
```

### Prompt Builders

```python
from lib.translators.prompts import (
    build_story_prompt_full,   # With all mappings (reliable)
    build_story_prompt_simple, # Without mappings (faster)
    build_jp_translate_prompt, # JP -> CN
    get_all_mappings,          # Get all BLHXFY mappings
)
```

### CSV Translator

Translate BLHXFY scenario CSV files.

```python
from lib.translators import (
    translate_csv_file,
    translate_csv_directory,
    analyze_csv_directory,
)

# Analyze CSV directory
stats = analyze_csv_directory("lib/local_data/blhxfy/scenario")

# Translate single file
result = translate_csv_file(Path("scenario.csv"))

# Translate directory (only untranslated files)
result = translate_csv_directory("scenario/", output_dir="translated/")
```

---

## BLHXFY Data Update (lib/update_blhxfy.py)

Sync official BLHXFY translation data from GitHub.

```bash
# Check current data status
python -m lib.update_blhxfy --status

# Update from repositories
python -m lib.update_blhxfy

# Force fresh clone
python -m lib.update_blhxfy --force
```

**Synced files:**
- `npc-name-en.csv` - English to Chinese name mappings
- `npc-name-jp.csv` - Japanese to Chinese name mappings
- `noun.csv` - Terminology mappings
- `noun-fix.csv` - Post-translation fixes
- `scenario/` - Pre-translated story content (merged from BLHXFY + AI-Translation)

---

## Notion Sync (lib/notion/)

### Module Structure (Refactored)

```
lib/notion/
├── __init__.py    # Public API exports
├── sync.py        # SyncContext, client, caching, page/database utils
├── render.py      # Story markdown -> Notion blocks
├── parsers.py     # Cast/Voice table parsing, URL normalization
├── database.py    # Cast/Voice database sync
└── content.py     # Rich text helpers
```

### SyncContext

```python
from lib.notion import SyncContext

ctx = SyncContext(
    api_key="ntn_xxx",
    cache_path=".cache/notion/vajra.json",
    mode="diff",  # or "force"
)

# Create/get page
page_id = ctx.ensure_page(parent_id, "Page Title")

# Sync blocks with content diff
updated = ctx.sync_page_blocks(page_id, blocks, cache_key="story:xxx")

# Force recreate page
page_id = ctx.recreate_page(parent_id, "Page Title")

ctx.save()
```

### Content Rendering

```python
from lib.notion import (
    render_story_blocks,
    parse_cast_table,
    parse_voice_table,
    sync_cast_database,
    sync_voice_database,
    normalize_gbf_media_url,
)

# Markdown -> Notion blocks
blocks = render_story_blocks(markdown_content)

# Parse cast.md
rows = parse_cast_table(cast_md)
# Returns: [{name, image_url, wiki_url}, ...]

# Parse voice.md
rows = parse_voice_table(voice_md)
# Returns: [{Label, Japanese, Chinese, English, Audio}, ...]

# Sync cast database
db_id = sync_cast_database(client, page_id, rows, mode="diff")

# Sync voice database
db_id = sync_voice_database(client, page_id, "General", rows, mode="diff")

# Normalize GBF Wiki media URLs
stable_url = normalize_gbf_media_url(thumbnail_url)
```

---

## Notion Upload Script (notion_upload.py)

### Usage

```bash
# Upload all characters from characters.json
python3 notion_upload.py --all

# Upload root stories only
python3 notion_upload.py --mode story

# Upload specific root story
python3 notion_upload.py --mode story --name "12.17"

# Upload single character (story, lore, voice)
python3 notion_upload.py vajra 瓦姬拉

# Upload character's specific event
python3 notion_upload.py vajra 瓦姬拉 --event zodiacamp

# Upload only voice for character(s)
python3 notion_upload.py vajra 瓦姬拉 --voice-only
python3 notion_upload.py --all --voice-only

# Upload only lore for character(s)
python3 notion_upload.py nier 妮娅 --lore-only

# Force recreate all pages
python3 notion_upload.py --all --sync-mode force

# Preview without uploading
python3 notion_upload.py --all --dry-run
```

### characters.json Format

```json
[
  {"folder": "vajra", "name": "瓦姬拉"},
  {"folder": "nier", "name": "妮娅"},
  {"folder": "galleon", "name": "伽莱翁"}
]
```

---

## Configuration (lib/utils/config.py)

```python
from lib.utils.config import (
    SCRIPT_DIR,      # lib/ directory
    REPO_ROOT,       # project root
    LOCAL_DATA_DIR,  # lib/local_data/
    CLAUDE_API_KEY,  # from .env
    CLAUDE_MODEL,    # from .env
    NOTION_API_KEY,  # from .env
    NOTION_ROOT_PAGE_ID,  # from .env
)
```

---

## Complete Workflow Example

```python
import sys
sys.path.insert(0, 'lib')
from extractors import StoryExtractor, CastExtractor, VoiceExtractor, LoreExtractor
from translators import translate_file, translate_directory
from pathlib import Path

CHARACTER = "Vajra"
CHAR_DIR = "characters/vajra"

# 1. Extract story
story_ext = StoryExtractor(headless=False)
story_ext.extract("Auld_Lang_Fry_PREMIUM", f"{CHAR_DIR}/story/auld_lang_fry_premium/raw")

# 2. Extract cast
cast_ext = CastExtractor(headless=False)
cast_ext.extract("Auld_Lang_Fry_PREMIUM", f"{CHAR_DIR}/story/auld_lang_fry_premium/trans/cast.md")

# 3. Extract voice
voice_ext = VoiceExtractor(headless=False)
voice_ext.extract(CHARACTER, CHAR_DIR)

# 4. Extract lore
lore_ext = LoreExtractor(headless=False)
lore_ext.extract(CHARACTER, CHAR_DIR)

# 5. Translate voice (auto-detects format)
translate_directory(f"{CHAR_DIR}/voice/raw", f"{CHAR_DIR}/voice/trans")

# 6. Translate lore
translate_directory(f"{CHAR_DIR}/lore/raw", f"{CHAR_DIR}/lore/trans")
```
