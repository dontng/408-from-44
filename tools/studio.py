#!/usr/bin/env python3
"""studio.py — 408 本地刷题台。

usage:  studio.py [repo_dir] [port]   （由根目录 studio.sh 启动）

仅标准库，只绑定 127.0.0.1。界面在 tools/studio.html。
题目图片在 bank/<年>/qNN.png，答案在 answers/<年>.txt，
学习状态(遗忘曲线)存 review/state.json —— 纯文本，可随仓库多机同步。
"""
import sys, os, re, json, datetime, mimetypes
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8408
HERE = Path(__file__).resolve().parent
PAGE = HERE / "studio.html"
STATE_FILE = REPO / "review" / "state.json"

# ── 可调参数（设计见 memory: project-408-study-system）──────
EXAM_DATE = "2026-12-19"          # 初试日期；考前最后一天 12-18
NEW_PER_DAY = 20                  # 每日新题上限(待最终敲定)

# 选择题遗忘曲线：单题间隔“扩张”(先短后长，抓住遗忘陡崖)，共 7 次曝光。
# 注：最后 1~2 次理想应“锁定”到 11/12 月做考前冲刺，目前先用纯间隔近似(TODO 日期锁定)。
INTERVALS = [2, 5, 12, 30, 60, 90]      # 6 个间隔 = 7 次曝光
# 大题遗忘曲线：至少 4 次，更稀；大题按“时间”排不按“道数”。(引擎接入待大题入库)
INTERVALS_BIG = [3, 12, 35, 70]

# 科目轮转：早期每天只激活一对子轨，配平工作量(大科配小科)
ROTATION = [["data_structures", "computer_networks"],        # 45 + 25
            ["computer_organization", "operating_systems"]]  # 45 + 35

# 打乱度(分块→交错)：随日期推进，从“按章节聚类”过渡到“完全随机跨科”
# 三段界线：~8月底、~11月底。需 tags/<年>.tsv 章节标签就绪后才生效。
SCRAMBLE_PHASES = [("2026-08-31", "blocked"),    # 早期：同章节成组、每天两门
                   ("2026-11-30", "interleaved"),# 中期：科目内交错+跨科适度
                   ("9999-12-31", "random")]     # 后期：完全随机跨章跨科=全真模拟


# ── 题库 / 答案 ───────────────────────────────────────────
def load_answers(year):
    p = REPO / "answers" / f"{year}.txt"
    d = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(\d{1,2})\s+([A-Da-d])", line)
            if m:
                d[int(m.group(1))] = m.group(2).upper()
    return d


def load_tags(year):
    """tags/<year>.tsv：每行 '题号<TAB>科目<TAB>章节'。无则返回空。"""
    p = REPO / "tags" / f"{year}.tsv"
    d = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[0].strip().isdigit():
                d[int(parts[0])] = {"subject": parts[1].strip(), "chapter": parts[2].strip()}
    return d


def load_questions():
    items = {}
    for ydir in sorted((REPO / "bank").glob("*")):
        if not ydir.is_dir():
            continue
        year = ydir.name
        ans = load_answers(year)
        tags = load_tags(year)
        for png in sorted(ydir.glob("q*.png")):
            m = re.search(r"q(\d+)\.png$", png.name)
            if not m:
                continue
            q = int(m.group(1))
            qid = f"{year}-{q:02d}"
            t = tags.get(q, {})
            items[qid] = {"id": qid, "year": year, "q": q,
                          "img": f"/bank/{year}/{png.name}", "answer": ans.get(q),
                          "subject": t.get("subject"), "chapter": t.get("chapter")}
    return items


QUESTIONS = load_questions()


# ── 状态 ──────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(s):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def today():
    return datetime.date.today().isoformat()


def add_days(d, n):
    return (datetime.date.fromisoformat(d) + datetime.timedelta(days=n)).isoformat()


def dday():
    # 倒计时到"考前最后一天"(考试日前一天)，与可复习天数一致
    return (datetime.date.fromisoformat(EXAM_DATE) - datetime.date.today()).days - 1


def day_log(state):
    return state.setdefault("_progress", {}).setdefault(today(), {"done": [], "ok": 0, "new": 0})


def build_today(state):
    """返回今日全量清单(含已做)：[{id,year,q,img,status,ok}]，新题在已做后。"""
    log = day_log(state)
    done = list(log["done"])
    done_set = set(done)
    t = today()
    due, fresh = [], []
    for qid, it in QUESTIONS.items():
        if qid in done_set:
            continue
        s = state.get(qid)
        if s:
            if s.get("due", "9999") <= t:
                due.append(qid)
        else:
            fresh.append(qid)
    remaining_new = max(0, NEW_PER_DAY - log["new"])
    pending = due + fresh[:remaining_new]
    out = []
    for qid in done:
        it = QUESTIONS.get(qid)
        if it:
            ent = state.get(qid, {})
            out.append({**_pub(it), "status": "done", "ok": ent.get("last_ok", True)})
    for qid in pending:
        out.append({**_pub(QUESTIONS[qid]), "status": "pending"})
    return out, log


def _pub(it):
    """对外不暴露答案。"""
    return {"id": it["id"], "year": it["year"], "q": it["q"], "img": it["img"]}


def grade(state, qid, pick=None, selfok=None):
    it = QUESTIONS.get(qid)
    if not it:
        return {"error": "no such question"}
    is_new = qid not in state
    ans = it["answer"]
    if ans is None and selfok is None:
        # 无官方答案，先告诉前端要自判
        return {"known": False}
    correct = (pick == ans) if ans else bool(selfok)
    s = state.get(qid, {"box": 0})
    s["box"] = min(s["box"] + 1, len(INTERVALS) - 1) if correct else 0
    s["due"] = add_days(today(), INTERVALS[s["box"]])
    s["seen"] = s.get("seen", 0) + 1
    s["right"] = s.get("right", 0) + (1 if correct else 0)
    s["last"] = today()
    s["last_ok"] = correct
    state[qid] = s
    log = day_log(state)
    if qid not in log["done"]:
        log["done"].append(qid)
        if correct:
            log["ok"] += 1
        if is_new:
            log["new"] += 1
    save_state(state)
    return {"known": True, "correct": correct, "answer": ans}


# ── HTTP ──────────────────────────────────────────────────
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
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
        path = self.path.split("?")[0]
        if path == "/":
            return self._send(200, PAGE.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        if path == "/api/today":
            state = load_state()
            items, log = build_today(state)
            return self._send(200, {
                "dday": dday(), "examDate": EXAM_DATE, "newPerDay": NEW_PER_DAY,
                "items": items,
                "done": len(log["done"]), "ok": log["ok"],
            })
        if path.startswith("/bank/"):
            f = (REPO / path.lstrip("/")).resolve()
            if REPO in f.parents and f.exists():
                ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
                return self._send(200, f.read_bytes(), ctype)
            return self._send(404, {"error": "not found"})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n) or "{}")
        if self.path == "/api/grade":
            state = load_state()
            res = grade(state, data.get("id"), data.get("pick"), data.get("self"))
            return self._send(200, res)
        return self._send(404, {"error": "not found"})


def main():
    print(f"408 studio · http://127.0.0.1:{PORT}  （题库 {len(QUESTIONS)} 题，距考试 {dday()} 天）")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
