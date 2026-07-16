#!/bin/bash
# 每日 02:00 与 20:00 的 Git 恢复安全网。
# 由 tools/setup-git-safety-net.sh 安装 crontab。仅在工作区有未提交改动时
# 创建一个完整 checkpoint；失败时保留本地状态并记日志，等待下次执行。

set -u -o pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$REPO_DIR/.autocommit.log"
# 与 autopull.sh 共用锁，避免整点同时 fetch/rebase/push。
LOCK_FILE="$REPO_DIR/.autopull.lock"

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

prune_log() {
    python3 - "$LOG_FILE" <<'PY'
import datetime as dt
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit
cutoff = dt.datetime.now() - dt.timedelta(days=7)
kept = []
for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
    if len(line) >= 21 and line[0] == "[" and line[20] == "]":
        try:
            if dt.datetime.strptime(line[1:20], "%Y-%m-%d %H:%M:%S") >= cutoff:
                kept.append(line)
            continue
        except ValueError:
            pass
    if kept:
        kept.append(line)
path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
PY
}

git_is_busy() {
    [[ -e "$REPO_DIR/.git/index.lock" ]] \
        || [[ -e "$REPO_DIR/.git/MERGE_HEAD" ]] \
        || [[ -d "$REPO_DIR/.git/rebase-merge" ]] \
        || [[ -d "$REPO_DIR/.git/rebase-apply" ]]
}

checkpoint() {
    cd "$REPO_DIR" || return 1
    if git_is_busy; then
        log "git 正忙；跳过，本地改动保留到下一次安全网"
        return 0
    fi

    if [[ -z "$(git status --porcelain)" ]]; then
        log "工作区干净；无需创建恢复点"
        return 0
    fi

    git add -A || { log "ERROR: git add 失败；改动仍在工作区"; return 1; }
    if git diff --cached --quiet; then
        log "没有可提交的非忽略改动"
        return 0
    fi

    local stamp message
    stamp="$(date '+%Y-%m-%d %H:%M')"
    message=$(mktemp)
    trap 'rm -f "$message"' RETURN
    cat >"$message" <<EOF
checkpoint: scheduled recovery $stamp

Implemented:
- captured all non-ignored worktree changes in the scheduled recovery checkpoint

Why:
- preserve current work for recovery from another machine after the daytime or overnight session

Verified:
- git status detected pending changes before staging; push is attempted after rebase
EOF
    if ! git commit -F "$message"; then
        log "ERROR: checkpoint 提交失败；改动仍保留在本地"
        return 1
    fi
    log "已创建本地恢复点"

    if ! git fetch origin main; then
        log "ERROR: fetch 失败；恢复点已留在本地，下一次重试推送"
        return 1
    fi
    if ! git rebase origin/main; then
        log "ERROR: rebase 失败；恢复点已留在本地，未丢失"
        git rebase --abort >/dev/null 2>&1 || true
        return 1
    fi
    if ! git push origin main; then
        log "ERROR: push 失败；恢复点已留在本地，下一次重试推送"
        return 1
    fi
    log "已推送恢复点"
}

(
    flock -n 9 || { log "另一个 Git 同步任务正在运行；跳过"; exit 0; }
    prune_log
    checkpoint
) 9>"$LOCK_FILE"
