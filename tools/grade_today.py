#!/usr/bin/env python3
"""Grade one day's answer card and persist the factual result."""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

import progress


REPO = Path(__file__).resolve().parent.parent
ROSTER_DIR = REPO / "data" / "rosters"
ANSWER_DIR = REPO / "data" / "answers"
RESULT_DIR = REPO / "data" / "results"
SRC_DIR = REPO / "src"

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_answers(year):
    path = REPO / "answers" / f"{year}.txt"
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(\d{1,2})\s+([A-Da-d])", line)
        if m:
            out[int(m.group(1))] = m.group(2).upper()
    return out


def date_key(date_iso):
    return date_iso[5:7] + date_iso[8:10]


def md_path_for(date_iso, day_no, roster=None):
    if roster and roster.get("md_path"):
        path = (REPO / roster["md_path"]).resolve()
        if REPO not in path.parents:
            raise SystemExit("roster md_path escapes repository")
        return path
    d = dt.date.fromisoformat(date_iso)
    return SRC_DIR / MONTHS[d.month - 1] / f"{d.strftime('%m%d')}-day{day_no:02d}.md"


def grade_item(item, pick, answer_cache):
    year = item["year"]
    answer = answer_cache.setdefault(year, load_answers(year)).get(item["q"])
    answered = pick in {"A", "B", "C", "D", "unknown"}
    if not answered:
        status = "blank"
        ok = None
    elif pick == "unknown":
        status = "unknown"
        ok = False
    elif answer is None:
        status = "self_check"
        ok = None
    else:
        ok = pick == answer
        status = "right" if ok else "wrong"
    return {
        "idx": item["idx"],
        "qid": item["qid"],
        "year": year,
        "q": item["q"],
        "source": item.get("source", "unknown"),
        "pick": pick or "",
        "answer": answer,
        "ok": ok,
        "status": status,
    }


def build_outputs(date_key_value):
    roster = read_json(ROSTER_DIR / f"{date_key_value}.json", None)
    if roster is None:
        raise SystemExit(f"missing roster: data/rosters/{date_key_value}.json")
    answer_data = read_json(ANSWER_DIR / f"{date_key_value}.json", {"answers": {}})
    answers = answer_data.get("answers", {})
    answer_cache = {}
    results = [grade_item(item, answers.get(item["qid"], ""), answer_cache) for item in roster["items"]]
    done = sum(1 for r in results if r["status"] != "blank")
    known = [r for r in results if r["ok"] is not None]
    ok_count = sum(1 for r in known if r["ok"])
    result_data = {
        "date": roster["date"],
        "day": roster["day"],
        "md_path": roster.get("md_path"),
        "total": len(results),
        "answered": done,
        "known_graded": len(known),
        "ok": ok_count,
        "items": results,
    }
    return roster, result_data


def result_mark(result):
    if result["status"] == "blank":
        return "未答"
    if result["status"] == "unknown":
        return "不会"
    if result["status"] == "self_check":
        return "自判"
    return "✓" if result["ok"] else "✗"


def pick_label(pick):
    return "不会" if pick == "unknown" else pick


def result_section(result_data):
    lines = [
        "## 结果",
        "",
        f"已答 {result_data['answered']} / {result_data['total']}；"
        f"已判 {result_data['known_graded']} 题，对 {result_data['ok']} 题。",
        "",
        "| # | 题号 | 作答 | 答案 | 结果 |",
        "|---:|---|---|---|---|",
    ]
    for r in result_data["items"]:
        answer = "" if r["status"] == "blank" else (r["answer"] or "")
        lines.append(
            f"| {r['idx']:02d} | {r['qid']} | {pick_label(r['pick'])} | {answer} | {result_mark(r)} |"
        )
    return "\n".join(lines) + "\n"


def update_md(result_data):
    md_path = md_path_for(result_data["date"], result_data["day"], result_data)
    if not md_path.exists():
        return None
    text = md_path.read_text(encoding="utf-8")
    marker = "\n## 结果\n"
    section = result_section(result_data).rstrip()
    if marker in text:
        head = text[: text.index(marker)].rstrip()
        tail = text[text.index(marker):].rstrip().splitlines()
        bottom_nav = tail[-1] if tail and tail[-1].startswith("[") else ""
        text = head + "\n\n" + section
        if bottom_nav:
            text += "\n\n" + bottom_nav
        text += "\n"
    else:
        # Keep the bottom navigation at the very end when present.
        lines = text.rstrip().splitlines()
        bottom_nav = ""
        if lines and lines[-1].startswith("["):
            bottom_nav = lines.pop()
        text = "\n".join(lines).rstrip() + "\n\n" + section
        if bottom_nav:
            text += "\n" + bottom_nav + "\n"
    md_path.write_text(text, encoding="utf-8")
    return md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().strftime("%m%d"), help="MMDD, e.g. 0705")
    args = parser.parse_args()
    key = args.date
    roster, result_data = build_outputs(key)
    result_path = RESULT_DIR / f"{key}.json"
    write_json(result_path, result_data)
    progress.record_day(result_data)
    md_path = update_md(result_data)
    print(f"wrote {result_path.relative_to(REPO)}")
    if md_path:
        print(f"updated {md_path.relative_to(REPO)}")
    print(f"answered {result_data['answered']}/{result_data['total']} ok {result_data['ok']}/{result_data['known_graded']}")


if __name__ == "__main__":
    main()
