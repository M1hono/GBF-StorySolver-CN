"""
GBF content extractors.

Web extractors (from GBF Wiki):
    StoryExtractor, CastExtractor, VoiceExtractor, LoreExtractor

Local extractors (from BLHXFY/AI-Translation CSV):
    ScenarioExtractor - Extract already-translated scenarios from CSV files

Usage:
    # Web extraction
    from lib.extractors import StoryExtractor
    ext = StoryExtractor()
    ext.extract("Event_Name", "output/")
    
    # LOCAL-FIRST: Extract from CSV (should check this FIRST)
    from lib.extractors import ScenarioExtractor
    ext = ScenarioExtractor()
    ext.extract_by_name("12.29", "story/translated/12.29")
    ext.list_available()  # See what's available locally
"""

from .story import StoryExtractor
from .cast import CastExtractor
from .voice import VoiceExtractor
from .lore import LoreExtractor
from .scenario import ScenarioExtractor

__all__ = [
    'StoryExtractor', 
    'CastExtractor', 
    'VoiceExtractor', 
    'LoreExtractor',
    'ScenarioExtractor',  # LOCAL-FIRST
]
