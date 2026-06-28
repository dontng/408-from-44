#!/bin/bash
# autopull.sh — 定期从 origin/main 拉取，避免手动 pull 冲突
#
# 策略：git pull --rebase --autostash
#   --rebase    : 把本地提交变基到远端之上，不产生 merge commit
#   --autostash : 自动 stash/unstash 工作区脏文件
# 效果：远端有新提交时，本地提交自动"接续"上去，不产生冲突。
#
# Usage:
#   bash tools/autopull.sh            # 拉一次就退出
#
# 建议配合 crontab，每 30 分钟自动触发：
#   */30 * * * * bash /home/djology/408-from-44/tools/autopull.sh

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$REPO_DIR/.autopull.log"
LOCK_FILE="$REPO_DIR/.autopull.lock"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

git_is_busy() {
    [[ -f "$REPO_DIR/.git/index.lock" ]] \
        || [[ -f "$REPO_DIR/.git/MERGE_HEAD" ]] \
        || [[ -f "$REPO_DIR/.git/rebase-merge" ]]
}

do_pull() {
    cd "$REPO_DIR"

    if git_is_busy; then
        log "Git 正忙（手动操作进行中）— 跳过本次"
        return 0
    fi

    local out rc=0
    out=$(git pull --rebase --autostash origin main 2>&1) || rc=$?

    if (( rc != 0 )); then
        log "ERROR: pull --rebase 失败 (exit $rc)"
        echo "$out" >> "$LOG_FILE"
        # 若 rebase 留下了中间状态，自动中止，保持仓库干净
        if [[ -f "$REPO_DIR/.git/rebase-merge" ]] || [[ -f "$REPO_DIR/.git/rebase-apply" ]]; then
            git rebase --abort 2>>"$LOG_FILE" && log "rebase 已中止，仓库恢复干净"
        fi
        return 1
    fi

    if grep -q 'Already up to date\.' <<< "$out"; then
        : # 已是最新，静默
    else
        log "已拉取新提交："
        echo "$out" >> "$LOG_FILE"
    fi
}

# 单实例：flock 保护，防止与 autocommit.sh 并发
(
    flock -n 9 || { log "另一个实例正在运行 — 跳过"; exit 0; }
    do_pull
) 9>"$LOCK_FILE"
