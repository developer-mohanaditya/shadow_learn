#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
cd "$project_dir/frontend"
npm run build
cd "$project_dir"
uv run python -m pytest

