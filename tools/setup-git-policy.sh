#!/usr/bin/env bash
set -euo pipefail

git config core.hooksPath .githooks
git config commit.template .gitmessage
echo "Enabled .githooks/commit-msg and .gitmessage for $(git rev-parse --show-toplevel)."
