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

if [[ -x "$project_dir/.engines/zonos2/zonos2-server" ]]; then
  sed -e "s|__PROJECT_DIR__|$project_dir|g" \
    "$project_dir/deploy/com.shadowlearn.zonos2.plist.template" > "$zonos_plist"
  launchctl bootout "gui/$(id -u)/com.shadowlearn.zonos2" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$zonos_plist"
  launchctl enable "gui/$(id -u)/com.shadowlearn.zonos2"
  echo "Installed ZONOS2 service at $zonos_plist"
fi
