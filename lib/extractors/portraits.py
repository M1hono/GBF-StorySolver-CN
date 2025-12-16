#!/usr/bin/env python3
"""
Character Portrait Extractor - Download expression variants.

Downloads character portraits with various expressions from GBF game assets.
Uses GBFAL index (https://github.com/MizaGBF/GBFAL) for resource mapping.

Supported types:
- Scene portraits: Expression variants (angry, laugh, serious, etc.)
- Skycompass portraits: High-res uncap portraits (optional)

Usage:
    from lib.extractors.portraits import PortraitExtractor
    
    ext = PortraitExtractor()
    ext.download_portraits("Yuisis", "portraits/yuisis")
"""

import json
import re
import urllib.request
import ssl
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# SSL context for downloads (bypass certificate verification)
_ssl_context = ssl.create_default_context()
_ssl_context.check_hostname = False
_ssl_context.verify_mode = ssl.CERT_NONE


@dataclass
class CharacterAssets:
    """Character asset information."""
    character_id: str
    name: str
    uncaps: List[str]
    scene_suffixes: List[str]
    voice_suffixes: List[str]


class PortraitExtractor:
    """Extract character portraits with expression variants."""
    
    # CDN endpoints (use mirror for better performance)
    CDN_MIRRORS = [
        "https://prd-game-a-granbluefantasy.akamaized.net",
        "https://prd-game-a1-granbluefantasy.akamaized.net",
        "https://prd-game-a2-granbluefantasy.akamaized.net",
    ]
    
    SKYCOMPASS_BASE = "https://media.skycompass.io/assets/customizes/characters/1138x1138"
    
    def __init__(self, data_file: Optional[str] = None):
        """
        Initialize extractor.
        
        Args:
            data_file: Path to GBFAL data.json. If None, uses default location.
        """
        if data_file is None:
            from ..utils.config import LOCAL_DATA_DIR
            data_file = str(Path(LOCAL_DATA_DIR) / "gbfal_data.json")
        
        self.data_file = Path(data_file)
        self.data = None
        self.name_to_id_map = {}
        
        if self.data_file.exists():
            self._load_data()
        else:
            print(f"Warning: GBFAL data not found at {data_file}")
            print("Run: python -m lib.update_blhxfy to download")
    
    def _load_data(self) -> None:
        """Load and parse GBFAL data.json."""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        # Build name → ID mapping from lookup
        self._build_name_mapping()
    
    def _build_name_mapping(self) -> None:
        """Build character name to ID mapping from lookup field."""
        if not self.data or 'lookup' not in self.data:
            return
        
        for char_id, tags in self.data['lookup'].items():
            if not char_id.startswith('304'):  # Characters start with 304
                continue
            
            # Extract wiki name from @@Name tag
            wiki_match = re.search(r'@@([^\s]+)', tags)
            if wiki_match:
                wiki_name = wiki_match.group(1).replace('_', ' ')
                # Store both with and without spaces/underscores
                self.name_to_id_map[wiki_name.lower()] = char_id
                self.name_to_id_map[wiki_name.replace(' ', '_').lower()] = char_id
                self.name_to_id_map[wiki_name.replace(' ', '').lower()] = char_id
    
    def find_character_id(self, name: str) -> Optional[str]:
        """
        Find character ID by name.
        
        Args:
            name: Character name (English, case-insensitive)
        
        Returns:
            Character ID or None if not found
        """
        name_lower = name.lower().replace('_', ' ')
        
        # Try exact match
        if name_lower in self.name_to_id_map:
            return self.name_to_id_map[name_lower]
        
        # Try without spaces
        name_no_space = name_lower.replace(' ', '')
        if name_no_space in self.name_to_id_map:
            return self.name_to_id_map[name_no_space]
        
        # Try partial match
        for key, char_id in self.name_to_id_map.items():
            if name_lower in key or key in name_lower:
                return char_id
        
        return None
    
    def get_character_assets(self, name_or_id: str) -> Optional[CharacterAssets]:
        """
        Get character asset information.
        
        Args:
            name_or_id: Character name or ID
        
        Returns:
            CharacterAssets object or None if not found
        """
        if not self.data:
            return None
        
        # Determine if it's an ID or name
        if name_or_id.startswith('304') and len(name_or_id) == 10:
            char_id = name_or_id
        else:
            char_id = self.find_character_id(name_or_id)
        
        if not char_id or char_id not in self.data['characters']:
            return None
        
        char_data = self.data['characters'][char_id]
        if char_data == 0:
            return None
        
        # Extract asset lists
        uncaps = char_data[6] if len(char_data) > 6 else []
        scene_suffixes = char_data[7] if len(char_data) > 7 else []
        voice_suffixes = char_data[8] if len(char_data) > 8 else []
        
        return CharacterAssets(
            character_id=char_id,
            name=name_or_id,
            uncaps=uncaps,
            scene_suffixes=scene_suffixes,
            voice_suffixes=voice_suffixes
        )
    
    def download_file(self, url: str, output_path: Path) -> bool:
        """
        Download a file from URL.
        
        Args:
            url: Source URL
            output_path: Target file path
        
        Returns:
            True if successful
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use SSL context to bypass certificate verification
            with urllib.request.urlopen(url, context=_ssl_context) as response:
                data = response.read()
                output_path.write_bytes(data)
            
            return True
        except Exception as e:
            print(f"  Failed: {output_path.name} - {e}")
            return False
    
    def download_portraits(
        self,
        name: str,
        output_dir: str,
        include_skycompass: bool = False,
        prefer_up: bool = False,
        cdn_index: int = 0
    ) -> Dict[str, int]:
        """
        Download character expression portraits.
        
        Output structure:
            output_dir/
            ├── angry.png           # Expression variants
            ├── laugh.png
            ├── serious.png
            ├── shy.png
            └── ...
        
        Optional (if include_skycompass=True):
            output_dir/skycompass/
            ├── 01.png              # High-res uncap portraits
            ├── 02.png
            └── ...
        
        Args:
            name: Character name (e.g., "Yuisis", "Vajra")
            output_dir: Output directory
            include_skycompass: Also download Skycompass high-res portraits
            prefer_up: If True, only download '_up' variants when available
            cdn_index: CDN mirror index (0-2)
        
        Returns:
            Dict with download counts: {expressions, skycompass, total}
        """
        assets = self.get_character_assets(name)
        
        if not assets:
            print(f"Character not found: {name}")
            return {"skycompass": 0, "scene": 0, "navi": 0, "total": 0}
        
        print(f"Downloading portraits for {name} ({assets.character_id})")
        
        output_path = Path(output_dir)
        cdn_base = self.CDN_MIRRORS[cdn_index]
        
        stats = {"expressions": 0, "skycompass": 0, "total": 0}
        
        # 1. Scene portraits with expressions (PRIMARY)
        scene_base = f"{cdn_base}/assets_en/img/sp/quest/scene/character/body"
        
        # Filter suffixes if prefer_up is enabled
        suffixes_to_download = assets.scene_suffixes
        
        if prefer_up:
            # Group by base expression name
            from collections import defaultdict
            expression_groups = defaultdict(list)
            
            for suffix in assets.scene_suffixes:
                # Extract base expression (remove _up, _speed, numbers, etc.)
                base = re.sub(r'_up\d*|_speed|_blood|_light|\d+$', '', suffix)
                expression_groups[base].append(suffix)
            
            # For each group, prefer _up variants
            filtered_suffixes = []
            for base, variants in expression_groups.items():
                # Find _up variants
                up_variants = [v for v in variants if '_up' in v]
                if up_variants:
                    # Prefer _up2 > _up
                    up2 = [v for v in up_variants if '_up2' in v]
                    filtered_suffixes.append(up2[0] if up2 else up_variants[0])
                else:
                    # No _up variant, use first one
                    filtered_suffixes.append(variants[0])
            
            suffixes_to_download = filtered_suffixes
            print(f"\n[Expressions] Downloading {len(suffixes_to_download)} preferred variants (filtered from {len(assets.scene_suffixes)})...")
        else:
            print(f"\n[Expressions] Downloading {len(suffixes_to_download)} variants...")
        
        for suffix in suffixes_to_download:
            filename = f"{suffix or 'base'}.png".lstrip('_')
            url = f"{scene_base}/{assets.character_id}{suffix}.png"
            target = output_path / filename
            
            if self.download_file(url, target):
                stats["expressions"] += 1
                if stats["expressions"] % 10 == 0:
                    print(f"  {stats['expressions']} / {len(suffixes_to_download)}...")
        
        print(f"  ✓ Downloaded {stats['expressions']} expressions")
        
        # 2. Skycompass high-res portraits (OPTIONAL)
        if include_skycompass:
            print("\n[Skycompass] High-res uncap portraits (1138×1138)...")
            skycompass_dir = output_path / "skycompass"
            
            for uncap in assets.uncaps:
                # Extract uncap ID (e.g., "3040345000_01" → "01")
                uncap_id = uncap.split('_')[1] if '_' in uncap else "01"
                url = f"{self.SKYCOMPASS_BASE}/{uncap}.png"
                target = skycompass_dir / f"{uncap_id}.png"
                
                if self.download_file(url, target):
                    print(f"  ✓ uncap_{uncap_id}.png")
                    stats["skycompass"] += 1
        
        stats["total"] = stats["expressions"] + stats["skycompass"]
        
        print(f"\n{'='*50}")
        print(f"Downloaded {stats['total']} portraits to {output_dir}")
        print(f"  Expressions: {stats['expressions']}")
        if include_skycompass:
            print(f"  Skycompass: {stats['skycompass']}")
        
        return stats


def download_portraits(name: str, output_dir: str, include_skycompass: bool = False, prefer_up: bool = False) -> Dict:
    """
    Convenience function to download character expression portraits.
    
    Args:
        name: Character name
        output_dir: Output directory
        include_skycompass: Also download high-res uncap portraits
        prefer_up: Only download '_up' variants when available
    
    Returns:
        Download statistics
    """
    ext = PortraitExtractor()
    return ext.download_portraits(name, output_dir, include_skycompass, prefer_up)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python portraits.py <character_name> [output_dir] [--skycompass] [--prefer-up]")
        print("Example: python portraits.py Yuisis portraits/yuisis")
        print("         python portraits.py Yuisis --prefer-up  # Only download '_up' variants")
        sys.exit(1)
    
    name = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else f"portraits/{name.lower()}"
    include_skycompass = '--skycompass' in sys.argv
    prefer_up = '--prefer-up' in sys.argv
    
    stats = download_portraits(name, output_dir, include_skycompass, prefer_up)
    
    if stats["total"] == 0:
        sys.exit(1)

