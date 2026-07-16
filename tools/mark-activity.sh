#!/bin/bash
# Refresh the ignored heartbeat used by the scheduled Git safety net.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
touch "$REPO_DIR/.git-safety-net.active"
