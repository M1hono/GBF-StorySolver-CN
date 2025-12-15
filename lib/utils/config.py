"""
Configuration and path constants for GBF tools.

Supports:
- Environment variables
- .env file (auto-loaded)
- YAML config file (optional)

Usage:
    from lib.utils.config import Config, REPO_ROOT, CLAUDE_API_KEY
    
    # Access paths
    print(REPO_ROOT)
    
    # Load custom config
    config = Config.load("config.yaml")
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any, TypedDict
from dataclasses import dataclass, field

# =============================================================================
# PATH CONSTANTS (computed at import)
# =============================================================================

SCRIPT_DIR: str = os.path.dirname(os.path.abspath(__file__))
LIB_DIR: str = os.path.dirname(SCRIPT_DIR)  # lib/
REPO_ROOT: str = os.path.dirname(LIB_DIR)   # gbf/

GBF_WIKI_BASE_URL: str = "https://gbf.wiki"


# =============================================================================
# ENV FILE LOADING
# =============================================================================

def _load_env_file(env_path: Optional[Path] = None) -> None:
    """Load .env file into environment variables."""
    if env_path is None:
        env_path = Path(REPO_ROOT) / ".env"
    
    if not env_path.exists():
        return
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)

_load_env_file()


# =============================================================================
# API KEYS
# =============================================================================

# API keys - set via .env file (sensitive, never commit)
CLAUDE_API_KEY: str = os.environ.get("CLAUDE_API_KEY", "")
CAIYUN_API_KEY: str = os.environ.get("CAIYUN_API_KEY", "")
CAIYUN_TOKEN: str = os.environ.get("CAIYUN_TOKEN", "")
NOTION_API_KEY: str = os.environ.get("NOTION_API_KEY", "")
NOTION_ROOT_PAGE_ID: str = os.environ.get("NOTION_ROOT_PAGE_ID", "")

# Default model settings (can be overridden in config.yaml)
CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
CAIYUN_MODEL: str = "general"


# =============================================================================
# DIRECTORY PATHS
# =============================================================================

LOCAL_DATA_DIR: str = os.path.join(LIB_DIR, "local_data")
LOCAL_BLHXFY_DIR: str = os.path.join(LOCAL_DATA_DIR, "blhxfy")
LOCAL_BLHXFY_ETC: str = os.path.join(LOCAL_BLHXFY_DIR, "etc")
LOCAL_BLHXFY_SCENARIO: str = os.path.join(LOCAL_BLHXFY_DIR, "scenario")

ALIAS_CACHE_FILE: str = os.path.join(LOCAL_DATA_DIR, "aliases.json")
EVENTS_DIR: str = os.path.join(LOCAL_DATA_DIR, "events")
CHARACTERS_CACHE_FILE: str = os.path.join(LOCAL_DATA_DIR, "characters.json")

BLHXFY_REPO_DIR: str = os.path.join(REPO_ROOT, "BLHXFY")
BLHXFY_DATA_DIR: str = os.path.join(BLHXFY_REPO_DIR, "data")
BLHXFY_SCENARIO_DIR: str = os.path.join(BLHXFY_DATA_DIR, "scenario")

AI_TRANSLATION_REPO_DIR: str = os.path.join(REPO_ROOT, "AI-Translation")
AI_TRANSLATION_STORY_DIR: str = os.path.join(AI_TRANSLATION_REPO_DIR, "story")


# =============================================================================
# CONFIG CLASS (for YAML support)
# =============================================================================

@dataclass
class TranslationConfig:
    """Translation settings."""
    mode: str = "prompt"  # prompt or replace
    chunk_size: int = 120
    max_tokens: int = 8192
    claude_model: str = "claude-sonnet-4-20250514"
    caiyun_model: str = "general"


@dataclass
class ExtractionConfig:
    """Extraction settings."""
    headless: bool = True
    timeout: int = 30000
    image_size: int = 200


@dataclass
class NotionConfig:
    """Notion sync settings."""
    api_key: str = ""
    force_mode: bool = False


@dataclass
class Config:
    """Main configuration class."""
    
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    notion: NotionConfig = field(default_factory=NotionConfig)
    
    # API keys
    claude_api_key: str = ""
    caiyun_api_key: str = ""
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML config file. If None, uses defaults.
        
        Returns:
            Config instance
        """
        config = cls()
        
        # Load API keys from environment
        config.claude_api_key = CLAUDE_API_KEY
        config.caiyun_api_key = CAIYUN_API_KEY
        config.notion.api_key = NOTION_API_KEY
        
        if config_path is None:
            return config
        
        path = Path(config_path)
        if not path.exists():
            return config
        
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # Translation config
            if 'translation' in data:
                t = data['translation']
                config.translation.mode = t.get('mode', config.translation.mode)
                config.translation.chunk_size = t.get('chunk_size', config.translation.chunk_size)
                config.translation.max_tokens = t.get('max_tokens', config.translation.max_tokens)
                config.translation.claude_model = t.get('claude_model', CLAUDE_MODEL)
                config.translation.caiyun_model = t.get('caiyun_model', CAIYUN_MODEL)
            
            # Extraction config
            if 'extraction' in data:
                e = data['extraction']
                config.extraction.headless = e.get('headless', config.extraction.headless)
                config.extraction.timeout = e.get('timeout', config.extraction.timeout)
                config.extraction.image_size = e.get('image_size', config.extraction.image_size)
            
            # Notion config
            if 'notion' in data:
                n = data['notion']
                config.notion.force_mode = n.get('force_mode', config.notion.force_mode)
            
        except ImportError:
            pass  # yaml not installed
        except Exception:
            pass  # ignore config errors
        
        return config
    
    def save(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        try:
            import yaml
            data = {
                'translation': {
                    'mode': self.translation.mode,
                    'chunk_size': self.translation.chunk_size,
                    'max_tokens': self.translation.max_tokens,
                    'claude_model': self.translation.claude_model,
                    'caiyun_model': self.translation.caiyun_model,
                },
                'extraction': {
                    'headless': self.extraction.headless,
                    'timeout': self.extraction.timeout,
                    'image_size': self.extraction.image_size,
                },
                'notion': {
                    'force_mode': self.notion.force_mode,
                }
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
        except ImportError:
            raise RuntimeError("PyYAML not installed. Run: pip install pyyaml")


# =============================================================================
# ENSURE DIRECTORIES EXIST
# =============================================================================

for _dir in [LOCAL_DATA_DIR, LOCAL_BLHXFY_DIR, LOCAL_BLHXFY_ETC, LOCAL_BLHXFY_SCENARIO, EVENTS_DIR]:
    os.makedirs(_dir, exist_ok=True)

