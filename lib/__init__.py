"""
GBF Wiki content extraction and translation library.

Structure:
    lib/
    ├── extractors/     - Web extraction (story, cast, voice, lore)
    ├── translators/    - Translation (BLHXFY, Claude, Caiyun)
    ├── notion/         - Notion sync
    ├── utils/          - Configuration
    ├── docs/           - Documentation
    ├── local_data/     - AUTHORITATIVE translation data (check first!)
    ├── extract.py      - Quick extraction CLI
    └── translate.py    - Quick translation CLI

Quick Usage:
    # Extraction
    from lib.extractors import StoryExtractor, CastExtractor, VoiceExtractor, LoreExtractor
    
    # Translation (LOCAL-FIRST)
    from lib.translators import translator
    cn_name = translator.smart_lookup('Vajra')  # Checks local data first
    
    # Notion sync
    from lib.notion import SyncContext

CLI:
    python -m lib.extract story Event_Name ./output
    python -m lib.translate lookup "Vajra"
"""

__version__ = "2.0.0"
