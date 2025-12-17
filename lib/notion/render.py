"""
Story markdown to Notion blocks rendering.
"""

from __future__ import annotations

import re


def _rt(text: str, *, bold: bool = False, italic: bool = False, color: str = "default") -> list[dict]:
    """Build a rich_text array with optional annotations."""
    return [{
        "type": "text",
        "text": {"content": text},
        "annotations": {
            "bold": bold,
            "italic": italic,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": color,
        },
    }]


def _split_text(s: str, max_len: int = 1800) -> list[str]:
    """Split long text for Notion block limits (2000 char max)."""
    s = s.strip()
    if not s:
        return []
    out = []
    while len(s) > max_len:
        cut = s.rfind(" ", 0, max_len)
        if cut < 200:
            cut = max_len
        out.append(s[:cut].strip())
        s = s[cut:].strip()
    if s:
        out.append(s)
    return out


def render_story_blocks(content: str) -> list[dict]:
    """
    Render story markdown to Notion blocks.

    Layout:
    - Narration (*text* or before first speaker): gray italic
    - Stage direction ((...), 【...】): gray italic
    - Speaker line (**Name：** ...): H3 bold blue + normal paragraph
    - Dialogue: normal paragraph
    """
    blocks: list[dict] = []
    seen_dialogue = False

    speaker_re = re.compile(r"^\*\*(.+?)[：:]\*\*\s*(.*)$")
    title_re = re.compile(r"^(#{1,3})\s+(.+)$")

    def add_paragraph(text: str, *, italic: bool = False, color: str = "default", bold: bool = False):
        for part in _split_text(text):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _rt(part, italic=italic, color=color, bold=bold)}
            })

    for raw in content.splitlines():
        s = raw.strip()
        if not s:
            continue

        # Markdown title
        m = title_re.match(s)
        if m:
            level = min(len(m.group(1)), 3)
            htype = f"heading_{level}"
            blocks.append({
                "object": "block",
                "type": htype,
                htype: {"rich_text": _rt(m.group(2).strip(), bold=True)}
            })
            continue

        # Speaker line: **Name：** text
        m = speaker_re.match(s)
        if m:
            seen_dialogue = True
            speaker = m.group(1).strip()
            first_text = m.group(2).strip()
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": _rt(speaker, bold=True, color="blue")}
            })
            if first_text:
                add_paragraph(first_text)
            continue

        # Stage direction: (...), （...）, 【...】
        if (s.startswith("（") and s.endswith("）")) or \
           (s.startswith("(") and s.endswith(")")) or \
           (s.startswith("【") and s.endswith("】")):
            add_paragraph(s, italic=True, color="gray")
            continue

        # Narration: *text* (single asterisk, not bold)
        if s.startswith("*") and not s.startswith("**"):
            text = s.lstrip("*").rstrip("*").strip()
            if text:
                add_paragraph(text, italic=True, color="gray")
            continue

        # Pre-dialogue narration
        if not seen_dialogue:
            add_paragraph(s, italic=True, color="gray")
            continue

        # Normal dialogue
        add_paragraph(s)

    return blocks


def render_profile_blocks(content: str) -> list[dict]:
    """
    Render profile markdown to Notion blocks.
    
    Profile format:
        **Key**: Value
    
    Renders as:
        Key (bold) + : + Value (normal)
    """
    blocks: list[dict] = []
    title_re = re.compile(r"^(#{1,3})\s+(.+)$")
    profile_re = re.compile(r"^\*\*(.+?)\*\*:\s*(.*)$")
    
    for raw in content.splitlines():
        s = raw.strip()
        if not s:
            continue
        
        # Markdown title
        m = title_re.match(s)
        if m:
            level = min(len(m.group(1)), 3)
            htype = f"heading_{level}"
            blocks.append({
                "object": "block",
                "type": htype,
                htype: {"rich_text": _rt(m.group(2).strip(), bold=True)}
            })
            continue
        
        # Data source link
        if s.startswith("数据源："):
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _rt(s, italic=True, color="gray")}
            })
            continue
        
        # Profile entry: **Key**: Value
        m = profile_re.match(s)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            
            # Build rich_text with bold key and normal value
            rich_text = [
                {
                    "type": "text",
                    "text": {"content": key},
                    "annotations": {"bold": True, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
                },
                {
                    "type": "text",
                    "text": {"content": f": {value}"},
                    "annotations": {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False, "color": "default"}
                }
            ]
            
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": rich_text}
            })
            continue
        
        # Other lines (description, etc.)
        if s:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _rt(s)}
            })
    
    return blocks

