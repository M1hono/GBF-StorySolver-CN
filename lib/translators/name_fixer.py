"""
Name fixer utility.
Fixes untranslated English/Japanese names in story files using BLHXFY mappings.

The translator outputs unfound names as original text.
This fixer scans translated files and replaces remaining EN names with CN.
"""

import os
import re
from pathlib import Path
from typing import Dict, Set, Optional, List, Tuple


class NameFixer:
    """Fix untranslated English/Japanese names in story files."""
    
    def __init__(self):
        self.en_to_cn: Dict[str, str] = {}
        self.jp_to_cn: Dict[str, str] = {}
        self._load_mappings()
    
    def _load_mappings(self):
        """Load all translation mappings from BLHXFY (includes added_en_mapping.csv)."""
        try:
            from .blhxfy import translator
            # EN->CN (includes both npc-name-en.csv and added_en_mapping.csv)
            self.en_to_cn.update(translator.npc_names)
            # JP->CN
            self.jp_to_cn.update(translator.npc_names_jp)
            print(f"Loaded {len(self.en_to_cn)} EN->CN and {len(self.jp_to_cn)} JP->CN mappings")
        except ImportError:
            import csv
            base = Path(__file__).parent.parent / "local_data" / "blhxfy" / "etc"
            
            # Load EN->CN
            for csv_name in ["npc-name-en.csv", "added_en_mapping.csv"]:
                en_file = base / csv_name
                if en_file.exists():
                    with open(en_file, 'r', encoding='utf-8-sig') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row.get('name') and row.get('trans'):
                                self.en_to_cn[row['name']] = row['trans']
            
            # Load JP->CN
            jp_file = base / "npc-name-jp.csv"
            if jp_file.exists():
                with open(jp_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('name') and row.get('trans'):
                            self.jp_to_cn[row['name']] = row['trans']
    
    def _is_japanese(self, text: str) -> bool:
        """Check if text contains Japanese characters."""
        return bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text))
    
    def lookup(self, name: str) -> Optional[str]:
        """Look up Chinese name for English or Japanese name."""
        # Check if Japanese
        if self._is_japanese(name):
            # JP exact match
            if name in self.jp_to_cn:
                return self.jp_to_cn[name]
            # JP normalized match
            name_clean = name.replace('・', '').replace('＝', '')
            for jp, cn in self.jp_to_cn.items():
                if jp.replace('・', '').replace('＝', '') == name_clean:
                    return cn
            return None
        
        # English lookup
        # Exact match
        if name in self.en_to_cn:
            return self.en_to_cn[name]
        
        # Case-insensitive lookup
        name_lower = name.lower()
        for en, cn in self.en_to_cn.items():
            if en.lower() == name_lower:
                return cn
        
        # Try possessive forms (Anila's → Anila)
        if name.endswith("'s"):
            base = name[:-2]
            cn = self.lookup(base)
            if cn:
                return cn + "的"
        
        # Try "X's Voice" pattern
        if "'s Voice" in name:
            base = name.replace("'s Voice", "")
            cn = self.lookup(base)
            if cn:
                return cn + "的声音"
        
        return None
    
    def find_untranslated_names(self, text: str) -> Set[str]:
        """Find English or Japanese names that appear in speaker positions."""
        names = set()
        
        # Pattern for English: **Name:** or **Name's Voice:**
        en_pattern = r'\*\*([A-Z][a-zA-Z\' ]+?)(?:\'s Voice)?:\*\*'
        for match in re.findall(en_pattern, text):
            name = match.strip()
            if name and not self.lookup(name):
                names.add(name)
        
        # Pattern for Japanese: **カタカナ:** 
        jp_pattern = r'\*\*([ァ-ヶー・]+?):\*\*'
        for match in re.findall(jp_pattern, text):
            name = match.strip()
            if name and not self.lookup(name):
                names.add(name)
        
        return names
    
    def fix_text(self, text: str, fix_body: bool = True) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Fix untranslated English/Japanese names in text.
        
        Args:
            text: The text to fix
            fix_body: If True, also replace names in body text (not just speakers)
        
        Returns (fixed_text, list of (original, cn) replacements made).
        """
        replacements = []
        
        def replace_en_speaker(match):
            full_match = match.group(0)
            name = match.group(1).strip()
            suffix = match.group(2) if match.lastindex >= 2 else ""
            
            cn = self.lookup(name)
            if cn:
                if suffix:
                    replacements.append((name + suffix, cn + "的声音"))
                    return f"**{cn}的声音:**"
                else:
                    replacements.append((name, cn))
                    return f"**{cn}:**"
            return full_match
        
        def replace_jp_speaker(match):
            full_match = match.group(0)
            name = match.group(1).strip()
            
            cn = self.lookup(name)
            if cn:
                replacements.append((name, cn))
                return f"**{cn}:**"
            return full_match
        
        # Replace English: **Name:** and **Name's Voice:**
        en_pattern = r'\*\*([A-Z][a-zA-Z\' ]+?)(\'s Voice)?:\*\*'
        fixed = re.sub(en_pattern, replace_en_speaker, text)
        
        # Replace Japanese: **カタカナ:**
        jp_pattern = r'\*\*([ァ-ヶー・]+?):\*\*'
        fixed = re.sub(jp_pattern, replace_jp_speaker, fixed)
        
        # Also fix names in body text
        if fix_body:
            fixed, body_replacements = self._fix_body_names(fixed)
            replacements.extend(body_replacements)
        
        return fixed, replacements
    
    def _fix_body_names(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Fix English/Japanese names that appear in body text.
        Only replaces exact matches to avoid false positives.
        """
        replacements = []
        
        # Build sorted list of names (longer names first to avoid partial replacements)
        all_names = []
        for en, cn in self.en_to_cn.items():
            if len(en) >= 3:  # Skip very short names to avoid false positives
                all_names.append((en, cn, 'en'))
        for jp, cn in self.jp_to_cn.items():
            if len(jp) >= 2:
                all_names.append((jp, cn, 'jp'))
        
        # Sort by length descending
        all_names.sort(key=lambda x: len(x[0]), reverse=True)
        
        # Replace each name
        for name, cn, lang in all_names:
            if name in text:
                # Use word boundary for English names
                if lang == 'en':
                    # Match whole word only (not inside other words)
                    pattern = r'\b' + re.escape(name) + r'\b'
                    new_text = re.sub(pattern, cn, text)
                else:
                    # For Japanese, direct replacement is fine (katakana is distinct)
                    new_text = text.replace(name, cn)
                
                if new_text != text:
                    count = text.count(name) - new_text.count(name)
                    if count > 0:
                        replacements.append((name, cn))
                    text = new_text
        
        return text, replacements
    
    def fix_file(self, file_path: Path) -> Tuple[int, List[Tuple[str, str]]]:
        """
        Fix untranslated names in a file.
        Returns (number of replacements, list of (en, cn) pairs).
        """
        content = file_path.read_text(encoding='utf-8')
        fixed, replacements = self.fix_text(content)
        
        if replacements:
            file_path.write_text(fixed, encoding='utf-8')
        
        return len(replacements), replacements
    
    def fix_directory(self, dir_path: Path) -> Dict[str, List[Tuple[str, str]]]:
        """
        Fix all markdown files in a directory.
        Returns dict of {filename: [(en, cn), ...]}.
        """
        results = {}
        
        for md_file in dir_path.glob("*.md"):
            count, replacements = self.fix_file(md_file)
            if replacements:
                results[md_file.name] = replacements
                print(f"  Fixed {md_file.name}: {count} names")
        
        return results
    
    def scan_untranslated(self, dir_path: Path) -> Dict[str, Set[str]]:
        """
        Scan directory for untranslated names without fixing.
        Returns dict of {filename: set of untranslated names}.
        """
        results = {}
        
        for md_file in dir_path.glob("*.md"):
            content = md_file.read_text(encoding='utf-8')
            names = self.find_untranslated_names(content)
            if names:
                results[md_file.name] = names
        
        return results


def fix_story_names(trans_dir: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Fix untranslated English names in story translation directory.
    
    Args:
        trans_dir: Path to trans/ directory containing translated .md files
    
    Returns:
        Dict mapping filename to list of (english, chinese) replacements
    """
    print(f"Building EN→JP→CN chain lookup...")
    fixer = NameFixer()
    
    trans_path = Path(trans_dir)
    if not trans_path.exists():
        print(f"Directory not found: {trans_dir}")
        return {}
    
    print(f"\nFixing names in: {trans_dir}")
    return fixer.fix_directory(trans_path)


def scan_untranslated_names(trans_dir: str) -> Dict[str, Set[str]]:
    """
    Scan for untranslated names without fixing.
    
    Args:
        trans_dir: Path to trans/ directory
    
    Returns:
        Dict mapping filename to set of untranslated English names
    """
    fixer = NameFixer()
    trans_path = Path(trans_dir)
    
    if not trans_path.exists():
        print(f"Directory not found: {trans_dir}")
        return {}
    
    return fixer.scan_untranslated(trans_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python name_fixer.py scan <trans_dir>   - Scan for untranslated names")
        print("  python name_fixer.py fix <trans_dir>    - Fix untranslated names")
        print()
        print("Example:")
        print("  python -m lib.translators.name_fixer fix characters/vajra/story/zodiacamp/trans")
        sys.exit(1)
    
    action = sys.argv[1]
    trans_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    
    if action == "scan":
        results = scan_untranslated_names(trans_dir)
        if results:
            print("\nUntranslated names found:")
            all_names = set()
            for filename, names in results.items():
                print(f"  {filename}: {', '.join(sorted(names))}")
                all_names.update(names)
            print(f"\nTotal unique untranslated names: {len(all_names)}")
            print(f"Names: {', '.join(sorted(all_names))}")
        else:
            print("No untranslated names found!")
    
    elif action == "fix":
        results = fix_story_names(trans_dir)
        if results:
            print(f"\nFixed {sum(len(v) for v in results.values())} names in {len(results)} files")
        else:
            print("No names to fix!")
    
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)

