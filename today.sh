#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

day="${1:-$(date +%m%d)}"
python3 tools/show_question_node.py --date "$day"
