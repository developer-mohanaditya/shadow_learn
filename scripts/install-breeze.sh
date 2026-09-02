#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
engine_dir="$project_dir/.engines/breeze"
model_dir="$project_dir/data-v2/models/vireo-mixed4bit"

mkdir -p "$project_dir/data-v2/models"
uv venv --python 3.12 "$engine_dir"
uv pip install --python "$engine_dir/bin/python" \
  "mlx>=0.32,<0.33" \
  "numpy>=2.0,<3" \
  "soundfile>=0.13,<0.15" \
  "transformers==4.57.3" \
  "huggingface-hub>=0.34,<1"
uv pip install --python "$engine_dir/bin/python" \
  "torch==2.9.1" \
  "torchaudio==2.9.1" \
  "qwen-tts==0.1.1"

hf download mchen04/Vireo-TTS-3B-MLX-mixed4bit --local-dir "$model_dir"
hf download BreezeBlue/Breeze-TTS-2 --include "audio_tokenizer/*" \
  --local-dir "$project_dir/data-v2/models/breeze-upstream"

echo "Breeze MLX runtime installed locally at $engine_dir"
echo "Vireo model downloaded locally at $model_dir"
echo "Breeze voice-cloning encoder downloaded locally under data-v2/models/breeze-upstream"
