#!/usr/bin/env python3
"""
Extract a character-centric GBF corpus from local BLHXFY scenario data.

This is intentionally local-first: it never machine-translates or fetches the web.
It copies authoritative translated scenario CSV data into a character folder and
also builds a speaking-only collection containing only lines spoken by the target.
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

# Allow running as `python tools/extract_character_corpus.py` from repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.extractors.scenario import DialogueLine, ScenarioExtractor
from lib.tools.find_character_stories import load_name_mappings, resolve_name
from lib.utils.config import LOCAL_BLHXFY_SCENARIO


DEFAULT_ALLOWED_CATEGORIES = {
    "活动剧情",
    "SIDE-STORY",
    "SIDE_STORY",
    "主线剧情",
    "支线剧情",
    "新手教程",
    "角色剧情",
    "SSR",
    "SR",
}


@dataclass(frozen=True)
class MatchedScenario:
    """A CSV scenario file matched by content or speaker."""

    path: Path
    category: str
    activity: str

    @property
    def activity_key(self) -> str:
        return f"{self.category}/{self.activity}" if self.activity else self.category


def normalize_text(value: str) -> str:
    """Normalize text for loose matching without destroying CJK names."""
    return re.sub(r"\s+", "", value or "").casefold()


def name_matches(value: str, names: Sequence[str]) -> bool:
    """Return True if value contains one of the target names."""
    normalized = normalize_text(value)
    return any(normalize_text(name) in normalized for name in names if name)


def build_search_names(name: str, extra_names: Iterable[str] = ()) -> List[str]:
    """Resolve EN/JP/CN names and preserve explicit aliases."""
    mappings = load_name_mappings()
    names: Set[str] = set(resolve_name(name, mappings))
    names.add(name)
    names.update(alias for alias in extra_names if alias)
    return sorted(names, key=lambda item: (len(item), item))


def scenario_activity_from_path(path: Path, scenario_root: Path) -> tuple[str, str]:
    """Return (category, activity) for a local scenario CSV path."""
    parts = path.relative_to(scenario_root).parts
    category = parts[0] if parts else "unknown"
    activity = "/".join(parts[1:-1]) if len(parts) > 2 else ""
    return category, activity


def iter_matched_scenarios(
    scenario_root: Path,
    search_names: Sequence[str],
    allowed_categories: Set[str],
) -> List[MatchedScenario]:
    """Find scenario CSV files containing any target name in content."""
    matches: List[MatchedScenario] = []

    for csv_path in scenario_root.rglob("*.csv"):
        if not csv_path.is_file():
            continue

        category, activity = scenario_activity_from_path(csv_path, scenario_root)
        if category not in allowed_categories:
            continue

        try:
            content = csv_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            content = csv_path.read_text(encoding="utf-8", errors="ignore")

        if name_matches(content, search_names):
            matches.append(MatchedScenario(csv_path, category, activity))

    return sorted(matches, key=lambda item: item.path.as_posix())


def group_by_activity(matches: Sequence[MatchedScenario]) -> Dict[str, List[MatchedScenario]]:
    """Group matched files by category/activity."""
    grouped: Dict[str, List[MatchedScenario]] = defaultdict(list)
    for match in matches:
        grouped[match.activity_key].append(match)
    return dict(sorted(grouped.items()))


def safe_folder_name(activity_key: str) -> str:
    """Create a filesystem-safe but readable folder name."""
    return activity_key.replace("/", "__").replace(":", "_").strip() or "unknown"


def extract_full_activities(
    grouped: Dict[str, List[MatchedScenario]],
    scenario_root: Path,
    character_dir: Path,
) -> List[Path]:
    """Extract complete matched activities into character story/trans folders."""
    extractor = ScenarioExtractor()
    written_dirs: List[Path] = []

    for activity_key in grouped:
        source_dir = scenario_root / activity_key
        if not source_dir.exists():
            # Some categories have empty activity; fall back to parent of file.
            source_dir = grouped[activity_key][0].path.parent

        output_dir = character_dir / "story" / safe_folder_name(activity_key) / "trans"
        result = extractor.extract(str(source_dir), str(output_dir))
        if result.get("success"):
            written_dirs.append(output_dir)

    return written_dirs


def filter_spoken_lines(lines: Sequence[DialogueLine], search_names: Sequence[str]) -> List[DialogueLine]:
    """Keep only lines whose speaker is the target character."""
    return [
        line
        for line in lines
        if name_matches(line.speaker_jp, search_names)
        or name_matches(line.speaker_cn, search_names)
    ]


def write_speaking_only_collection(
    matches: Sequence[MatchedScenario],
    character_dir: Path,
    search_names: Sequence[str],
    title: str,
) -> Path:
    """Write one aggregate markdown file containing only target-spoken lines."""
    extractor = ScenarioExtractor()
    output_path = character_dir / "speaking_only" / f"{title.lower()}_only_lines.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sections: List[str] = [
        f"# {title} 仅本人台词集合",
        "",
        "数据源：`lib/local_data/blhxfy/scenario/`",
        f"匹配名：{', '.join(search_names)}",
        "",
    ]

    total = 0
    for match in matches:
        lines = extractor._parse_csv(match.path)
        spoken = filter_spoken_lines(lines, search_names)
        if not spoken:
            continue

        total += len(spoken)
        rel_path = match.path.relative_to(Path(LOCAL_BLHXFY_SCENARIO))
        sections.append(f"## {match.activity_key} / {match.path.stem}")
        sections.append("")
        sections.append(f"来源：`{rel_path}`")
        sections.append("")
        sections.append(extractor._to_markdown(spoken).strip())
        sections.append("")

    sections.insert(4, f"台词行数：{total}")
    sections.insert(5, "")
    output_path.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return output_path


def write_manifest(
    character_dir: Path,
    title: str,
    grouped: Dict[str, List[MatchedScenario]],
    written_dirs: Sequence[Path],
    speaking_only_path: Path,
    search_names: Sequence[str],
) -> Path:
    """Write an index manifest for extracted content."""
    manifest = character_dir / "README.md"
    lines = [
        f"# {title} 内容提取索引",
        "",
        "本目录由本地 BLHXFY 数据提取生成，遵循 Local-First 数据策略。",
        "",
        f"匹配名：{', '.join(search_names)}",
        f"出场活动/剧情数：{len(grouped)}",
        f"完整剧情输出目录数：{len(written_dirs)}",
        f"仅本人台词集合：`{speaking_only_path.relative_to(character_dir)}`",
        "",
        "## 出场故事",
        "",
    ]

    for activity_key, activity_matches in grouped.items():
        output_dir = character_dir / "story" / safe_folder_name(activity_key) / "trans"
        lines.append(f"- {activity_key}")
        lines.append(f"  - 输出：`{output_dir.relative_to(character_dir)}`")
        lines.append(f"  - 命中文件数：{len(activity_matches)}")

    manifest.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return manifest


def extract_character_corpus(
    name: str,
    output: Path,
    aliases: Sequence[str],
    title: Optional[str] = None,
    scenario_root: Path = Path(LOCAL_BLHXFY_SCENARIO),
) -> Dict[str, object]:
    """Extract full matched activities and speaking-only collection."""
    display_title = title or name
    search_names = build_search_names(name, aliases)
    output.mkdir(parents=True, exist_ok=True)

    matches = iter_matched_scenarios(
        scenario_root=scenario_root,
        search_names=search_names,
        allowed_categories=DEFAULT_ALLOWED_CATEGORIES,
    )
    grouped = group_by_activity(matches)
    written_dirs = extract_full_activities(grouped, scenario_root, output)
    speaking_only_path = write_speaking_only_collection(
        matches, output, search_names, display_title
    )
    manifest = write_manifest(
        output, display_title, grouped, written_dirs, speaking_only_path, search_names
    )

    return {
        "search_names": search_names,
        "matched_files": len(matches),
        "matched_activities": len(grouped),
        "written_dirs": [str(path) for path in written_dirs],
        "speaking_only_path": str(speaking_only_path),
        "manifest": str(manifest),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract local GBF character corpus")
    parser.add_argument("name", help="Character name, e.g. Galleon")
    parser.add_argument("output", help="Character output directory, e.g. characters/galleon")
    parser.add_argument("--alias", action="append", default=[], help="Additional name alias")
    parser.add_argument("--title", help="Display title for generated markdown")
    args = parser.parse_args()

    result = extract_character_corpus(
        name=args.name,
        output=Path(args.output),
        aliases=args.alias,
        title=args.title,
    )

    print("Extraction complete")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
