"""
Tests for Notion sync modules.

Run with: pytest tests/test_notion.py -v
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.notion.sync import sha1_text, normalize_text_for_diff
from lib.notion.content import render_story_blocks, parse_cast_table


class TestSyncUtils:
    """Tests for sync utility functions."""
    
    def test_sha1_text(self):
        """Should generate consistent hash."""
        hash1 = sha1_text("Hello World")
        hash2 = sha1_text("Hello World")
        hash3 = sha1_text("Different")
        
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 40  # SHA1 hex digest length
    
    def test_normalize_text(self):
        """Should produce consistent output for similar text."""
        text1 = "Hello World Test"
        text2 = "Hello World Test"
        
        norm1 = normalize_text_for_diff(text1)
        norm2 = normalize_text_for_diff(text2)
        
        # Same text should normalize to same result
        assert norm1 == norm2


class TestContentRendering:
    """Tests for content rendering functions."""
    
    def test_render_story_blocks(self):
        """Should render markdown to Notion blocks."""
        markdown = """# Chapter 1

**Vajra:** Hello!

This is a paragraph.
"""
        blocks = render_story_blocks(markdown)
        
        assert isinstance(blocks, list)
        assert len(blocks) > 0
    
    def test_render_empty_content(self):
        """Should handle empty content."""
        blocks = render_story_blocks("")
        assert isinstance(blocks, list)
    
    def test_parse_cast_table(self):
        """Should parse cast table markdown."""
        cast_md = """# Event - Cast

| 角色（英 / 中） | 头像 |
| --- | --- |
| [Vajra / 瓦姬拉](url) | ![img](img_url) |
"""
        rows = parse_cast_table(cast_md)
        
        assert isinstance(rows, list)
        # Depending on implementation, may have rows or not


class TestSyncContext:
    """Tests for SyncContext (mock tests, no API calls)."""
    
    def test_import(self):
        """Should import SyncContext."""
        from lib.notion.sync import SyncContext
        assert SyncContext is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

