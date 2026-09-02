#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
export SHADOW_LEARN_HOST="127.0.0.1"
export SHADOW_LEARN_PORT="8421"
export SHADOW_LEARN_DATA="$project_dir/data-v2"
export SHADOW_LEARN_BREEZE_MODEL="$project_dir/data-v2/models/vireo-mixed4bit"
export SHADOW_LEARN_BREEZE_PYTHON="$project_dir/.engines/breeze/bin/python"
export BREEZE_AUDIO_TOKENIZER="$project_dir/data-v2/models/breeze-upstream/audio_tokenizer"

cd "$project_dir"
exec .venv/bin/shadow-learn
