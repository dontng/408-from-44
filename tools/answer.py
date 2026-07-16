#!/usr/bin/env python3
"""Minimal local answer card for MD-first daily rosters."""
import json
import mimetypes
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

import grade_today


REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8409
DEFAULT_DATE = sys.argv[3] if len(sys.argv) > 3 else ""
HERE = Path(__file__).resolve().parent
PAGE = HERE / "answer.html"
ROSTER_DIR = REPO / "data" / "rosters"
ANSWER_DIR = REPO / "data" / "answers"

TOKENS = {"A", "B", "C", "D", "unknown", ""}


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_date(raw):
    if raw and len(raw) == 4 and raw.isdigit():
        return raw
    return ""


class H(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_body(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if path == "/":
            return self.send_body(200, PAGE.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        if path == "/api/roster":
            date = safe_date((query.get("date") or [""])[0])
            if not date:
                return self.send_body(400, {"error": "bad date"})
            roster = read_json(ROSTER_DIR / f"{date}.json", None)
            if roster is None:
                return self.send_body(404, {"error": "roster not found"})
            return self.send_body(200, roster)
        if path == "/api/answers":
            date = safe_date((query.get("date") or [""])[0])
            if not date:
                return self.send_body(400, {"error": "bad date"})
            data = read_json(ANSWER_DIR / f"{date}.json", {"date": date, "answers": {}})
            return self.send_body(200, data)
        if path == "/api/result":
            date = safe_date((query.get("date") or [""])[0])
            if not date:
                return self.send_body(400, {"error": "bad date"})
            data = read_json(REPO / "data" / "results" / f"{date}.json", {"date": date, "items": []})
            return self.send_body(200, data)
        if path.startswith("/bank/"):
            f = (REPO / path.lstrip("/")).resolve()
            if REPO in f.parents and f.exists():
                ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
                return self.send_body(200, f.read_bytes(), ctype)
            return self.send_body(404, {"error": "not found"})
        return self.send_body(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/grade":
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or "{}")
            date = safe_date(data.get("date", ""))
            if not date:
                return self.send_body(400, {"error": "bad date"})
            _, result_data, today_data, diagnoses = grade_today.build_outputs(date)
            result_path = REPO / "data" / "results" / f"{date}.json"
            today_path = REPO / "coach" / "today" / f"{date}.json"
            grade_today.write_json(result_path, result_data)
            grade_today.write_json(today_path, today_data)
            grade_today.update_md(result_data)
            grade_today.progress.record_day(result_data, diagnoses)
            return self.send_body(200, {
                "ok": True,
                "date": date,
                "answered": result_data["answered"],
                "total": result_data["total"],
                "known_graded": result_data["known_graded"],
                "correct": result_data["ok"],
                "today_open": today_data["open"],
            })
        if self.path != "/api/answer":
            if self.path != "/api/diagnosis":
                return self.send_body(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n) or "{}")
        date = safe_date(data.get("date", ""))
        qid = data.get("qid", "")
        pick = data.get("pick", "")
        diagnosis = data.get("diagnosis", "")
        if not date or not qid:
            return self.send_body(400, {"error": "bad payload"})
        path = ANSWER_DIR / f"{date}.json"
        ans = read_json(path, {"date": date, "answers": {}, "diagnoses": {}})
        ans["date"] = date
        ans.setdefault("answers", {})
        ans.setdefault("diagnoses", {})
        if self.path == "/api/answer":
            if pick not in TOKENS:
                return self.send_body(400, {"error": "bad payload"})
            if pick:
                ans["answers"][qid] = pick
            else:
                ans["answers"].pop(qid, None)
        else:
            if diagnosis not in {"", "outside", "misselect", "hesitant", "solid"}:
                return self.send_body(400, {"error": "bad diagnosis"})
            if diagnosis:
                ans["diagnoses"][qid] = diagnosis
            else:
                ans["diagnoses"].pop(qid, None)
        write_json(path, ans)
        return self.send_body(200, {"ok": True, "date": date, "qid": qid, "pick": pick, "diagnosis": diagnosis})


def main():
    date = safe_date(DEFAULT_DATE) or "MMDD"
    print(f"answer card · http://127.0.0.1:{PORT}/?date={date}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
