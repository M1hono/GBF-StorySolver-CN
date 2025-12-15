"""
Table parsing utilities for cast and voice markdown files.
"""

from __future__ import annotations

import re


def normalize_gbf_media_url(url: str) -> str:
    """Convert GBF wiki thumbnail URL to stable FilePath URL."""
    if not url or not url.startswith("https://gbf.wiki/"):
        return url
    
    # Extract filename from various URL patterns
    patterns = [
        r"/images/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/]+)$",
        r"/images/thumb/[0-9a-f]/[0-9a-f]{2}/([^/]+)/",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return f"https://gbf.wiki/Special:FilePath/{m.group(1)}"
    return url


def parse_cast_table(content: str) -> list[dict]:
    """
    Parse cast.md table.
    
    Formats supported:
    - | [EN Name / CN Name](wiki_url) | ![alt](img_url) |
    - | Name | ![alt](img_url) |
    
    Returns list of {name, image_url, wiki_url?}
    """
    rows = []
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith('|') or '---' in line:
            continue
        
        # Skip header
        if '角色' in line or 'Name' in line or '头像' in line:
            continue
        
        # Extract image URL
        img_match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', line)
        if not img_match:
            continue
        image_url = img_match.group(1).strip()
        
        # Extract name and wiki URL
        link_match = re.search(r'\|\s*\[([^\]]+)\]\((https?://[^\s)]+)\)', line)
        if link_match:
            rows.append({
                'name': link_match.group(1).strip(),
                'wiki_url': link_match.group(2).strip(),
                'image_url': image_url,
            })
            continue
        
        # Simple name without link
        simple_match = re.search(r'^\|\s*([^|\[]+?)\s*\|', line)
        if simple_match:
            name = simple_match.group(1).strip()
            if name:
                rows.append({'name': name, 'image_url': image_url})
    
    return rows


def parse_voice_table(content: str) -> list[dict]:
    """
    Parse voice markdown table.
    
    Expected columns: Label, Japanese, Chinese, English, Audio
    Returns list of dicts with those keys.
    
    Supports:
    - Multiple rows with same Label (empty Label inherits from previous)
    - Auto-numbering for rows without Labels
    """
    rows = []
    header_found = False
    col_map = {}
    last_label = ""
    label_counter = {}
    
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            # Reset header state on non-table lines (multiple tables in one file)
            if line and not line.startswith('#'):
                header_found = False
            continue
        
        if '---' in line:
            header_found = True
            continue
        
        # Split and keep empty cells (important for column mapping)
        cells = line.split('|')
        # Remove first and last empty elements from | delimited line
        if cells and cells[0].strip() == '':
            cells = cells[1:]
        if cells and cells[-1].strip() == '':
            cells = cells[:-1]
        cells = [c.strip() for c in cells]
        
        if not cells:
            continue
        
        # Detect if this is a header row (for multi-table files)
        is_header_row = False
        temp_col_map = {}
        for i, cell in enumerate(cells):
            cl = cell.lower()
            if cl == 'label' or (cl and 'label' in cl and len(cl) < 15):
                temp_col_map['Label'] = i
                is_header_row = True
            elif 'japanese' in cl or cl == 'jp':
                temp_col_map['Japanese'] = i
                is_header_row = True
            elif 'chinese' in cl or cl == 'cn':
                temp_col_map['Chinese'] = i
                is_header_row = True
            elif 'english' in cl or cl == 'en':
                temp_col_map['English'] = i
                is_header_row = True
            elif 'audio' in cl:
                temp_col_map['Audio'] = i
                is_header_row = True
        
        # If this looks like a header row, update col_map and skip
        if is_header_row and len(temp_col_map) >= 2:
            col_map = temp_col_map
            header_found = False  # Wait for --- separator
            continue
        
        # Skip if we haven't seen the --- separator yet
        if not header_found:
            continue
        
        # Parse data row
        row = {}
        for key, idx in col_map.items():
            if idx < len(cells):
                value = cells[idx]
                if key == 'Audio':
                    m = re.search(r'\[.*?\]\((https?://[^\s)]+)\)', value)
                    if m:
                        value = m.group(1)
                    elif not value.startswith('http'):
                        value = ''
                if value:
                    row[key] = value
        
        # Need at least Japanese or Chinese or Audio content
        if row.get('Japanese') or row.get('Chinese') or row.get('Audio'):
            # Handle Label: inherit from previous or auto-generate
            if row.get('Label'):
                last_label = row['Label']
                label_counter[last_label] = 1
            elif last_label:
                # Increment counter for this label
                label_counter[last_label] = label_counter.get(last_label, 0) + 1
                row['Label'] = f"{last_label} #{label_counter[last_label]}"
            else:
                # No previous label, generate from content
                row['Label'] = (row.get('Japanese', '') or row.get('Chinese', ''))[:30] or "Voice"
            
            rows.append(row)
    
    return rows

