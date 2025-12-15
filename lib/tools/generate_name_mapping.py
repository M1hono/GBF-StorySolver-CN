"""
Convert JP->CN mappings to EN->CN mappings.
Translates Japanese names to English and validates Chinese names.

Features:
1. Use Google Translate to convert JP names to EN
2. Validate CN names against cn_character_names.txt
3. Search scenario CSVs for JP/CN patterns (e.g., サルナーン/萨鲁纳恩)

Usage:
    python -m lib.tools.generate_name_mapping convert    # Convert all JP->CN to EN->CN
    python -m lib.tools.generate_name_mapping export     # Export to added_en_mapping.csv
    python -m lib.tools.generate_name_mapping stats      # Show statistics
"""

import os
import re
import csv
import json
import time
from pathlib import Path
from typing import Dict, Set, Optional, List, Tuple


class JPToENConverter:
    """Convert JP->CN mappings to EN->CN mappings."""
    
    def __init__(self):
        self.jp_to_cn: Dict[str, str] = {}
        self.en_to_cn: Dict[str, str] = {}
        self.valid_cn_names: Set[str] = set()
        self.scenario_cn_cache: Dict[str, str] = {}  # JP -> CN from scenarios
        self._load_data()
        self._build_scenario_cache()
    
    def _load_data(self):
        """Load all data files."""
        base = Path(__file__).parent.parent / "local_data" / "blhxfy" / "etc"
        
        # Load JP -> CN
        jp_file = base / "npc-name-jp.csv"
        if jp_file.exists():
            with open(jp_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('name') and row.get('trans'):
                        self.jp_to_cn[row['name']] = row['trans']
            print(f"Loaded {len(self.jp_to_cn)} JP->CN mappings")
        
        # Load existing EN -> CN
        en_file = base / "npc-name-en.csv"
        if en_file.exists():
            with open(en_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('name') and row.get('trans'):
                        self.en_to_cn[row['name']] = row['trans']
            print(f"Loaded {len(self.en_to_cn)} existing EN->CN mappings")
        
        # Load valid CN character names
        cn_file = Path(__file__).parent.parent / "local_data" / "cn_character_names.txt"
        if cn_file.exists():
            content = cn_file.read_text(encoding='utf-8')
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    self.valid_cn_names.add(line)
            print(f"Loaded {len(self.valid_cn_names)} valid CN names")
    
    def _build_scenario_cache(self):
        """Build cache of JP->CN from scenario CSV files by searching for JP/CN patterns."""
        scenario_dirs = [
            Path(__file__).parent.parent / "local_data" / "blhxfy" / "scenario",
        ]
        
        # Pattern: Japanese name followed by / and Chinese name
        # e.g., サルナーン/萨鲁纳恩 or ヴィカラ/碧卡拉
        pattern = re.compile(r'([ァ-ヶー・]+)/([^\s/,，。！？\n]+)')
        
        csv_count = 0
        for base_dir in scenario_dirs:
            if not base_dir.exists():
                continue
            
            for csv_file in base_dir.rglob("*.csv"):
                try:
                    with open(csv_file, 'r', encoding='utf-8-sig') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        for jp, cn in matches:
                            # Validate: CN should contain Chinese characters
                            if re.search(r'[\u4e00-\u9fff]', cn) and len(cn) >= 2:
                                if jp not in self.scenario_cn_cache:
                                    self.scenario_cn_cache[jp] = cn
                    csv_count += 1
                except Exception:
                    continue
        
        print(f"Scanned {csv_count} scenario CSVs, found {len(self.scenario_cn_cache)} JP/CN patterns")
    
    def translate_jp_to_en(self, jp_name: str) -> Optional[str]:
        """Translate Japanese name to English."""
        try:
            from googletrans import Translator
            translator = Translator()
            result = translator.translate(jp_name, src='ja', dest='en')
            return result.text
        except Exception as e:
            return None
    
    def lookup_cn_from_scenario(self, jp_name: str) -> Optional[str]:
        """Look up CN name from scenario cache."""
        # Exact match
        if jp_name in self.scenario_cn_cache:
            return self.scenario_cn_cache[jp_name]
        
        # Try without common suffixes/variations
        for jp, cn in self.scenario_cn_cache.items():
            if jp in jp_name or jp_name in jp:
                return cn
        
        return None
    
    def is_valid_cn_name(self, cn_name: str) -> bool:
        """Check if CN name exists in the valid names list."""
        if cn_name in self.valid_cn_names:
            return True
        # Also check without common suffixes
        for suffix in ['（活动）', '（夏日）', '（圣诞）', '（万圣）', '（情人节）']:
            if cn_name.endswith(suffix):
                base = cn_name[:-len(suffix)]
                if base in self.valid_cn_names:
                    return True
        return False
    
    def get_cn_name(self, jp_name: str, cn_from_jp_mapping: str) -> Tuple[str, str]:
        """
        Get validated CN name.
        Returns (cn_name, source) where source is 'valid', 'scenario', or 'invalid'
        """
        # First check if it's in valid list
        if self.is_valid_cn_name(cn_from_jp_mapping):
            return cn_from_jp_mapping, 'valid'
        
        # Try to find from scenario
        scenario_cn = self.lookup_cn_from_scenario(jp_name)
        if scenario_cn and self.is_valid_cn_name(scenario_cn):
            return scenario_cn, 'scenario'
        
        # Use scenario CN even if not in valid list (might be a valid name)
        if scenario_cn:
            return scenario_cn, 'scenario_unverified'
        
        # Return original but mark as invalid
        return cn_from_jp_mapping, 'invalid'
    
    def convert_all(self, output_file: Path = None, delay: float = 0.3) -> Dict[str, dict]:
        """Convert all JP->CN mappings to EN->CN."""
        if output_file is None:
            output_file = Path(__file__).parent / "jp_to_en_mapping.json"
        
        # Load existing progress
        results = {}
        if output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"Resuming from {len(results)} existing entries")
        
        total = len(self.jp_to_cn)
        processed = 0
        
        for jp_name, cn_name in self.jp_to_cn.items():
            processed += 1
            
            # Skip if already processed
            if jp_name in results:
                continue
            
            # Translate JP to EN
            en_name = self.translate_jp_to_en(jp_name)
            
            # Get validated CN name
            final_cn, source = self.get_cn_name(jp_name, cn_name)
            
            results[jp_name] = {
                'en': en_name,
                'cn': final_cn if source != 'invalid' else '',
                'cn_original': cn_name,
                'source': source
            }
            
            if en_name:
                status = '✓' if source in ['valid', 'scenario'] else '?' if source == 'scenario_unverified' else '✗'
                print(f"[{processed}/{total}] {status} {jp_name} -> {en_name} -> {final_cn} ({source})")
            else:
                print(f"[{processed}/{total}] ✗ {jp_name} -> ? (translation failed)")
            
            # Save progress periodically
            if processed % 50 == 0:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"  === Saved progress ({processed}/{total}) ===")
            
            # Rate limiting
            time.sleep(delay)
        
        # Final save
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n=== Conversion complete: {len(results)} entries ===")
        return results
    
    def export_csv(self, json_file: Path = None, csv_file: Path = None):
        """Export to added_en_mapping.csv (only new mappings not in npc-name-en.csv)."""
        if json_file is None:
            json_file = Path(__file__).parent / "jp_to_en_mapping.json"
        if csv_file is None:
            csv_file = Path(__file__).parent.parent / "local_data" / "blhxfy" / "etc" / "added_en_mapping.csv"
        
        if not json_file.exists():
            print(f"JSON file not found: {json_file}")
            return
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Collect valid mappings (EN->CN) that are NOT already in npc-name-en.csv
        mappings = []
        for jp, info in data.items():
            en = info.get('en')
            cn = info.get('cn')  # Empty if invalid
            
            if en and cn:  # Only include if both EN and CN are present
                # Normalize EN name for comparison
                en_normalized = en.strip()
                
                # Skip if EN name already exists in original mapping
                if en_normalized in self.en_to_cn:
                    continue
                if en_normalized.lower() in [k.lower() for k in self.en_to_cn]:
                    continue
                
                mappings.append({
                    'name': en_normalized,
                    'trans': cn,
                    'jp': jp,
                    'note': info.get('source', '')
                })
        
        # Sort by name
        mappings.sort(key=lambda x: x['name'].lower())
        
        # Write CSV
        csv_file.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            f.write("name,trans,jp,note\n")
            for m in mappings:
                # Escape commas in values
                name = m['name'].replace(',', '，')
                trans = m['trans'].replace(',', '，')
                jp = m['jp'].replace(',', '，')
                f.write(f"{name},{trans},{jp},{m['note']}\n")
        
        print(f"Exported {len(mappings)} NEW mappings to {csv_file}")
        
        # Stats
        valid_count = sum(1 for info in data.values() if info.get('cn'))
        invalid_count = sum(1 for info in data.values() if not info.get('cn'))
        existing_count = len(data) - len(mappings) - invalid_count
        
        print(f"\nStats:")
        print(f"  Total JP entries: {len(data)}")
        print(f"  Valid CN: {valid_count}")
        print(f"  Invalid/Empty CN: {invalid_count}")
        print(f"  Already in npc-name-en.csv: {existing_count}")
        print(f"  New mappings added: {len(mappings)}")
    
    def show_stats(self, json_file: Path = None):
        """Show statistics."""
        if json_file is None:
            json_file = Path(__file__).parent / "jp_to_en_mapping.json"
        
        if not json_file.exists():
            print("No conversion data found. Run 'convert' first.")
            return
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sources = {'valid': 0, 'scenario': 0, 'scenario_unverified': 0, 'invalid': 0}
        no_en = 0
        
        for info in data.values():
            source = info.get('source', 'invalid')
            sources[source] = sources.get(source, 0) + 1
            if not info.get('en'):
                no_en += 1
        
        print(f"Total: {len(data)}")
        print(f"  Valid (in cn_character_names.txt): {sources.get('valid', 0)}")
        print(f"  From scenario (verified): {sources.get('scenario', 0)}")
        print(f"  From scenario (unverified): {sources.get('scenario_unverified', 0)}")
        print(f"  Invalid (no CN found): {sources.get('invalid', 0)}")
        print(f"  No EN translation: {no_en}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    action = sys.argv[1]
    converter = JPToENConverter()
    
    if action == "convert":
        delay = float(sys.argv[2]) if len(sys.argv) > 2 else 0.3
        converter.convert_all(delay=delay)
    
    elif action == "export":
        converter.export_csv()
    
    elif action == "stats":
        converter.show_stats()
    
    elif action == "scenario":
        # Show scenario cache
        print(f"\nScenario JP/CN patterns ({len(converter.scenario_cn_cache)}):")
        for jp, cn in list(converter.scenario_cn_cache.items())[:30]:
            print(f"  {jp} -> {cn}")
        if len(converter.scenario_cn_cache) > 30:
            print(f"  ... and {len(converter.scenario_cn_cache) - 30} more")
    
    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
