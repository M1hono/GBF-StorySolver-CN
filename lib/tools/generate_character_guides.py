#!/usr/bin/env python3
"""Generate local-first GBF character digest and act/react guide notes.

This tool intentionally summarizes from already-extracted local markdown under
characters/<character>/ and does not call translation APIs.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


def iter_markdown(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def strip_markup(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[[^\]]+\]\([^)]*\)", lambda m: m.group(0).split("]", 1)[0].lstrip("["), text)
    text = re.sub(r"[`*_>#|]", "", text)
    return text.strip()


def sentence_candidates(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        s = strip_markup(raw)
        if not s or s.startswith("---") or s.startswith("数据源"):
            continue
        if len(s) < 8:
            continue
        lines.append(s)
    return lines


def extract_speaker_lines(speaking_file: Path, limit: int = 40) -> list[str]:
    if not speaking_file.exists():
        return []
    out = []
    for line in read_text(speaking_file).splitlines():
        line = line.strip()
        if not line.startswith("**") or ":**" not in line:
            continue
        text = strip_markup(line.split(":**", 1)[1])
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def count_speaker_lines(speaking_file: Path) -> int:
    if not speaking_file.exists():
        return 0
    return sum(1 for line in read_text(speaking_file).splitlines() if line.strip().startswith("**") and ":**" in line)


def story_dirs(character_root: Path) -> list[Path]:
    story_root = character_root / "story"
    if not story_root.exists():
        return []
    return sorted(d for d in story_root.iterdir() if d.is_dir() and (d / "trans").exists())


def summarize_event(event_dir: Path, aliases: list[str]) -> dict:
    files = list(iter_markdown(event_dir / "trans"))
    hit_files = 0
    samples = []
    speaker_counter = Counter()
    for path in files:
        text = read_text(path)
        if any(a and a in text for a in aliases):
            hit_files += 1
        for line in text.splitlines():
            m = re.match(r"^\*\*([^:*]{1,40}):\*\*\s*(.+)$", line.strip())
            if m:
                speaker_counter[m.group(1).strip()] += 1
                if any(a and (a in m.group(1) or a in m.group(2)) for a in aliases) and len(samples) < 3:
                    samples.append(strip_markup(m.group(2))[:160])
            elif any(a and a in line for a in aliases) and len(samples) < 3:
                s = strip_markup(line)[:160]
                if s:
                    samples.append(s)
    return {
        "name": event_dir.name,
        "files": len(files),
        "hit_files": hit_files,
        "samples": samples,
        "top_speakers": speaker_counter.most_common(5),
    }


def classify_line(line: str) -> str:
    if any(k in line for k in ["早安", "晚安", "你好", "再见", "欢迎", "休息"]):
        return "日常问候/照护"
    if any(k in line for k in ["我", "吾", "六龙", "世界", "楔", "空之世界", "龙"]):
        return "自我认知/六龙视角"
    if any(k in line for k in ["团长", "你", "汝", "达夫", "碧"]):
        return "对他者的观察与回应"
    if any(k in line for k in ["战", "敌", "力量", "守护", "破坏", "攻击"]):
        return "行动/战斗反应"
    return "语气样本/其他"


def write_digest(character_root: Path, title: str, aliases: list[str]) -> Path:
    events = [summarize_event(d, aliases) for d in story_dirs(character_root)]
    speaking_file = character_root / "speaking_only" / f"{character_root.name}_only_lines.md"
    speaker_lines = extract_speaker_lines(speaking_file, 30)
    voice_raw = list(iter_markdown(character_root / "voice" / "raw"))
    lore_raw = list(iter_markdown(character_root / "lore" / "raw"))
    total_story_files = sum(e["files"] for e in events)
    total_hit_files = sum(e["hit_files"] for e in events)
    line_count = count_speaker_lines(speaking_file)

    content = []
    content.append(f"# {title} Story Digest")
    content.append("")
    content.append("本 digest 基于本仓库已整理的 local-first 产物生成；剧情正文优先来自 BLHXFY 本地 scenario。")
    content.append("不把 wiki raw voice/lore 称作权威中文译文；所有出场故事为名字命中启发式结果。")
    content.append("")
    content.append("## Corpus Snapshot")
    content.append(f"- 匹配名：{', '.join(aliases)}")
    content.append(f"- 出场故事目录：{len(events)}")
    content.append(f"- story/trans Markdown：{total_story_files}")
    content.append(f"- 命中 Galleon/伽莱翁/ガレヲン 的文件：{total_hit_files}")
    content.append(f"- 仅本人台词：{line_count}")
    content.append(f"- voice/raw Markdown：{len(voice_raw)}")
    content.append(f"- lore/raw Markdown：{len(lore_raw)}")
    content.append("")
    content.append("## Reading Map")
    for e in events:
        content.append(f"- {e['name']}")
        content.append(f"  - 文件数：{e['files']}；命中文件数：{e['hit_files']}")
        if e["samples"]:
            content.append(f"  - 样例：{e['samples'][0]}")
    content.append("")
    content.append("## Character Voice Digest")
    buckets=defaultdict(list)
    for line in speaker_lines:
        buckets[classify_line(line)].append(line)
    for name, lines in buckets.items():
        content.append(f"### {name}")
        for line in lines[:5]:
            content.append(f"- {line}")
        content.append("")
    content.append("## Caveats")
    content.append("- 出场故事集合来自 CSV 全文名字命中，并按 activity 输出完整目录；可能包含被提及但未实际登场的章节，也可能漏掉没有名字字符串的无声登场。")
    content.append("- 仅本人台词依赖 speaker 字段和别名覆盖；原始 speaker 缺失时可能漏收。")
    content.append("- voice/raw 与 lore/raw 来自 wiki 抽取或既有 raw，不等同于 BLHXFY 权威中文翻译。")
    path = character_root / f"{character_root.name}_story_digest.md"
    path.write_text("\n".join(content)+"\n", encoding="utf-8")
    return path


def write_act_react(character_root: Path, title: str, aliases: list[str]) -> Path:
    speaking_file = character_root / "speaking_only" / f"{character_root.name}_only_lines.md"
    lines = extract_speaker_lines(speaking_file, 120)
    buckets=defaultdict(list)
    for line in lines:
        buckets[classify_line(line)].append(line)
    content=[]
    content.append(f"# {title} Act React Guide")
    content.append("")
    content.append("用于写作、整理、二次校对时把角色行为 Act 与语言/情绪 React 对齐。基于 speaking-only 和本地剧情样本生成，不调用机翻 API。")
    content.append("")
    content.append("## Act / React Matrix")
    matrix=[
        ("照护与问候", "先确认对方状态，再给出缓慢、低压的关照", "语句短，像大地一样稳；少用夸张感叹"),
        ("观察人类/团长", "把人类行动当作值得记录的现象，而不是普通社交寒暄", "可保留少量距离感，但中文要自然"),
        ("六龙/世界尺度叙述", "反应不急，先从世界结构或职责出发", "避免中二堆词；用沉静、古老、客观的语气"),
        ("战斗/危机", "保护与压制并行，判断优先于情绪爆发", "动词简洁有重量，避免轻飘飘口号"),
        ("被触动/困惑", "先停顿、观察，再给出朴素直接的结论", "可以使用括号或短句表现内心处理"),
    ]
    content.append("| Act | React | 中文语气执行 |")
    content.append("| --- | --- | --- |")
    for row in matrix:
        content.append(f"| {row[0]} | {row[1]} | {row[2]} |")
    content.append("")
    content.append("## Evidence Lines")
    for name, vals in buckets.items():
        content.append(f"### {name}")
        for v in vals[:8]:
            content.append(f"- {v}")
        content.append("")
    content.append("## Editing Rules")
    content.append("- Galleon/伽莱翁的反应应偏慢、稳、观察式；不要写成活泼吐槽役。")
    content.append("- 遇到 Captain 一律按项目规则写作“团长”。")
    content.append("- 保留六龙的非人尺度，但中文句子要短、清楚、自然。")
    content.append("- 若原文是旁白提及而非本人发言，不要混入 speaking-only。")
    content.append("- 不确定是否本人台词时，回查 `speaking_only/galleon_only_lines.md` 和对应 story/trans 源文件。")
    path = character_root / f"{character_root.name}_act_react_guide.md"
    path.write_text("\n".join(content)+"\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate GBF character digest and act/react guide notes")
    parser.add_argument("character_root")
    parser.add_argument("--title", default="")
    parser.add_argument("--alias", action="append", default=[])
    args = parser.parse_args()
    root = Path(args.character_root)
    title = args.title or root.name.title()
    aliases = args.alias or [title]
    digest = write_digest(root, title, aliases)
    act = write_act_react(root, title, aliases)
    print(f"wrote {digest}")
    print(f"wrote {act}")


if __name__ == "__main__":
    main()
