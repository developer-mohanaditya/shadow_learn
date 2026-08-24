#!/bin/zsh
set -euo pipefail

if ! command -v tailscale >/dev/null; then
  echo "Install and sign in to Tailscale first: https://tailscale.com/download/mac" >&2
  exit 1
fi
tailscale serve --bg http://127.0.0.1:8420
tailscale serve status

