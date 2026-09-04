#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
plist="$HOME/Library/LaunchAgents/com.shadowlearn.app.plist"
zonos_plist="$HOME/Library/LaunchAgents/com.shadowlearn.zonos2.plist"
mkdir -p "$HOME/Library/LaunchAgents"

sed \
  -e "s|__PROJECT_DIR__|$project_dir|g" \
  -e "s|__HOME__|$HOME|g" \
  "$project_dir/deploy/com.shadowlearn.app.plist.template" > "$plist"

launchctl bootout "gui/$(id -u)/com.shadowlearn.app" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$plist"
launchctl enable "gui/$(id -u)/com.shadowlearn.app"
echo "Installed Shadow Learn service at $plist"

# ZONOS2 is intentionally not a launchd service. The app starts its local
# Metal server only for a ZONOS generation and shuts it down afterwards.
launchctl bootout "gui/$(id -u)/com.shadowlearn.zonos2" 2>/dev/null || true
rm -f "$zonos_plist"
echo "ZONOS2 is configured for on-demand use only"
