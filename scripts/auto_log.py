#!/usr/bin/env python3
"""
Stop hook: 检测新 commit，重建 logs/sessions.txt
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_DIR   = Path(__file__).parent.parent
DATA_FILE  = REPO_DIR / '.log_entries'       # 内部数据，tab 分隔，newest first
DISPLAY    = REPO_DIR / 'logs' / 'sessions.txt'
STATE_FILE = REPO_DIR / '.last_logged_commit'
PIN_COUNT = 3
HDR_WIDTH = 52  # total width of section headers

MONTHS = {
    '01': 'january',  '02': 'february', '03': 'march',    '04': 'april',
    '05': 'may',      '06': 'june',     '07': 'july',     '08': 'august',
    '09': 'september','10': 'october',  '11': 'november', '12': 'december',
}


def hdr(label):
    inner = f' {label} '
    stars = HDR_WIDTH - 2 - len(inner)
    if stars % 2 != 0:
        stars += 1  # 保证左右各半，总宽最多多 1
    half = stars // 2
    return '/' + '*' * half + inner + '*' * half + '/'

SUBJECT_MAP = {
    'operating_systems':    'OS',
    'data_structures':      'DS',
    'computer_organization':'CO',
    'computer_networks':    'CN',
}

SUBJECT_KEYWORDS = [
    (['操作系统', ' OS', 'os '], 'OS'),
    (['数据结构', ' DS', 'ds '], 'DS'),
    (['组成原理', '计算机组成'],  'CO'),
    (['计算机网络', '网络'],      'CN'),
]

TASK_KEYWORDS = [
    (['OCR', '纠错', '修复'],           'ocr-fix'),
    (['提取', '新增'],                   'extract'),
    (['重组', '重命名', '整理', '目录'], 'reorg'),
    (['复习', '练习', '刷题'],           'review'),
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_DIR).stdout.strip()


def get_new_commits():
    last = STATE_FILE.read_text().strip() if STATE_FILE.exists() else ''
    if last:
        out = run(['git', 'log', '--format=%H\t%s', f'{last}..HEAD'])
    else:
        out = run(['git', 'log', '--format=%H\t%s', '-10'])
    if not out:
        return []
    rows = [line.split('\t', 1) for line in out.splitlines() if '\t' in line]
    return list(reversed(rows))  # 时间正序


def get_subject(commit_hash, msg):
    files = run(['git', 'diff-tree', '--no-commit-id', '-r', '--name-only', commit_hash]).splitlines()
    seen, subjects = set(), []
    for f in files:
        for key, abbr in SUBJECT_MAP.items():
            if key in f and abbr not in seen:
                subjects.append(abbr)
                seen.add(abbr)
    if subjects:
        return '+'.join(subjects)
    return next(
        (abbr for kws, abbr in SUBJECT_KEYWORDS if any(k in msg for k in kws)),
        '?'
    )


def get_task(msg):
    for keywords, label in TASK_KEYWORDS:
        if any(k in msg for k in keywords):
            return label
    return 'other'


def get_commit_time(commit_hash):
    raw = run(['git', 'log', '-1', '--format=%ai', commit_hash])
    try:
        dt = datetime.strptime(raw[:19], '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y/%m/%d %H:%M')
    except Exception:
        return datetime.now().strftime('%Y/%m/%d %H:%M')


def load_entries():
    if not DATA_FILE.exists():
        return []
    entries = []
    for line in DATA_FILE.read_text(encoding='utf-8').splitlines():
        parts = line.split('\t', 3)
        if len(parts) == 4:
            entries.append({'time': parts[0], 'subject': parts[1],
                            'task': parts[2], 'desc': parts[3]})
    return entries  # newest first


def save_entries(entries):
    lines = [f"{e['time']}\t{e['subject']}\t{e['task']}\t{e['desc']}" for e in entries]
    DATA_FILE.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def render(entries):
    chronological = list(reversed(entries))
    if len(chronological) <= PIN_COUNT:
        pinned, rest = chronological, []
    else:
        pinned = chronological[-PIN_COUNT:]
        rest   = chronological[:-PIN_COUNT]

    out = []

    out.append(hdr('pinned'))
    out.append('')
    for e in pinned:
        out.append(f"{e['time']}  {e['subject']}  {e['task']}")
        out.append(f"    {e['desc']}")
        out.append('')

    prev_month = None
    for e in rest:
        mm = e['time'][5:7]
        if mm != prev_month:
            out.append(hdr(f"log for {MONTHS[mm]}"))
            out.append('')
            prev_month = mm
        out.append(f"{e['time']}  {e['subject']}  {e['task']}")
        out.append(f"    {e['desc']}")
        out.append('')

    return '\n'.join(out)


def main():
    commits = get_new_commits()
    if not commits:
        return

    entries = load_entries()

    new_entries = []
    for commit_hash, msg in reversed(commits):  # newest first
        new_entries.append({
            'time':    get_commit_time(commit_hash),
            'subject': get_subject(commit_hash, msg),
            'task':    get_task(msg),
            'desc':    msg[:60] + ('…' if len(msg) > 60 else ''),
        })

    entries = new_entries + entries
    save_entries(entries)

    DISPLAY.parent.mkdir(exist_ok=True)
    DISPLAY.write_text(render(entries), encoding='utf-8')

    head = run(['git', 'rev-parse', 'HEAD'])
    STATE_FILE.write_text(head)
    print(f'[auto_log] {len(commits)} 条新记录', file=sys.stderr)


if __name__ == '__main__':
    main()
