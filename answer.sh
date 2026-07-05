#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
date_key="${1:-$(date +%m%d)}"
python3 tools/answer.py "$PWD" 8409 "$date_key"
