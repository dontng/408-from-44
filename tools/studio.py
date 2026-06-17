#!/usr/bin/env python3
"""studio.py — 408 本地刷题台。

usage:  studio.py [repo_dir] [port]   （由根目录 studio.sh 启动）

仅标准库，只绑定 127.0.0.1。界面在 tools/studio.html。
题目图片在 bank/<年>/qNN.png，答案在 answers/<年>.txt，
学习状态(遗忘曲线)存 review/state.json —— 纯文本，可随仓库多机同步。
"""
import sys, os, re, json, datetime, mimetypes, random
from collections import defaultdict, deque, Counter
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8408
HERE = Path(__file__).resolve().parent
PAGE = HERE / "studio.html"
STATE_FILE = REPO / "review" / "state.json"
NORM_FILE = REPO / "review" / "imgnorm.json"   # 每题显示宽(见 tools/imgnorm.py)：让屏幕字号一致
JOURNAL = REPO / "journal"                     # 每天做题记录(journal/YYYY-MM/MMDD.md)，回顾页的真相源

# ── 可调参数（设计见 memory: project-408-study-system）──────
EXAM_DATE = "2026-12-19"          # 初试日期；考前最后一天 12-18
NEW_PER_DAY = 20                  # 每日新题上限(待最终敲定)

# 选择题遗忘曲线：单题间隔“扩张”(先短后长，抓住遗忘陡崖)，共 7 次曝光。
# 注：最后 1~2 次理想应“锁定”到 11/12 月做考前冲刺，目前先用纯间隔近似(TODO 日期锁定)。
INTERVALS = [2, 4, 8, 16, 30, 45]       # 压缩版：7次曝光11-11收齐(见 docs/学习数学模型.md)
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

SUBJECTS = ["data_structures", "computer_organization",
            "operating_systems", "computer_networks"]
SUBJECT_CN = {"data_structures": "数据结构", "computer_organization": "组成原理",
              "operating_systems": "操作系统", "computer_networks": "计算机网络"}
# 无 tags 时按题号位置兜底归科(408 选择题长期分布: DS1-10 / CO11-23 / OS24-33 / 网34-40)
SUBJECT_BOUNDS = [(10, "data_structures"), (23, "computer_organization"),
                  (33, "operating_systems"), (40, "computer_networks")]


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


def load_norm():
    """题图显示宽 {qid: px}。由 tools/imgnorm.py 离线算好；缺失则前端按默认宽兜底。"""
    if NORM_FILE.exists():
        return json.loads(NORM_FILE.read_text(encoding="utf-8")).get("items", {})
    return {}


NORM = load_norm()


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


# ── 调度器：科目轮转 + 分块→交错(见 memory: project-408-study-system) ──
def q_subject(it):
    """题目科目：优先用 tags/<年>.tsv 标签，无则按题号位置兜底。"""
    if it.get("subject"):
        return it["subject"]
    for hi, subj in SUBJECT_BOUNDS:
        if it["q"] <= hi:
            return subj
    return "computer_networks"


def q_chapter(it):
    return it.get("chapter") or "zz_未标"


def phase_today():
    t = today()
    for date, name in SCRAMBLE_PHASES:
        if t <= date:
            return name
    return "random"


def active_subjects():
    """按天交替激活一对子轨(大科配小科，配平当日工作量)。"""
    idx = datetime.date.fromisoformat(today()).toordinal() % len(ROTATION)
    return ROTATION[idx]


def _subj_order(active):
    return active + [s for s in SUBJECTS if s not in active]


def _cluster(items, active):
    """按 科目(今日激活对在前)→章节→年份 聚类成组。"""
    order = _subj_order(active)
    return sorted(items, key=lambda it: (order.index(q_subject(it)),
                                         q_chapter(it), it["year"], it["q"]))


def _interleave(items):
    """科目内按章节聚类，科目之间 round-robin 交错。"""
    buckets = defaultdict(list)
    for it in items:
        buckets[q_subject(it)].append(it)
    queues = []
    for s in SUBJECTS:
        if buckets[s]:
            buckets[s].sort(key=lambda it: (q_chapter(it), it["year"], it["q"]))
            queues.append(deque(buckets[s]))
    out = []
    while queues:
        for dq in queues:
            out.append(dq.popleft())
        queues = [dq for dq in queues if dq]
    return out


def order_questions(items, phase, active):
    if phase == "blocked":
        return _cluster(items, active)          # 同章成组、每天两门
    if phase == "interleaved":
        return _interleave(items)               # 科目间交错
    random.Random(today()).shuffle(items)       # 完全随机跨章跨科=全真模拟
    return items


def build_today(state):
    """返回今日全量清单(含已做)：[{id,year,q,img,subject,chapter,status,ok}]。

    复习题(due)按遗忘曲线始终全出(retention 优先)；新题在 blocked/interleaved
    阶段只从今日激活科目对引入；最终顺序按阶段 分块→交错→随机 排列。
    """
    log = day_log(state)
    done = list(log["done"])
    done_set = set(done)
    t = today()
    phase = phase_today()
    active = active_subjects()

    due, fresh = [], []
    for qid, it in QUESTIONS.items():
        if qid in done_set:
            continue
        s = state.get(qid)
        if s:
            if s.get("due", "9999") <= t:
                due.append(it)
        else:
            fresh.append(it)

    # 新题配额
    remaining_new = max(0, NEW_PER_DAY - log["new"])
    if phase in ("blocked", "interleaved"):
        # 只从今日激活科目对引入，且在两门间均衡(round-robin)，保证每天两门都出
        pools = [deque(_cluster([it for it in fresh if q_subject(it) == s], active))
                 for s in active]
        new_today = []
        while len(new_today) < remaining_new and any(pools):
            for dq in pools:
                if dq and len(new_today) < remaining_new:
                    new_today.append(dq.popleft())
    else:
        pool = list(fresh)
        random.Random(today() + "f").shuffle(pool)
        new_today = pool[:remaining_new]

    pending = order_questions(due + new_today, phase, active)

    out = []
    for qid in done:
        it = QUESTIONS.get(qid)
        if it:
            ent = state.get(qid, {})
            out.append({**_pub(it), "status": "done", "ok": ent.get("last_ok", True)})
    for it in pending:
        out.append({**_pub(it), "status": "pending"})
    return out, log


# ── 历史回顾：每天题单存成 journal/YYYY-MM/MMDD.md，左右键翻看 ──
PHASE_CN = {"blocked": "分块期", "interleaved": "交错期", "random": "全真模拟"}
JROW = re.compile(r"^\|\s*(\d{4}-\d{2})\s*\|\s*(答对|答错|未答)\s*\|\s*([A-D]?)\s*\|")


def journal_path(date):
    """'YYYY-MM-DD' → journal/YYYY-MM/MMDD.md"""
    y, m, d = date.split("-")
    return JOURNAL / f"{y}-{m}" / f"{m}{d}.md"


def journal_date(f):
    """journal/2026-06/0617.md → '2026-06-17'"""
    return f"{f.parent.name}-{f.stem[2:]}"


def progress_days(state):
    """所有有记录的日期(升序)：journal 文件 ∪ 旧 _progress 键 ∪ 今天(最右实时页)。"""
    days = set(state.get("_progress", {}).keys())          # 兼容尚无 journal 的旧记录
    if JOURNAL.exists():
        days |= {journal_date(f) for f in JOURNAL.glob("*/*.md")}
    days.add(today())
    return sorted(days)


def day_nav(date, days):
    """在日期序列里给出 (前一天, 后一天)；越界为 ''。"""
    if date not in days:
        return "", ""
    i = days.index(date)
    return (days[i - 1] if i > 0 else "", days[i + 1] if i < len(days) - 1 else "")


def write_journal_today(state, items):
    """把今天的完整题单(含未答)写成 markdown 表，供回顾页与人肉翻阅。
    每次访问/判分后整文件重写——一天几十行，开销可忽略。"""
    log = day_log(state)
    answered = sum(1 for it in items if it.get("status") == "done")
    ok = sum(1 for it in items if it.get("status") == "done" and it.get("ok"))
    acc = round(ok / answered * 100) if answered else 0
    subj = " + ".join(SUBJECT_CN[s] for s in active_subjects())
    head = (f"# {today()} 做题记录\n\n"
            f"共 {len(items)} 题 · 答 {answered} · 对 {ok}（{acc}%）\n"
            f"{PHASE_CN[phase_today()]} · {subj}\n\n"
            "| 年份·题号 | 状态 | 选 |\n|---|---|---|\n")
    rows = []
    for it in items:
        st = ("答对" if it.get("ok") else "答错") if it.get("status") == "done" else "未答"
        pick = state.get(it["id"], {}).get("last_pick") or ""
        rows.append(f"| {it['id']} | {st} | {pick} |")
    p = journal_path(today())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(head + "\n".join(rows) + "\n", encoding="utf-8")


def refresh_journal(state):
    """用当前状态重算今天题单并落盘 journal。/api/today 与判分后各调一次。"""
    items, _ = build_today(state)
    write_journal_today(state, items)


def parse_journal(date):
    """读 journal/YYYY-MM/MMDD.md 的题行 → [(qid, 状态, 选项)]；无文件返回 None。"""
    p = journal_path(date)
    if not p.exists():
        return None
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        m = JROW.match(line.strip())
        if m:
            out.append((m.group(1), m.group(2), m.group(3)))
    return out


def build_day(state, date):
    """只读回顾历史某天：当天完整题单(答对/答错/未答) + 小结 + 前后导航。"""
    days = progress_days(state)
    prev, nxt = day_nav(date, days)
    base = {"date": date, "isToday": date == today(), "prev": prev, "next": nxt}
    rows = parse_journal(date)
    if rows is None:
        return _build_day_legacy(state, date, base)        # 旧记录无 journal 文件
    items, done, okn = [], 0, 0
    for qid, st, pick in rows:
        it = QUESTIONS.get(qid)
        if not it:
            continue
        if st == "未答":
            items.append({**_pub(it), "status": "pending"})
        else:
            ok = st == "答对"
            done += 1; okn += 1 if ok else 0
            d = {**_pub(it), "status": "done", "ok": ok}
            if pick:
                d["pick"] = pick
            items.append(d)
    return {**base, "exists": bool(items), "items": items,
            "total": len(items), "done": done, "ok": okn}


def _build_day_legacy(state, date, base):
    """向后兼容：journal 出现前、只在 _progress 里留过痕迹的日子(回退到答过的题)。"""
    log = state.get("_progress", {}).get(date)
    if not log:
        return {**base, "exists": False, "items": [], "total": 0, "done": 0, "ok": 0}
    res = log.get("res", {})
    items = []
    for qid in log.get("done", []):
        it = QUESTIONS.get(qid)
        if it:
            ok = res.get(qid, state.get(qid, {}).get("last_ok", True))
            items.append({**_pub(it), "status": "done", "ok": ok})
    okn = sum(1 for x in items if x.get("ok"))
    return {**base, "exists": bool(items), "items": items,
            "total": len(items), "done": len(items), "ok": okn}


def _pub(it):
    """对外不暴露答案。带上科目/章节供前端分组显示。"""
    return {"id": it["id"], "year": it["year"], "q": it["q"], "img": it["img"],
            "dispW": NORM.get(it["id"]),
            "subject": q_subject(it), "subjectCN": SUBJECT_CN[q_subject(it)],
            "chapter": q_chapter(it)}


# ── 战况诊断：今日小结 / 弱项 / 错题本 / 冲刺预测分 ──────────
def pretty_ch(ch):
    if not ch or ch.startswith("zz"):
        return "未标章节"
    return re.sub(r"^ch\d+_", "", ch)


# 408 各科满分(选择+综合)，用于冲刺预测分
EXAM_POINTS = {"data_structures": 45, "computer_organization": 45,
               "operating_systems": 35, "computer_networks": 25}


def build_stats(state):
    t = today()
    log = state.get("_progress", {}).get(t, {"done": [], "ok": 0})

    # ① 今日小结：今日错题按 科目·章节 计数
    tw = Counter()
    for qid in log.get("done", []):
        s = state.get(qid, {})
        it = QUESTIONS.get(qid)
        if it and not s.get("last_ok", True):
            tw[f"{SUBJECT_CN[q_subject(it)]}·{pretty_ch(q_chapter(it))}"] += 1
    done = len(log.get("done", []))
    today_summary = {"done": done, "ok": log.get("ok", 0),
                     "acc": round(log.get("ok", 0) / done * 100) if done else 0,
                     "wrong": [{"label": k, "n": n} for k, n in tw.most_common()]}

    # 累积聚合(全历史)：按 科目·章节 与 科目
    ch_agg = defaultdict(lambda: {"seen": 0, "right": 0})
    subj_agg = defaultdict(lambda: {"seen": 0, "right": 0})
    mistakes, stuck = [], []
    for qid, it in QUESTIONS.items():
        s = state.get(qid)
        if not s or not s.get("seen"):
            continue
        subj, ch = q_subject(it), q_chapter(it)
        ck = (SUBJECT_CN[subj], pretty_ch(ch))
        ch_agg[ck]["seen"] += s["seen"]; ch_agg[ck]["right"] += s.get("right", 0)
        subj_agg[subj]["seen"] += s["seen"]; subj_agg[subj]["right"] += s.get("right", 0)
        if s.get("stuck"):                  # ⓪ 待解清单：手动标"没懂"，持久不清
            stuck.append({**_pub(it), "pick": s.get("last_pick")})
        if not s.get("last_ok", True):      # ③ 错题本：最近一次做错
            mistakes.append(_pub(it))

    # ② 弱项诊断：章节正确率升序(最弱在前)
    weak = [{"subject": s, "chapter": c, "seen": v["seen"],
             "acc": round(v["right"] / v["seen"] * 100)}
            for (s, c), v in ch_agg.items()]
    weak.sort(key=lambda w: (w["acc"], -w["seen"]))

    mistakes.sort(key=lambda m: (m["subjectCN"], m["chapter"], m["year"], m["q"]))
    stuck.sort(key=lambda m: (m["subjectCN"], m["chapter"], m["year"], m["q"]))

    # ④ 冲刺预测分：各科正确率 × 满分，求和(粗估，仅基于选择题表现)
    by_subj, total = [], 0.0
    for subj, pts in EXAM_POINTS.items():
        v = subj_agg.get(subj, {"seen": 0, "right": 0})
        acc = v["right"] / v["seen"] if v["seen"] else 0
        total += acc * pts
        by_subj.append({"subject": SUBJECT_CN[subj], "points": pts,
                        "acc": round(acc * 100) if v["seen"] else None,
                        "score": round(acc * pts, 1), "seen": v["seen"]})
    projection = {"total": round(total), "full": sum(EXAM_POINTS.values()),
                  "target": 120, "by_subject": by_subj}

    return {"today": today_summary, "weak": weak, "stuck": stuck,
            "mistakes": mistakes, "projection": projection}


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
    if pick:
        s["last_pick"] = pick        # 记下选了哪个干扰项，供拷打扎具体错念
    state[qid] = s
    log = day_log(state)
    if qid not in log["done"]:
        log["done"].append(qid)
        if correct:
            log["ok"] += 1
        if is_new:
            log["new"] += 1
    save_state(state)
    refresh_journal(state)        # 把这次作答落进当天 journal(回顾页真相源)
    return {"known": True, "correct": correct, "answer": ans}


def mark_stuck(state, qid, stuck):
    """标"没懂"→进持久待解清单(只堆不清,不强制通关)；"搞懂了"→撤下。"""
    s = state.get(qid)
    if s is None:
        return {"error": "not graded yet"}
    if stuck:
        s["stuck"] = True
    else:
        s.pop("stuck", None)
    state[qid] = s
    save_state(state)
    return {"ok": True, "stuck": bool(s.get("stuck"))}


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
            write_journal_today(state, items)    # 落盘当天完整题单(含未答)，供回顾页/人肉翻阅
            phase = phase_today()
            prev, nxt = day_nav(today(), progress_days(state))
            return self._send(200, {
                "dday": dday(), "examDate": EXAM_DATE, "newPerDay": NEW_PER_DAY,
                "items": items,
                "done": len(log["done"]), "ok": log["ok"],
                "today": today(), "prev": prev, "next": nxt,
                "phase": phase,
                "phaseCN": {"blocked": "分块期", "interleaved": "交错期",
                            "random": "全真模拟"}[phase],
                "subjects": [SUBJECT_CN[s] for s in active_subjects()],
            })
        if path == "/api/day":
            date = (parse_qs(urlparse(self.path).query).get("d") or [""])[0]
            return self._send(200, build_day(load_state(), date))
        if path == "/api/stats":
            return self._send(200, build_stats(load_state()))
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
        if self.path == "/api/stuck":
            state = load_state()
            res = mark_stuck(state, data.get("id"), data.get("stuck"))
            return self._send(200, res)
        return self._send(404, {"error": "not found"})


def main():
    print(f"408 studio · http://127.0.0.1:{PORT}  （题库 {len(QUESTIONS)} 题，距考试 {dday()} 天）")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()


if __name__ == "__main__":
    main()
