#!/bin/bash
# 自动提交 review/ 和 sessions/ 的进度变更，防止白天忙忘了 push
# 由 crontab 每 2 小时触发，仅在有改动时才 commit

set -e
cd "$(dirname "$0")/.."

# 只关心这两个目录
if git diff --quiet review/ sessions/ 2>/dev/null; then
  exit 0  # 没改动，跳过
fi

git add review/ sessions/
git commit -m "auto: 进度自动提交 $(date '+%m/%d %H:%M')" || exit 0
git push origin main
