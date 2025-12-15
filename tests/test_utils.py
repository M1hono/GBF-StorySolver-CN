"""
Tests for utility modules.

Run with: pytest tests/test_utils.py -v
"""
import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfig:
    """Tests for configuration module."""
    
    def test_paths_exist(self):
        """Config paths should be defined."""
        from lib.utils.config import SCRIPT_DIR, LIB_DIR, REPO_ROOT
        
        assert SCRIPT_DIR is not None
        assert LIB_DIR is not None
        assert REPO_ROOT is not None
    
    def test_local_data_dir_exists(self):
        """Local data directory should exist."""
        from lib.utils.config import LOCAL_DATA_DIR
        
        assert Path(LOCAL_DATA_DIR).exists()
    
    def test_blhxfy_dirs_exist(self):
        """BLHXFY directories should exist."""
        from lib.utils.config import LOCAL_BLHXFY_DIR, LOCAL_BLHXFY_ETC
        
        assert Path(LOCAL_BLHXFY_DIR).exists()
        assert Path(LOCAL_BLHXFY_ETC).exists()
    
    def test_api_key_from_env(self):
        """API key should be readable from environment."""
        from lib.utils.config import CLAUDE_API_KEY
        
        # Should have a value (either from .env or hardcoded default)
        assert CLAUDE_API_KEY is not None
        assert len(CLAUDE_API_KEY) > 0


class TestLogger:
    """Tests for logging module."""
    
    def test_get_logger(self):
        """Should create logger instance."""
        from lib.utils.logger import get_logger
        
        logger = get_logger("test")
        assert logger is not None
    
    def test_logger_namespace(self):
        """Logger should be in lib namespace."""
        from lib.utils.logger import get_logger
        
        logger = get_logger("mymodule")
        assert logger.name.startswith("lib")
    
    def test_configure_root_logger(self):
        """Should configure root logger without error."""
        from lib.utils.logger import configure_root_logger
        import logging
        
        configure_root_logger(level=logging.DEBUG, verbose=True)
        
        root = logging.getLogger('lib')
        assert root.level == logging.DEBUG
    
    def test_convenience_functions(self):
        """Convenience logging functions should work."""
        from lib.utils.logger import info, debug, warning, error
        
        # These should not raise
        info("Test info message")
        debug("Test debug message")
        warning("Test warning message")
        # Don't test error to avoid noise in test output


class TestUpdateBLHXFY:
    """Tests for BLHXFY update module."""
    
    def test_paths_defined(self):
        """Update module paths should be defined."""
        from lib.update_blhxfy import LIB_DIR, LOCAL_DATA_DIR, BLHXFY_DIR
        
        assert LIB_DIR is not None
        assert LOCAL_DATA_DIR is not None
        assert BLHXFY_DIR is not None
    
    def test_check_status_runs(self):
        """Status check should run without error."""
        from lib.update_blhxfy import check_status
        
        # Should not raise
        check_status()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

