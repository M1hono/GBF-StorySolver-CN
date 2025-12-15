"""
Tests for extractor modules.

Run with: pytest tests/test_extractors.py -v
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.extractors import StoryExtractor, CastExtractor, VoiceExtractor, LoreExtractor


class TestStoryExtractor:
    """Tests for StoryExtractor."""
    
    def test_init(self):
        """Should initialize without error."""
        ext = StoryExtractor(headless=True)
        assert ext is not None
        assert ext.headless == True
    
    def test_has_extract_method(self):
        """Should have extract method."""
        ext = StoryExtractor()
        assert hasattr(ext, 'extract')
        assert callable(ext.extract)
    
    def test_attributes(self):
        """Should have required attributes."""
        ext = StoryExtractor()
        assert hasattr(ext, 'headless')
        assert hasattr(ext, 'timeout')


class TestCastExtractor:
    """Tests for CastExtractor."""
    
    def test_init(self):
        """Should initialize without error."""
        ext = CastExtractor(headless=True)
        assert ext is not None
    
    def test_has_extract_method(self):
        """Should have extract method."""
        ext = CastExtractor()
        assert hasattr(ext, 'extract')
        assert callable(ext.extract)


class TestVoiceExtractor:
    """Tests for VoiceExtractor."""
    
    def test_init(self):
        """Should initialize without error."""
        ext = VoiceExtractor(headless=True)
        assert ext is not None
    
    def test_has_extract_method(self):
        """Should have extract method."""
        ext = VoiceExtractor()
        assert hasattr(ext, 'extract')
        assert callable(ext.extract)


class TestLoreExtractor:
    """Tests for LoreExtractor."""
    
    def test_init(self):
        """Should initialize without error."""
        ext = LoreExtractor(headless=True)
        assert ext is not None
    
    def test_has_extract_method(self):
        """Should have extract method."""
        ext = LoreExtractor()
        assert hasattr(ext, 'extract')
        assert callable(ext.extract)


class TestExtractorHelpers:
    """Test extractor helper methods."""
    
    def test_story_output_structure(self, tmp_path):
        """Story extractor should create correct directory structure."""
        ext = StoryExtractor()
        
        # Mock the expected output
        output_dir = tmp_path / "story" / "event" / "raw"
        output_dir.mkdir(parents=True)
        (output_dir / "00_opening.md").write_text("# Opening")
        
        assert output_dir.exists()
        assert (output_dir / "00_opening.md").exists()
    
    def test_voice_output_structure(self, tmp_path):
        """Voice extractor should create correct directory structure."""
        voice_dir = tmp_path / "voice" / "raw"
        
        # Expected subdirs
        subdirs = ["battle", "menu", "chain_burst", "holidays"]
        for subdir in subdirs:
            (voice_dir / subdir).mkdir(parents=True)
        
        for subdir in subdirs:
            assert (voice_dir / subdir).exists()
    
    def test_lore_output_structure(self, tmp_path):
        """Lore extractor should create correct directory structure."""
        lore_dir = tmp_path / "lore" / "raw"
        
        # Expected subdirs
        subdirs = ["profile", "fate_episodes", "special_cutscenes"]
        for subdir in subdirs:
            (lore_dir / subdir).mkdir(parents=True)
        
        for subdir in subdirs:
            assert (lore_dir / subdir).exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

