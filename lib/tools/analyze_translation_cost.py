#!/usr/bin/env python3
"""
Translation Cost Analyzer - Estimate translation costs.

Tests translation of sample files and calculates token usage and USD costs.

Usage:
    python -m lib.tools.analyze_translation_cost
    python -m lib.tools.analyze_translation_cost --test-file path/to/file.md
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.translators.claude import split_into_chunks, extract_speakers
from lib.translators.prompts import build_story_prompt_full


# Claude Model Pricing (as of 2024-12, per million tokens)
# Source: https://www.anthropic.com/pricing
PRICING = {
    'claude-sonnet-4-20250514': {'input': 3.0, 'output': 15.0},      # 推荐
    'claude-3-5-sonnet-20241022': {'input': 3.0, 'output': 15.0},    # 备选
    'claude-3-opus-20240229': {'input': 15.0, 'output': 75.0},       # 最高质量
    'claude-3-haiku-20240307': {'input': 0.25, 'output': 1.25},      # 最便宜
}

# Default model
DEFAULT_MODEL = 'claude-sonnet-4-20250514'
INPUT_COST_PER_1M = PRICING[DEFAULT_MODEL]['input']
OUTPUT_COST_PER_1M = PRICING[DEFAULT_MODEL]['output']

# Token estimation (rough)
# 1 token ≈ 4 characters for English, ≈ 2-3 characters for Chinese
EN_CHARS_PER_TOKEN = 4
CN_CHARS_PER_TOKEN = 2.5


def estimate_tokens(text: str, is_chinese: bool = False) -> int:
    """
    Estimate token count for text.
    
    Args:
        text: Text content
        is_chinese: If True, use Chinese character ratio
    
    Returns:
        Estimated token count
    """
    chars_per_token = CN_CHARS_PER_TOKEN if is_chinese else EN_CHARS_PER_TOKEN
    return int(len(text) / chars_per_token)


def analyze_file_cost(file_path: Path, chunk_size: int = 500) -> Dict:
    """
    Analyze translation cost for a single file.
    
    Args:
        file_path: Path to markdown file
        chunk_size: Chunk size setting
    
    Returns:
        Dict with cost analysis
    """
    content = file_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # Extract speakers for prompt building
    speakers = extract_speakers(content)
    
    # Build prompt (same logic as actual translation)
    prompt = build_story_prompt_full(content, speakers)
    
    # Split into chunks
    chunks = split_into_chunks(content, chunk_size)
    
    # Calculate tokens
    prompt_tokens = estimate_tokens(prompt)
    
    total_input_tokens = 0
    total_output_tokens = 0
    
    for chunk in chunks:
        # Input: prompt + chunk content
        chunk_input_tokens = prompt_tokens + estimate_tokens(chunk)
        # Output: assume same length as input (conservative estimate)
        chunk_output_tokens = estimate_tokens(chunk, is_chinese=True)
        
        total_input_tokens += chunk_input_tokens
        total_output_tokens += chunk_output_tokens
    
    # Calculate costs
    input_cost = (total_input_tokens / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (total_output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
    total_cost = input_cost + output_cost
    
    return {
        'file': file_path.name,
        'lines': len(lines),
        'chars': len(content),
        'speakers': len(speakers),
        'chunks': len(chunks),
        'prompt_tokens': prompt_tokens,
        'input_tokens': total_input_tokens,
        'output_tokens': total_output_tokens,
        'total_tokens': total_input_tokens + total_output_tokens,
        'input_cost_usd': input_cost,
        'output_cost_usd': output_cost,
        'total_cost_usd': total_cost,
    }


def categorize_by_size(lines: int) -> str:
    """Categorize file by size."""
    if lines < 150:
        return "小型"
    elif lines < 400:
        return "中型"
    else:
        return "大型"


def analyze_story_directory(story_dir: Path, chunk_size: int = 500) -> Dict:
    """
    Analyze all story files in a directory.
    
    Args:
        story_dir: Directory containing story markdown files
        chunk_size: Chunk size setting
    
    Returns:
        Analysis summary
    """
    md_files = sorted(story_dir.glob('*.md'))
    
    if not md_files:
        return {'error': 'No markdown files found'}
    
    results = []
    totals = {
        'files': 0,
        'lines': 0,
        'chars': 0,
        'chunks': 0,
        'input_tokens': 0,
        'output_tokens': 0,
        'total_tokens': 0,
        'total_cost_usd': 0.0,
    }
    
    categories = {'小型': [], '中型': [], '大型': []}
    
    print(f"Analyzing {len(md_files)} files from {story_dir.name}...\n")
    
    for md_file in md_files:
        analysis = analyze_file_cost(md_file, chunk_size)
        results.append(analysis)
        
        # Update totals
        totals['files'] += 1
        totals['lines'] += analysis['lines']
        totals['chars'] += analysis['chars']
        totals['chunks'] += analysis['chunks']
        totals['input_tokens'] += analysis['input_tokens']
        totals['output_tokens'] += analysis['output_tokens']
        totals['total_tokens'] += analysis['total_tokens']
        totals['total_cost_usd'] += analysis['total_cost_usd']
        
        # Categorize
        category = categorize_by_size(analysis['lines'])
        categories[category].append(analysis)
    
    return {
        'results': results,
        'totals': totals,
        'categories': categories,
    }


def print_analysis(analysis: Dict) -> None:
    """Print formatted cost analysis."""
    totals = analysis['totals']
    categories = analysis['categories']
    
    print("="*70)
    print(" 翻译成本分析")
    print("="*70)
    print()
    
    # Overall stats
    print(f"文件总数: {totals['files']}")
    print(f"总行数: {totals['lines']:,}")
    print(f"总字符数: {totals['chars']:,}")
    print(f"总分块数: {totals['chunks']}")
    print()
    
    # Token breakdown
    print("Token 消耗:")
    print(f"  输入 (Input):  {totals['input_tokens']:,} tokens")
    print(f"  输出 (Output): {totals['output_tokens']:,} tokens")
    print(f"  总计:          {totals['total_tokens']:,} tokens")
    print()
    
    # Cost breakdown
    print("美元花费 (Claude Sonnet 4):")
    input_cost = (totals['input_tokens'] / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (totals['output_tokens'] / 1_000_000) * OUTPUT_COST_PER_1M
    print(f"  输入成本:  ${input_cost:.4f}")
    print(f"  输出成本:  ${output_cost:.4f}")
    print(f"  总成本:    ${totals['total_cost_usd']:.4f}")
    print()
    
    # Category analysis
    print("="*70)
    print(" 按文件大小分类")
    print("="*70)
    print()
    
    for cat_name in ['小型', '中型', '大型']:
        cat_files = categories[cat_name]
        if not cat_files:
            continue
        
        cat_total_cost = sum(f['total_cost_usd'] for f in cat_files)
        cat_avg_cost = cat_total_cost / len(cat_files) if cat_files else 0
        cat_avg_lines = sum(f['lines'] for f in cat_files) / len(cat_files) if cat_files else 0
        
        print(f"{cat_name}文件 ({len(cat_files)}个):")
        print(f"  平均行数: {cat_avg_lines:.0f}")
        print(f"  平均成本: ${cat_avg_cost:.4f}")
        print(f"  总成本:   ${cat_total_cost:.4f}")
        print()
    
    # Sample file details
    if analysis['results']:
        print("="*70)
        print(" 示例文件详细分析")
        print("="*70)
        print()
        
        for i, result in enumerate(analysis['results'][:5]):
            print(f"{i+1}. {result['file']}")
            print(f"   行数: {result['lines']}, 字符: {result['chars']:,}")
            print(f"   分块: {result['chunks']}, Prompt: {result['prompt_tokens']} tokens")
            print(f"   成本: ${result['total_cost_usd']:.4f}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze translation costs"
    )
    parser.add_argument(
        "--test-file",
        help="Test a specific file"
    )
    parser.add_argument(
        "--test-dir",
        help="Test all files in a directory"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Chunk size (default: 500)"
    )
    
    args = parser.parse_args()
    
    if args.test_file:
        # Single file analysis
        file_path = Path(args.test_file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        
        analysis = analyze_file_cost(file_path, args.chunk_size)
        
        print("="*70)
        print(f" 文件: {analysis['file']}")
        print("="*70)
        print()
        print(f"行数: {analysis['lines']}")
        print(f"字符数: {analysis['chars']:,}")
        print(f"说话者: {analysis['speakers']}")
        print(f"分块数: {analysis['chunks']}")
        print()
        print(f"Prompt tokens: {analysis['prompt_tokens']}")
        print(f"输入 tokens:   {analysis['input_tokens']:,}")
        print(f"输出 tokens:   {analysis['output_tokens']:,}")
        print(f"总 tokens:     {analysis['total_tokens']:,}")
        print()
        print(f"估算成本: ${analysis['total_cost_usd']:.4f} USD")
    
    elif args.test_dir:
        # Directory analysis
        dir_path = Path(args.test_dir)
        if not dir_path.exists():
            print(f"Error: Directory not found: {dir_path}")
            sys.exit(1)
        
        analysis = analyze_story_directory(dir_path, args.chunk_size)
        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
            sys.exit(1)
        
        print_analysis(analysis)
    
    else:
        # Default: analyze sample files
        print("请指定 --test-file 或 --test-dir")
        print()
        print("示例:")
        print("  python -m lib.tools.analyze_translation_cost --test-file characters/tikoh/story/marionette_stars/raw/01_opening.md")
        print("  python -m lib.tools.analyze_translation_cost --test-dir characters/tikoh/story/marionette_stars/raw")


if __name__ == "__main__":
    main()

