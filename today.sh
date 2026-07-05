#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

day="${1:-$(date +%m%d)}"
python3 tools/select_today.py --date "$day"

echo
echo "答题卡服务：bash answer.sh"
echo "答题卡地址：http://127.0.0.1:8409/?date=$day"
