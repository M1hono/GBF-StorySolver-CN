"""
Scenario CSV extractor - Extract translated stories from CSV files.

Extracts dialogue from BLHXFY-format CSV files and outputs readable markdown.

Usage:
    from lib.extractors.scenario import ScenarioExtractor
    
    ext = ScenarioExtractor()
    
    # Direct path - any CSV folder works
    ext.extract("/path/to/csv/folder", "output/")
    
    # Multiple folders
    ext.batch_extract([
        "folder1",
        "folder2",
    ], "output/")
"""
import os
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    from ..translators.blhxfy import translator
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from translators.blhxfy import translator


@dataclass
class DialogueLine:
    """Single line of dialogue."""
    id: str
    speaker_jp: str
    speaker_cn: str
    text_jp: str
    text_cn: str


class ScenarioExtractor:
    """
    Extract translated scenarios from CSV files.
    
    Logic:
    1. Use Chinese translation (trans column) if available
    2. If only Japanese (text column), apply name mappings
    3. Output clean readable markdown
    """
    
    def __init__(self):
        self.translator = translator
    
    def _parse_speaker(self, name_field: str) -> Tuple[str, str]:
        """
        Parse speaker name field.
        Format: "JP名/CN名" or just "JP名"
        
        Returns: (jp_name, cn_name)
        """
        if not name_field:
            return ("", "")
        
        if "/" in name_field:
            parts = name_field.split("/", 1)
            return (parts[0].strip(), parts[1].strip())
        
        # Only JP name - try to find CN mapping
        jp_name = name_field.strip()
        cn_name = self.translator.smart_lookup(jp_name)
        
        if not cn_name:
            cn_name = self.translator.npc_names_jp.get(jp_name)
        
        return (jp_name, cn_name or jp_name)
    
    def _apply_mappings(self, text: str) -> str:
        """Apply name/noun mappings to text."""
        if not text:
            return text
        
        result = text
        
        # JP->CN name mappings
        for jp, cn in self.translator.npc_names_jp.items():
            result = result.replace(jp, cn)
        
        # Noun mappings
        for jp, cn in self.translator.nouns.items():
            result = result.replace(jp, cn)
        
        return result
    
    def _parse_csv(self, csv_path: Path) -> List[DialogueLine]:
        """Parse CSV file into dialogue lines."""
        lines = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    line_id = row.get('id', '')
                    name = row.get('name', '')
                    text_jp = row.get('text', '')
                    text_cn = row.get('trans', '')
                    
                    speaker_jp, speaker_cn = self._parse_speaker(name)
                    
                    # Priority: Chinese > Japanese with mappings
                    if text_cn:
                        final_text = text_cn
                    elif text_jp:
                        final_text = self._apply_mappings(text_jp)
                    else:
                        continue
                    
                    final_text = final_text.replace('\\n', '\n')
                    
                    lines.append(DialogueLine(
                        id=line_id,
                        speaker_jp=speaker_jp,
                        speaker_cn=speaker_cn,
                        text_jp=text_jp.replace('\\n', '\n') if text_jp else '',
                        text_cn=final_text
                    ))
        
        except Exception as e:
            print(f"  Error: {csv_path.name} - {e}")
        
        return lines
    
    def _clean_text(self, text: str) -> str:
        """Remove HTML tags and clean text."""
        if not text:
            return text
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up multiple spaces/newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def _to_markdown(self, lines: List[DialogueLine]) -> str:
        """Convert dialogue lines to markdown."""
        md = []
        
        for line in lines:
            speaker = line.speaker_cn or line.speaker_jp
            text = self._clean_text(line.text_cn)
            
            if not text:
                continue
            
            # Join multi-line text into single line
            text_joined = ' '.join(t.strip() for t in text.split('\n') if t.strip())
            
            if speaker:
                # Dialogue: **Speaker:** text
                md.append(f"**{speaker}:** {text_joined}")
            else:
                # Narration: *text*
                md.append(f"*{text_joined}*")
            
            md.append("")
        
        return '\n'.join(md)
    
    def _sort_files(self, files: List[Path]) -> List[Path]:
        """Sort CSV files by scene order."""
        def key(f: Path) -> Tuple:
            m = re.search(r'cp(\d+)_q(\d+)_s(\d+)', f.stem)
            if m:
                return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            nums = re.findall(r'\d+', f.stem)
            return tuple(int(n) for n in nums[:3]) if nums else (999,)
        
        return sorted(files, key=key)
    
    def extract(
        self, 
        source: str, 
        output: str,
        combined: bool = False
    ) -> Dict:
        """
        Extract scenario from CSV folder.
        
        Args:
            source: Path to CSV folder (absolute or relative)
            output: Output folder path
            combined: True = single file, False = per-CSV files
        
        Returns:
            {"success": bool, "files": int, "lines": int}
        """
        source_path = Path(source)
        output_path = Path(output)
        
        if not source_path.exists():
            print(f"Not found: {source_path}")
            return {"success": False, "error": "Not found"}
        
        csv_files = list(source_path.glob("*.csv"))
        if not csv_files:
            print(f"No CSV files: {source_path}")
            return {"success": False, "error": "No CSV files"}
        
        csv_files = self._sort_files(csv_files)
        print(f"Processing {len(csv_files)} files from {source_path.name}")
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        total_lines = 0
        all_lines = []
        
        for csv_file in csv_files:
            lines = self._parse_csv(csv_file)
            total_lines += len(lines)
            
            if not combined and lines:
                md = self._to_markdown(lines)
                out = output_path / f"{csv_file.stem}.md"
                out.write_text(md, encoding='utf-8')
            
            all_lines.extend(lines)
        
        if combined and all_lines:
            md = self._to_markdown(all_lines)
            out = output_path / f"{source_path.name}.md"
            out.write_text(md, encoding='utf-8')
        
        print(f"  -> {total_lines} lines extracted")
        return {"success": True, "files": len(csv_files), "lines": total_lines}
    
    def batch_extract(
        self,
        sources: List[str],
        output_base: str,
        **kwargs
    ) -> Dict:
        """
        Extract multiple scenarios.
        
        Args:
            sources: List of CSV folder paths
            output_base: Base output directory
        """
        results = {"success": 0, "failed": 0}
        
        for src in sources:
            src_path = Path(src)
            out = Path(output_base) / src_path.name
            
            result = self.extract(src, str(out), **kwargs)
            
            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract translated scenarios from CSV")
    parser.add_argument("source", help="CSV folder path")
    parser.add_argument("-o", "--output", default="story/translated", help="Output folder")
    parser.add_argument("--combined", action="store_true", help="Output single file")
    
    args = parser.parse_args()
    
    ext = ScenarioExtractor()
    ext.extract(args.source, args.output, combined=args.combined)
