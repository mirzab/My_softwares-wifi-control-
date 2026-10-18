#!/usr/bin/env bash
set -euo pipefail

APP_NAME="wifi-control"
INSTALL_DIR="${HOME}/.local/share/${APP_NAME}"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_APP="${SOURCE_DIR}/wifi_control.py"
SOURCE_ICON="${SOURCE_DIR}/wifi-control.png"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"

if [[ ! -f "$SOURCE_APP" ]]; then
  echo "Error: wifi_control.py must be in the same folder as install.sh." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it with: sudo apt install python3" >&2
  exit 1
fi
if ! command -v nmcli >/dev/null 2>&1; then
  echo "NetworkManager's nmcli is required. Install it with: sudo apt install network-manager" >&2
  exit 1
fi
if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
  echo "Tkinter is missing. Install it with: sudo apt install python3-tk" >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR"
install -m 755 "$SOURCE_APP" "$INSTALL_DIR/wifi_control.py"
if [[ -f "$SOURCE_ICON" ]]; then
  install -m 644 "$SOURCE_ICON" "$INSTALL_DIR/wifi-control.png"
  mkdir -p "$ICON_DIR"
  install -m 644 "$SOURCE_ICON" "$ICON_DIR/wifi-control.png"
fi

cat > "$BIN_DIR/wifi-control" <<EOF
#!/usr/bin/env bash
exec /usr/bin/python3 "$INSTALL_DIR/wifi_control.py" "\$@"
EOF
chmod 755 "$BIN_DIR/wifi-control"

cat > "$DESKTOP_DIR/wifi-control.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Wi-Fi Control
Comment=Turn Wi-Fi on or off and manage wireless networks
Exec=$BIN_DIR/wifi-control
Icon=wifi-control
Terminal=false
Categories=Network;Settings;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_DIR/wifi-control.desktop"

echo
echo "Wi-Fi Control installed."
echo "Launch it from the Mint menu by searching for: Wi-Fi Control"
echo "Or run: $BIN_DIR/wifi-control"
echo
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "Note: $BIN_DIR is not in PATH for this terminal. The app-menu launcher still works."
fi
