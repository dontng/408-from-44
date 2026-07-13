#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

day="${1:-$(date +%m%d)}"
mode="${2:-auto}"
python3 tools/select_today.py --date "$day" --mode "$mode"

echo
echo "答题卡服务：bash answer.sh $day"
echo "答题卡地址：http://127.0.0.1:8409/?date=$day"
