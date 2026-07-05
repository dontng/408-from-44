#!/usr/bin/env python3
"""Commit and push the small set of files needed by the daily workflow."""
import argparse
import datetime as dt
import os
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LOGS = [REPO / ".sync.log", REPO / ".autopull.log", REPO / ".autocommit.log"]
SYNC_PATHS = [
    ".gitignore",
    "AGENTS.md",
    "README.md",
    "STATUS.md",
    "coach",
    "data",
    "docs",
    "src",
    "today.sh",
    "answer",
    "answer.sh",
    "tools/answer.html",
    "tools/answer.py",
    "tools/autopull.sh",
    "tools/coach_mark.py",
    "tools/coach_next.py",
    "tools/grade_today.py",
    "tools/select_today.py",
    "tools/sync_now.py",
]


def run(cmd, check=True):
    return subprocess.run(cmd, cwd=REPO, text=True, capture_output=True, check=check)


def log(message):
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    path = REPO / ".sync.log"
    path.write_text(path.read_text(encoding="utf-8") + line + "\n" if path.exists() else line + "\n", encoding="utf-8")
    print(line)


def prune_log(path, days=7):
    if not path.exists():
        return
    cutoff = dt.datetime.now() - dt.timedelta(days=days)
    kept = []
    keep_current_block = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if len(line) >= 21 and line[0] == "[" and line[20] == "]":
            try:
                stamp = dt.datetime.strptime(line[1:20], "%Y-%m-%d %H:%M:%S")
                keep_current_block = stamp >= cutoff
                if keep_current_block:
                    kept.append(line)
                continue
            except ValueError:
                pass
        if keep_current_block:
            kept.append(line)
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def prune_logs():
    for path in LOGS:
        prune_log(path)


def git_busy():
    return any((REPO / p).exists() for p in [".git/index.lock", ".git/MERGE_HEAD", ".git/rebase-merge", ".git/rebase-apply"])


def has_sync_changes():
    cmd = ["git", "status", "--porcelain", "--"] + SYNC_PATHS
    out = run(cmd).stdout.strip()
    return bool(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("message", nargs="*", default=["sync workflow state"])
    args = parser.parse_args()
    message = " ".join(args.message).strip() or "sync workflow state"

    prune_logs()
    if os.environ.get("SKIP_SYNC") == "1":
        log(f"SKIP_SYNC=1, skip sync: {message}")
        return
    if git_busy():
        log("git busy, skip sync")
        return
    if not has_sync_changes():
        log(f"no sync changes: {message}")
        return

    run(["git", "add", "--"] + SYNC_PATHS)
    diff = run(["git", "diff", "--cached", "--quiet"], check=False)
    if diff.returncode == 0:
        log(f"nothing staged: {message}")
        return

    run(["git", "commit", "-m", message])
    fetch = run(["git", "fetch", "origin", "main"], check=False)
    if fetch.returncode != 0:
        log("fetch failed; commit kept locally")
        log(fetch.stderr.strip())
        return
    rebase = run(["git", "rebase", "--autostash", "origin/main"], check=False)
    if rebase.returncode != 0:
        log("rebase failed; aborting")
        run(["git", "rebase", "--abort"], check=False)
        log(rebase.stderr.strip())
        return
    push = run(["git", "push", "origin", "main"], check=False)
    if push.returncode != 0:
        log("push failed")
        log(push.stderr.strip())
        return
    log(f"pushed: {message}")
    prune_logs()


if __name__ == "__main__":
    main()
