# GBF Story Extractor

[中文](README.md)

A complete toolkit for extracting, translating, and publishing Granblue Fantasy story content. Supports content extraction from GBF Wiki, translation using Claude/Caiyun AI, and publishing to Notion.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration Guide](#configuration-guide)
- [Quick Start](#quick-start)
- [Detailed Usage](#detailed-usage)
  - [Content Extraction](#content-extraction)
  - [Translation](#translation)
  - [Notion Publishing](#notion-publishing)
- [Project Structure](#project-structure)
- [Local Data](#local-data)
- [AI-Assisted Usage](#ai-assisted-usage)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Python 3.9 or higher
- Chromium browser (installed via Playwright)
- API keys for respective services

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/gbf-story-extractor.git
cd gbf-story-extractor
```

### Step 2: Install Python Dependencies

```bash
pip install -r lib/requirements.txt
```

### Step 3: Install Playwright Browser

```bash
playwright install chromium
```

### Step 4: Initialize BLHXFY Translation Data

Download community translation resources for character name mapping:

```bash
python -m lib.update_blhxfy
```

This downloads:
- BLHXFY official translation data (character names, terminology)
- AI-Translation community-translated story files

---

## Configuration Guide

This project uses two configuration files. Understanding them is essential:

### Configuration Files Overview

| File | Required | Purpose | Content Type |
|------|----------|---------|--------------|
| `.env` | ✅ | API credentials | Sensitive info (keys, IDs) |
| `config.yaml` | ❌ | Behavior settings | Model, timeout, etc. |
| `characters.json` | ❌ | Batch upload | Character folder/name mapping |

### .env File (Required)

Contains all API keys and sensitive configurations. **Do not commit to Git!**

```bash
# Copy template
cp .env.example .env
```

Full configuration example:

```ini
# ============ Translation Services ============
# Claude API (recommended, best quality)
CLAUDE_API_KEY=sk-ant-api03-xxxxx

# Caiyun Translation API (optional, backup)
CAIYUN_API_KEY=xxxxx

# ============ Notion Publishing ============
# Notion integration key
NOTION_API_KEY=ntn_xxxxx

# Notion root page ID (32 chars, from URL)
NOTION_ROOT_PAGE_ID=2c77c15a92478012aa9ee809fec41257
```

### How to Get API Keys

#### Claude API Key

1. Visit https://console.anthropic.com/
2. Create/login to account
3. Go to Settings → API Keys
4. Click "Create Key"
5. Copy key (format: `sk-ant-api03-xxx`)

#### Caiyun Translation API Key

1. Visit https://dashboard.caiyunapp.com/
2. Register and login
3. Go to Token management
4. Copy your Token

#### Notion API Key

1. Visit https://www.notion.so/my-integrations
2. Click "New integration"
3. Fill in name, select workspace
4. Copy "Internal Integration Token"
5. **Important**: Share target page with this integration

#### Notion Root Page ID

This is the target page ID where all content will be uploaded:

1. Open target page in Notion
2. Check browser URL:
   ```
   https://www.notion.so/workspace/Page-Title-2c77c15a92478012aa9ee809fec41257
   ```
3. Copy the 32-character ID after the last hyphen
4. Add to `.env` as `NOTION_ROOT_PAGE_ID`

**Note**: You must share the page with your Notion integration!
- Open page → "Share" (top right) → "Invite" → Select your integration

### config.yaml File (Optional)

Customize tool behavior. Uses defaults if not present:

```bash
cp config.example.yaml config.yaml
```

Full configuration options:

```yaml
# Translation settings
translation:
  # Mode: prompt (accurate) or replace (fast)
  mode: prompt
  
  # Lines per translation chunk (too large may truncate)
  chunk_size: 120
  
  # Claude model selection
  claude_model: claude-sonnet-4-20250514
  
  # Translation timeout (seconds)
  timeout: 120

# Extraction settings
extraction:
  # Headless mode (false shows browser window for debugging)
  headless: true
  
  # Page load timeout (milliseconds)
  timeout: 30000
  
  # Retry count
  retries: 3

# Notion settings
notion:
  # Force recreate all pages
  force_mode: false
  
  # Request interval (seconds, avoids rate limiting)
  rate_limit: 0.1
```

### characters.json File

Used for batch uploads, defines character list:

```json
[
  {"folder": "vajra", "name": "瓦姬拉"},
  {"folder": "nier", "name": "妮娅"},
  {"folder": "galleon", "name": "伽莱翁"}
]
```

Fields:
- `folder`: Folder name under `characters/` (English, lowercase)
- `name`: Display name in Notion (Chinese)

---

## Quick Start

### Complete Workflow Example

Using Vajra's event story as example:

```bash
# 1. Extract story content
python -m lib.extract story Auld_Lang_Fry_PREMIUM characters/vajra

# 2. Extract character portraits
python -m lib.extract cast Auld_Lang_Fry_PREMIUM characters/vajra

# 3. Translate to Chinese
python -m lib.translate claude \
  characters/vajra/story/auld_lang_fry_premium/raw \
  characters/vajra/story/auld_lang_fry_premium/trans

# 4. Upload to Notion
python3 notion_upload.py vajra 瓦姬拉 --event auld_lang_fry_premium
```

### Extract Voice and Lore

```bash
# Extract voice lines
python -m lib.extract voice Vajra characters/vajra

# Extract character lore (profile, fate episodes, etc.)
python -m lib.extract lore Vajra characters/vajra

# Translate voice
python -m lib.translate claude \
  characters/vajra/voice/raw \
  characters/vajra/voice/trans

# Translate lore
python -m lib.translate claude \
  characters/vajra/lore/raw \
  characters/vajra/lore/trans
```

---

## Detailed Usage

### Content Extraction

Extraction tools fetch content from GBF Wiki pages using Playwright browser automation.

#### Story Extraction (story)

Extract chapter dialogue from event story pages.

```bash
python -m lib.extract story {event_code} {output_dir}
```

**Parameters**:
- `event_code`: Event identifier in Wiki URL
  - Source: `https://gbf.wiki/{event_code}/Story`
  - Examples: `Auld_Lang_Fry_PREMIUM`, `ZodiaCamp:_The_2nd_Divine_Generals_Assembly`
- `output_dir`: Character directory path
  - Recommended: `characters/{character}`

**Output Structure**:
```
characters/vajra/story/auld_lang_fry_premium/
└── raw/
    ├── 00_opening.md
    ├── 01_chapter_1_episode_1.md
    └── ...
```

#### Cast Extraction (cast)

Extract character portraits and names from story pages for Notion display.

```bash
python -m lib.extract cast {event_code} {output_dir}
```

**Output**: `{output_dir}/story/{event}/trans/cast.md`

#### Voice Extraction (voice)

Extract all voice lines from character pages.

```bash
python -m lib.extract voice {character_name} {output_dir}
```

**Parameters**:
- `character_name`: Wiki page name (capitalized)
  - Examples: `Vajra`, `Nier`, `Vikala`

**Output Structure**:
```
characters/vajra/voice/
└── raw/
    ├── general.md           # General lines
    ├── battle/              # Battle voice
    ├── holidays/            # Holiday voice
    ├── outfits/             # Skin voice
    └── character_banter/    # Character interactions
```

#### Lore Extraction (lore)

Extract character profile, fate episodes, and special cutscenes.

```bash
python -m lib.extract lore {character_name} {output_dir}
```

#### Local Scenario Extraction (scenario)

Extract stories from downloaded BLHXFY CSV files (offline).

```bash
# List available scenarios
python -m lib.extract scenario --list

# Extract specific scenario
python -m lib.extract scenario "12.17" story/translated/12.17
```

### Translation

This project supports multiple translation engines. Choose based on your needs and budget.

#### Translation Engine Comparison

| Engine | Input Price | Output Price | 130K Cost | Quality | Glossary | Recommended |
|--------|------------|--------------|-----------|---------|----------|-------------|
| **Gemini 2.0 Flash** | $0.075/1M | $0.30/1M | **$0.05** | ✅ Good | ✅ Prompt | 🥇 Daily |
| **OpenAI GPT-4o-mini** | $0.15/1M | $0.60/1M | $0.10 | ✅ Good | ✅ Prompt | 🥈 Balanced |
| **Claude Sonnet 4** | $3/1M | $15/1M | $2.34 | ⭐ Best | ✅ Prompt | Quality |
| Claude Haiku 3.5 | $1/1M | $5/1M | $0.78 | ✅ Good | ✅ Prompt | Value |
| DeepL Free | Free | Free | $0 | OK | ✅ Native | ⚠️ Format issues |
| Caiyun | ¥40/1M | ¥40/1M | ¥0.05 | OK | ❌ No | Preview |

**Recommended order**: Gemini > OpenAI > Haiku > Sonnet

> 💡 Detailed comparison: [lib/docs/TRANSLATION_API_COMPARISON.md](lib/docs/TRANSLATION_API_COMPARISON.md)

#### Usage

```bash
# Estimate cost first
python -m lib.translate cost {input_dir}

# Gemini (recommended, cheapest)
python -m lib.translate gemini {input_dir} {output_dir}

# OpenAI GPT-4o-mini
python -m lib.translate openai {input_dir} {output_dir}

# Claude (best quality, expensive)
python -m lib.translate claude {input_dir} {output_dir}

# Caiyun (quick preview)
python -m lib.translate caiyun {input_dir} {output_dir}
```

**Examples**:
```bash
# Check cost first
python -m lib.translate cost characters/vajra/story/zodiacamp/raw

# Translate with Gemini (cheap)
python -m lib.translate gemini \
  characters/vajra/story/zodiacamp/raw \
  characters/vajra/story/zodiacamp/trans

# Use Claude for important content
python -m lib.translate claude \
  characters/vajra/lore/raw \
  characters/vajra/lore/trans
```

#### Configure Translation Engines

Set models in `config.yaml`:

```yaml
translation:
  claude_model: claude-sonnet-4-20250514
  openai_model: gpt-4o-mini
  gemini_model: gemini-2.0-flash
```

Set API keys in `.env`:

```bash
CLAUDE_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
```

#### Lookup Character Names

Check if a character name has Chinese translation:

```bash
python -m lib.translate lookup "Vajra"
# Output: Vajra -> 瓦姬拉
```

#### Fix Untranslated Names

Some names may remain in English/Japanese after translation:

```bash
# Scan for untranslated names
python -m lib.translators.name_fixer scan {directory}

# Apply fixes
python -m lib.translators.name_fixer fix {directory}
```

### Notion Publishing

#### Basic Usage

```bash
# Upload single character (all content)
python3 notion_upload.py {folder_name} {display_name}

# Example
python3 notion_upload.py vajra 瓦姬拉
```

#### Full Parameter Reference

```bash
python3 notion_upload.py [character] [display_name] [OPTIONS]
```

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `character` | positional | Character folder name | `vajra` |
| `display_name` | positional | Notion display name | `瓦姬拉` |
| `--mode` | option | Upload mode | `--mode story` |
| `--sync-mode` | option | Sync mode | `--sync-mode force` |
| `--event` | option | Upload specific event only | `--event zodiacamp` |
| `--name` | option | Filter root story name | `--name "12.17"` |
| `--all` | flag | Upload all characters | `--all` |
| `--clean` | flag | Delete before upload | `--clean` |
| `--dry-run` | flag | Preview without uploading | `--dry-run` |
| `--voice-only` | flag | Upload voice only | `--voice-only` |
| `--lore-only` | flag | Upload lore only | `--lore-only` |

#### --mode Values

| Value | Description | Uploads |
|-------|-------------|---------|
| `story` | Root stories only | `story/translated/` |
| `character` | Character content only | `characters/{char}/` |
| `both` | Both (default) | All |

#### --sync-mode Values

| Value | Description | Use Case |
|-------|-------------|----------|
| `diff` | Incremental (default) | Daily updates |
| `force` | Force recreate | Fix issues |

#### Common Commands

```bash
# ===== Single Character =====

# Upload all content
python3 notion_upload.py vajra 瓦姬拉

# Upload specific event only (fastest)
python3 notion_upload.py vajra 瓦姬拉 --event zodiacamp

# Upload voice only
python3 notion_upload.py vajra 瓦姬拉 --voice-only

# Upload lore only
python3 notion_upload.py vajra 瓦姬拉 --lore-only

# Force rebuild voice databases
python3 notion_upload.py vajra 瓦姬拉 --voice-only --sync-mode force

# ===== Root Stories =====

# Upload all root stories
python3 notion_upload.py --mode story

# Upload specific story
python3 notion_upload.py --mode story --name "12.17"

# ===== Batch Operations =====

# Upload all characters (requires characters.json)
python3 notion_upload.py --all

# Clean and re-upload all
python3 notion_upload.py --all --clean

# Force rebuild all pages
python3 notion_upload.py --all --sync-mode force

# Preview mode
python3 notion_upload.py --all --dry-run
```

#### Notion Page Structure

After upload, Notion structure looks like:

```
GBF/
├── Story/                      # Root stories (story/translated/)
│   ├── 12.17/
│   └── 202302 ……and you/
└── Character/
    ├── 瓦姬拉/
    │   ├── Story/              # Event stories
    │   │   ├── auld_lang_fry_premium/
    │   │   │   ├── 00_opening
    │   │   │   ├── Cast Portraits  (database)
    │   │   │   └── ...
    │   │   └── zodiacamp/
    │   ├── Lore/               # Character lore
    │   └── Voice/              # Voice lines (databases)
    │       ├── general/
    │       ├── holidays/
    │       └── outfits/
    └── 妮娅/
        └── ...
```

---

## Project Structure

```
gbf/
├── lib/                          # Core library
│   ├── extractors/               # Web extraction modules
│   │   ├── story.py              # Story chapter extraction
│   │   ├── cast.py               # Character portrait extraction
│   │   ├── voice.py              # Voice line extraction
│   │   ├── lore.py               # Lore content extraction
│   │   └── scenario.py           # Local CSV extraction
│   ├── translators/              # Translation modules
│   │   ├── blhxfy.py             # BLHXFY terminology mapping
│   │   ├── claude.py             # Claude AI translation
│   │   ├── caiyun.py             # Caiyun translation
│   │   └── name_fixer.py         # Post-translation name fix
│   ├── notion/                   # Notion sync modules
│   │   ├── sync.py               # Sync context, page/database ops
│   │   ├── render.py             # Story rendering to Notion blocks
│   │   ├── parsers.py            # Cast/Voice table parsing
│   │   ├── database.py           # Database sync (Cast/Voice)
│   │   └── content.py            # Unified exports (backwards compat)
│   ├── utils/                    # Utilities
│   │   └── config.py             # Configuration loading
│   ├── docs/                     # Developer docs
│   ├── local_data/               # Local translation data
│   │   └── blhxfy/
│   ├── extract.py                # Extraction CLI entry
│   ├── translate.py              # Translation CLI entry
│   └── update_blhxfy.py          # Update local data
│
├── story/                        # Root story content
│   └── translated/               # Stories from BLHXFY
│
├── characters/                   # Character content
│   └── {name}/
│       ├── story/{event}/
│       │   ├── raw/              # English source
│       │   └── trans/            # Chinese translation + cast.md
│       ├── voice/
│       └── lore/
│
├── .cache/notion/                # Notion sync cache
├── notion_upload.py              # Notion upload script
├── characters.json               # Batch upload config
├── .env                          # API keys (don't commit)
└── config.yaml                   # Behavior config (optional)
```

---

## Local Data

### Data Priority

This project uses a **local-first** strategy:

1. **Local translation data** (`lib/local_data/blhxfy/`) - Highest priority
2. **GBF Wiki** - Only when local data unavailable
3. **Machine translation** - Last resort

### Local Data Contents

```
lib/local_data/blhxfy/
├── scenario/                   # Community-translated stories (CSV)
└── etc/                        # Terminology and name mappings
    ├── npc-name-en.csv         # EN→CN character name mapping
    ├── npc-name-jp.csv         # JP→CN character name mapping
    ├── noun.csv                # Terminology (pre-translation)
    ├── noun-fix.csv            # Terminology fix (post-translation)
    └── added_en_mapping.csv    # Manually added mappings
```

### Update Local Data

```bash
# Normal update (incremental)
python -m lib.update_blhxfy

# Force re-download
python -m lib.update_blhxfy --force
```

### Add Custom Mappings

If you find untranslated character names, edit `lib/local_data/blhxfy/etc/added_en_mapping.csv`:

```csv
EnglishName,中文名,,manual
NewCharacter,新角色,,manual
```

---

## AI-Assisted Usage

This project is designed to work well with AI coding assistants like Cursor.

### With Playwright MCP

If your AI assistant has Playwright MCP enabled, it can:

- Navigate to wiki pages and verify content
- Debug extraction issues by inspecting page structure
- Discover event URLs from wiki navigation

Example prompts:

```
Extract story content from https://gbf.wiki/Auld_Lang_Fry_PREMIUM/Story
and translate for vajra.
```

```
Cast extraction is missing some characters,
can you check what's on the page?
```

### Without Playwright MCP

Provide URLs directly. To find URLs:

1. Visit https://gbf.wiki/
2. Search for event or character
3. Navigate to Story or Voice page
4. Copy URL code

Example prompts:

```
Extract story from event code "ZodiaCamp:_The_2nd_Divine_Generals_Assembly"
to characters/vajra
```

---

## Troubleshooting

### Common Issues

#### Browser Not Installed

```
Error: Browser not found
```

**Solution**: Run `playwright install chromium`

#### API Key Error

```
Error: CLAUDE_API_KEY not set
```

**Solution**:
1. Confirm `.env` file exists
2. Check key format is correct
3. Ensure no extra spaces or quotes

#### Notion Page Not Found

```
Error: Could not find page with ID: xxx
```

**Solution**:
1. Verify `NOTION_ROOT_PAGE_ID` is correct 32-char ID
2. Confirm page is shared with your Notion integration
3. Check integration has correct permissions

#### Notion Page Archived

```
Error: Can't edit page on block with an archived ancestor
```

**Solution**:
1. Delete cache: `rm -rf .cache/notion/`
2. Re-run upload command
3. If persists, manually delete pages in Notion and retry

#### Extraction Timeout

```
Error: Timeout waiting for page
```

**Solution**:
1. Set `headless: false` in `config.yaml` to see browser
2. Increase `timeout` value
3. Check network connection
4. Verify Wiki page URL is correct

#### Incomplete Translation

Long files may not translate completely.

**Solution**:
1. Reduce `chunk_size` in `config.yaml` (e.g., to 80)
2. Re-run translation on specific file
3. Check API quota

### Cleanup and Reset

```bash
# Clear Notion cache (fixes sync issues)
rm -rf .cache/notion/

# Clear specific character cache
rm .cache/notion/vajra.json

# Re-download local data
python -m lib.update_blhxfy --force

# Full re-upload for a character
rm .cache/notion/vajra.json
python3 notion_upload.py vajra 瓦姬拉 --sync-mode force
```

---

## License

MIT License - see LICENSE file.
