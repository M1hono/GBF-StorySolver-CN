"""
Notion sync utilities.

Reusable API:
- SyncContext: manages cache, client, mode (diff/force), dry_run
- Page/database creation with caching
- Content-equality sync via hash comparison
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Callable

from notion_client import Client


def get_client(api_key: str) -> Client:
    """Create Notion client with API version 2025-09-03."""
    from notion_client.client import ClientOptions
    return Client(ClientOptions(auth=api_key, notion_version="2025-09-03"))


def sha1_text(text: str) -> str:
    """SHA1 hash of text."""
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def load_state(path: str | Path) -> dict:
    """Load cache state from JSON file."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(path: str | Path, state: dict) -> None:
    """Save cache state to JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


class SyncContext:
    """
    Centralized sync state manager.

    Usage:
        ctx = SyncContext(api_key, cache_path=".sync_cache.json", mode="diff")
        page_id = ctx.ensure_page(parent_id, "Title")
        ctx.sync_page_blocks(page_id, blocks, cache_key="story:xxx")
        ctx.save()
    """

    def __init__(
        self,
        api_key: str,
        *,
        cache_path: str | Path = ".notion_sync_cache.json",
        mode: str = "diff",
        dry_run: bool = False,
    ):
        self.client = get_client(api_key)
        self.cache_path = Path(cache_path)
        self.mode = mode
        self.dry_run = dry_run
        self._cache = load_state(self.cache_path)

    def save(self) -> None:
        save_state(self.cache_path, self._cache)

    def _get_cached(self, section: str, key: str) -> str | None:
        return self._cache.get(section, {}).get(key)

    def _set_cached(self, section: str, key: str, value: str) -> None:
        self._cache.setdefault(section, {})[key] = value

    def ensure_page(self, parent_id: str, title: str) -> str:
        """Get or create child page, with ID caching."""
        cache_key = f"{parent_id}:{title}"
        cached_id = self._get_cached("page_ids", cache_key)
        if cached_id:
            return cached_id
        page_id = ensure_page(self.client, parent_id, title)
        self._set_cached("page_ids", cache_key, page_id)
        return page_id

    def sync_page_blocks(
        self,
        page_id: str,
        blocks: list[dict],
        cache_key: str,
        *,
        block_text_fn: Callable[[list[dict]], str] | None = None,
        skip_clear: bool = False,
    ) -> bool:
        """
        Sync blocks to a page with content-equality diff.
        Returns True if updated, False if skipped.
        """
        if block_text_fn is None:
            block_text_fn = blocks_plain_text
        desired_text = normalize_text_for_diff(block_text_fn(blocks))
        desired_hash = sha1_text(desired_text)

        if self.mode != "force":
            cached_hash = self._get_cached("hashes", cache_key)
            if cached_hash == desired_hash:
                return False

        if self.dry_run:
            return False

        if not skip_clear:
            clear_page_blocks(self.client, page_id)
        append_blocks(self.client, page_id, blocks)
        self._set_cached("hashes", cache_key, desired_hash)
        return True

    def recreate_page(self, parent_id: str, title: str) -> str:
        """Delete existing page and create new one."""
        import time
        cache_key = f"{parent_id}:{title}"
        existing = get_child_block_by_title(self.client, parent_id, title)
        if existing:
            try:
                self.client.blocks.delete(block_id=existing["id"])
                time.sleep(0.2)
            except Exception:
                pass
            if "page_ids" in self._cache and cache_key in self._cache["page_ids"]:
                del self._cache["page_ids"][cache_key]
        page = self.client.pages.create(
            parent={"page_id": parent_id},
            properties={"title": {"title": [{"type": "text", "text": {"content": title}}]}},
        )
        page_id = page["id"]
        self._set_cached("page_ids", cache_key, page_id)
        return page_id


# =============================================================================
# PAGE OPERATIONS
# =============================================================================

def get_child_block_by_title(client: Client, parent_id: str, title: str) -> Optional[dict]:
    """Find child page or database by title."""
    cursor = None
    while True:
        res = client.blocks.children.list(block_id=parent_id, page_size=100, start_cursor=cursor)
        for b in res.get("results", []):
            if b.get("type") == "child_page" and b.get("child_page", {}).get("title") == title:
                return b
            if b.get("type") == "child_database" and b.get("child_database", {}).get("title") == title:
                return b
        if not res.get("has_more"):
            return None
        cursor = res.get("next_cursor")


def ensure_page(client: Client, parent_id: str, title: str) -> str:
    """Get or create a child page."""
    existing = get_child_block_by_title(client, parent_id, title)
    if existing:
        return existing["id"]
    page = client.pages.create(
        parent={"page_id": parent_id},
        properties={"title": {"title": [{"type": "text", "text": {"content": title}}]}},
    )
    return page["id"]


def clear_page_blocks(client: Client, page_id: str) -> None:
    """Delete all blocks from a page (except child pages/databases)."""
    cursor = None
    while True:
        res = client.blocks.children.list(block_id=page_id, page_size=100, start_cursor=cursor)
        for child in res.get("results", []):
            if child.get("type") in {"child_page", "child_database"}:
                continue
            try:
                client.blocks.delete(block_id=child["id"])
            except Exception:
                pass
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")


def append_blocks(client: Client, page_id: str, children: list[dict], *, chunk_size: int = 80) -> None:
    """Append blocks to a page in chunks."""
    if not children:
        return
    for i in range(0, len(children), chunk_size):
        client.blocks.children.append(block_id=page_id, children=children[i : i + chunk_size])


# =============================================================================
# DATABASE OPERATIONS (API version 2025-09-03)
# =============================================================================

def create_database_with_schema(
    client: Client,
    parent_page_id: str,
    title: str,
    properties: dict,
    *,
    is_inline: bool = True,
) -> tuple[str, str]:
    """
    Create a new database with schema using initial_data_source.
    
    Args:
        client: Notion client
        parent_page_id: Parent page ID
        title: Database title
        properties: Schema like {"Name": {"title": {}}, "Field": {"rich_text": {}}}
    
    Returns:
        (database_id, data_source_id) tuple
    """
    db = client.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": title}}],
        is_inline=is_inline,
        initial_data_source={
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        },
    )
    ds_id = db["data_sources"][0]["id"]
    return db["id"], ds_id


def get_or_create_database(
    client: Client,
    parent_page_id: str,
    title: str,
    properties: dict,
) -> tuple[str, str]:
    """
    Get existing database or create new one.
    
    Returns:
        (database_id, data_source_id) tuple
    """
    existing = get_child_block_by_title(client, parent_page_id, title)
    if existing and existing.get("type") == "child_database":
        db = client.databases.retrieve(database_id=existing["id"])
        ds_id = (db.get("data_sources") or [{}])[0].get("id", "")
        return existing["id"], ds_id
    return create_database_with_schema(client, parent_page_id, title, properties)


def query_data_source(client: Client, data_source_id: str) -> list[dict]:
    """Query all rows from a data source."""
    out = []
    cursor = None
    while True:
        kwargs = {"data_source_id": data_source_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        res = client.data_sources.query(**kwargs)
        out.extend(res.get("results") or [])
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return out


def create_database_row(client: Client, data_source_id: str, properties: dict) -> str:
    """Create a new row in a database using data_source_id."""
    page = client.pages.create(
        parent={"data_source_id": data_source_id},
        properties=properties,
    )
    return page["id"]


def update_database_row(client: Client, row_id: str, properties: dict) -> None:
    """Update an existing database row."""
    client.pages.update(page_id=row_id, properties=properties)


# =============================================================================
# TEXT UTILITIES
# =============================================================================

def normalize_text_for_diff(text: str) -> str:
    """Normalize text for content-equality diff."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    out: list[str] = []
    blank_run = 0
    for ln in lines:
        if ln == "":
            blank_run += 1
            if blank_run <= 2:
                out.append("")
            continue
        blank_run = 0
        out.append(ln)
    while len(out) > 0 and out[-1] == "":
        out.pop()
    return "\n".join(out)


def _collect_text_nodes(value: Any) -> list[str]:
    """Collect plain text from Notion structures."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        if "plain_text" in value and isinstance(value["plain_text"], str):
            return [value["plain_text"]]
        if "text" in value and isinstance(value["text"], dict):
            content = value["text"].get("content")
            if isinstance(content, str):
                return [content]
        out = []
        for k, v in value.items():
            if k in {"rich_text", "caption"} and isinstance(v, list):
                for it in v:
                    out.extend(_collect_text_nodes(it))
            else:
                out.extend(_collect_text_nodes(v))
        return out
    if isinstance(value, list):
        out = []
        for it in value:
            out.extend(_collect_text_nodes(it))
        return out
    return []


def blocks_plain_text(blocks: list[dict]) -> str:
    """Extract plain text from blocks for diff comparison."""
    parts = []
    for b in blocks:
        parts.extend(_collect_text_nodes(b))
        parts.append("\n")
    return "".join(parts)


def rich_text_plain(prop: dict) -> str:
    """Extract plain text from a rich_text property."""
    if not prop:
        return ""
    t = prop.get("type")
    items = prop.get(t) or []
    out = []
    for it in items:
        text = (it.get("text") or {}).get("content")
        if text:
            out.append(text)
    return "".join(out)
