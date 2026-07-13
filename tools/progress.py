#!/usr/bin/env python3
"""Canonical answer-event ledger and derived review state."""
import datetime as dt
import json
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
EVENT_DIR = REPO / "data" / "progress"
BASELINE_FILE = EVENT_DIR / "baseline.json"
STATE_FILE = REPO / "review" / "state.json"
INTERVALS = [2, 4, 8, 16, 30, 45]


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bootstrap_baseline():
    if BASELINE_FILE.exists():
        return
    state = read_json(STATE_FILE, {})
    questions = {qid: value for qid, value in state.items() if not qid.startswith("_")}
    last = max((item.get("last", "") for item in questions.values()), default="")
    write_json(BASELINE_FILE, {"schema": 1, "as_of": last, "questions": questions})


def event_files():
    return sorted(EVENT_DIR.glob("*.json"))


def all_events():
    events = []
    for path in event_files():
        if path.name == BASELINE_FILE.name:
            continue
        events.extend(read_json(path, {}).get("events", []))
    return sorted(events, key=lambda item: (item["date"], item["qid"]))


def answer_confidence(year, question):
    if year == "2025":
        if question == 5:
            return "ungraded"
        if question in {8, 30}:
            return "provisional_low"
        return "provisional"
    return "official"


def record_day(result_data, diagnostics):
    """Replace one day's events, making re-grading deterministic and idempotent."""
    bootstrap_baseline()
    events = []
    for result in result_data["items"]:
        if result["status"] == "blank":
            continue
        qid = result["qid"]
        events.append({
            "id": f"{result_data['date']}:{qid}",
            "date": result_data["date"],
            "qid": qid,
            "year": result["year"],
            "q": result["q"],
            "source": result["source"],
            "pick": result["pick"],
            "answer": result["answer"],
            "status": result["status"],
            "ok": result["ok"],
            "diagnosis": diagnostics.get(qid, ""),
            "answer_confidence": answer_confidence(result["year"], result["q"]),
        })
    write_json(EVENT_DIR / f"{result_data['date'][5:7]}{result_data['date'][8:10]}.json", {
        "schema": 1,
        "date": result_data["date"],
        "events": events,
    })
    rebuild_state()


def rebuild_state():
    bootstrap_baseline()
    baseline = read_json(BASELINE_FILE, {"questions": {}})
    previous = read_json(STATE_FILE, {})
    state = {qid: dict(value) for qid, value in baseline.get("questions", {}).items()}
    for event in all_events():
        qid = event["qid"]
        item = state.setdefault(qid, {"box": 0, "seen": 0, "right": 0})
        correct = event["ok"] is True
        item["box"] = min(item.get("box", 0) + 1, len(INTERVALS) - 1) if correct else 0
        item["seen"] = item.get("seen", 0) + 1
        item["right"] = item.get("right", 0) + (1 if correct else 0)
        item["last"] = event["date"]
        item["last_ok"] = correct
        item["last_pick"] = event["pick"]
        item["last_diagnosis"] = event["diagnosis"]
        item["answer_confidence"] = event["answer_confidence"]
        item["due"] = (dt.date.fromisoformat(event["date"]) + dt.timedelta(days=INTERVALS[item["box"]])).isoformat()
        if event["diagnosis"] == "solid":
            item["stuck"] = False
        elif event["diagnosis"] in {"outside", "misselect", "hesitant"} or not correct:
            item["stuck"] = True
    if "_progress" in previous:
        state["_progress"] = previous["_progress"]
    write_json(STATE_FILE, state)
