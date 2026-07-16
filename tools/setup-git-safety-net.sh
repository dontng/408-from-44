#!/bin/bash
# Install one predictable recovery checkpoint schedule without touching other cron jobs.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MARKER="# 408-from-44 git safety net"
ENTRY="0 2,20 * * * bash $REPO_DIR/tools/autocommit.sh $MARKER"

existing="$(crontab -l 2>/dev/null || true)"
filtered="$(printf '%s\n' "$existing" | grep -F -v "$MARKER" || true)"
printf '%s\n%s\n' "$filtered" "$ENTRY" | crontab -
printf 'Installed Git safety net: 02:00 and 20:00 local time.\n'
