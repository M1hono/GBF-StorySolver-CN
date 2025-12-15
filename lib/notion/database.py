"""
Database sync operations for cast and voice data.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from notion_client import Client

from .sync import (
    get_or_create_database,
    query_data_source,
    create_database_row,
    update_database_row,
    rich_text_plain,
)
from .parsers import normalize_gbf_media_url


# Database property schemas (for initial_data_source)
CAST_SCHEMA = {
    "Name": {"title": {}},
    "Portrait": {"files": {}},
    "WikiUrl": {"url": {}},
}

VOICE_SCHEMA = {
    "Label": {"title": {}},
    "Japanese": {"rich_text": {}},
    "Chinese": {"rich_text": {}},
    "English": {"rich_text": {}},
    "Audio": {"files": {}},
}


def _build_title_index(client: "Client", ds_id: str, title_prop: str = "Name") -> dict[str, str]:
    """Build index of existing rows: title -> row_id."""
    index = {}
    rows = query_data_source(client, ds_id)
    for row in rows:
        props = row.get("properties", {})
        title = rich_text_plain(props.get(title_prop, {}))
        if title:
            index[title] = row["id"]
    return index


def sync_cast_database(
    client: "Client",
    parent_id: str,
    rows: list[dict],
    *,
    cache: dict = None,
    mode: str = "diff",
    dry_run: bool = False,
) -> str:
    """
    Sync cast portraits to a Notion database.
    
    Args:
        client: Notion client
        parent_id: Parent page ID
        rows: List of {name, image_url, wiki_url?}
        cache: Optional cache dict (unused, for API compatibility)
        mode: "diff" or "force"
        dry_run: Skip actual writes
    
    Returns:
        Database ID
    """
    db_id, ds_id = get_or_create_database(client, parent_id, "Cast Portraits", CAST_SCHEMA)
    
    if dry_run:
        return db_id
    
    # Build index of existing rows
    existing = _build_title_index(client, ds_id, "Name")
    
    for row_data in rows:
        name = row_data.get('name', '')
        image_url = row_data.get('image_url', '')
        wiki_url = row_data.get('wiki_url')
        
        if not name or not image_url:
            continue
        
        stable_url = normalize_gbf_media_url(image_url)
        
        # Properties must include "type" field for data_source_id parent
        properties = {
            "Name": {"type": "title", "title": [{"type": "text", "text": {"content": name}}]},
            "Portrait": {"type": "files", "files": [{"type": "external", "name": name, "external": {"url": stable_url}}]},
        }
        if wiki_url:
            properties["WikiUrl"] = {"type": "url", "url": wiki_url}
        
        row_id = existing.get(name)
        try:
            if row_id:
                if mode != "force":
                    continue  # Skip existing in diff mode
                update_database_row(client, row_id, properties)
            else:
                create_database_row(client, ds_id, properties)
            time.sleep(0.05)
        except Exception:
            pass  # Silently continue on errors
    
    return db_id


def sync_voice_database(
    client: "Client",
    parent_id: str,
    title: str,
    voice_data: list[dict],
    *,
    cache: dict = None,
    mode: str = "diff",
    dry_run: bool = False,
) -> str:
    """
    Sync voice lines to a Notion database.
    
    Args:
        client: Notion client
        parent_id: Parent page ID
        title: Database title prefix
        voice_data: List of {Label, Japanese, Chinese, English, Audio}
        cache: Optional cache dict (unused)
        mode: "diff" or "force"
        dry_run: Skip actual writes
    
    Returns:
        Database ID
    """
    db_title = f"{title} - Voice Lines"
    db_id, ds_id = get_or_create_database(client, parent_id, db_title, VOICE_SCHEMA)
    
    if dry_run:
        return db_id
    
    existing = _build_title_index(client, ds_id, "Label")
    
    for item in voice_data:
        label = item.get("Label", "Unknown")
        if not label:
            continue
        
        audio_url = item.get("Audio", "")
        if audio_url:
            audio_url = normalize_gbf_media_url(audio_url)
        
        # Properties must include "type" field for data_source_id parent
        properties = {
            "Label": {"type": "title", "title": [{"type": "text", "text": {"content": label}}]},
        }
        
        if item.get("Japanese"):
            properties["Japanese"] = {"type": "rich_text", "rich_text": [{"type": "text", "text": {"content": item["Japanese"]}}]}
        if item.get("Chinese"):
            properties["Chinese"] = {"type": "rich_text", "rich_text": [{"type": "text", "text": {"content": item["Chinese"]}}]}
        if item.get("English"):
            properties["English"] = {"type": "rich_text", "rich_text": [{"type": "text", "text": {"content": item["English"]}}]}
        if audio_url:
            properties["Audio"] = {"type": "files", "files": [{"type": "external", "name": label, "external": {"url": audio_url}}]}
        
        row_id = existing.get(label)
        try:
            if row_id:
                if mode != "force":
                    continue
                update_database_row(client, row_id, properties)
            else:
                create_database_row(client, ds_id, properties)
            time.sleep(0.05)
        except Exception:
            pass
    
    return db_id

