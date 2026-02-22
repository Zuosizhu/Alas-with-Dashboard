#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

git config core.hooksPath .githooks
chmod +x .githooks/pre-push .githooks/pre-commit

echo "Installed repo-tracked hooks."
echo "core.hooksPath=$(git config --get core.hooksPath)"
