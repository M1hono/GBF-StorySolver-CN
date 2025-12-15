#!/usr/bin/env python3
"""
Batch processing for multiple characters.

Usage:
    # Process multiple characters from config
    python -m lib.batch process --config batch.json
    
    # Quick batch with inline list
    python -m lib.batch extract --chars "Vajra,Kumbhira,Vikala" --type lore
    python -m lib.batch translate --chars "Vajra,Kumbhira" --type voice
"""
import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    from .extractors import StoryExtractor, CastExtractor, VoiceExtractor, LoreExtractor
    from .translators import translate_directory
    from .utils.logger import get_logger
except ImportError:
    from extractors import StoryExtractor, CastExtractor, VoiceExtractor, LoreExtractor
    from translators import translate_directory
    from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CharacterConfig:
    """Configuration for a single character."""
    name: str
    wiki_name: str  # Name as it appears on wiki
    events: List[str] = None  # Event slugs for story extraction
    output_dir: str = None


@dataclass
class BatchResult:
    """Result of batch operation."""
    character: str
    operation: str
    success: bool
    details: Dict = None
    error: str = None


def load_batch_config(config_path: Path) -> List[CharacterConfig]:
    """
    Load batch configuration from JSON file.
    
    Expected format:
    {
        "characters": [
            {
                "name": "vajra",
                "wiki_name": "Vajra",
                "events": ["Auld_Lang_Fry_PREMIUM", "ZodiaCamp"],
                "output_dir": "characters/vajra"
            }
        ]
    }
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    characters = []
    for char in data.get("characters", []):
        characters.append(CharacterConfig(
            name=char["name"],
            wiki_name=char.get("wiki_name", char["name"]),
            events=char.get("events", []),
            output_dir=char.get("output_dir", f"characters/{char['name']}")
        ))
    
    return characters


def extract_character(
    char: CharacterConfig,
    content_type: Literal["story", "cast", "voice", "lore", "all"],
    headless: bool = True
) -> List[BatchResult]:
    """Extract content for a single character."""
    results = []
    output_dir = Path(char.output_dir)
    
    if content_type in ("voice", "all"):
        logger.info(f"[{char.name}] Extracting voice...")
        try:
            ext = VoiceExtractor(headless=headless)
            result = ext.extract(char.wiki_name, str(output_dir))
            results.append(BatchResult(
                character=char.name,
                operation="voice",
                success=result.get("success", False),
                details=result
            ))
        except Exception as e:
            logger.error(f"[{char.name}] Voice extraction failed: {e}")
            results.append(BatchResult(
                character=char.name,
                operation="voice",
                success=False,
                error=str(e)
            ))
    
    if content_type in ("lore", "all"):
        logger.info(f"[{char.name}] Extracting lore...")
        try:
            ext = LoreExtractor(headless=headless)
            result = ext.extract(char.wiki_name, str(output_dir))
            results.append(BatchResult(
                character=char.name,
                operation="lore",
                success=result.get("success", False),
                details=result
            ))
        except Exception as e:
            logger.error(f"[{char.name}] Lore extraction failed: {e}")
            results.append(BatchResult(
                character=char.name,
                operation="lore",
                success=False,
                error=str(e)
            ))
    
    if content_type in ("story", "cast", "all") and char.events:
        for event in char.events:
            if content_type in ("story", "all"):
                logger.info(f"[{char.name}] Extracting story: {event}")
                try:
                    ext = StoryExtractor(headless=headless)
                    result = ext.extract(event, str(output_dir))
                    results.append(BatchResult(
                        character=char.name,
                        operation=f"story:{event}",
                        success=result.get("success", False),
                        details=result
                    ))
                except Exception as e:
                    results.append(BatchResult(
                        character=char.name,
                        operation=f"story:{event}",
                        success=False,
                        error=str(e)
                    ))
            
            if content_type in ("cast", "all"):
                logger.info(f"[{char.name}] Extracting cast: {event}")
                try:
                    ext = CastExtractor(headless=headless)
                    result = ext.extract(event, str(output_dir))
                    results.append(BatchResult(
                        character=char.name,
                        operation=f"cast:{event}",
                        success=result.get("success", False),
                        details=result
                    ))
                except Exception as e:
                    results.append(BatchResult(
                        character=char.name,
                        operation=f"cast:{event}",
                        success=False,
                        error=str(e)
                    ))
    
    return results


def translate_character(
    char: CharacterConfig,
    content_type: Literal["story", "voice", "lore", "all"],
    mode: str = "prompt"
) -> List[BatchResult]:
    """Translate content for a single character."""
    results = []
    output_dir = Path(char.output_dir)
    
    translations = []
    if content_type in ("voice", "all"):
        translations.append(("voice", output_dir / "voice" / "raw", output_dir / "voice" / "trans"))
    if content_type in ("lore", "all"):
        translations.append(("lore", output_dir / "lore" / "raw", output_dir / "lore" / "trans"))
    if content_type in ("story", "all") and char.events:
        for event in char.events:
            event_slug = event.lower().replace(" ", "_")
            translations.append((
                f"story:{event}",
                output_dir / "story" / event_slug / "raw",
                output_dir / "story" / event_slug / "trans"
            ))
    
    for name, raw_dir, trans_dir in translations:
        if not raw_dir.exists():
            logger.warning(f"[{char.name}] Raw dir not found: {raw_dir}")
            continue
        
        logger.info(f"[{char.name}] Translating {name}...")
        try:
            result = translate_directory(str(raw_dir), str(trans_dir), mode=mode)
            results.append(BatchResult(
                character=char.name,
                operation=f"translate:{name}",
                success=result.get("failed", 0) == 0,
                details=result
            ))
        except Exception as e:
            logger.error(f"[{char.name}] Translation failed: {e}")
            results.append(BatchResult(
                character=char.name,
                operation=f"translate:{name}",
                success=False,
                error=str(e)
            ))
    
    return results


def batch_extract(
    characters: List[CharacterConfig],
    content_type: str,
    headless: bool = True,
    parallel: bool = False
) -> List[BatchResult]:
    """
    Extract content for multiple characters.
    
    Args:
        characters: List of character configurations
        content_type: Type of content to extract
        headless: Run browser in headless mode
        parallel: Run extractions in parallel (not recommended for Playwright)
    """
    all_results = []
    
    iterator = characters
    if HAS_TQDM:
        iterator = tqdm(characters, desc="Extracting", unit="char")
    
    for char in iterator:
        results = extract_character(char, content_type, headless)
        all_results.extend(results)
    
    return all_results


def batch_translate(
    characters: List[CharacterConfig],
    content_type: str,
    mode: str = "prompt",
    parallel: bool = True,
    max_workers: int = 2
) -> List[BatchResult]:
    """
    Translate content for multiple characters.
    
    Args:
        characters: List of character configurations
        content_type: Type of content to translate
        mode: Translation mode (prompt/replace)
        parallel: Run translations in parallel
        max_workers: Number of parallel workers
    """
    all_results = []
    
    if parallel and len(characters) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(translate_character, char, content_type, mode): char
                for char in characters
            }
            
            iterator = as_completed(futures)
            if HAS_TQDM:
                iterator = tqdm(iterator, total=len(futures), desc="Translating", unit="char")
            
            for future in iterator:
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception as e:
                    char = futures[future]
                    logger.error(f"[{char.name}] Translation failed: {e}")
    else:
        iterator = characters
        if HAS_TQDM:
            iterator = tqdm(characters, desc="Translating", unit="char")
        
        for char in iterator:
            results = translate_character(char, content_type, mode)
            all_results.extend(results)
    
    return all_results


def print_results(results: List[BatchResult]) -> None:
    """Print batch results summary."""
    success = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    
    print(f"\n{'='*50}")
    print(f"Batch Complete: {success} success, {failed} failed")
    print(f"{'='*50}")
    
    if failed > 0:
        print("\nFailed operations:")
        for r in results:
            if not r.success:
                print(f"  [{r.character}] {r.operation}: {r.error}")


def main():
    parser = argparse.ArgumentParser(description="Batch processing for GBF content")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract content")
    extract_parser.add_argument("--config", help="Batch config JSON file")
    extract_parser.add_argument("--chars", help="Comma-separated character names")
    extract_parser.add_argument("--type", default="all", 
                                choices=["story", "cast", "voice", "lore", "all"])
    extract_parser.add_argument("--no-headless", action="store_true")
    
    # Translate command
    trans_parser = subparsers.add_parser("translate", help="Translate content")
    trans_parser.add_argument("--config", help="Batch config JSON file")
    trans_parser.add_argument("--chars", help="Comma-separated character names")
    trans_parser.add_argument("--type", default="all",
                             choices=["story", "voice", "lore", "all"])
    trans_parser.add_argument("--mode", default="prompt", choices=["prompt", "replace"])
    trans_parser.add_argument("--parallel", action="store_true")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Build character list
    if args.config:
        characters = load_batch_config(Path(args.config))
    elif args.chars:
        names = [n.strip() for n in args.chars.split(",")]
        characters = [
            CharacterConfig(
                name=n.lower(),
                wiki_name=n,
                output_dir=f"characters/{n.lower()}"
            )
            for n in names
        ]
    else:
        print("Error: Provide --config or --chars")
        return
    
    logger.info(f"Processing {len(characters)} characters")
    
    if args.command == "extract":
        results = batch_extract(
            characters,
            args.type,
            headless=not args.no_headless
        )
    elif args.command == "translate":
        results = batch_translate(
            characters,
            args.type,
            mode=args.mode,
            parallel=args.parallel
        )
    
    print_results(results)


if __name__ == "__main__":
    main()

