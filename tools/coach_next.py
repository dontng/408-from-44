#!/usr/bin/env python3
"""Build coach/current.md from the next open item in coach/today/MMDD.json."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
TODAY_DIR = REPO / "coach" / "today"
CURRENT_FILE = REPO / "coach" / "current.md"
ROSTER_DIR = REPO / "data" / "rosters"


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def normalize_date(raw):
    if re.fullmatch(r"\d{4}", raw):
        return raw
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw[5:7] + raw[8:10]
    raise SystemExit("date must be MMDD or YYYY-MM-DD, e.g. 0705 or 2026-07-05")


def pick_next(today):
    open_items = [item for item in today.get("items", []) if item.get("decision") == "open" and item.get("grade") != "blank"]
    if not open_items:
        return None
    return sorted(open_items, key=lambda item: (item.get("priority", 9), item.get("idx", 999)))[0]


def item_image(qid, roster):
    for item in roster.get("items", []):
        if item.get("qid") == qid:
            return item.get("image", "")
    year, num = qid.split("-")
    return f"bank/{year}/q{int(num):02d}.png"


def pick_label(pick):
    return "?" if pick == "unknown" else (pick or "")


def write_current(date_key, today, item, roster):
    image = item_image(item["qid"], roster)
    image_link = f"../{image}" if image else ""
    lines = [
        "# Current",
        "",
        f"日期：{today.get('date', date_key)} · Day {today.get('day', '?')}",
        "",
        f"题号：{item['qid']}",
        "",
        f"作答：{pick_label(item.get('pick', ''))}",
        "",
        f"答案：{item.get('answer') or ''}",
        "",
        f"结果：{item.get('grade', '')}",
        "",
        f"来源：{item.get('source', '')} · 优先级：{item.get('priority', '')}",
        "",
        "## 题图",
        "",
        f"![]({image_link})",
        "",
        "## 本轮任务",
        "",
        "只处理这一题，不展开全量 today。",
        "",
        "目标是判断本题处置：",
        "",
        "```text",
        "pass / revisit / pin",
        "```",
        "",
        "- `pass`：今晚收口，回正常调度。",
        "- `revisit`：短期回炉，近期必须再出现。",
        "- `pin`：长期悬挂，考前必须拔掉。",
        "",
    ]
    CURRENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_FILE.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().strftime("%m%d"))
    args = parser.parse_args()
    key = normalize_date(args.date)
    today = read_json(TODAY_DIR / f"{key}.json", None)
    if today is None:
        raise SystemExit(f"missing coach/today/{key}.json")
    roster = read_json(ROSTER_DIR / f"{key}.json", {})
    item = pick_next(today)
    if item is None:
        CURRENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        CURRENT_FILE.write_text("# Current\n\n今日没有待处理的 open 题。\n", encoding="utf-8")
        print("no open item")
        return
    write_current(key, today, item, roster)
    print(f"wrote {CURRENT_FILE.relative_to(REPO)}")
    print(f"{item['idx']:02d} {item['qid']} {item.get('grade')} priority={item.get('priority')}")


if __name__ == "__main__":
    main()
