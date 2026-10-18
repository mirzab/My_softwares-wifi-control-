#!/usr/bin/env bash
set -euo pipefail
rm -rf "${HOME}/.local/share/wifi-control"
rm -f "${HOME}/.local/bin/wifi-control"
rm -f "${HOME}/.local/share/applications/wifi-control.desktop"
rm -f "${HOME}/.local/share/icons/hicolor/256x256/apps/wifi-control.png"
echo "Wi-Fi Control removed. System NetworkManager/GTK packages were not changed."
