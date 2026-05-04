"""Tests for local character corpus extraction helpers."""

import csv
from pathlib import Path

from lib.tools.extract_character_corpus import (
    filter_spoken_lines,
    iter_matched_scenarios,
    name_matches,
)
from lib.extractors.scenario import DialogueLine


def test_name_matches_handles_aliases_and_whitespace():
    assert name_matches(" ガレヲン / 伽莱翁 ", ["伽莱翁"])
    assert name_matches("Galleon", ["galleon"])
    assert not name_matches("威尔纳斯", ["伽莱翁", "Galleon"])


def test_filter_spoken_lines_only_keeps_target_speaker():
    lines = [
        DialogueLine("1", "ガレヲン", "伽莱翁", "jp", "你好"),
        DialogueLine("2", "ビィ", "碧", "jp", "不是本人"),
        DialogueLine("3", "", "伽莱翁", "jp", "中文名匹配"),
    ]

    spoken = filter_spoken_lines(lines, ["伽莱翁", "ガレヲン"])

    assert [line.id for line in spoken] == ["1", "3"]


def test_iter_matched_scenarios_searches_local_csv_content(tmp_path: Path):
    scenario_root = tmp_path / "scenario"
    activity_dir = scenario_root / "活动剧情" / "测试活动"
    activity_dir.mkdir(parents=True)
    csv_path = activity_dir / "scene_evt_test.csv"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "text", "trans"])
        writer.writeheader()
        writer.writerow({"id": "1", "name": "ガレヲン/伽莱翁", "text": "x", "trans": "伽莱翁说话"})

    matches = iter_matched_scenarios(
        scenario_root=scenario_root,
        search_names=["伽莱翁"],
        allowed_categories={"活动剧情"},
    )

    assert len(matches) == 1
    assert matches[0].path == csv_path
    assert matches[0].activity_key == "活动剧情/测试活动"
