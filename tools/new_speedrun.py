#!/usr/bin/env python3
"""Create one speedrun session scaffold from immutable daily results."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
RESULT_DIR = REPO / "data" / "results"
SESSION_DIR = REPO / "speedrun" / "sessions"


def date_key(raw):
    if re.fullmatch(r"\d{4}", raw):
        return raw
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw[5:7] + raw[8:10]
    raise SystemExit("date must be MMDD or YYYY-MM-DD")


def pick_label(pick):
    if pick == "unknown":
        return "不会"
    if not pick:
        return "未答"
    return pick


def render_session(result):
    key = result["date"][5:7] + result["date"][8:10]
    right = sum(item.get("status") == "right" for item in result["items"])
    wrong = sum(item.get("status") == "wrong" for item in result["items"])
    unknown = sum(item.get("status") == "unknown" for item in result["items"])
    lines = [
        f"# {key}｜速通草稿",
        "",
        "> 执行协议：[speedrun README](../../README.md)｜逐题骨架：[TEMPLATE](../../TEMPLATE.md)",
        ">",
        "> 本文件由真实判分结果生成。`draft` 只表示骨架存在，不属于掌握状态；每题完成独立诊断、机制闭合、选项裁决和验证设计后，才可改为 `explained`。",
        "",
        "## 本次证据",
        "",
        f"- 共 {result['total']} 题：首次做对 {right}，做错 {wrong}，不会 {unknown}。",
        "- 首次作答只作证据，不得覆盖；不得从选项反推用户的心理原因。",
        "",
        "---",
        "",
    ]
    for item in result["items"]:
        qid = item["qid"]
        image = f"../../../bank/{item['year']}/q{int(item['q']):02d}.png"
        lines += [
            f"## {int(item['idx']):02d}｜{qid}：待命名机制",
            "",
            f"**首次作答：{pick_label(item.get('pick'))}；正确答案：{item.get('answer') or '待核'}；当前状态：`draft`。**",
            "",
            f"> [查看原题图]({image})",
            "",
            "### 真正要解决的问题",
            "",
            "<!-- 只写证据支持的断层；不要复述答案或猜测用户心理。 -->",
            "",
            "### 最小机制",
            "",
            "<!-- 建立足以读懂题干、裁决选项和完成邻近迁移的最短闭环。 -->",
            "",
            "### 逐项裁决",
            "",
            "| 选项 | 裁决 | 成立条件或具体错误 |",
            "| --- | --- | --- |",
            "| A |  |  |",
            "| B |  |  |",
            "| C |  |  |",
            "| D |  |  |",
            "",
            f"所以选 **{item.get('answer') or '待核'}**。",
            "",
            "### 最小验证",
            "",
            "<!-- 改变最有区分力的条件，击穿一种具体错误理解。 -->",
            "",
            "<验证题>",
            "",
            "<details>",
            "<summary>核对</summary>",
            "",
            "<答案、关键理由，以及它击穿了什么错误理解>",
            "",
            "</details>",
            "",
            "---",
            "",
        ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().strftime("%m%d"))
    parser.add_argument("--output", help="override output path, mainly for verification")
    parser.add_argument("--force", action="store_true", help="replace an existing scaffold intentionally")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    key = date_key(args.date)
    result_path = RESULT_DIR / f"{key}.json"
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"missing result: {result_path.relative_to(REPO)}")

    if result.get("answered") != result.get("total") and not args.allow_incomplete:
        raise SystemExit("daily result is incomplete; finish grading or pass --allow-incomplete")

    year_month = result["date"][:7]
    output = Path(args.output) if args.output else SESSION_DIR / year_month / f"{key}.md"
    if output.exists() and not args.force:
        try:
            label = output.relative_to(REPO)
        except ValueError:
            label = output
        raise SystemExit(f"refusing to overwrite existing session: {label}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_session(result), encoding="utf-8")
    try:
        label = output.relative_to(REPO)
    except ValueError:
        label = output
    print(f"wrote {label}")
    print("next: replace every draft section, then run speedrun.sh --check", key)


if __name__ == "__main__":
    main()
