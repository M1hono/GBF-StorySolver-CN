"""
CSV Translation Tool for BLHXFY scenario files.

Translates Japanese text in CSV files to Chinese.
Supports two formats:
- BLHXFY scenario: id,name,text,trans
- Simple: jp_text,cn_text
"""
import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import anthropic

try:
    from .blhxfy import translator
    from ..utils.config import CLAUDE_API_KEY
except ImportError:
    import os
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from blhxfy import BLHXFYTranslator
    translator = BLHXFYTranslator()
    CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, timeout=180.0)


# =============================================================================
# CSV DETECTION
# =============================================================================

def detect_csv_format(file_path: Path) -> Optional[str]:
    """
    Detect CSV format type.
    
    Returns:
        "blhxfy_scenario": id,name,text,trans format
        "simple": jp,cn format
        None: Unknown format
    """
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            
            if not headers:
                return None
            
            headers_lower = [h.lower().strip() for h in headers]
            
            # BLHXFY scenario format
            if 'id' in headers_lower and 'text' in headers_lower and 'trans' in headers_lower:
                return "blhxfy_scenario"
            
            # Simple JP/CN format
            if len(headers) >= 2:
                return "simple"
            
            return None
    except Exception:
        return None


def count_untranslated(file_path: Path) -> Tuple[int, int]:
    """
    Count untranslated lines in CSV.
    
    Returns:
        (untranslated_count, total_count)
    """
    fmt = detect_csv_format(file_path)
    if not fmt:
        return (0, 0)
    
    untranslated = 0
    total = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if fmt == "blhxfy_scenario":
                    if row.get('id', '').lower() == 'info':
                        continue
                    text = row.get('text', '').strip()
                    trans = row.get('trans', '').strip()
                    if text and not trans:
                        untranslated += 1
                    if text:
                        total += 1
                else:
                    # Simple format - first column is source
                    keys = list(row.keys())
                    if len(keys) >= 2:
                        src = row.get(keys[0], '').strip()
                        tgt = row.get(keys[1], '').strip()
                        if src and not tgt:
                            untranslated += 1
                        if src:
                            total += 1
    except Exception:
        pass
    
    return (untranslated, total)


# =============================================================================
# TRANSLATION
# =============================================================================

def build_csv_translate_prompt() -> str:
    """Build prompt for CSV translation."""
    return """你是《碧蓝幻想》(Granblue Fantasy)专业翻译。将日文翻译成自然流畅的简体中文。

## 术语对照
- 団長 → 团长
- 騎空団 → 骑空团
- 騎空士 → 骑空士
- 星晶獣 → 星晶兽
- ルリア → 露莉亚
- ビィ → 碧
- カタリナ → 卡塔莉娜

## 格式要求
- 保留 <br> 换行标签
- 保留标点符号风格
- 对话要口语化

输入格式：JSON {"0": "日文1", "1": "日文2", ...}
输出格式：JSON {"0": "中文1", "1": "中文2", ...}

直接输出JSON，不要添加说明。"""


def batch_translate_jp_texts(texts: List[str], batch_size: int = 20) -> Dict[int, str]:
    """Batch translate Japanese texts to Chinese."""
    if not texts:
        return {}
    
    all_translations = {}
    prompt = build_csv_translate_prompt()
    
    for batch_start in range(0, len(texts), batch_size):
        batch_end = min(batch_start + batch_size, len(texts))
        batch = texts[batch_start:batch_end]
        
        input_json = {str(i): t for i, t in enumerate(batch)}
        
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.1,
                system=prompt,
                messages=[{"role": "user", "content": json.dumps(input_json, ensure_ascii=False)}]
            )
            
            result_text = response.content[0].text.strip()
            
            # Extract JSON from response
            if '{' in result_text:
                json_str = result_text[result_text.index('{'):result_text.rindex('}')+1]
                parsed = json.loads(json_str)
                
                for local_idx, translation in parsed.items():
                    global_idx = batch_start + int(local_idx)
                    all_translations[global_idx] = translation
                    
        except Exception as e:
            print(f"      Batch translation error: {e}")
    
    return all_translations


def translate_csv_file(
    input_file: Path, 
    output_file: Optional[Path] = None,
    overwrite: bool = False
) -> Dict:
    """
    Translate a single CSV file.
    
    Args:
        input_file: Source CSV file
        output_file: Output file (None = overwrite input)
        overwrite: If True, overwrite existing translations
    
    Returns:
        {"success": bool, "translated": int, "total": int, "error": str?}
    """
    if output_file is None:
        output_file = input_file
    
    fmt = detect_csv_format(input_file)
    if not fmt:
        return {"success": False, "error": "Unknown CSV format"}
    
    # Read CSV
    rows = []
    headers = None
    texts_to_translate = []
    text_indices = []
    
    try:
        with open(input_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            
            if not headers:
                return {"success": False, "error": "Empty CSV"}
            
            for row_idx, row in enumerate(reader):
                rows.append(list(row))
                
                if fmt == "blhxfy_scenario":
                    # Check if this row needs translation
                    if len(row) >= 4:
                        row_id = row[0].strip().lower()
                        text = row[2].strip() if len(row) > 2 else ""
                        trans = row[3].strip() if len(row) > 3 else ""
                        
                        if row_id != 'info' and text and (not trans or overwrite):
                            texts_to_translate.append(text)
                            text_indices.append(row_idx)
                else:
                    # Simple format
                    if len(row) >= 2:
                        src = row[0].strip()
                        tgt = row[1].strip()
                        if src and (not tgt or overwrite):
                            texts_to_translate.append(src)
                            text_indices.append(row_idx)
    
    except Exception as e:
        return {"success": False, "error": f"Read error: {e}"}
    
    if not texts_to_translate:
        return {"success": True, "translated": 0, "total": len(rows), "message": "No translation needed"}
    
    # Translate
    print(f"    Translating {len(texts_to_translate)} lines...")
    translations = batch_translate_jp_texts(texts_to_translate)
    
    # Apply translations
    translated_count = 0
    for local_idx, (row_idx, text) in enumerate(zip(text_indices, texts_to_translate)):
        if local_idx in translations:
            trans = translations[local_idx]
            if fmt == "blhxfy_scenario":
                # Ensure row has enough columns
                while len(rows[row_idx]) < 4:
                    rows[row_idx].append("")
                rows[row_idx][3] = trans
            else:
                while len(rows[row_idx]) < 2:
                    rows[row_idx].append("")
                rows[row_idx][1] = trans
            translated_count += 1
    
    # Write output
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
    except Exception as e:
        return {"success": False, "error": f"Write error: {e}"}
    
    return {
        "success": True, 
        "translated": translated_count, 
        "total": len(rows),
        "file": str(output_file)
    }


def translate_csv_directory(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    overwrite: bool = False,
    only_untranslated: bool = True
) -> Dict:
    """
    Translate all CSV files in a directory.
    
    Args:
        input_dir: Source directory
        output_dir: Output directory (None = in-place)
        overwrite: Overwrite existing translations
        only_untranslated: Only process files with untranslated content
    
    Returns:
        {"success": int, "failed": int, "skipped": int, "files": list}
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir) if output_dir else input_path
    
    results = {"success": 0, "failed": 0, "skipped": 0, "files": []}
    
    csv_files = list(input_path.rglob("*.csv"))
    print(f"Found {len(csv_files)} CSV files")
    
    for i, csv_file in enumerate(csv_files):
        rel_path = csv_file.relative_to(input_path)
        out_file = output_path / rel_path
        
        # Check if translation needed
        if only_untranslated:
            untrans, total = count_untranslated(csv_file)
            if untrans == 0:
                results["skipped"] += 1
                continue
            print(f"[{i+1}/{len(csv_files)}] {rel_path} ({untrans}/{total} untranslated)")
        else:
            print(f"[{i+1}/{len(csv_files)}] {rel_path}")
        
        result = translate_csv_file(csv_file, out_file, overwrite)
        
        if result.get("success"):
            results["success"] += 1
            results["files"].append({
                "file": str(rel_path),
                "translated": result.get("translated", 0)
            })
        else:
            results["failed"] += 1
            print(f"    Error: {result.get('error')}")
    
    return results


# =============================================================================
# ANALYSIS
# =============================================================================

def analyze_csv_directory(dir_path: Path) -> Dict:
    """
    Analyze CSV files in directory.
    
    Returns:
        {
            "total_files": int,
            "total_lines": int,
            "untranslated_lines": int,
            "fully_translated": int,
            "partially_translated": int,
            "not_translated": int,
            "files": [...]
        }
    """
    result = {
        "total_files": 0,
        "total_lines": 0,
        "untranslated_lines": 0,
        "fully_translated": 0,
        "partially_translated": 0,
        "not_translated": 0,
        "files": []
    }
    
    for csv_file in Path(dir_path).rglob("*.csv"):
        untrans, total = count_untranslated(csv_file)
        
        result["total_files"] += 1
        result["total_lines"] += total
        result["untranslated_lines"] += untrans
        
        if total == 0:
            continue
        elif untrans == 0:
            result["fully_translated"] += 1
        elif untrans == total:
            result["not_translated"] += 1
        else:
            result["partially_translated"] += 1
            result["files"].append({
                "file": str(csv_file.relative_to(dir_path)),
                "untranslated": untrans,
                "total": total
            })
    
    return result


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Translate BLHXFY CSV files")
    parser.add_argument("command", choices=["translate", "analyze"], help="Command to run")
    parser.add_argument("path", help="File or directory path")
    parser.add_argument("-o", "--output", help="Output path (optional)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing translations")
    
    args = parser.parse_args()
    path = Path(args.path)
    
    if args.command == "analyze":
        if path.is_dir():
            result = analyze_csv_directory(path)
            print(f"\nCSV Analysis: {path}")
            print("=" * 50)
            print(f"Total files: {result['total_files']}")
            print(f"Total lines: {result['total_lines']}")
            print(f"Untranslated lines: {result['untranslated_lines']}")
            print(f"Fully translated: {result['fully_translated']}")
            print(f"Partially translated: {result['partially_translated']}")
            print(f"Not translated: {result['not_translated']}")
            
            if result['files']:
                print(f"\nFiles needing translation:")
                for f in result['files'][:20]:
                    print(f"  {f['file']}: {f['untranslated']}/{f['total']}")
                if len(result['files']) > 20:
                    print(f"  ... and {len(result['files']) - 20} more")
        else:
            untrans, total = count_untranslated(path)
            print(f"{path}: {untrans}/{total} untranslated")
    
    elif args.command == "translate":
        output = Path(args.output) if args.output else None
        
        if path.is_file():
            result = translate_csv_file(path, output, args.overwrite)
            print(f"Result: {result}")
        else:
            result = translate_csv_directory(path, output, args.overwrite)
            print(f"\nDone: {result['success']} success, {result['failed']} failed, {result['skipped']} skipped")

