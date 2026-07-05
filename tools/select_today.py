#!/usr/bin/env python3
"""Generate the Markdown roster for one day.

This is the lightweight MD-first entry point. It does not grade answers and it
does not run the coach flow. It only turns the fixed roster policy into today's
work file under src/<month>/MMDD-dayNN.md.
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
POLICY_FILE = REPO / "data" / "roster_policy.json"
STATE_FILE = REPO / "review" / "state.json"
NORM_FILE = REPO / "review" / "imgnorm.json"
ROSTER_DIR = REPO / "data" / "rosters"
SRC_DIR = REPO / "src"
COACH_TODAY_DIR = REPO / "coach" / "today"

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def normalize_date(raw):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    if re.fullmatch(r"\d{4}", raw):
        year = dt.date.today().year
        return f"{year}-{raw[:2]}-{raw[2:]}"
    raise SystemExit("date must be YYYY-MM-DD or MMDD, e.g. 2026-07-05 or 0705")


def load_answers(year):
    path = REPO / "answers" / f"{year}.txt"
    answers = {}
    if not path.exists():
        return answers
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(\d{1,2})\s+([A-Da-d])", line)
        if m:
            answers[int(m.group(1))] = m.group(2).upper()
    return answers


def load_questions():
    questions = {}
    for ydir in sorted((REPO / "bank").glob("*")):
        if not ydir.is_dir():
            continue
        year = ydir.name
        answers = load_answers(year)
        for png in sorted(ydir.glob("q*.png")):
            m = re.search(r"q(\d+)\.png$", png.name)
            if not m:
                continue
            q = int(m.group(1))
            qid = f"{year}-{q:02d}"
            questions[qid] = {
                "id": qid,
                "year": year,
                "q": q,
                "img": f"bank/{year}/{png.name}",
                "answer_known": q in answers,
            }
    return questions


def load_norm():
    """Return qid -> normalized display width in px for consistent image text size."""
    data = read_json(NORM_FILE, {})
    return data.get("items", {})


def day_index(date_iso, policy):
    start = dt.date.fromisoformat(policy["start_date"])
    current = dt.date.fromisoformat(date_iso)
    return (current - start).days + 1


def limits_for_day(day_no, policy):
    daily = policy["daily_limits"]
    if day_no <= daily["restart_days"]:
        return daily["restart"]
    return daily["stable"]


def tier_map(policy):
    out = {}
    for tier in policy["choice_tiers"]:
        for year in tier["years"]:
            out[year] = tier
    return out


def year_rank(year, tiers):
    tier = tiers.get(year, {"role": "unknown"})
    role_rank = {"core": 0, "training": 1, "patch": 2, "reserve": 3}
    # More recent years first inside the same tier.
    return (role_rank.get(tier["role"], 9), -int(year))


def load_coach_feedback(date_iso):
    """Return qid -> highest-risk coach decision before date_iso."""
    target = dt.date.fromisoformat(date_iso)
    rank = {"pin": 0, "revisit": 1}
    feedback = {}
    for path in sorted(COACH_TODAY_DIR.glob("*.json")):
        data = read_json(path, {})
        day = data.get("date")
        if not day:
            continue
        try:
            if dt.date.fromisoformat(day) >= target:
                continue
        except ValueError:
            continue
        for item in data.get("items", []):
            decision = item.get("decision")
            qid = item.get("qid")
            if decision not in rank or not qid:
                continue
            prev = feedback.get(qid)
            if prev is None or rank[decision] < rank[prev["decision"]]:
                feedback[qid] = {
                    "decision": decision,
                    "date": day,
                    "grade": item.get("grade"),
                }
    return feedback


def load_prior_rostered(date_iso):
    """Return qids already assigned by the MD-first roster flow before date_iso."""
    target = dt.date.fromisoformat(date_iso)
    used = set()
    for path in sorted(ROSTER_DIR.glob("*.json")):
        data = read_json(path, {})
        day = data.get("date")
        if not day:
            continue
        try:
            if dt.date.fromisoformat(day) >= target:
                continue
        except ValueError:
            continue
        for item in data.get("items", []):
            qid = item.get("qid")
            if qid:
                used.add(qid)
    return used


def review_rank(qid, state, questions, date_iso, tiers, coach_feedback=None):
    s = state.get(qid, {})
    q = questions[qid]
    coach_feedback = coach_feedback or {}
    due = s.get("due", "9999-12-31")
    due_days = 999
    try:
        due_days = (dt.date.fromisoformat(due) - dt.date.fromisoformat(date_iso)).days
    except ValueError:
        pass
    risk = 0
    decision = coach_feedback.get(qid, {}).get("decision")
    if decision == "pin":
        risk -= 250
    elif decision == "revisit":
        risk -= 180
    if s.get("stuck"):
        risk -= 100
    if s.get("last_ok") is False:
        risk -= 70
    if due <= date_iso:
        risk -= 40
    risk += max(-30, min(30, due_days))
    return (risk, *year_rank(q["year"], tiers), q["q"])


def select_roster(date_iso, policy, state, questions):
    day_no = day_index(date_iso, policy)
    limits = limits_for_day(day_no, policy)
    tiers = tier_map(policy)
    coach_feedback = load_coach_feedback(date_iso)
    prior_rostered = load_prior_rostered(date_iso)
    allowed_new_years = {
        year
        for year, tier in tiers.items()
        if tier.get("default_new_pool") and tier.get("target_passes", 0) > 0
    }

    review_candidates = []
    new_candidates = []
    for qid, q in questions.items():
        s = state.get(qid)
        if qid in coach_feedback:
            review_candidates.append(qid)
        elif qid in prior_rostered:
            continue
        elif s:
            if s.get("stuck") or s.get("last_ok") is False or s.get("due", "9999-12-31") <= date_iso:
                review_candidates.append(qid)
        elif q["year"] in allowed_new_years:
            new_candidates.append(qid)

    review_candidates = list(dict.fromkeys(review_candidates))
    review_candidates.sort(key=lambda qid: review_rank(qid, state, questions, date_iso, tiers, coach_feedback))
    new_candidates.sort(key=lambda qid: (*year_rank(questions[qid]["year"], tiers), questions[qid]["q"]))

    review_ids = review_candidates[: limits["review"]]
    used = set(review_ids)
    new_ids = [qid for qid in new_candidates if qid not in used][: limits["new"]]

    # If one pool is short, let the other fill up to total, still respecting the hard daily total.
    total = min(limits["total"], policy["daily_limits"]["hard_cap"])
    roster = review_ids + new_ids
    sources = {qid: "review" for qid in review_ids}
    sources.update({qid: "new" for qid in new_ids})
    if len(roster) < total:
        for qid in review_candidates + new_candidates:
            if qid not in used and qid not in roster:
                roster.append(qid)
                sources[qid] = "review" if qid in review_candidates else "new"
                if len(roster) >= total:
                    break
    roster = roster[:total]
    for qid in roster:
        if qid in coach_feedback:
            sources[qid] = coach_feedback[qid]["decision"]
    return roster, {qid: sources.get(qid, "unknown") for qid in roster}, day_no, limits


def md_rel_img(md_path, q):
    return Path(q["img"]).as_posix()


def nav_line(day_no, date_obj):
    parts = []
    prev_day = day_no - 1
    if prev_day >= 1:
        prev_date = date_obj - dt.timedelta(days=1)
        prev_name = f"{prev_date.strftime('%m%d')}-day{prev_day:02d}.md"
        parts.append(f"[« {prev_date.strftime('%m%d')}-day{prev_day:02d}]({prev_name})")
    next_day = day_no + 1
    next_date = date_obj + dt.timedelta(days=1)
    next_name = f"{next_date.strftime('%m%d')}-day{next_day:02d}.md"
    parts.append(f"[» {next_date.strftime('%m%d')}-day{next_day:02d}]({next_name})")
    return " | ".join(parts)


def write_roster_json(date_iso, day_no, limits, roster, sources, questions):
    ROSTER_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "date": date_iso,
        "day": day_no,
        "limits": limits,
        "items": [
            {
                "idx": i,
                "qid": qid,
                "year": questions[qid]["year"],
                "q": questions[qid]["q"],
                "image": questions[qid]["img"],
                "answer_known": questions[qid]["answer_known"],
                "source": sources.get(qid, "unknown"),
            }
            for i, qid in enumerate(roster, 1)
        ],
    }
    path = ROSTER_DIR / f"{date_iso[5:7]}{date_iso[8:10]}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def md_img_tag(md_path, qid, q, norm):
    src = f"../../{md_rel_img(md_path, q)}"
    width = norm.get(qid)
    if width:
        return f'<img src="{src}" width="{width}" style="max-width:100%; height:auto;">'
    return f'<img src="{src}" style="max-width:100%; height:auto;">'


def write_md(date_iso, day_no, roster, questions, norm):
    date_obj = dt.date.fromisoformat(date_iso)
    month_dir = SRC_DIR / MONTHS[date_obj.month - 1]
    month_dir.mkdir(parents=True, exist_ok=True)
    md_path = month_dir / f"{date_obj.strftime('%m%d')}-day{day_no:02d}.md"
    nav = nav_line(day_no, date_obj)
    lines = [
        nav,
        "",
        f"# Day {day_no:02d} · {date_iso}",
        "",
        f"> [!IMPORTANT]  [打开答题卡](http://127.0.0.1:8409/?date={date_obj.strftime('%m%d')})",
        "",
        f"> 今日 {len(roster)} 题；答题卡可选 `A/B/C/D/?`，`?` 表示不会。",
        "",
        "## 题目",
        "",
    ]
    for i, qid in enumerate(roster, 1):
        q = questions[qid]
        lines += [
            f"### {i:02d} · {qid}",
            "",
            "作答：",
            "",
            md_img_tag(md_path, qid, q, norm),
            "",
        ]
    lines += [nav, ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=dt.date.today().strftime("%m%d"))
    args = parser.parse_args()
    date_iso = normalize_date(args.date)

    policy = read_json(POLICY_FILE, {})
    state = read_json(STATE_FILE, {})
    questions = load_questions()
    norm = load_norm()
    roster, sources, day_no, limits = select_roster(date_iso, policy, state, questions)
    json_path = write_roster_json(date_iso, day_no, limits, roster, sources, questions)
    md_path = write_md(date_iso, day_no, roster, questions, norm)
    print(f"wrote {md_path.relative_to(REPO)}")
    print(f"wrote {json_path.relative_to(REPO)}")
    print(" ".join(roster))
    subprocess.run([sys.executable, str(REPO / "tools" / "sync_now.py"), f"sync roster {date_iso[5:7]}{date_iso[8:10]}"], cwd=REPO)


if __name__ == "__main__":
    main()
