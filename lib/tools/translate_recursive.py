import os
from pathlib import Path
from lib.translators.gemini import translate_file

def translate_recursive(input_dir, output_dir):
    input_p = Path(input_dir)
    output_p = Path(output_dir)
    
    files = list(input_p.rglob("*.md"))
    print(f"Total files found: {len(files)}")
    
    # Sort files to ensure stable order
    files.sort()
    
    for i, md_file in enumerate(files):
        rel_path = md_file.relative_to(input_p)
        output_file = output_p / rel_path
        
        # Skip if output already exists (optional, but good for resuming)
        # if output_file.exists():
        #     print(f"[{i+1}/{len(files)}] Skipping (already exists): {rel_path}")
        #     continue
            
        print(f"\n[{i+1}/{len(files)}] Translating: {rel_path}")
        translate_file(str(md_file), str(output_file))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python lib/tools/translate_recursive.py <input_dir> <output_dir>")
        sys.exit(1)
    translate_recursive(sys.argv[1], sys.argv[2])

