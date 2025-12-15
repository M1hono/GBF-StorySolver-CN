"""
Translation modules.

Usage:
    from lib.translators import translator
    from lib.translators import translate_file, translate_directory
    
    # Two modes available:
    # - "prompt": Include all mappings in prompt (reliable, default)
    # - "replace": Pre-replace terms before translation (cheaper)
    translate_file(input, output, mode="prompt")
    
    # CSV translation:
    from lib.translators import translate_csv_file, analyze_csv_directory
"""

from .blhxfy import BLHXFYTranslator, translator
from .prompts import get_all_mappings
from .voice_translator import is_voice_table, translate_voice_table
from .claude import (
    translate_file,
    translate_directory,
    translate_story,
    translate_lore,
    DEFAULT_MODE,
)
from .csv_translator import (
    translate_csv_file,
    translate_csv_directory,
    analyze_csv_directory,
    count_untranslated,
    detect_csv_format,
)

__all__ = [
    # BLHXFY
    'BLHXFYTranslator', 
    'translator',
    # Claude translation
    'translate_file',
    'translate_directory',
    'translate_story',
    'translate_lore',
    'get_all_mappings',
    'is_voice_table',
    'translate_voice_table',
    'DEFAULT_MODE',
    # CSV translation
    'translate_csv_file',
    'translate_csv_directory',
    'analyze_csv_directory',
    'count_untranslated',
    'detect_csv_format',
]
