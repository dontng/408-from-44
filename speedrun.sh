#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" == "--check" ]]; then
  date_key="${2:-$(date +%m%d)}"
  python3 tools/check_speedrun.py --date "$date_key"
else
  date_key="${1:-$(date +%m%d)}"
  python3 tools/new_speedrun.py --date "$date_key"
fi
