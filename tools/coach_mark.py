#!/usr/bin/env python3
"""Mark a coach/today item as pass, revisit, or pin."""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
TODAY_DIR = REPO / "coach" / "today"
CURRENT_FILE = REPO / "coach" / "current.md"
PINS_INDEX = REPO / "coach" / "pins" / "index.md"

DECISIONS = {"pass", "revisit", "pin"}


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_date(raw):
    if re.fullmatch(r"\d{4}", raw):
        return raw
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw[5:7] + raw[8:10]
    raise SystemExit("date must be MMDD or YYYY-MM-DD, e.g. 0705 or 2026-07-05")


def current_qid():
    try:
        text = CURRENT_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    m = re.search(r"^题号：(\d{4}-\d{2})$", text, re.M)
    return m.group(1) if m else ""


def update_today(date_key, qid, decision):
    path = TODAY_DIR / f"{date_key}.json"
    today = read_json(path, None)
    if today is None:
        raise SystemExit(f"missing coach/today/{date_key}.json")
    found = None
    for item in today.get("items", []):
        if item.get("qid") == qid:
            item["decision"] = decision
            found = item
            break
    if found is None:
        raise SystemExit(f"{qid} not found in coach/today/{date_key}.json")
    today["open"] = sum(1 for item in today.get("items", []) if item.get("decision") == "open" and item.get("grade") != "blank")
    write_json(path, today)
    return today, found


def append_pin(today, item, note):
    PINS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    if PINS_INDEX.exists():
        text = PINS_INDEX.read_text(encoding="utf-8")
    else:
        text = "# Pins\n\n考前必须拔掉的钉子。\n\n"
    qid = item["qid"]
    if f"`{qid}`" in text:
        return
    line = (
        f"- `{qid}` · {today.get('date', '')} · {item.get('grade', '')} · "
        f"作答 {item.get('pick') or '-'} / 答案 {item.get('answer') or '-'}"
    )
    if note:
        line += f" · {note}"
    text = text.rstrip() + "\n" + line + "\n"
    PINS_INDEX.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().strftime("%m%d"))
    parser.add_argument("--qid", default="")
    parser.add_argument("--decision", required=True, choices=sorted(DECISIONS))
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    date_key = normalize_date(args.date)
    qid = args.qid or current_qid()
    if not qid:
        raise SystemExit("missing qid; pass --qid or generate coach/current.md first")
    today, item = update_today(date_key, qid, args.decision)
    if args.decision == "pin":
        append_pin(today, item, args.note)
    print(f"{qid} -> {args.decision}")
    print(f"open {today['open']}")
    subprocess.run([sys.executable, str(REPO / "tools" / "sync_now.py"), f"sync decision {date_key} {qid} {args.decision}"], cwd=REPO)


if __name__ == "__main__":
    main()
