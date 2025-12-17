"""
Batch Translation Module - 50% Cost Savings

All major LLM APIs offer batch processing with 50% discount:
- OpenAI Batch API: 50% off, 24h turnaround
- Anthropic Message Batches: 50% off, 24h turnaround  
- Gemini Batch API: 50% off, 24h turnaround

Usage:
    # Submit batch job
    python -m lib.translators.batch_translator submit ./raw --engine openai
    
    # Check status
    python -m lib.translators.batch_translator status <batch_id>
    
    # Download results when ready
    python -m lib.translators.batch_translator download <batch_id> ./trans
"""
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")


# =============================================================================
# OPENAI BATCH API (50% discount)
# =============================================================================

def openai_create_batch_file(files: List[Path], output_path: Path) -> Path:
    """Create JSONL batch file for OpenAI."""
    from .openai_translator import build_prompt
    
    jsonl_path = output_path / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for i, file_path in enumerate(files):
            content = file_path.read_text(encoding='utf-8')
            prompt = build_prompt(content)
            
            request = {
                "custom_id": f"request-{i}-{file_path.stem}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": content}
                    ],
                    "max_tokens": 16000
                }
            }
            f.write(json.dumps(request, ensure_ascii=False) + '\n')
    
    print(f"Created batch file: {jsonl_path}")
    return jsonl_path


def openai_submit_batch(jsonl_path: Path) -> str:
    """Submit batch job to OpenAI. Returns batch_id."""
    from openai import OpenAI
    
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Upload file
    with open(jsonl_path, 'rb') as f:
        batch_file = client.files.create(file=f, purpose="batch")
    
    print(f"Uploaded file: {batch_file.id}")
    
    # Create batch
    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )
    
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.status}")
    print(f"Expected completion: within 24 hours")
    
    return batch.id


def openai_check_batch(batch_id: str) -> Dict:
    """Check batch status."""
    from openai import OpenAI
    
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    batch = client.batches.retrieve(batch_id)
    
    return {
        "id": batch.id,
        "status": batch.status,
        "created_at": batch.created_at,
        "completed_at": batch.completed_at,
        "request_counts": {
            "total": batch.request_counts.total,
            "completed": batch.request_counts.completed,
            "failed": batch.request_counts.failed
        },
        "output_file_id": batch.output_file_id
    }


def openai_download_results(batch_id: str, output_dir: Path, file_mapping: Dict[str, str]) -> int:
    """Download batch results and save to files."""
    from openai import OpenAI
    
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    batch = client.batches.retrieve(batch_id)
    
    if batch.status != "completed":
        print(f"Batch not ready. Status: {batch.status}")
        return 0
    
    if not batch.output_file_id:
        print("No output file available")
        return 0
    
    # Download results
    content = client.files.content(batch.output_file_id)
    results = content.text.strip().split('\n')
    
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    
    for line in results:
        result = json.loads(line)
        custom_id = result["custom_id"]
        
        if result["response"]["status_code"] == 200:
            translation = result["response"]["body"]["choices"][0]["message"]["content"]
            
            # Extract filename from custom_id
            filename = file_mapping.get(custom_id, f"{custom_id}.md")
            output_path = output_dir / filename
            output_path.write_text(translation, encoding='utf-8')
            count += 1
            print(f"  Saved: {output_path.name}")
    
    return count


# =============================================================================
# ANTHROPIC BATCH API (50% discount)
# =============================================================================

def claude_create_batch_requests(files: List[Path]) -> List[Dict]:
    """Create batch requests for Claude."""
    from .prompts import build_story_prompt_full, extract_speakers
    
    requests = []
    for file_path in files:
        content = file_path.read_text(encoding='utf-8')
        speakers = extract_speakers(content)
        prompt = build_story_prompt_full(content, speakers)
        
        requests.append({
            "custom_id": file_path.stem,
            "params": {
                "model": os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
                "max_tokens": 8192,
                "messages": [
                    {"role": "user", "content": f"{prompt}\n\n{content}"}
                ]
            }
        })
    
    return requests


def claude_submit_batch(requests: List[Dict]) -> str:
    """Submit batch to Anthropic. Returns batch_id."""
    import anthropic
    
    client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))
    
    batch = client.messages.batches.create(requests=requests)
    
    print(f"Batch submitted: {batch.id}")
    print(f"Status: {batch.processing_status}")
    print(f"Requests: {len(requests)}")
    
    return batch.id


def claude_check_batch(batch_id: str) -> Dict:
    """Check Claude batch status."""
    import anthropic
    
    client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))
    batch = client.messages.batches.retrieve(batch_id)
    
    return {
        "id": batch.id,
        "status": batch.processing_status,
        "created_at": batch.created_at,
        "ended_at": batch.ended_at,
        "request_counts": batch.request_counts
    }


def claude_download_results(batch_id: str, output_dir: Path) -> int:
    """Download Claude batch results."""
    import anthropic
    
    client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))
    
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            translation = result.result.message.content[0].text
            output_path = output_dir / f"{result.custom_id}.md"
            output_path.write_text(translation, encoding='utf-8')
            count += 1
            print(f"  Saved: {output_path.name}")
    
    return count


# =============================================================================
# UNIFIED INTERFACE
# =============================================================================

def submit_batch(input_dir: str, engine: str = "openai") -> str:
    """
    Submit batch translation job.
    
    Args:
        input_dir: Directory with .md files to translate
        engine: "openai" or "claude"
    
    Returns:
        batch_id for status checking
    """
    input_path = Path(input_dir)
    files = sorted(input_path.glob("*.md"))
    
    if not files:
        raise ValueError(f"No .md files in {input_dir}")
    
    print(f"Submitting {len(files)} files for batch translation ({engine})")
    print(f"💰 50% discount applies!")
    
    if engine == "openai":
        # Create temp dir for batch files
        batch_dir = input_path.parent / ".batch"
        batch_dir.mkdir(exist_ok=True)
        
        jsonl_path = openai_create_batch_file(files, batch_dir)
        batch_id = openai_submit_batch(jsonl_path)
        
        # Save file mapping
        mapping = {f"request-{i}-{f.stem}": f.name for i, f in enumerate(files)}
        mapping_path = batch_dir / f"{batch_id}_mapping.json"
        mapping_path.write_text(json.dumps(mapping), encoding='utf-8')
        
    elif engine == "claude":
        requests = claude_create_batch_requests(files)
        batch_id = claude_submit_batch(requests)
    else:
        raise ValueError(f"Unknown engine: {engine}")
    
    return batch_id


def check_status(batch_id: str, engine: str = "openai") -> Dict:
    """Check batch job status."""
    if engine == "openai":
        return openai_check_batch(batch_id)
    elif engine == "claude":
        return claude_check_batch(batch_id)
    else:
        raise ValueError(f"Unknown engine: {engine}")


def download_results(batch_id: str, output_dir: str, engine: str = "openai", input_dir: str = None) -> int:
    """Download completed batch results."""
    output_path = Path(output_dir)
    
    if engine == "openai":
        # Load file mapping
        if input_dir:
            mapping_path = Path(input_dir).parent / ".batch" / f"{batch_id}_mapping.json"
            if mapping_path.exists():
                file_mapping = json.loads(mapping_path.read_text())
            else:
                file_mapping = {}
        else:
            file_mapping = {}
        
        return openai_download_results(batch_id, output_path, file_mapping)
    elif engine == "claude":
        return claude_download_results(batch_id, output_path)
    else:
        raise ValueError(f"Unknown engine: {engine}")


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch translation with 50% discount")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Submit
    submit_parser = subparsers.add_parser("submit", help="Submit batch job")
    submit_parser.add_argument("input_dir", help="Directory with .md files")
    submit_parser.add_argument("--engine", default="openai", choices=["openai", "claude"])
    
    # Status
    status_parser = subparsers.add_parser("status", help="Check batch status")
    status_parser.add_argument("batch_id", help="Batch ID")
    status_parser.add_argument("--engine", default="openai", choices=["openai", "claude"])
    
    # Download
    download_parser = subparsers.add_parser("download", help="Download results")
    download_parser.add_argument("batch_id", help="Batch ID")
    download_parser.add_argument("output_dir", help="Output directory")
    download_parser.add_argument("--engine", default="openai", choices=["openai", "claude"])
    download_parser.add_argument("--input-dir", help="Original input dir (for file mapping)")
    
    args = parser.parse_args()
    
    if args.command == "submit":
        batch_id = submit_batch(args.input_dir, args.engine)
        print(f"\n✅ Batch submitted: {batch_id}")
        print(f"Check status with: python -m lib.translators.batch_translator status {batch_id}")
        
    elif args.command == "status":
        status = check_status(args.batch_id, args.engine)
        print(f"\nBatch Status:")
        print(f"  ID: {status['id']}")
        print(f"  Status: {status['status']}")
        if 'request_counts' in status:
            print(f"  Requests: {status['request_counts']}")
        
    elif args.command == "download":
        count = download_results(args.batch_id, args.output_dir, args.engine, args.input_dir)
        print(f"\n✅ Downloaded {count} files to {args.output_dir}")

