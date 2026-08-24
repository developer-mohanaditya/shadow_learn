#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
engine="${1:-all}"
mkdir -p "$project_dir/.engines"

install_chatterbox() {
  uv venv --clear --python 3.11 "$project_dir/.engines/chatterbox"
  # Perth still imports pkg_resources, which setuptools 81+ removed.
  uv pip install --python "$project_dir/.engines/chatterbox/bin/python" numpy==1.26.4 "setuptools<81" wheel cython
  uv pip install --python "$project_dir/.engines/chatterbox/bin/python" pkuseg==0.0.25 --no-build-isolation
  uv pip install --python "$project_dir/.engines/chatterbox/bin/python" chatterbox-tts==0.1.4
  echo "export SHADOW_LEARN_CHATTERBOX_PYTHON='$project_dir/.engines/chatterbox/bin/python'"
}

install_kokoro() {
  uv venv --clear --python 3.11 "$project_dir/.engines/kokoro"
  uv pip install --python "$project_dir/.engines/kokoro/bin/python" kokoro-mlx soundfile
  uv pip install --python "$project_dir/.engines/kokoro/bin/python" \
    "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
  echo "export SHADOW_LEARN_KOKORO_PYTHON='$project_dir/.engines/kokoro/bin/python'"
}

install_zonos2() {
  local version="v0.5.1"
  local archive="zonos2-macos-arm64-metal.tar.gz"
  local expected_sha="ef88cdcde0ebf263c3b84f4ed5bebc18bb0b9431aa2825e6e6e14f711a9886f6"
  local target="$project_dir/.engines/zonos2"
  local download_dir
  local actual_sha
  download_dir="$(mktemp -d)"
  curl -L --fail --show-error \
    --output "$download_dir/$archive" \
    "https://github.com/Zyphra/zonos2.cpp/releases/download/$version/$archive"
  actual_sha="$(shasum -a 256 "$download_dir/$archive" | awk '{print $1}')"
  if [[ "$actual_sha" != "$expected_sha" ]]; then
    echo "ZONOS2 archive checksum mismatch" >&2
    exit 1
  fi
  mkdir -p "$target"
  tar -xzf "$download_dir/$archive" -C "$target"
  chmod +x "$target"/start-zonos2.sh "$target"/zonos2-server "$target"/zonos2-cli
  rm -r -- "$download_dir"
  echo "Installed ZONOS2 $version. Download its Q4_K model with:"
  echo "  $target/start-zonos2.sh --quant q4_k --gpu -y --no-browser"
}

case "$engine" in
  chatterbox) install_chatterbox ;;
  kokoro) install_kokoro ;;
  zonos2) install_zonos2 ;;
  all) install_chatterbox; install_kokoro; install_zonos2 ;;
  *) echo "Usage: $0 [chatterbox|kokoro|zonos2|all]" >&2; exit 2 ;;
esac
