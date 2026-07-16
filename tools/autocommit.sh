#!/bin/bash
# 每日 02:00 与 20:00 的 Git 恢复安全网。
# 由 tools/setup-git-safety-net.sh 安装 crontab。仅在工作区有未提交改动时
# 且连续 10 分钟无活动时创建完整 checkpoint；失败时保留本地状态并记日志。

set -u -o pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$REPO_DIR/.autocommit.log"
# 与 autopull.sh 共用锁，避免整点同时 fetch/rebase/push。
LOCK_FILE="$REPO_DIR/.autopull.lock"
ACTIVITY_FILE="$REPO_DIR/.git-safety-net.active"
QUIET_SECONDS="${QUIET_SECONDS:-600}"
RECHECK_SECONDS="${RECHECK_SECONDS:-120}"

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

has_changes() {
    cd "$REPO_DIR" || return 1
    [[ -n "$(git status --porcelain)" ]]
}

latest_activity() {
    local latest=0 stamp path
    if [[ -e "$ACTIVITY_FILE" ]]; then
        latest=$(stat -c %Y "$ACTIVITY_FILE")
    fi
    while IFS= read -r -d '' path; do
        [[ -e "$REPO_DIR/$path" ]] || continue
        stamp=$(stat -c %Y "$REPO_DIR/$path")
        (( stamp > latest )) && latest=$stamp
    done < <(cd "$REPO_DIR" && git ls-files -m -o --exclude-standard -z)
    printf '%s\n' "$latest"
}

project_is_active() {
    local now latest
    now=$(date +%s)
    latest=$(latest_activity)
    (( latest > 0 && now - latest < QUIET_SECONDS ))
}

wait_until_idle() {
    while has_changes; do
        if ! project_is_active; then
            return 0
        fi
        log "项目仍在活动；${RECHECK_SECONDS} 秒后重查"
        sleep "$RECHECK_SECONDS"
    done
    log "工作区已恢复干净；无需创建恢复点"
    return 1
}

checkpoint() {
    cd "$REPO_DIR" || return 1
    if git_is_busy; then
        log "git 正忙；继续等待"
        return 77
    fi

    if ! has_changes; then
        log "工作区干净；无需创建恢复点"
        return 0
    fi

    if [[ "${SAFETY_NET_DRY_RUN:-0}" == "1" ]]; then
        log "DRY RUN: 工作区空闲且有改动；此时会创建恢复点"
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

run_when_idle() {
    while true; do
        wait_until_idle || return 0
        (
            flock -n 9 || exit 75
            if project_is_active; then
                exit 76
            fi
            checkpoint
        ) 9>"$LOCK_FILE"
        case $? in
            0) return 0 ;;
            75) log "另一个 Git 同步任务正在运行；${RECHECK_SECONDS} 秒后重查" ;;
            76) log "项目恢复活动；继续等待空闲" ;;
            77) log "Git 操作结束后继续重查" ;;
            *) return 1 ;;
        esac
        sleep "$RECHECK_SECONDS"
    done
}

prune_log
run_when_idle
