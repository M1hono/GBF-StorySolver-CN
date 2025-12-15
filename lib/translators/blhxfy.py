"""
BLHXFY Translation utilities.
Loads and applies official BLHXFY translation mappings.
"""

import os
import csv
import logging
from typing import Dict, Any, Optional

try:
    from ..utils.config import LOCAL_BLHXFY_ETC, SCRIPT_DIR
except ImportError:
    import os
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    LOCAL_BLHXFY_ETC = os.path.join(os.path.dirname(SCRIPT_DIR), "local_data", "blhxfy", "etc")

logger = logging.getLogger("gbf-wiki.translator")


class BLHXFYTranslator:
    """
    Handles translation using BLHXFY official translation files.
    """
    
    def __init__(self):
        self.npc_names: Dict[str, str] = {}  # EN -> CN
        self.npc_names_jp: Dict[str, str] = {}  # JP -> CN
        self.nouns: Dict[str, str] = {}
        self.noun_fixes: Dict[str, str] = {}
        self.caiyun_prefixes: Dict[str, str] = {}
        self.npc_en_file_path: Optional[str] = None
        self._load_translations()
    
    def _first_existing(self, paths):
        for p in paths:
            if os.path.exists(p):
                return p
        return None
    
    def _load_translations(self):
        # Load EN -> CN mappings (original)
        npc_file = self._first_existing([
            os.path.join(LOCAL_BLHXFY_ETC, "npc-name-en.csv"),
            os.path.join(SCRIPT_DIR, "blhxfy_npc_name_en.csv"),
        ])
        if npc_file:
            self.npc_en_file_path = npc_file
            with open(npc_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('name') and row.get('trans'):
                        self.npc_names[row['name']] = row['trans']
            logger.info(f"Loaded {len(self.npc_names)} EN->CN NPC names")
        
        # Load added EN -> CN mappings (generated)
        added_file = os.path.join(LOCAL_BLHXFY_ETC, "added_en_mapping.csv")
        if os.path.exists(added_file):
            added_count = 0
            with open(added_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('name', '').strip()
                    trans = row.get('trans', '').strip()
                    if name and trans and name not in self.npc_names:
                        self.npc_names[name] = trans
                        added_count += 1
            logger.info(f"Loaded {added_count} added EN->CN mappings")
        
        # Load JP -> CN mappings
        jp_file = self._first_existing([
            os.path.join(LOCAL_BLHXFY_ETC, "npc-name-jp.csv"),
        ])
        if jp_file:
            with open(jp_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('name') and row.get('trans'):
                        self.npc_names_jp[row['name']] = row['trans']
            logger.info(f"Loaded {len(self.npc_names_jp)} JP->CN NPC names")
        
        noun_file = self._first_existing([
            os.path.join(LOCAL_BLHXFY_ETC, "noun.csv"),
            os.path.join(SCRIPT_DIR, "blhxfy_noun.csv"),
        ])
        if noun_file:
            with open(noun_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2 and row[0] and row[1]:
                        self.nouns[row[0]] = row[1]
            logger.info(f"Loaded {len(self.nouns)} nouns")
        
        fix_file = self._first_existing([
            os.path.join(LOCAL_BLHXFY_ETC, "noun-fix.csv"),
            os.path.join(SCRIPT_DIR, "blhxfy_noun_fix.csv"),
        ])
        if fix_file:
            with open(fix_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2 and row[0] and row[1]:
                        self.noun_fixes[row[0]] = row[1]
            logger.info(f"Loaded {len(self.noun_fixes)} fixes")
        
        # Load caiyun-prefix mappings
        prefix_file = self._first_existing([
            os.path.join(LOCAL_BLHXFY_ETC, "caiyun-prefix.csv"),
        ])
        if prefix_file:
            with open(prefix_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 2 and row[0] and row[1]:
                        self.caiyun_prefixes[row[0]] = row[1]
            logger.info(f"Loaded {len(self.caiyun_prefixes)} caiyun prefixes")
    
    def add_en_mapping(self, en_name: str, cn_name: str) -> bool:
        """Add a new EN->CN mapping and persist to file."""
        if not en_name or not cn_name:
            return False
        
        self.npc_names[en_name] = cn_name
        
        if self.npc_en_file_path and os.path.exists(self.npc_en_file_path):
            try:
                with open(self.npc_en_file_path, 'a', encoding='utf-8', newline='') as f:
                    f.write(f"{en_name},{cn_name},,\n")
                logger.info(f"Added mapping: {en_name} -> {cn_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to persist mapping: {e}")
        return False
    
    def _strip_suffix(self, name: str) -> str:
        """Remove common character variant suffixes."""
        suffixes = [
            ' (Event)', ' (Summer)', ' (Grand)', ' (Yukata)', ' (Halloween)',
            ' (Holiday)', ' (Valentine)', ' (Dark)', ' (Light)', ' (SR)',
            ' (Promo)', ' (Fire)', ' (Water)', ' (Earth)', ' (Wind)',
        ]
        result = name
        for suffix in suffixes:
            if result.endswith(suffix):
                result = result[:-len(suffix)]
                break
        return result
    
    def lookup_cn_name(self, en_name: str) -> Optional[str]:
        """
        Lookup Chinese name with fallback chain:
        1. Exact match in EN->CN
        2. Strip suffix and retry
        3. Case-insensitive match
        4. Partial match (name contained in key or vice versa)
        """
        if not en_name:
            return None
            
        # 1. Exact match
        if en_name in self.npc_names:
            return self.npc_names[en_name]
        
        # 2. Strip suffix and retry
        base_name = self._strip_suffix(en_name)
        if base_name != en_name and base_name in self.npc_names:
            return self.npc_names[base_name]
        
        # 3. Case-insensitive match
        en_lower = en_name.lower()
        base_lower = base_name.lower()
        for key, cn in self.npc_names.items():
            key_lower = key.lower()
            if key_lower == en_lower or key_lower == base_lower:
                return cn
        
        # 4. Partial match (for names with extra context)
        for key, cn in self.npc_names.items():
            key_base = self._strip_suffix(key)
            if key_base.lower() == base_lower:
                return cn
        
        return None
    
    def find_cn_from_jp_mapping(self, en_name: str) -> Optional[str]:
        """
        Try to find Chinese translation from JP mapping.
        This is a heuristic - we check if the EN name appears similar to any JP entry.
        """
        base_name = self._strip_suffix(en_name)
        base_lower = base_name.lower()
        
        for jp, cn in self.npc_names_jp.items():
            # Case-insensitive match
            if base_lower == jp.lower():
                return cn
            # Check if JP name is romanization of EN name
            jp_normalized = jp.replace('・', ' ').replace('＝', ' ')
            if base_lower == jp_normalized.lower():
                return cn
        return None
    
    def _is_japanese(self, text: str) -> bool:
        """Check if text contains Japanese characters (hiragana/katakana)."""
        import re
        # Hiragana: \u3040-\u309f, Katakana: \u30a0-\u30ff
        return bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text))
    
    def _is_english(self, text: str) -> bool:
        """Check if text is primarily ASCII/English."""
        import re
        # Check if mostly ASCII letters
        ascii_chars = len(re.findall(r'[a-zA-Z]', text))
        return ascii_chars > len(text) * 0.5
    
    def lookup_jp_name(self, jp_name: str) -> Optional[str]:
        """Lookup Chinese name from Japanese name."""
        if not jp_name:
            return None
        
        # Exact match
        if jp_name in self.npc_names_jp:
            return self.npc_names_jp[jp_name]
        
        # Try without separators
        jp_clean = jp_name.replace('・', '').replace('＝', '').replace(' ', '')
        for key, cn in self.npc_names_jp.items():
            key_clean = key.replace('・', '').replace('＝', '').replace(' ', '')
            if key_clean == jp_clean:
                return cn
        
        return None
    
    def smart_lookup(self, name: str, fallback_format: bool = False) -> Optional[str]:
        """
        Smart name lookup - detects language and uses appropriate mapping.
        - Japanese (katakana/hiragana) -> use JP->CN mapping
        - English (ASCII) -> use EN->CN mapping (includes added_en_mapping)
        
        Args:
            name: The name to look up
            fallback_format: If True and not found, return "EN/JP" format for name_fixer
        
        Returns:
            Chinese name if found, or "EN/JP" format if fallback_format=True, else None
        """
        if not name:
            return None
        
        # Detect language and use appropriate mapping
        if self._is_japanese(name):
            # Japanese name -> JP mapping
            result = self.lookup_jp_name(name)
            if result:
                return result
        
        if self._is_english(name):
            # English name -> EN mapping (includes added_en_mapping)
            result = self.lookup_cn_name(name)
            if result:
                return result
        
        # Fallback: try both mappings
        result = self.lookup_cn_name(name)
        if result:
            return result
        
        result = self.lookup_jp_name(name)
        if result:
            return result
        
        # Not found - return fallback format if requested
        if fallback_format:
            return name  # Keep original, name_fixer will handle it
        
        return None
    
    def translate_name_with_fallback(self, name: str) -> str:
        """
        Translate name with fallback to original if not found.
        Used in story translation where we want to keep the name visible.
        """
        result = self.smart_lookup(name)
        return result if result else name
    
    def get_cn_to_en_mapping(self) -> Dict[str, str]:
        return {cn: en for en, cn in self.npc_names.items()}
    
    def get_en_to_cn_mapping(self) -> Dict[str, str]:
        return dict(self.npc_names)
    
    def apply_caiyun_prefix(self, text: str) -> str:
        """Apply Caiyun preprocessing (before translation)."""
        for original, replacement in self.caiyun_prefixes.items():
            text = text.replace(original, replacement)
        return text
    
    def apply_pre_translation(self, text: str) -> str:
        """Apply terminology substitution (before translation)."""
        # Apply caiyun-prefix first
        text = self.apply_caiyun_prefix(text)
        # Then apply noun replacements
        for original, replacement in self.nouns.items():
            text = text.replace(original, replacement)
        for en, cn in self.npc_names.items():
            text = text.replace(en, cn)
        return text
    
    def apply_post_translation(self, text: str) -> str:
        """Apply post-translation fixes."""
        for wrong, correct in self.noun_fixes.items():
            text = text.replace(wrong, correct)
        return text
    
    def apply_translation(self, text: str, phase: str = "pre") -> str:
        """
        Unified interface for BLHXFY translation processing.
        
        Args:
            text: Text to process
            phase: "pre" = Pre-translation processing (terminology substitution)
                   "post" = Post-translation processing (error correction)
        
        Returns:
            Processed text
        """
        if phase == "pre":
            return self.apply_pre_translation(text)
        elif phase == "post":
            return self.apply_post_translation(text)
        else:
            return text
    
    def translate_speaker_name(self, name: str) -> str:
        """Translate English character name to Chinese."""
        return self.npc_names.get(name, name)
    
    def resolve_character_name(self, query: str) -> Dict[str, Any]:
        cn_to_en = self.get_cn_to_en_mapping()
        
        if query in cn_to_en:
            return {
                "original_query": query,
                "official_name": cn_to_en[query],
                "confidence": 0.98,
                "source": "blhxfy_official"
            }
        
        for cn, en in cn_to_en.items():
            if query in cn or cn in query:
                return {
                    "original_query": query,
                    "official_name": en,
                    "confidence": 0.85,
                    "source": "blhxfy_partial"
                }
        
        normalized = query.strip().title().replace(" ", "")
        return {
            "original_query": query,
            "official_name": normalized,
            "confidence": 0.3,
            "source": "normalized"
        }


# Singleton instance
translator = BLHXFYTranslator()

