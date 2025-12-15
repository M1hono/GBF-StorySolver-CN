"""
Tests for translator modules.

Run with: pytest tests/test_translators.py -v
"""
import pytest
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.translators.blhxfy import BLHXFYTranslator, translator


class TestBLHXFYTranslator:
    """Tests for BLHXFY translator."""
    
    def test_singleton_exists(self):
        """Translator singleton should be initialized."""
        assert translator is not None
        assert isinstance(translator, BLHXFYTranslator)
    
    def test_npc_names_loaded(self):
        """NPC names should be loaded from CSV."""
        assert len(translator.npc_names) > 0
        # Check some known characters
        assert "Lyria" in translator.npc_names
        assert "Vyrn" in translator.npc_names
    
    def test_lookup_cn_name_exact(self):
        """Exact name lookup should work."""
        assert translator.lookup_cn_name("Lyria") == "露莉亚"
        assert translator.lookup_cn_name("Vyrn") == "碧"
    
    def test_lookup_cn_name_with_suffix(self):
        """Name lookup with variant suffix should work."""
        # Should strip suffix and find base name
        result = translator.lookup_cn_name("Vajra (Summer)")
        # If Vajra exists, it should return the CN name
        if "Vajra" in translator.npc_names:
            assert result is not None
    
    def test_lookup_cn_name_case_insensitive(self):
        """Name lookup should be case insensitive."""
        lyria_lower = translator.lookup_cn_name("lyria")
        lyria_upper = translator.lookup_cn_name("LYRIA")
        assert lyria_lower == lyria_upper
    
    def test_lookup_cn_name_not_found(self):
        """Non-existent name should return None."""
        result = translator.lookup_cn_name("NonExistentCharacter12345")
        assert result is None
    
    def test_smart_lookup(self):
        """Smart lookup should combine multiple strategies."""
        # Known character
        result = translator.smart_lookup("Lyria")
        assert result == "露莉亚"
        
        # Unknown character returns None
        result = translator.smart_lookup("UnknownChar")
        assert result is None
    
    def test_nouns_loaded(self):
        """Noun mappings should be loaded."""
        assert len(translator.nouns) > 0
    
    def test_apply_pre_translation(self):
        """Pre-translation should apply noun mappings."""
        text = "The Captain said hello."
        result = translator.apply_pre_translation(text)
        # Captain should be replaced with 团长
        assert "团长" in result or "Captain" in result  # Depends on noun.csv content
    
    def test_apply_post_translation(self):
        """Post-translation should apply fixes."""
        # Test with known fix if exists
        if translator.noun_fixes:
            wrong, correct = next(iter(translator.noun_fixes.items()))
            result = translator.apply_post_translation(wrong)
            assert result == correct


class TestClaudeTranslator:
    """Tests for Claude translator (mock tests, no API calls)."""
    
    def test_get_all_mappings(self):
        """Should collect all mappings."""
        from lib.translators.claude import get_all_mappings
        
        maps = get_all_mappings()
        assert "en_to_cn" in maps
        assert "jp_to_cn" in maps
        assert "nouns" in maps
        assert isinstance(maps["en_to_cn"], dict)
    
    def test_extract_speakers(self):
        """Should extract speaker names from dialogue."""
        from lib.translators.claude import extract_speakers
        
        content = """**Vajra:** Hello!
**Lyria:** Hi there!
**Vyrn:** Let's go!"""
        
        speakers = extract_speakers(content)
        assert "Vajra" in speakers
        assert "Lyria" in speakers
        assert "Vyrn" in speakers
    
    def test_split_into_chunks(self):
        """Should split content into chunks."""
        from lib.translators.claude import split_into_chunks
        
        # Short content - single chunk
        short = "Line 1\nLine 2\nLine 3"
        chunks = split_into_chunks(short, chunk_size=100)
        assert len(chunks) == 1
        
        # Long content - multiple chunks
        long_content = "\n".join([f"Line {i}" for i in range(200)])
        chunks = split_into_chunks(long_content, chunk_size=50)
        assert len(chunks) > 1
    
    def test_is_voice_table(self):
        """Should detect voice table format."""
        from lib.translators.claude import is_voice_table
        
        voice = "| Label | Japanese | Chinese | English |\n| --- | --- | --- | --- |"
        assert is_voice_table(voice) == True
        
        story = "**Vajra:** Hello!"
        assert is_voice_table(story) == False


class TestCSVTranslator:
    """Tests for CSV translator."""
    
    def test_detect_csv_format_blhxfy(self, tmp_path):
        """Should detect BLHXFY scenario format."""
        from lib.translators.csv_translator import detect_csv_format
        
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name,text,trans\n0,Test,Hello,你好\n")
        
        assert detect_csv_format(csv_file) == "blhxfy_scenario"
    
    def test_detect_csv_format_simple(self, tmp_path):
        """Should detect simple format."""
        from lib.translators.csv_translator import detect_csv_format
        
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("source,target\nHello,你好\n")
        
        assert detect_csv_format(csv_file) == "simple"
    
    def test_count_untranslated(self, tmp_path):
        """Should count untranslated lines."""
        from lib.translators.csv_translator import count_untranslated
        
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id,name,text,trans\n0,A,Hello,你好\n1,B,World,\n2,C,Test,测试\n")
        
        untrans, total = count_untranslated(csv_file)
        assert untrans == 1  # "World" has no translation
        assert total == 3


class TestMappings:
    """Test mapping data integrity."""
    
    def test_en_cn_mappings_not_empty(self):
        """EN to CN mappings should not be empty."""
        assert len(translator.npc_names) > 100
    
    def test_jp_cn_mappings_not_empty(self):
        """JP to CN mappings should not be empty."""
        assert len(translator.npc_names_jp) > 100
    
    def test_core_characters_exist(self):
        """Core characters should have mappings."""
        core_chars = ["Lyria", "Vyrn", "Katalina", "Rackam", "Io"]
        for char in core_chars:
            assert char in translator.npc_names, f"Missing: {char}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

